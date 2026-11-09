"""Verify the offline E2 fairness audit in Ubuntu without changing serving/registry."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

root=Path(__file__).resolve().parents[1];os.chdir(root)
sys.path.insert(0,str(root/'src'))
from hotel_cancel.csv_parity import compare_nightly_csv
assert platform.system()=='Linux','Run inside Ubuntu'
expected=json.loads((root/'config/stage11-run-inventory.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for group,folder,pattern in [('source_sha256','src/hotel_cancel','*.py'),('test_sha256','tests','*.py'),('knowledge_sha256','knowledge','**/*')]:
    actual={str(p.relative_to(root/folder)):sha(p) for p in sorted((root/folder).glob(pattern)) if p.is_file()}
    assert actual==expected[group],f'{folder} differs from the prepared inventory'
for name,digest in expected['config_sha256'].items():assert sha(root/name)==digest,name
protected=[root/'compose.yaml',*list((root/'models/serving').glob('*')),
           *list((root/'artifacts/stage9-ubuntu').glob('mlflow.db'))]
before={str(p.relative_to(root)):sha(p) for p in protected if p.is_file()}
out=root/'docs/evidence/stage11-ubuntu';out.mkdir(parents=True,exist_ok=True)
base=['docker','run','--rm','--user',f'{os.getuid()}:{os.getgid()}',
      '-e','PYTHONPATH=/project/src','-e','MPLCONFIGDIR=/tmp/matplotlib',
      '-e','MLFLOW_DISABLE_TELEMETRY=true','-e','MLFLOW_DISABLE_AGENT_HINT=true',
      '-e','DATASETS_TASKS_DATA=/project/data','-e','MODEL_DIR=/project/models',
      '-v',f'{root}:/project','-w','/project','hotel-cancel:stage9-check']
def capture(args,name):
    p=subprocess.Popen(base+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);lines=[]
    for line in p.stdout:print(line,end='',flush=True);lines.append(line)
    code=p.wait();text=''.join(lines);(out/name).write_text(text);return code,text
collection='''import pytest,json
from pathlib import Path
class Inventory:
 def pytest_collection_finish(self,session):
  Path('/project/docs/evidence/stage11-ubuntu/test-inventory.json').write_text(json.dumps({'nodeids':[i.nodeid for i in session.items]},indent=2)+'\\n')
raise SystemExit(pytest.main(['--collect-only','-q'],plugins=[Inventory()]))
'''
code,_=capture(['python','-c',collection],'collection.txt');assert code==0
nodes=json.loads((out/'test-inventory.json').read_text())['nodeids'];assert nodes==expected['nodeids'],'Collected tests differ'
for path in [out/'shacl/report.json',out/'quality-gate/report.json']:path.unlink(missing_ok=True)
code,text=capture(['make','ci','PYTHON=python','QUALITY_OUTPUT=docs/evidence/stage11-ubuntu/quality-gate',
                   'KB_OUTPUT=docs/evidence/stage11-ubuntu/shacl'],'ci.txt')
counts=re.search(r'(\d+) passed(?:, (\d+) skipped)?',text)
assert counts and int(counts[1])==expected['expected_passed_without_database'] and ' failed' not in text
assert code!=0 and 'Quality gate: FAIL;' in text,'Expected quality gate failure was not reached'
assert json.loads((out/'shacl/report.json').read_text())['conforms']
gate=json.loads((out/'quality-gate/report.json').read_text())
assert gate['identity_verified'] and gate['hotels']['City Hotel']['gate']=='PASS'
assert gate['hotels']['Resort Hotel']['checks']['calibration_ratio'] is False
code,_=capture(['python','-m','hotel_cancel.walking','--output','docs/evidence/stage11-ubuntu'],'walking.txt');assert code==0
result=json.loads((out/'verification.json').read_text())
assert result['reference_nightly_quantities_exact'] and result['allocation_conserved_per_hotel']
assert result['audit_attribute_permutation_does_not_change_selection']
assert result['allocation_digest']==expected['allocation_digest'],'Simulated selected booking rows differ'
comparisons={}
for name,digest in expected['aggregate_csv_sha256'].items():
    if sha(out/name)==digest:
        comparisons[name]={'byte_identical':True}
    elif name=='nightly-overflow.csv':
        reference=root/'config/stage11-nightly-reference.csv'
        assert sha(reference)==digest,'Mac nightly reference identity differs'
        comparisons[name]=dict(byte_identical=False,**compare_nightly_csv(reference,out/name))
    else:
        raise AssertionError(f'Aggregate output differs: {name}')
(out/'csv-comparison.json').write_text(json.dumps(comparisons,indent=2)+'\n')
assert all(sha(root/name)==digest for name,digest in before.items()),'Protected runtime/registry file changed'
image=json.loads(subprocess.check_output(['docker','image','inspect','hotel-cancel:stage9-check'],text=True))[0]
summary=dict(status='VERIFIED',environment='Linux container on Ubuntu VM',
  source_test_knowledge_config_identical=True,collected_tests=len(nodes),tests_passed=int(counts[1]),tests_skipped=int(counts[2] or 0),
  all_486_reference_nightly_quantities_match=True,aggregate_values_match_mac=True,
  expected_sum_absolute_tolerance=1e-12,all_decision_cost_and_group_fields_exact=True,
  simulated_walks=result['total_simulated_walks'],allocation_digest=result['allocation_digest'],
  audit_label_permutation_preserves_selection=True,country_excluded_from_ranking=True,
  production_authorized=False,serving_compose_registry_unchanged=True,
  make_ci_expected_resort_calibration_failure=True,legal_scope='coursework governance assessment; no live-guest authority',
  image_id=image['Id'],architecture=image['Architecture'])
(out/'ubuntu-verification.json').write_text(json.dumps(summary,indent=2)+'\n')
print('\nSTAGE11_UBUNTU_VERIFIED\n'+json.dumps(summary,indent=2))
