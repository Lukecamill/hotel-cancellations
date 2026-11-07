"""Build and test the slim image against an exported local runtime bundle."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request
from uuid import uuid4

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--bundle',default='models/serving')
p.add_argument('--snapshot',default='artifacts/stage6/snapshot.json')
p.add_argument('--output',default='docs/evidence/stage6/container.json')
args=p.parse_args()
if not shutil.which('docker'):
    raise SystemExit('Docker is required; container verification has not run.')
root=Path(__file__).resolve().parents[1]
bundle=(root/args.bundle).resolve()
snapshot=json.loads((root/args.snapshot).read_text())
name='hotel-stage6-'+uuid4().hex[:8]
image='hotel-cancel:stage6'
subprocess.run(['docker','build','-t',image,'.'],cwd=root,check=True)
subprocess.run(['docker','run','-d','--name',name,'--read-only','--tmpfs','/tmp',
                '--cap-drop','ALL','--security-opt','no-new-privileges:true',
                '-p','127.0.0.1::8080','-v',f'{bundle}:/models:ro',image],check=True,capture_output=True)
try:
    inspect=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    port=inspect['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort']
    base=f'http://127.0.0.1:{port}'
    for attempt in range(30):
        try:
            with urllib.request.urlopen(base+'/health',timeout=2) as response:
                health=json.load(response)
            break
        except (OSError,ValueError):
            state=json.loads(subprocess.check_output(['docker','inspect',name]))[0]['State']
            if not state['Running'] or attempt==29:
                logs=subprocess.check_output(['docker','logs',name],stderr=subprocess.STDOUT,text=True)
                raise RuntimeError('Container failed readiness: '+logs) from None
            time.sleep(1)
    body=json.dumps({'booking':snapshot['bookings'][0]['booking']}).encode()
    request=urllib.request.Request(base+'/predict',body,{'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=10) as response:
        prediction=json.load(response)
    assert prediction['model_version']==snapshot['model_version']
    assert 0<=prediction['cancellation_probability']<=1
    # Exercise the batch entry point in the same image and compare its JSON result.
    snap_path=(root/args.snapshot).resolve()
    result=subprocess.check_output(['docker','run','--rm','--read-only','--tmpfs','/tmp',
                                    '-v',f'{bundle}:/models:ro','-v',f'{snap_path}:/snapshot.json:ro',image,
                                    'sh','-c','python -m hotel_cancel.batch --snapshot-file /snapshot.json --output /tmp/batch.json >/dev/null && cat /tmp/batch.json'])
    batch=json.loads(result)
    expected=json.loads((root/'artifacts/stage6/batch.json').read_text())
    def matches(left,right):
        if type(left) is not type(right): return False
        if isinstance(left,dict): return left.keys()==right.keys() and all(matches(left[k],right[k]) for k in left)
        if isinstance(left,list): return len(left)==len(right) and all(matches(x,y) for x,y in zip(left,right))
        if isinstance(left,float): return math.isclose(left,right,rel_tol=1e-12,abs_tol=1e-12)
        return left==right
    assert matches(batch,expected), 'Batch differs beyond 1e-12 float tolerance or exact discrete fields'
    size=json.loads(subprocess.check_output(['docker','image','inspect',image]))[0]['Size']
    started=time.perf_counter()
    subprocess.run(['docker','stop',name],check=True,capture_output=True)
    stop_seconds=time.perf_counter()-started
    stopped=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    assert stopped['State']['ExitCode']==0
    assert stop_seconds<1., f'Container stop took {stop_seconds:.3f}s'
    report=dict(status='passed',image=image,image_size_bytes=size,stop_seconds=stop_seconds,exit_code=0,health=health,
                http_prediction=prediction,batch_matches_host=True,batch_float_absolute_tolerance=1e-12,batch_float_relative_tolerance=1e-12)
    path=root/args.output;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n')
finally:
    subprocess.run(['docker','rm','-f',name],check=False,capture_output=True)
