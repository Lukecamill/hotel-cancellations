"""A separate booking-horizon calibration challenger; never replaces reference."""
import json
from pathlib import Path
import hashlib
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from hotel_cancel.config import load_config
from hotel_cancel.quality_gate import prepare,verify_identity,assess,plot_reliability,sha
from hotel_cancel.serving import Predictor
from hotel_cancel.policy import logit
from hotel_cancel.data import load_bookings,separate_outcome
ROOT=Path(__file__).resolve().parents[2]
PLAN=dict(method='Existing notebook LogisticRegression on clipped logit booking probabilities; Resort only',
 fit_start='2016-07-01',fit_end='2016-10-01',validation_end='2017-01-01',
 status_date_rule='Recorded status strictly before fit end',selection='Evaluate unchanged thresholds on Oct-Dec validation; inspect frozen test once only if candidate passes validation',
 no_learner_refit=True,no_policy_change=True,no_threshold_change=True,reference_gate_retained=True,
 limitation='Already exposed historical holdout; not a new pristine generalisation claim')

def fit_mask(arrival,status_date):
 return arrival.ge(pd.Timestamp(PLAN['fit_start'])) & arrival.lt(pd.Timestamp(PLAN['fit_end'])) & status_date.lt(pd.Timestamp(PLAN['fit_end']))

def fit_calibrator(p,y,arrival,status_date):
 if not p.index.equals(y.index) or not p.index.equals(arrival.index) or not p.index.equals(status_date.index):raise ValueError('Calibration inputs must align')
 mask=fit_mask(arrival,status_date)
 if len(np.unique(y.loc[mask]))!=2:raise ValueError('Calibration requires both classes')
 model=LogisticRegression().fit(logit(p.loc[mask]).to_frame('z'),y.loc[mask])
 if model.coef_[0,0]<=0:raise ValueError('Non-monotone calibrator not accepted')
 return model,mask

def apply_calibration(probabilities,hotels,artifact,*,base_model_sha256,horizon='booking_to_arrival'):
    p=np.asarray(probabilities,dtype=float);hotels=np.asarray(hotels)
    if p.ndim!=1 or hotels.shape!=p.shape or not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('Aligned finite booking probabilities required')
    if not set(hotels).issubset({'City Hotel','Resort Hotel'}):raise ValueError('Unknown hotel')
    if artifact['base_model_sha256']!=base_model_sha256 or artifact['horizon']!=horizon:raise ValueError('Model/horizon binding mismatch')
    if horizon!='booking_to_arrival' or artifact['hotel']!='Resort Hotel':raise ValueError('Booking-horizon Resort calibrator required')
    result=p.copy();mask=hotels=='Resort Hotel'
    if mask.any():result[mask]=artifact['calibrator'].predict_proba(logit(pd.Series(p[mask])).to_frame('z'))[:,1]
    return result


def verify_saved(output=None):
    report=json.loads((Path(output) if output else ROOT/'docs/evidence/remediation/calibration').joinpath('report.json').read_text())
    lock=json.loads((ROOT/'config/evaluation-lock.json').read_text())
    verify_identity(report['identity'],lock['identity'])
    if report['plan']!=PLAN or report['lock_sha256']!=sha(ROOT/'config/evaluation-lock.json'):raise ValueError('Calibration plan/lock changed')
    t=lock['thresholds']['Resort Hotel'];v=report['validation']['challenger']
    if not (v['auprc']>=t['min_auprc'] and t['ratio_band'][0]<=v['expected_observed_ratio']<=t['ratio_band'][1] and v['ece']<=t['max_ece']):raise ValueError('Calibration failed validation')
    artifact=ROOT/'artifacts/remediation/booking-calibrator.joblib'
    if sha(artifact)!=report['calibrator_sha256']:raise ValueError('Calibrator bytes changed')
    for hotel,value in report.get('hotels',{}).items():
        t=lock['thresholds'][hotel]
        if not (value['auprc']>=t['min_auprc'] and t['ratio_band'][0]<=value['expected_observed_ratio']<=t['ratio_band'][1] and value['ece']<=t['max_ece']):raise ValueError('Challenger fails numeric gate')
    if set(report.get('hotels',{}))!=set(lock['thresholds']):raise ValueError('Both hotels required')
    if report['validation']['challenger']['gate']!='PASS' or report['fit_latest_status_date'][:10]>=PLAN['fit_end']:raise ValueError('Invalid calibration provenance')
    for name,value in report['original_runtime_sha256'].items():
        if sha(ROOT/'models/serving'/name)!=value:raise ValueError('Original runtime changed')
    return dict(status='PASS',reference_baseline_changed=False,calibrated_challenger_only=True,production_authorized=False)


def run(output=None):
 out=Path(output) if output else ROOT/'docs/evidence/remediation/calibration';out.mkdir(parents=True,exist_ok=True)
 (out/'prespecified-plan.json').write_text(json.dumps(PLAN,indent=2)+'\n')
 config=load_config();bk,X,y,masks,identity=prepare(config)
 lock=json.loads((ROOT/'config/evaluation-lock.json').read_text());verify_identity(identity,lock['identity'])
 pred=Predictor(ROOT/'models/serving');before=pred.manifest['sha256']
 _,outcome=separate_outcome(load_bookings(config,use_cache=False))
 p=pd.Series(pred.bundle['model'].predict_proba(X)[:,1],index=X.index)
 resort=bk.hotel.astype(str).eq('Resort Hotel');ids=bk.index[resort]
 model,fit=fit_calibrator(p.loc[ids],y.loc[ids],bk.loc[ids,'arrival'],outcome.loc[ids,'status_date'])
 corrected=p.copy();corrected.loc[ids]=model.predict_proba(logit(p.loc[ids]).to_frame('z'))[:,1]
 validation=bk.arrival.ge(pd.Timestamp(PLAN['fit_end'])) & bk.arrival.lt(pd.Timestamp(PLAN['validation_end'])) & resort
 validation_result={name:assess(y.loc[validation],prob.loc[validation],**lock['thresholds']['Resort Hotel'])[0] for name,prob in [('reference',p),('challenger',corrected)]}
 result=dict(plan=PLAN,identity_verified=True,identity=identity,lock_sha256=sha(ROOT/'config/evaluation-lock.json'),fit_rows=int(fit.sum()),fit_latest_arrival=str(bk.loc[ids[fit],'arrival'].max()),
 fit_latest_status_date=str(outcome.loc[ids[fit],'status_date'].max()),coefficient=float(model.coef_[0,0]),intercept=float(model.intercept_[0]),
 validation=validation_result,holdout_evaluated=False,production_authorized=False,original_runtime_sha256=before)
 if validation_result['challenger']['gate']=='PASS':
  tables={};hotels={}
  for hotel in config['hotels']:
   mask=masks['test'] & bk.hotel.astype(str).eq(hotel)
   hotels[hotel],tables[hotel]=assess(y.loc[mask],corrected.loc[mask],**lock['thresholds'][hotel])
  result.update(holdout_evaluated=True,hotels=hotels,status='PASS' if all(v['gate']=='PASS' for v in hotels.values()) else 'FAIL')
  plot_reliability(tables,out)
 else:result['status']='VALIDATION_FAIL_NO_HOLDOUT_EVALUATION'
 artifact=ROOT/'artifacts/remediation';artifact.mkdir(parents=True,exist_ok=True)
 joblib.dump(dict(calibrator=model,hotel='Resort Hotel',horizon='booking_to_arrival',base_model_sha256=pred.version,plan=PLAN),artifact/'booking-calibrator.joblib')
 result['calibrator_sha256']=sha(artifact/'booking-calibrator.joblib')
 assert before=={n:sha(ROOT/'models/serving'/n) for n in before}
 (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('mode',nargs='?',choices=['run','verify'],default='run');parser.add_argument('--output');args=parser.parse_args()
 if args.mode=='run':run(args.output)
 else:print(json.dumps(verify_saved(args.output),indent=2))
