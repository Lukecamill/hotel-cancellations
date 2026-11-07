"""Verify PostgreSQL snapshots and training parity in the built Linux image.

Run after container_smoke.py, with models/serving and artifacts/stage6/parity.json
prepared on the training machine. Reads the local Compose .env, never logs it.
"""
import hashlib
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from uuid import uuid4

root=Path(__file__).resolve().parents[1]
os.chdir(root)
settings=dict(line.split('=',1) for line in (root/'.env').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
env=dict(os.environ)
env['DATABASE_URL']='postgresql://hotel:'+settings['POSTGRES_PASSWORD']+'@127.0.0.1:5432/hotel'
code='''
import json
from pathlib import Path
import numpy as np
import psycopg
import os
from hotel_cancel.serving import Predictor
from hotel_cancel.snapshot import read_postgres,write_postgres
from hotel_cancel.batch import nightly_batch
p=Predictor('/models')
s=json.loads(Path('/evidence/snapshot.json').read_text())
url=os.environ['DATABASE_URL']
write_postgres(s,url);write_postgres(s,url)
loaded=read_postgres(s['snapshot_id'],url)
assert loaded==s
assert nightly_batch(loaded,p)==nightly_batch(s,p)
golden=json.loads(Path('/evidence/parity.json').read_text())
actual=p.predict(golden['bookings'])
error=float(np.max(np.abs(actual-np.array(golden['probabilities']))))
assert error<=1e-12
with psycopg.connect(url) as c:
 version=c.execute('SHOW server_version').fetchone()[0]
print(json.dumps(dict(status='passed',postgres_version=version,model_version=p.version,snapshot_id=s['snapshot_id'],
                     parity_bookings=len(actual),maximum_probability_difference=error,probability_absolute_tolerance=1e-12,
                     postgres_round_trip=True,idempotent_insert=True,file_postgres_batch_identical=True)))
'''
command=['docker','run','--rm','-i','--network','host','--read-only','--tmpfs','/tmp',
         '-v',f'{root}/models/serving:/models:ro','-v',f'{root}/artifacts/stage6:/evidence:ro',
         '-e','DATABASE_URL','hotel-cancel:stage6','python','-']
result=subprocess.run(command,input=code,text=True,capture_output=True,env=env,check=True)
report=json.loads(result.stdout)
report['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'src/hotel_cancel').glob('*.py') if not p.name.startswith('.')}
report['docker_version']=subprocess.check_output(['docker','version','--format','{{.Server.Version}}'],text=True).strip()
report['compose_version']=subprocess.check_output(['docker','compose','version','--short'],text=True).strip()
image=json.loads(subprocess.check_output(['docker','image','inspect','hotel-cancel:stage6']))[0]
report['image_id']=image['Id'];report['architecture']=image['Architecture']
report['image_size_bytes']=image['Size']
report['production_approval']=False
path=root/'docs/evidence/stage6/linux-postgres.json';path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

if '--tests' in sys.argv:
    name='hotel-stage6-tests-'+uuid4().hex[:8]
    env['TEST_DATABASE_URL']=env['DATABASE_URL']
    command=['docker','run','--name',name,'--network','host','--read-only','--tmpfs','/tmp',
             '-v',f'{root}:/project:ro','-w','/project','-e','TEST_DATABASE_URL',
             '-e','PYTHONPATH=/app/src:/tmp/test-deps','hotel-cancel:stage6','sh','-c',
             'python -m pip install --no-cache-dir --disable-pip-version-check -q --target /tmp/test-deps -r requirements-test-container.txt && python -m pytest -q -o cache_dir=/tmp/pytest-cache --junitxml=/tmp/tests.xml && python -c \"import base64; print(\'JUNIT_BASE64=\'+base64.b64encode(open(\'/tmp/tests.xml\',\'rb\').read()).decode())\"']
    try:
        completed=subprocess.run(command,env=env,text=True,capture_output=True)
        (root/'artifacts/stage6/linux-tests.log').write_text(completed.stdout+completed.stderr)
        completed.check_returncode()
        xml=base64.b64decode(completed.stdout.rsplit('JUNIT_BASE64=',1)[1].strip())
        (root/'artifacts/stage6/linux-tests.xml').write_bytes(xml)
        suite=ET.fromstring(xml).find('testsuite')
        assert suite is not None
        counts={k:int(suite.attrib[k]) for k in ['tests','failures','errors','skipped']}
        assert counts['failures']==counts['errors']==counts['skipped']==0
        counts.update(status='passed',postgres_enabled=True,environment='Linux arm64 container on Ubuntu VM',seconds=float(suite.attrib['time']))
        (root/'docs/evidence/stage6/tests-linux.json').write_text(json.dumps(counts,indent=2)+'\n')
        print(json.dumps(counts,indent=2))
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True)
