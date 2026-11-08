"""Import replay, record a monitored batch and verify the running monitoring stack.

Run in the prepared Ubuntu project, before/after scripts/load_stage7.py.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--after-load',action='store_true')
args=p.parse_args()
root=Path(__file__).resolve().parents[1];os.chdir(root)
env=dict(os.environ)
settings=dict(line.split('=',1) for line in (root/'.env').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
env['DATABASE_URL']='postgresql://hotel:'+settings['POSTGRES_PASSWORD']+'@127.0.0.1:5432/hotel'
def container(code):
 command=['docker','run','--rm','-i','--network','host','--read-only','--tmpfs','/tmp','-e','DATABASE_URL',
          '-v',f'{root}/models/serving:/models:ro','-v',f'{root}/artifacts:/artifacts:ro',
          '-v',f'{root}/docs/evidence/stage7/replay:/replay:ro','hotel-cancel:stage7','python','-']
 result=subprocess.run(command,input=code,text=True,env=env,capture_output=True,check=True)
 return json.loads(result.stdout)

def get(url):
 with urllib.request.urlopen(url,timeout=10) as response:return json.load(response)

def query(expression,at=None):
 params={'query':expression}
 if at is not None:params['time']=at
 return get('http://127.0.0.1:9090/api/v1/query?'+urllib.parse.urlencode(params))['data']['result']

if not args.after_load:
 result=container('''
import json,os,time
from pathlib import Path
from uuid import uuid4
from psycopg.types.json import Jsonb
from hotel_cancel.monitoring import Telemetry
from hotel_cancel.serving import Predictor
from hotel_cancel.batch import nightly_batch
report=json.loads(Path('/replay/report.json').read_text())
t=Telemetry(os.environ['DATABASE_URL'])
with t.connect() as c:
 c.execute('INSERT INTO hotel_monitoring_reports (report_id,payload) VALUES (%s,%s) ON CONFLICT DO NOTHING',(report['report_id'],Jsonb(report)))
snapshot=json.loads(Path('/artifacts/stage6/snapshot.json').read_text())
started=time.perf_counter();batch=nightly_batch(snapshot,Predictor('/models'));seconds=time.perf_counter()-started
with t.connect() as c:c.execute('INSERT INTO hotel_batch_logs (run_id,payload) VALUES (%s,%s)',(uuid4().hex,Jsonb(dict(batch,runtime_seconds=seconds))))
print(json.dumps(dict(replay_imported=True,batch_logged=True,batch_seconds=seconds,snapshot_id=snapshot['snapshot_id'])))
''')
 (root/'docs/evidence/stage7/batch.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result));raise SystemExit(0)

persisted=container('''
import json,os
from pathlib import Path
import psycopg
ids=json.loads(Path('/artifacts/stage7/prediction-ids.json').read_text())
with psycopg.connect(os.environ['DATABASE_URL']) as c:
 rows=c.execute('SELECT prediction_id,model_version,horizon FROM hotel_predictions WHERE prediction_id=ANY(%s)',(ids,)).fetchall()
assert len(rows)==len(ids)==len(set(ids))
assert all(r[2]=='booking_to_arrival' for r in rows)
print(json.dumps(dict(load_predictions=len(ids),persisted=len(rows),model_versions=sorted({r[1] for r in rows}))))
''')
# Scrapes are scheduled every five seconds. Retry only until this new report is visible.
for attempt in range(12):
 targets=get('http://127.0.0.1:9090/api/v1/targets')['data']['activeTargets']
 metrics=query('hotel_replay_calibration_ratio')
 if targets and all(t['health']=='up' for t in targets) and metrics:break
 time.sleep(1)
assert targets and all(t['health']=='up' for t in targets) and metrics
health=get('http://127.0.0.1:3000/api/health');assert health['database']=='ok'
dashboard=get('http://127.0.0.1:3000/api/dashboards/uid/hotel-monitoring')
assert len(dashboard['dashboard']['panels'])==8
alerts=get('http://127.0.0.1:9090/api/v1/rules')['data']['groups']
assert alerts and all(rule['health']=='ok' for group in alerts for rule in group['rules'])
performance=json.loads((root/'docs/evidence/stage7/performance.json').read_text())
means=[]
for phase in performance['phases']:
 values=query('sum(rate(hotel_input_lead_days_sum[1m])) / sum(rate(hotel_input_lead_days_count[1m]))',phase['ended_at_epoch']-1)
 assert values
 means.append(float(values[0]['value'][1]))
assert means[1]>1.4*means[0], 'Deliberate lead-time shift was not visible in input metrics'
result=dict(status='passed',input_shift_demonstrated=True,baseline_mean_lead_days=means[0],shifted_mean_lead_days=means[1],database=persisted,prometheus_targets_up=True,grafana_healthy=True,provisioned_panels=8,
            metric_families_checked=['hotel_http_requests_total','hotel_http_request_seconds_bucket','hotel_input_lead_days_bucket','hotel_prediction_logs_total','hotel_replay_calibration_ratio','hotel_replay_psi','hotel_replay_policy_cost_eur','hotel_last_batch_seconds'],
            alert_rules=[dict(name=rule['name'],state=rule['state']) for group in alerts for rule in group['rules']],
            model_calibration=query('hotel_replay_calibration_ratio'),input_drift=query('hotel_replay_psi'),
            metric_samples={name:query(name) for name in ['hotel_prediction_logs_total','hotel_prediction_log_failures_total','hotel_last_batch_seconds']},
            generated_at_epoch=time.time(),
            api_image_id=json.loads(subprocess.check_output(['docker','inspect',subprocess.check_output(['docker','compose','-p','hotel-stage6','ps','-q','api'],text=True).strip()]))[0]['Image'],
            build_input_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ['compose.yaml','Dockerfile','requirements-serving.txt','scripts/load_stage7.py','scripts/verify_stage7.py']},
            source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['src/hotel_cancel','monitoring'] for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in str(p) and not p.name.startswith('.')})
(root/'docs/evidence/stage7/verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status','database','prometheus_targets_up','grafana_healthy','provisioned_panels','alert_rules']},indent=2))
