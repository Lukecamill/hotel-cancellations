"""Verify Stage 9 tracking in Ubuntu without changing the Stage 7 service."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
os.chdir(root)
assert platform.system()=='Linux', 'Run this script inside Ubuntu'
expected=json.loads((root/'config/stage9-run-inventory.json').read_text())
for group,folder in [('source_sha256','src/hotel_cancel'),('test_sha256','tests')]:
    actual={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/folder).glob('*.py'))}
    assert actual==expected[group], f'{folder}: files differ from the prepared Stage 9 inventory'
protected=[root/'compose.yaml', *list((root/'models/serving').glob('*'))]
before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
with tempfile.TemporaryDirectory(prefix='hotel-stage9-check-') as tmp:
    ctx=Path(tmp)
    shutil.copy2(root/'requirements-tracking.txt',ctx/'requirements-tracking.txt')
    (ctx/'Dockerfile').write_text('''FROM hotel-cancel:stage8-check
USER root
COPY requirements-tracking.txt /tmp/requirements-tracking.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements-tracking.txt
USER hotel
''')
    subprocess.run(['docker','build','-t','hotel-cancel:stage9-check',str(ctx)],check=True)
out=root/'docs/evidence/stage9-ubuntu'
out.mkdir(parents=True,exist_ok=True)
base=['docker','run','--rm','--user',f'{os.getuid()}:{os.getgid()}',
      '-e','PYTHONPATH=/project/src','-e','MPLCONFIGDIR=/tmp/matplotlib',
      '-e','MLFLOW_DISABLE_TELEMETRY=true','-e','MLFLOW_DISABLE_AGENT_HINT=true',
      '-e','DATASETS_TASKS_DATA=/project/data','-e','MODEL_DIR=/project/models',
      '-v',f'{root}:/project','-w','/project','hotel-cancel:stage9-check']
def capture(args,name):
    p=subprocess.Popen(base+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    lines=[]
    for line in p.stdout:
        print(line,end='',flush=True);lines.append(line)
    code=p.wait();text=''.join(lines)
    (out/name).write_text(text)
    return code,text
collection_code='''import json,pytest
from pathlib import Path
class Inventory:
 def pytest_collection_finish(self,session):
  Path('/project/docs/evidence/stage9-ubuntu/test-inventory.json').write_text(json.dumps({'nodeids':[i.nodeid for i in session.items]},indent=2)+'\\n')
raise SystemExit(pytest.main(['--collect-only','-q'],plugins=[Inventory()]))
'''
code,_=capture(['python','-c',collection_code],'collection.txt')
assert code==0
actual=json.loads((out/'test-inventory.json').read_text())['nodeids']
assert actual==expected['nodeids'], 'Mac/Ubuntu collected tests differ'
code,text=capture(['make','ci','PYTHON=python'],'ci.txt')
summary=re.search(r'(\d+) passed(?:, (\d+) skipped)?',text)
assert summary and int(summary[1])==expected['expected_passed_without_database'] and ' failed' not in text
assert code!=0, 'The known-failing Resort must still block make ci'
gate=json.loads((root/'docs/evidence/stage8/report.json').read_text())
assert gate['identity_verified'] and gate['hotels']['City Hotel']['gate']=='PASS'
assert gate['hotels']['Resort Hotel']['checks']['calibration_ratio'] is False
code,_=capture(['python','-m','hotel_cancel.tracking','--output','docs/evidence/stage9-ubuntu',
                '--store','artifacts/stage9-ubuntu'],'tracking.txt')
assert code==0,'MLflow tracking/readback failed; inspect tracking.txt'
tracked=json.loads((out/'verification.json').read_text())
assert 'champion' in tracked['models']['City Hotel']['aliases']
assert 'champion' not in tracked['models']['Resort Hotel']['aliases']
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest for name,digest in before.items())
image=json.loads(subprocess.check_output(['docker','image','inspect','hotel-cancel:stage9-check'],text=True))[0]
result=dict(status='VERIFIED',environment='Linux ARM64 container on Ubuntu VM',
            test_files_and_python_sources_identical=True,collected_tests=len(actual),
            tests_passed=int(summary[1]),tests_skipped=int(summary[2] or 0),
            make_ci_expected_quality_failure=True,mlflow_readback_verified=True,
            all_holdout_probabilities_identical=True,serving_and_compose_unchanged=True,
            city_champion=True,resort_champion_withheld=True,
            mlflow_version=tracked['mlflow_version'],image_id=image['Id'],architecture=image['Architecture'])
(out/'ubuntu-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('\nSTAGE9_UBUNTU_VERIFIED\n'+json.dumps(result,indent=2))
