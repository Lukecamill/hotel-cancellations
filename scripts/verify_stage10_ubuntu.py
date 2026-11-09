"""Verify Stage 10 RDF, ablations and grounding in the existing Ubuntu check image."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess

root=Path(__file__).resolve().parents[1];os.chdir(root)
assert platform.system()=='Linux','Run inside Ubuntu, not on the Mac'
expected=json.loads((root/'config/stage10-run-inventory.json').read_text())
for group,folder,pattern in [('source_sha256','src/hotel_cancel','*.py'),('test_sha256','tests','*.py'),('knowledge_sha256','knowledge','**/*')]:
    actual={str(p.relative_to(root/folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/folder).glob(pattern)) if p.is_file()}
    assert actual==expected[group], f'{folder} differs from the prepared Stage 10 inventory'
protected=[root/'compose.yaml', *list((root/'models/serving').glob('*')),
           *list((root/'artifacts/stage9-ubuntu').glob('mlflow.db'))]
before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
out=root/'docs/evidence/stage10-ubuntu';out.mkdir(parents=True,exist_ok=True)
base=['docker','run','--rm','--user',f'{os.getuid()}:{os.getgid()}',
      '-e','PYTHONPATH=/project/src','-e','MPLCONFIGDIR=/tmp/matplotlib',
      '-e','MLFLOW_DISABLE_TELEMETRY=true','-e','MLFLOW_DISABLE_AGENT_HINT=true',
      '-e','DATASETS_TASKS_DATA=/project/data','-e','MODEL_DIR=/project/models',
      '-v',f'{root}:/project','-w','/project','hotel-cancel:stage9-check']
def capture(args,name):
    process=subprocess.Popen(base+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    lines=[]
    for line in process.stdout: print(line,end='',flush=True);lines.append(line)
    code=process.wait();text=''.join(lines);(out/name).write_text(text);return code,text
collection='''import json,pytest
from pathlib import Path
class Inventory:
 def pytest_collection_finish(self,session):
  Path('/project/docs/evidence/stage10-ubuntu/test-inventory.json').write_text(json.dumps({'nodeids':[i.nodeid for i in session.items]},indent=2)+'\\n')
raise SystemExit(pytest.main(['--collect-only','-q'],plugins=[Inventory()]))
'''
code,_=capture(['python','-c',collection],'collection.txt');assert code==0
actual=json.loads((out/'test-inventory.json').read_text())['nodeids'];assert actual==expected['nodeids'],'Collected tests differ'
for path in [out/'shacl/report.json',out/'quality-gate/report.json']:
    path.unlink(missing_ok=True)
code,text=capture(['make','ci','PYTHON=python','QUALITY_OUTPUT=docs/evidence/stage10-ubuntu/quality-gate','KB_OUTPUT=docs/evidence/stage10-ubuntu/shacl'],'ci.txt')
summary=re.search(r'(\d+) passed(?:, (\d+) skipped)?',text)
assert summary and int(summary[1])==expected['expected_passed_without_database'] and ' failed' not in text
assert code!=0 and 'Quality gate: FAIL;' in text,'Expected Resort quality failure was not reached'
shacl=json.loads((out/'shacl/report.json').read_text());assert shacl['conforms']
gate=json.loads((out/'quality-gate/report.json').read_text())
assert gate['identity_verified'] and gate['hotels']['City Hotel']['gate']=='PASS'
assert gate['hotels']['Resort Hotel']['checks']['calibration_ratio'] is False
code,_=capture(['python','-m','hotel_cancel.kb_ablation','--output','docs/evidence/stage10-ubuntu/ablation'],'ablation.txt');assert code==0
code,_=capture(['python','-m','hotel_cancel.kb_briefing_eval','--output','docs/evidence/stage10-ubuntu/briefing'],'briefing.txt');assert code==0
ablation=json.loads((out/'ablation/verification.json').read_text());assert ablation['status']=='VERIFIED'
brief=json.loads((out/'briefing/report.json').read_text());assert brief['status']=='VERIFIED'
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest for name,digest in before.items())
image=json.loads(subprocess.check_output(['docker','image','inspect','hotel-cancel:stage9-check'],text=True))[0]
result=dict(status='VERIFIED',environment='Linux container on Ubuntu VM',
            source_test_knowledge_files_identical=True,collected_tests=len(actual),
            tests_passed=int(summary[1]),tests_skipped=int(summary[2] or 0),
            extended_shacl_conforms=True,reference_triples=ablation['reference_triples'],extended_triples=ablation['extended_triples'],
            notebook_ablation_reproduced=True,cold_reference_metrics_match=ablation['cold_reference_metrics_match'],
            cold_renamed_bookings=ablation['cold_renamed_bookings'],
            briefing_golden_cases=brief['reports']['codes + temporal KB']['cases'],
            briefing_unsupported_claims=brief['reports']['codes + temporal KB']['unsupported_semantic_claims'],
            briefing_scope='deterministic grounding contract, no LLM execution',
            serving_and_compose_unchanged=True,registry_unchanged=True,
            make_ci_expected_resort_calibration_failure=True,image_id=image['Id'],architecture=image['Architecture'])
(out/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('\nSTAGE10_UBUNTU_VERIFIED\n'+json.dumps(result,indent=2))
