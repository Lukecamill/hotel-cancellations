"""Operational smoke/parity evidence. Requires a dedicated TEST_DATABASE_URL."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import subprocess
import threading

import numpy as np
import pandas as pd
import psycopg

from hotel_cancel.batch import nightly_batch
from hotel_cancel.config import load_config
from hotel_cancel.data import load_bookings, separate_outcome
from hotel_cancel.features import build_features
from hotel_cancel.service import make_server
from hotel_cancel.serving import Predictor, REQUEST_FIELDS
from hotel_cancel.snapshot import create_snapshot, read_postgres, write_postgres

root=Path(__file__).resolve().parents[1]
predictor=Predictor(root/'models/serving')
cfg=load_config(project_root=root)
raw=load_bookings(cfg,use_cache=False)
bk,_=separate_outcome(raw)
# Compare to the original training-side path across both hotels and time periods.
sample=bk.sample(1000,random_state=3217).sort_index()
X=build_features(sample,predictor.bundle['top_agents'])
expected=predictor.bundle['model'].predict_proba(X[predictor.bundle['feature_columns']])[:,1]
request=sample.loc[:,sorted(REQUEST_FIELDS)].copy()
request['arrival']=request.arrival.dt.strftime('%Y-%m-%d')
records=json.loads(request.to_json(orient='records'))
actual=predictor.predict(records)
max_error=float(np.max(np.abs(expected-actual)))
assert max_error<=1e-12
snapshot=create_snapshot(cfg,predictor,'2017-08-08')
url=os.environ['TEST_DATABASE_URL']
write_postgres(snapshot,url)
write_postgres(snapshot,url)
loaded=read_postgres(snapshot['snapshot_id'],url)
assert loaded==snapshot
file_result=nightly_batch(snapshot,predictor)
postgres_result=nightly_batch(loaded,predictor)
assert file_result==postgres_result
assert [r['on_books'] for r in file_result['results']]==[66,15]
assert [r['candidate_oversell'] for r in file_result['results']]==[3,0]
server=make_server(predictor,port=0)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
 conn=http.client.HTTPConnection(*server.server_address,timeout=10)
 conn.request('POST','/predict',json.dumps({'booking':records[0]}),{'Content-Type':'application/json'})
 response=conn.getresponse();body=json.loads(response.read());conn.close()
 assert response.status==200 and body['cancellation_probability']==actual[0]
finally:
 server.shutdown();server.server_close();thread.join(timeout=5)
with psycopg.connect(url) as conn:
 server_version=conn.execute('SHOW server_version').fetchone()[0]
artifacts=root/'artifacts/stage6';artifacts.mkdir(parents=True,exist_ok=True)
(artifacts/'snapshot.json').write_text(json.dumps(snapshot,indent=2)+'\n')
(artifacts/'batch.json').write_text(json.dumps(file_result,indent=2)+'\n')
(root/'docs/evidence/stage6/example-batch.json').write_text(json.dumps(file_result,indent=2)+'\n')
report=dict(status='passed',python=platform.python_version(),postgres_version=server_version,
            checks=['1000-row training/serving parity','HTTP/model parity','PostgreSQL immutable round trip',
                    'idempotent snapshot insert','file/PostgreSQL batch equivalence',
                    'example-night counts and candidate quantities'],
            maximum_probability_difference=max_error,model_version=predictor.version,
            snapshot_id=snapshot['snapshot_id'],raw_sha256=predictor.manifest['raw_sha256'],
            source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'src/hotel_cancel').glob('*.py')},
            container_build='not_run: no Docker or compatible container runtime installed',
            production_approval=False)
(root/'docs/evidence/stage6/verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
