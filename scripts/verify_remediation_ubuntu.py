"""Reproduce the calibrated challenger; replay Mac LLM evidence offline on Ubuntu."""
import hashlib,json,os,platform,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert platform.system()=='Linux','Run inside Ubuntu'
 os.chdir(ROOT);inv=json.loads((ROOT/'config/remediation-run-inventory.json').read_text())
 for name,value in inv['files'].items():
  if sha(ROOT/name)!=value:raise ValueError('Transfer differs: '+name)
 for folder in ['src/hotel_cancel','tests','knowledge']:
  actual={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
  if actual!={n:h for n,h in inv['files'].items() if n.startswith(folder+'/')}:raise ValueError('Complete inventory differs: '+folder)
 out=ROOT/'docs/evidence/remediation-ubuntu';out.mkdir(parents=True,exist_ok=True);(out/'verification.json').unlink(missing_ok=True)
 protected=[ROOT/'compose.yaml',ROOT/'knowledge/hotel.ttl',*list((ROOT/'models/serving').glob('*')),*list((ROOT/'artifacts/stage9-ubuntu').glob('mlflow.db'))]
 before={str(p.relative_to(ROOT)):sha(p) for p in protected if p.is_file()}
 base=['docker','run','--rm','--network','none','--user',f'{os.getuid()}:{os.getgid()}',
  '-v',str(ROOT)+':/project','-w','/project','-e','PYTHONPATH=/project/src','-e','MPLCONFIGDIR=/tmp/matplotlib','hotel-cancel:stage9-check']
 def run(command,name,allowed=(0,)):
  p=subprocess.run(base+command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);print(p.stdout,flush=True);(out/name).write_text(p.stdout)
  if p.returncode not in allowed:raise ValueError('Command failed: '+name)
  return p
 p=run(['make','ci','PYTHON=python','QUALITY_OUTPUT=docs/evidence/remediation-ubuntu/reference-quality','KB_OUTPUT=docs/evidence/remediation-ubuntu/shacl'],'reference-ci.txt',(2,))
 if f"{inv['tests_passed']} passed, 6 skipped" not in p.stdout or ' failed' in p.stdout or 'Quality gate: FAIL' not in p.stdout:raise ValueError('Unexpected reference CI/test outcome')
 run(['python','-m','hotel_cancel.calibration_challenger','run','--output','docs/evidence/remediation-ubuntu/calibration'],'calibration.txt')
 actual=json.loads((out/'calibration/report.json').read_text());expected=inv['calibration']
 if actual['status']!='PASS' or actual['identity']!=expected['identity'] or actual['fit_rows']!=expected['fit_rows']:raise ValueError('Calibrated challenger differs')
 for hotel in actual['hotels']:
  for key in ['auprc','expected_observed_ratio','ece','brier']:
   if abs(actual['hotels'][hotel][key]-expected['hotels'][hotel][key])>1e-12:raise ValueError('Calibration metric differs')
 for key in ['coefficient','intercept']:
  if abs(actual[key]-expected[key])>1e-12:raise ValueError('Calibrator parameters differ')
 run(['python','-m','hotel_cancel.calibration_challenger','verify','--output','docs/evidence/remediation-ubuntu/calibration'],'calibration-verify.txt')
 p=run(['python','-m','hotel_cancel.briefing_revision','replay'],'briefing-replay.txt');replay=json.loads(p.stdout)
 if replay!=inv['briefing_replay']:raise ValueError('Revised prompt replay differs')
 signed=(ROOT/'docs/reviews/coursework-policy-signoff-v1.json').exists()
 if signed!=inv['formal_signoff_recorded']:raise ValueError('Unexpected/missing sign-off record')
 if signed:
  p=run(['python','scripts/record_simulation_signoff.py','verify'],'simulation-signoff.txt');approval=json.loads(p.stdout)
  if approval['production_authorized'] or approval['max_authorized_extra_rooms']!=0:raise ValueError('Invalid simulation scope')
 if before!={n:sha(ROOT/n) for n in before}:raise ValueError('Existing demo/registry/KB changed')
 result=dict(status='VERIFIED',tests_passed=inv['tests_passed'],tests_skipped=6,calibrated_challenger_gate='PASS',
  resort_ratio=actual['hotels']['Resort Hotel']['expected_observed_ratio'],calibration_matches_mac_tolerance=1e-12,
  briefing_replay=replay,live_llm_called_on_ubuntu=False,coursework_simulation_signoff_verified=signed,coursework_signoff_status="VERIFIED" if signed else "PENDING_USER_REQUEST",
  original_reference_failures_preserved=True,serving_registry_core_kb_unchanged=True,production_authorized=False)
 (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('REMEDIATION_UBUNTU_VERIFIED');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
