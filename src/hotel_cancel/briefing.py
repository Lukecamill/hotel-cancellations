"""S1 local-model briefing; strict factual validation and no sending capability."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.request import Request,urlopen
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[2]
GUEST='We are sorry for the disruption. Our team will discuss suitable alternatives with you.'
PROMPT='prompts/revenue-manager-v1.txt'
HOTELS=['City Hotel','Resort Hotel']


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def object_schema(properties):
    return dict(type='object',properties=properties,required=list(properties),additionalProperties=False)


NUMBER={'type':'number','minimum':0}
HOTEL_SCHEMA=object_schema({**{k:NUMBER for k in ['on_books','rooms_in_blocks','expected_releases','walk_probability','empty_room_cost_eur','proposed_q']},
                           'policy':{'type':'string'},'gate':{'type':'string','enum':['PASS','FAIL']}})
SCHEMA=object_schema({'batch_date':{'type':'string'},'arrival_night':{'type':'string'},'walk_cost_eur':NUMBER,
    'hotels':object_schema({h:HOTEL_SCHEMA for h in HOTELS}),
    'deposit_prepaid':{'type':['boolean','null']},
    'action':{'type':'string','enum':['hold_for_calibration_review','manager_review']},
    'guest_message':{'type':'string'},'human_approval_required':{'type':'boolean'}})


def expected(case):
    c=json.loads(json.dumps(case['context_pack'],allow_nan=False))
    return {**c,'deposit_prepaid':case.get('kb_facts',{}).get('deposit_prepaid'),
            'action':'hold_for_calibration_review' if any(h['gate']=='FAIL' for h in c['hotels'].values()) else 'manager_review',
            'guest_message':GUEST,'human_approval_required':True}


def parse_response(raw):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError('Duplicate JSON key')
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def evaluate(raw,case):
    from jsonschema import Draft202012Validator
    try:
        answer=parse_response(raw)
        errors=list(Draft202012Validator(SCHEMA).iter_errors(answer))
        if errors:return dict(schema_valid=False,numeric_exact=False,grounded=False,accepted=False,error='schema')
    except (ValueError,TypeError):return dict(schema_valid=False,numeric_exact=False,grounded=False,accepted=False,error='invalid JSON')
    target=expected(case)
    numeric=answer['walk_cost_eur']==target['walk_cost_eur'] and all(
        answer['hotels'][h][k]==target['hotels'][h][k] for h in HOTELS for k in HOTEL_SCHEMA['properties'] if k not in ['policy','gate'])
    grounded=answer==target
    return dict(schema_valid=True,numeric_exact=numeric,grounded=grounded,accepted=grounded,error=None if grounded else 'factual or approval mismatch')


def render(raw,case):
    """Only accepted content is displayed; failed output is never repaired silently."""
    if not evaluate(raw,case)['accepted']:raise ValueError('Briefing withheld: model response failed validation')
    a=parse_response(raw)
    lines=[f"AI-generated simulation — arrival {a['arrival_night']} (as of {a['batch_date']})"]
    for hotel,r in a['hotels'].items():
        lines.append(f"{hotel}: {r['on_books']} on-book booking units; expected releases {r['expected_releases']}; proposed extra rooms {r['proposed_q']}; walking probability {r['walk_probability']}; gate {r['gate']}.")
    lines.extend([a['action'].replace('_',' ')+'. No operational approval.',
      'Deposit prepaid: '+('unknown' if a['deposit_prepaid'] is None else str(a['deposit_prepaid'])),
      'Unsent guest draft — human approval required: '+a['guest_message']])
    return '\n'.join(lines)+'\n'


def request(case,settings):
    base=settings['base_url'].rstrip('/')
    # This baseline deliberately forbids accidentally routing data to cloud endpoints.
    u=urlparse(base)
    if u.scheme!='http' or u.hostname not in ['localhost','127.0.0.1','::1'] or u.username or u.password:
        raise ValueError('Local baseline requires a loopback HTTP endpoint')
    body=dict(model=settings['model'],temperature=settings['temperature'],max_tokens=settings['max_tokens'],seed=3217,
       messages=[dict(role='system',content=(ROOT/PROMPT).read_text()),dict(role='user',content=json.dumps(case,allow_nan=False))],
       response_format=dict(type='json_schema',json_schema=dict(name='manager_briefing',strict=True,schema=SCHEMA)))
    headers={'Content-Type':'application/json'}
    key=os.environ.get(settings['api_key_env'],'')
    if key:headers['Authorization']='Bearer '+key
    start=time.perf_counter()
    with urlopen(Request(base+'/chat/completions',json.dumps(body).encode(),headers),timeout=300) as response:result=json.load(response)
    return dict(raw=result['choices'][0]['message']['content'],usage=result.get('usage',{}),
                latency_seconds=time.perf_counter()-start,finish_reason=result['choices'][0].get('finish_reason'))


def replay(path=None):
    fixtures=json.loads(Path(path or ROOT/'docs/evidence/stage13/responses.json').read_text())
    if fixtures['prompt_sha256']!=hashlib.sha256((ROOT/PROMPT).read_bytes()).hexdigest():raise ValueError('Prompt changed; re-record live run')
    if fixtures['schema_sha256']!=digest(SCHEMA):raise ValueError('Schema changed; re-record live run')
    import yaml
    settings=yaml.safe_load((ROOT/'config/config.yaml').read_text())['llm']
    if fixtures['settings']!=settings:raise ValueError('Model or decoding settings changed; re-record live run')
    if fixtures['model']['digest']!=settings['digest']:raise ValueError('Recorded model digest mismatch')
    cases=json.loads((ROOT/'config/stage13-golden.json').read_text())
    if fixtures['golden_sha256']!=digest(cases):raise ValueError('Context changed; re-record live run')
    results=[evaluate(r['raw'],r['case']) for r in fixtures['records']]
    if any(r['case']!=cases[r['case_id']] for r in fixtures['records']):raise ValueError('Fixture context mismatch')
    if len(fixtures['records'])!=len(cases) or set(r['case_id'] for r in fixtures['records'])!=set(cases):raise ValueError('Incomplete fixture coverage')
    if results!=[r['evaluation'] for r in fixtures['records']]:raise ValueError('Recorded scores differ on replay')
    return dict(records=len(results),accepted=sum(r['accepted'] for r in results),all_failures_withheld=True,
                fixture_regression_gate='PASS',model_quality_gate='PASS' if all(r['accepted'] for r in results) else 'FAIL',
                live_model_called=False,prompt_sha256=fixtures['prompt_sha256'])


def approve_guest_draft(raw,case,*,reviewer,reason,approved_digest):
    """Record review of this exact unsent text; deliberately no dispatch function."""
    if not evaluate(raw,case)['accepted']:raise ValueError('Cannot approve invalid briefing')
    text=parse_response(raw)['guest_message']
    binding=digest(dict(message=text,context=case))
    if approved_digest!=binding:raise ValueError('Draft/context changed or digest not explicitly approved')
    if not isinstance(reviewer,str) or len(reviewer.strip())<2 or not isinstance(reason,str) or len(reason.strip())<5:
        raise ValueError('Named human reviewer and meaningful reason required')
    from datetime import datetime,timezone
    return dict(reviewed_at=datetime.now(timezone.utc).isoformat(),reviewer=reviewer.strip(),reason=reason.strip(),draft_context_digest=binding,
                approved_for_manual_review=True,sent=False,production_authorized=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['record','replay']);p.add_argument('--require-model-pass',action='store_true');args=p.parse_args()
    if args.mode=='replay':
        result=replay();print(json.dumps(result,indent=2))
        if args.require_model_pass and result['model_quality_gate']!='PASS':raise SystemExit(1)
        return
    import yaml
    import numpy as np
    settings=yaml.safe_load((ROOT/'config/config.yaml').read_text())['llm']
    cases=json.loads((ROOT/'config/stage13-golden.json').read_text())
    out=ROOT/'docs/evidence/stage13';out.mkdir(parents=True,exist_ok=True)
    # Digest verification is local Ollama metadata, not a second inference endpoint.
    base=settings['base_url'].removesuffix('/v1')
    with urlopen(base+'/api/tags') as response:tags=json.load(response)
    metadata=next(m for m in tags['models'] if m['name']==settings['model'])
    if settings.get('digest')!=metadata['digest']:raise ValueError('Local model digest mismatch')
    records=[]
    for key,case in cases.items():
        result=request(case,settings);result.update(case_id=key,case=case,evaluation=evaluate(result['raw'],case));records.append(result)
        print(key,result['evaluation'],round(result['latency_seconds'],2),flush=True)
        (out/'partial-responses.json').write_text(json.dumps(records,indent=2)+'\n')
    fixture=dict(prompt_version='revenue-manager-v1',prompt_sha256=hashlib.sha256((ROOT/PROMPT).read_bytes()).hexdigest(),
       schema_sha256=digest(SCHEMA),golden_sha256=digest(cases),model=metadata,settings=settings,records=records)
    (out/'responses.json').write_text(json.dumps(fixture,indent=2)+'\n');(out/'partial-responses.json').unlink()
    groups={}
    for group in ['with_kb','without_kb','injection']:
        rs=[r for r in records if r['case_id'].startswith(group+'/')]
        groups[group]={k:sum(r['evaluation'][k] for r in rs) for k in ['schema_valid','numeric_exact','grounded','accepted']};groups[group]['n']=len(rs)
    report=dict(groups=groups,provider='local Ollama',base_url=settings['base_url'],model=metadata,
       prompt_version='revenue-manager-v1',prompt_sha256=fixture['prompt_sha256'],temperature=settings['temperature'],
       hardware=dict(chip='Apple M5',memory_gb=16,machine='MacBook Air',runtime='Ollama 0.40.16',quantization='Q4_K_M'),
       input_tokens=sum(r['usage'].get('prompt_tokens',0) for r in records),output_tokens=sum(r['usage'].get('completion_tokens',0) for r in records),
       latency_p50_seconds=float(np.percentile([r['latency_seconds'] for r in records],50)),latency_p95_seconds=float(np.percentile([r['latency_seconds'] for r in records],95)),
       cost_per_1000_answers_eur=0,energy_cost_measured=False,production_authorized=False,
       semantic_contract='KB prepaid status or explicit null; no free-form semantic claims',
       exact_numeric_fields_per_night=13,recorded_requests=len(records),
       failures_withheld=sum(not r['evaluation']['accepted'] for r in records))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    for r in records:
        if r['evaluation']['accepted']:
            (out/'example-briefing.txt').write_text(render(r['raw'],r['case']));break
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
