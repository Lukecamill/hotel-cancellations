"""Notebook KB ablation and an explicit new-code stress test; offline only."""
import argparse
from importlib.metadata import version
import json
from pathlib import Path
import time
from urllib.parse import unquote

import numpy as np
import pandas as pd
from rdflib import Graph, RDF

from hotel_cancel.config import load_config
from hotel_cancel.evaluate import per_hotel
from hotel_cancel.features import build_features, select_top_agents, FEATURE_COLUMNS
from hotel_cancel.model import fit, model_parameters
from hotel_cancel.quality_gate import prepare, verify_identity, sha
from hotel_cancel.knowledge import KB_DIR, HB, PROV, KB_POLICY, KB_REGION, kb_features, validate_graph

ROOT=Path(__file__).resolve().parents[2]
NEW='Non Refund (new plan)'


def run(config,output):
    started=time.perf_counter();output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/'verification.json').unlink(missing_ok=True)
    reference=Graph().parse(KB_DIR/'reference.ttl',format='turtle')
    extended=Graph().parse(KB_DIR/'hotel.ttl',format='turtle')
    if not validate_graph(extended)[0]:raise ValueError('Extended graph fails SHACL')
    bk,X,y,masks,identity=prepare(config)
    lock=json.loads((ROOT/'config/evaluation-lock.json').read_text())
    verify_identity(identity,lock['identity'])
    reference_shapes=Graph().parse(KB_DIR/'reference-shapes.ttl',format='turtle')
    raw_ok,raw_report,raw_text,raw_violations=validate_graph(reference,reference_shapes)
    raw_report.serialize(output/'reference-shacl.ttl',format='turtle')
    (output/'reference-shacl.txt').write_text(raw_text)
    unique=sorted({(r['focus'],r['message']) for r in raw_violations})
    assert len(reference)==607 and not raw_ok and len(unique)==5
    Xk=kb_features(bk,X,reference)
    raw_country=X.copy()
    top_country=bk.loc[masks['train'],'country'].value_counts().index[:40]
    raw_country['country']=pd.Categorical(bk.country.astype(str).where(bk.country.isin(top_country),'other'))
    classes=[c for c in FEATURE_COLUMNS if c not in ['market_segment','distribution_channel','deposit_type']]+KB_POLICY
    specs={'codes only':(X,list(FEATURE_COLUMNS)),
           'codes + KB policy':(Xk,list(FEATURE_COLUMNS)+KB_POLICY),
           'KB classes instead of codes':(Xk,classes),
           'raw country (diagnostic only)':(raw_country,list(FEATURE_COLUMNS)+['country']),
           'KB region (diagnostic only)':(Xk,list(FEATURE_COLUMNS)+KB_REGION)}
    models={};results=[]
    for name,(frame,columns) in specs.items():
        # Exactly the supplied learner and training partition; only inputs differ.
        model=fit(columns,masks['train'],frame,y,seed=config['seed']);models[name]=model
        for split in ['valid','test']:
            metric=per_hotel(model.predict_proba(frame.loc[masks[split],columns])[:,1],masks[split],bk,y,config['hotels'])
            for hotel,row in metric.iterrows():results.append(dict(variant=name,split=split,hotel=hotel,**row.to_dict()))
    scores=pd.DataFrame(results);scores.to_csv(output/'ablation.csv',index=False)
    # Real new-code lookup: change raw codes, then rebuild both codes and RDF-derived features.
    cold=bk.copy();renamed=masks['test'] & cold.deposit_type.eq('Non Refund')
    cold['deposit_type']=cold.deposit_type.cat.add_categories([NEW]);cold.loc[renamed,'deposit_type']=NEW
    coldX=build_features(cold,select_top_agents(bk,masks['train']))
    coldXk=kb_features(cold,coldX,extended,temporal=True,as_of='2017-01-01')
    warmXk=kb_features(bk,X,extended,temporal=True,as_of='2017-01-01')
    # Prove the extension's policy features agree with the given mappings on existing codes.
    pd.testing.assert_frame_equal(warmXk[KB_POLICY],Xk[KB_POLICY])
    pd.testing.assert_frame_equal(coldXk.loc[masks['test'],classes],warmXk.loc[masks['test'],classes])
    cold_results=[]
    for name in ['codes only','codes + KB policy','KB classes instead of codes']:
        columns=specs[name][1];frame=coldX if name=='codes only' else coldXk
        pred=models[name].predict_proba(frame.loc[masks['test'],columns])[:,1]
        metric=per_hotel(pred,masks['test'],bk,y,config['hotels'])
        for hotel,row in metric.iterrows():cold_results.append(dict(variant=name,hotel=hotel,**row.to_dict()))
    cold_scores=pd.DataFrame(cold_results);cold_scores.to_csv(output/'cold-start.csv',index=False)
    plot_comparison(scores,cold_scores,config['hotels'],output)
    # Printed-reference tolerances were fixed by the earlier baseline precision.
    expected={'codes only':[(.786,.91),(.628,.68)],'codes + KB policy':[(.783,.91),(.632,.69)],
              'KB classes instead of codes':[(.783,.92),(.634,.69)],
              'raw country (diagnostic only)':[(.809,.80),(.628,.49)],
              'KB region (diagnostic only)':[(.806,.81),(.639,.50)]}
    checks=[]
    for name,values in expected.items():
        for hotel,(ap,ratio) in zip(config['hotels'],values):
            row=scores[(scores.variant==name)&(scores.split=='test')&(scores.hotel==hotel)].iloc[0]
            passed=abs(row['AUPRC']-ap)<=.0005 and abs(row['expected ÷ realised']-ratio)<=.005
            checks.append(dict(variant=name,hotel=hotel,reference_printed_metrics_match=bool(passed)))
    expected_cold={'codes only':[.595,.561],'codes + KB policy':[.684,.597],'KB classes instead of codes':[.783,.634]}
    cold_matches=[]
    for name,values in expected_cold.items():
        for hotel,ap in zip(config['hotels'],values):
            row=cold_scores[(cold_scores.variant==name)&(cold_scores.hotel==hotel)].iloc[0]
            cold_matches.append(bool(abs(row['AUPRC']-ap)<=.0005))
    verified=all(c['reference_printed_metrics_match'] for c in checks) and all(cold_matches)
    report=dict(status='VERIFIED' if verified else 'REFERENCE_MISMATCH',scope='offline notebook E1 reproduction; no serving promotion',
                identity=identity,reference_triples=len(reference),extended_triples=len(extended),
                reference_shacl_conforms=raw_ok,reference_distinct_violations=[dict(focus=f,message=m,bookings=int(bk[{'country':'country','segment':'market_segment','channel':'distribution_channel'}[f.split('#')[1].split('/')[0]]].astype(str).eq(unquote(f.split('/')[-1])).sum())) for f,m in unique],
                extended_shacl_conforms=True,reference_metrics_checks=checks,cold_reference_metrics_match=all(cold_matches),
                cold_renamed_bookings=int(renamed.sum()),cold_knowledge_date='2017-01-01',
                classes_cold_features_identical=True,model_parameters=model_parameters(config['seed']),
                fitted_on='train arrivals Jul 2015-Jun 2016 only',selected_on_holdout=False,
                tolerances=dict(printed_auprc_absolute=.0005,printed_ratio_absolute=.005),
                knowledge_sha256={p.name:sha(p) for p in sorted(KB_DIR.iterdir()) if p.is_file()},
                source_sha256={n:sha(Path(__file__).parent/n) for n in ['knowledge.py','kb_ablation.py','model.py','features.py']},
                packages={p:version(p) for p in ['pandas','lightgbm','scikit-learn','rdflib','pyshacl']},
                runtime_seconds=time.perf_counter()-started,
                limitations=['Region and raw-country models are diagnostic only; excluded from serving',
                             'Cold start renames existing held-out codes at evaluation time; not a natural launch cohort',
                             'Synthetic launch semantics are declared assumptions, not learned from outcomes',
                             'Repeated holdout comparisons are assignment diagnostics, not independent model selection'])
    (output/'verification.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    if not verified:raise ValueError('Notebook ablation differs from printed reference; inspect evidence')
    return report


def plot_comparison(scores,cold,hotels,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    variants=['codes only','codes + KB policy','KB classes instead of codes']
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,hotel in zip(axes,hotels):
        warm=[float(scores[(scores.variant==v)&(scores.split=='test')&(scores.hotel==hotel)]['AUPRC'].iloc[0]) for v in variants]
        stress=[float(cold[(cold.variant==v)&(cold.hotel==hotel)]['AUPRC'].iloc[0]) for v in variants]
        x=np.arange(3);ax.bar(x-.18,warm,.36,label='Existing codes');ax.bar(x+.18,stress,.36,label='Renamed plan code')
        ax.set_xticks(x,['Codes','Codes + KB','KB classes']);ax.set(title=hotel,ylim=(0,1),ylabel='Test AUPRC');ax.legend()
    fig.suptitle('Offline code-renaming stress test · fixed supplied learner')
    fig.tight_layout();fig.savefig(output/'cold-start-comparison.png',dpi=160);plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default=str(ROOT/'docs/evidence/stage10/ablation'))
    args=p.parse_args();r=run(load_config(),args.output);print(json.dumps(r,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
