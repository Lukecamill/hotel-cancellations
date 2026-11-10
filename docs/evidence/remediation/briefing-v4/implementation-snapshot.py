"""Versioned prompt-v2 regression plus disjoint-calendar local evaluation."""
import argparse,hashlib,json
from pathlib import Path
from urllib.request import urlopen
import numpy as np
import yaml
from hotel_cancel.briefing import ROOT,SCHEMA,GUEST,digest,evaluate,request,render
PROMPT='prompts/revenue-manager-v4.txt'
OUT=ROOT/'docs/evidence/remediation/briefing-v4'

def source_schema(case):
    schema=json.loads(json.dumps(SCHEMA))
    for key in ['batch_date','arrival_night']:schema['properties'][key]['enum']=[case['context_pack'][key]]
    for hotel,row in case['context_pack']['hotels'].items():
        for field in ['policy','gate']:schema['properties']['hotels']['properties'][hotel]['properties'][field]['enum']=[row[field]]
    schema['properties']['guest_message']['enum']=[GUEST]
    schema['properties']['human_approval_required']['enum']=[True]
    return schema


def cases():
 old=json.loads((ROOT/'config/stage13-golden.json').read_text())
 new=json.loads((ROOT/'config/briefing-v4-golden.json').read_text())
 result={'regression/'+k.split('/',1)[1]:v for k,v in old.items() if k.startswith('with_kb/')}
 result.update(new)
 assert len(result)==96
 a={v['context_pack']['arrival_night'] for k,v in result.items() if k.startswith('regression/')}
 b={v['context_pack']['arrival_night'] for k,v in result.items() if k.startswith('with_kb/')}
 assert len(a)==len(b)==30 and not a&b
 return result

def replay():
 f=json.loads((OUT/'responses.json').read_text());c=cases()
 settings=yaml.safe_load((ROOT/'config/config.yaml').read_text())['llm']
 if f['prompt_sha256']!=hashlib.sha256((ROOT/PROMPT).read_bytes()).hexdigest() or f['schema_sha256']!=digest(SCHEMA) or f['cases_sha256']!=digest(c):raise ValueError('Prompt/schema/context changed; re-record')
 if f['settings']!=settings or f['model']['digest']!=settings['digest']:raise ValueError('Model/settings changed')
 if len(f['records'])!=len(c) or {r['case_id'] for r in f['records']}!=set(c):raise ValueError('Incomplete recording')
 evaluations=[]
 for r in f['records']:
  if r['case']!=c[r['case_id']]:raise ValueError('Fixture case mismatch')
  if r['decoder_schema_sha256']!=digest(source_schema(r['case'])):raise ValueError('Decoder schema changed')
  e=evaluate(r['raw'],r['case'])
  if e!=r['evaluation']:raise ValueError('Score regression')
  evaluations.append(e)
 return dict(records=len(evaluations),accepted=sum(e['accepted'] for e in evaluations),
  fixture_regression_gate='PASS',model_quality_gate='PASS' if all(e['accepted'] for e in evaluations) else 'FAIL',
  live_model_called=False,original_v1_evidence_preserved=True)

def record():
 OUT.mkdir(parents=True,exist_ok=True);c=cases()
 settings=yaml.safe_load((ROOT/'config/config.yaml').read_text())['llm']
 with urlopen(settings['base_url'].removesuffix('/v1')+'/api/tags') as response:tags=json.load(response)
 metadata=next(m for m in tags['models'] if m['name']==settings['model'])
 if metadata['digest']!=settings['digest']:raise ValueError('Model digest mismatch')
 provenance=dict(prompt_version='revenue-manager-v4',prompt_sha256=hashlib.sha256((ROOT/PROMPT).read_bytes()).hexdigest(),
  schema_sha256=digest(SCHEMA),cases_sha256=digest(c),model=metadata,settings=settings,
  design='v4 uses source-enumerated dates, policy/gate strings and guest/approval constants during decoding. All 13 numeric fields remain unconstrained and independently evaluated. Original 30 are regression; new 30 exclude every v1/v3 planned date. v2/v3 failures retained.; 30 old nights are regression only. 30 different dates are new calendar evaluation; paired KB/no-KB plus six attacks. No retry or output repair.')
 (OUT/'prespecified-run.json').write_text(json.dumps(provenance,indent=2)+'\n')
 records=[]
 for key,case in c.items():
  result=request(case,settings,prompt_path=PROMPT,response_schema=source_schema(case));result['decoder_schema_sha256']=digest(source_schema(case));result.update(case_id=key,case=case,evaluation=evaluate(result['raw'],case));records.append(result)
  (OUT/'partial-responses.json').write_text(json.dumps(records,indent=2)+'\n')
  print(key,result['evaluation'],round(result['latency_seconds'],2),flush=True)
 (OUT/'responses.json').write_text(json.dumps(dict(provenance,records=records),indent=2)+'\n');(OUT/'partial-responses.json').unlink()
 groups={}
 for name in ['regression','with_kb','without_kb','injection']:
  rows=[r for r in records if r['case_id'].startswith(name+'/')]
  groups[name]=dict(n=len(rows),**{k:sum(r['evaluation'][k] for r in rows) for k in ['schema_valid','numeric_exact','grounded','accepted']})
 report=dict(provenance,groups=groups,quality_gate=replay()['model_quality_gate'],
  input_tokens=sum(r['usage'].get('prompt_tokens',0) for r in records),output_tokens=sum(r['usage'].get('completion_tokens',0) for r in records),
  latency_p50_seconds=float(np.percentile([r['latency_seconds'] for r in records],50)),latency_p95_seconds=float(np.percentile([r['latency_seconds'] for r in records],95)),
  cost_per_1000_answers_eur=0,hardware='Apple M5 MacBook Air 16 GB, Ollama 0.40.16, Q4_K_M',energy_measured=False,retries=0,production_authorized=False)
 (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 for r in records:
  if r['evaluation']['accepted'] and r['case_id'].startswith('with_kb/'):
   (OUT/'example-briefing.txt').write_text(render(r['raw'],r['case']));break
 print(json.dumps(report,indent=2))

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['record','replay']);a=p.parse_args()
 if a.mode=='record':record()
 else:
  result=replay();print(json.dumps(result,indent=2));return int(result['model_quality_gate']!='PASS')
if __name__=='__main__':raise SystemExit(main())
