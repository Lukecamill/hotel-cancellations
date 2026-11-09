"""Verify E4 block reconstruction and RDF without changing serving or registry."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

root=Path(__file__).resolve().parents[1];os.chdir(root);sys.path.insert(0,str(root/'src'))
from hotel_cancel.csv_parity import compare_aggregate_table
assert platform.system()=='Linux','Run inside Ubuntu'
expected=json.loads((root/'config/stage12-run-inventory.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for key,folder,pattern in [('source_sha256','src/hotel_cancel','*.py'),('test_sha256','tests','*.py'),('knowledge_sha256','knowledge','**/*')]:
 actual={str(p.relative_to(root/folder)):sha(p) for p in sorted((root/folder).glob(pattern)) if p.is_file()}
 assert actual==expected[key],f'{folder} differs from prepared inventory'
for name,digest in expected['config_sha256'].items():assert sha(root/name)==digest,name
protected=[root/'compose.yaml',root/'knowledge/hotel.ttl',*list((root/'models/serving').glob('*')),
           *list((root/'artifacts/stage9-ubuntu').glob('mlflow.db'))]
before={str(p.relative_to(root)):sha(p) for p in protected if p.is_file()}
out=root/'docs/evidence/stage12-ubuntu';out.mkdir(parents=True,exist_ok=True)
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
  Path('/project/docs/evidence/stage12-ubuntu/test-inventory.json').write_text(json.dumps({'nodeids':[i.nodeid for i in session.items]},indent=2)+'\\n')
raise SystemExit(pytest.main(['--collect-only','-q'],plugins=[Inventory()]))
'''
code,_=capture(['python','-c',collection],'collection.txt');assert code==0
nodes=json.loads((out/'test-inventory.json').read_text())['nodeids'];assert nodes==expected['nodeids'],'Collected tests differ'
for path in [out/'shacl/report.json',out/'quality-gate/report.json',out/'verification.json']:path.unlink(missing_ok=True)
code,text=capture(['make','ci','PYTHON=python','QUALITY_OUTPUT=docs/evidence/stage12-ubuntu/quality-gate','KB_OUTPUT=docs/evidence/stage12-ubuntu/shacl'],'ci.txt')
counts=re.search(r'(\d+) passed(?:, (\d+) skipped)?',text)
assert counts and int(counts[1])==expected['expected_passed_without_database'] and ' failed' not in text
assert code!=0 and 'Quality gate: FAIL;' in text,'Expected quality gate failure not reached'
assert json.loads((out/'shacl/report.json').read_text())['conforms']
gate=json.loads((out/'quality-gate/report.json').read_text())
assert gate['identity_verified'] and gate['hotels']['City Hotel']['gate']=='PASS'
assert gate['hotels']['Resort Hotel']['checks']['calibration_ratio'] is False
code,_=capture(['python','-m','hotel_cancel.blocks','--output','docs/evidence/stage12-ubuntu'],'blocks.txt');assert code==0
result=json.loads((out/'verification.json').read_text())
assert result['reference_nightly_quantities_exact'] and result['covariance_reference_matches_original_q'] and result['generated_block_shacl_conforms']
assert result['stage11_allocation_digest']==expected['stage11_allocation_digest']
assert result['block_state_digest']==expected['block_state_digest'],'Block identities or reconstructed states differ'
reference=json.loads((root/'config/stage12-aggregate-reference.json').read_text())
comparison={name:compare_aggregate_table(table,out/name) for name,table in reference.items()}
(out/'csv-comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
assert all(sha(root/name)==digest for name,digest in before.items()),'Protected runtime/registry/core-KB file changed'
summary=dict(status='VERIFIED',environment='Linux container on Ubuntu VM',
 source_test_knowledge_config_identical=True,collected_tests=len(nodes),tests_passed=int(counts[1]),tests_skipped=int(counts[2] or 0),
 inferred_live_blocks=result['inferred_live_blocks'],multirow_blocks=result['multirow_blocks'],multirow_live_units=result['multirow_live_units'],
 complete_generated_block_shacl_conforms=True,reference_and_covariance_quantities_exact=True,
 stage11_allocation_preserved=True,block_identities_and_states_exact=True,aggregate_values_match_mac=True,all_counts_costs_labels_exact=True,diagnostic_ratio_tolerance=1e-12,
 serving_registry_core_kb_unchanged=True,production_authorized=False,make_ci_expected_resort_calibration_failure=True)
(out/'ubuntu-verification.json').write_text(json.dumps(summary,indent=2)+'\n')
print('\nSTAGE12_UBUNTU_VERIFIED\n'+json.dumps(summary,indent=2))
