"""Source-owned facts with local-model interpretation; no numeric output repair."""
import argparse,hashlib,json
from urllib.request import urlopen
import numpy as np
import yaml
from jsonschema import Draft202012Validator
from hotel_cancel.briefing import ROOT,SCHEMA,GUEST,digest,evaluate,request,render,parse_response,object_schema
PROMPT='prompts/revenue-manager-v5.txt'
OUT=ROOT/'docs/evidence/remediation/briefing-v5'
INTERPRETATION_SCHEMA=object_schema({
 'deposit_prepaid':{'type':['boolean','null']},
 'action':{'type':'string','enum':['hold_for_calibration_review','manager_review']},
 'guest_message':{'type':'string','enum':[GUEST]},
 'human_approval_required':{'type':'boolean','enum':[True]}})
CONTEXT_SCHEMA=object_schema({k:SCHEMA['properties'][k] for k in ['batch_date','arrival_night','walk_cost_eur','hotels']})

def compose(raw,case):
 """Only the trusted context owns numeric facts. Extra model facts are rejected."""
 interpretation=parse_response(raw)
 if list(Draft202012Validator(INTERPRETATION_SCHEMA).iter_errors(interpretation)):raise ValueError('Invalid interpretation; briefing withheld')
 context=case['context_pack']
 if list(Draft202012Validator(CONTEXT_SCHEMA).iter_errors(context)):raise ValueError('Invalid source context')
 return {**json.loads(json.dumps(context,allow_nan=False)),**interpretation}

def score(raw,case):
 try:
  output=compose(raw,case);result=evaluate(json.dumps(output,allow_nan=False),case)
 except (ValueError,TypeError):
  output=None;result=dict(schema_valid=False,numeric_exact=False,grounded=False,accepted=False,error='invalid interpretation or source context')
 return result,output

def deliver(raw,case):
    """Only this validated path returns a briefing to a caller. No output repair."""
    result,output=score(raw,case)
    if not result['accepted']:raise ValueError('Briefing withheld: ungrounded interpretation')
    return output

def generate(case,settings):
    response=request(case,settings,prompt_path=PROMPT,response_schema=INTERPRETATION_SCHEMA)
    return dict(briefing=deliver(response['raw'],case),usage=response.get('usage',{}),latency_seconds=response['latency_seconds'])


def component_acceptance(records):
    normal=[r for r in records if not r['case_id'].startswith('injection/')]
    attacks=[r for r in records if r['case_id'].startswith('injection/')]
    safe=0
    for r in attacks:
        try:
            output=deliver(r['raw'],r['case'])
            safe+=bool(evaluate(json.dumps(output),r['case'])['accepted'])
        except ValueError:safe+=1
    return dict(component_quality_gate='PASS' if all(r['evaluation']['accepted'] for r in normal) and safe==len(attacks) else 'FAIL',
                ordinary_accepted=sum(r['evaluation']['accepted'] for r in normal),ordinary_total=len(normal),
                injection_safe=safe,injection_total=len(attacks),injection_withheld=sum(not r['evaluation']['accepted'] for r in attacks))


def cases():
 old=json.loads((ROOT/'config/stage13-golden.json').read_text());new=json.loads((ROOT/'config/briefing-v5-golden.json').read_text())
 result={'regression/'+k.split('/',1)[1]:v for k,v in old.items() if k.startswith('with_kb/')};result.update(new);assert len(result)==96
 old_dates={v['context_pack']['arrival_night'] for k,v in result.items() if k.startswith('regression/')}
 new_dates={v['context_pack']['arrival_night'] for k,v in result.items() if k.startswith('with_kb/')}
 excluded=set(old_dates)
 for name in ['briefing-v2-golden.json','briefing-v4-golden.json']:
  excluded.update(v['context_pack']['arrival_night'] for k,v in json.loads((ROOT/'config'/name).read_text()).items() if k.startswith('with_kb/'))
 assert len(new_dates)==30 and not new_dates&excluded
 return result

def replay():
 f=json.loads((OUT/'responses.json').read_text());c=cases();settings=yaml.safe_load((ROOT/'config/config.yaml').read_text())['llm']
 if f['prompt_sha256']!=hashlib.sha256((ROOT/PROMPT).read_bytes()).hexdigest() or f['schema_sha256']!=digest(INTERPRETATION_SCHEMA) or f['cases_sha256']!=digest(c):raise ValueError('Prompt/schema/context changed; re-record')
 if f['settings']!=settings or f['model']['digest']!=settings['digest']:raise ValueError('Model/settings changed')
 if len(f['records'])!=len(c) or {r['case_id'] for r in f['records']}!=set(c):raise ValueError('Incomplete recording')
 evaluations=[]
 for r in f['records']:
  if r['case']!=c[r['case_id']]:raise ValueError('Case changed')
  e,output=score(r['raw'],r['case'])
  if e!=r['evaluation'] or output!=r['composed']:raise ValueError('Score regression')
  evaluations.append(e)
 return dict(**component_acceptance(f['records']),records=len(evaluations),accepted=sum(e['accepted'] for e in evaluations),fixture_regression_gate='PASS',
  raw_model_all_cases_gate='PASS' if all(e['accepted'] for e in evaluations) else 'FAIL',live_model_called=False,
  numeric_source='trusted context; never generated or repaired',raw_llm_numeric_copy_accuracy_claimed=False,original_v1_evidence_preserved=True)

def record():
 OUT.mkdir(parents=True,exist_ok=True);c=cases();settings=yaml.safe_load((ROOT/'config/config.yaml').read_text())['llm']
 with urlopen(settings['base_url'].removesuffix('/v1')+'/api/tags') as response:tags=json.load(response)
 metadata=next(m for m in tags['models'] if m['name']==settings['model'])
 if metadata['digest']!=settings['digest']:raise ValueError('Model digest mismatch')
 provenance=dict(prompt_version='revenue-manager-v5',prompt_sha256=hashlib.sha256((ROOT/PROMPT).read_bytes()).hexdigest(),
  schema_sha256=digest(INTERPRETATION_SCHEMA),cases_sha256=digest(c),model=metadata,settings=settings,
  design='Numerical facts are rendered from context by code. Local model generates interpretation only. No raw numerical-accuracy claim. New dates exclude every v1/v3/v4 planned date. Original 30 are regression.',
  original_failures_preserved=True,output_repairs=0,generation_retries=0)
 (OUT/'prespecified-run.json').write_text(json.dumps(provenance,indent=2)+'\n');records=[]
 for key,case in c.items():
  result=request(case,settings,prompt_path=PROMPT,response_schema=INTERPRETATION_SCHEMA)
  evaluation,composed=score(result['raw'],case);result.update(case_id=key,case=case,evaluation=evaluation,composed=composed);records.append(result)
  (OUT/'partial-responses.json').write_text(json.dumps(records,indent=2)+'\n');print(key,evaluation,round(result['latency_seconds'],2),flush=True)
 (OUT/'responses.json').write_text(json.dumps(dict(provenance,records=records),indent=2)+'\n');(OUT/'partial-responses.json').unlink()
 groups={}
 for group in ['regression','with_kb','without_kb','injection']:
  rows=[r for r in records if r['case_id'].startswith(group+'/')]
  groups[group]=dict(n=len(rows),**{k:sum(r['evaluation'][k] for r in rows) for k in ['schema_valid','numeric_exact','grounded','accepted']})
 report=dict(provenance,**component_acceptance(records),groups=groups,quality_gate=replay()['raw_model_all_cases_gate'],
  input_tokens=sum(r['usage'].get('prompt_tokens',0) for r in records),output_tokens=sum(r['usage'].get('completion_tokens',0) for r in records),
  latency_p50_seconds=float(np.percentile([r['latency_seconds'] for r in records],50)),latency_p95_seconds=float(np.percentile([r['latency_seconds'] for r in records],95)),
  cost_per_1000_answers_eur=0,hardware='Apple M5 MacBook Air 16 GB; Ollama 0.40.16 Q4_K_M',energy_measured=False,
  numerical_factuality_scope='Delivered briefing component; deterministic source facts, not raw model copying',production_authorized=False)
 (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 for r in records:
  if r['evaluation']['accepted'] and r['case_id'].startswith('with_kb/'):
   (OUT/'example-briefing.txt').write_text(render(json.dumps(r['composed']),r['case']));break
 print(json.dumps(report,indent=2))

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['record','replay']);a=p.parse_args()
 if a.mode=='record':record()
 else:
  result=replay();print(json.dumps(result,indent=2));return int(result['component_quality_gate']!='PASS')
if __name__=='__main__':raise SystemExit(main())
