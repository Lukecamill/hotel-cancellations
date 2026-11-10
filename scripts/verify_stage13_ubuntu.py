"""Verify Stage 13 offline recorded local-model evidence in the existing check image."""
import hashlib,json,subprocess,os,platform,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert platform.system()=='Linux','Run inside Ubuntu'
 os.chdir(ROOT)
 inventory=json.loads((ROOT/'config/stage13-run-inventory.json').read_text())
 for name,value in inventory['files'].items():
  if sha(ROOT/name)!=value:raise ValueError('Source/evidence mismatch: '+name)
 for folder in ['src/hotel_cancel','tests','knowledge']:
  actual={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
  pinned={k:v for k,v in inventory['files'].items() if k.startswith(folder+'/')}
  if actual!=pinned:raise ValueError('Complete inventory differs: '+folder)
 out=ROOT/'docs/evidence/stage13-ubuntu';out.mkdir(parents=True,exist_ok=True)
 for path in ['verification.json','quality-gate/report.json','shacl/report.json']:(out/path).unlink(missing_ok=True)
 def run(command):
  p=subprocess.run(['docker','run','--rm','--network','none','--user',str(__import__('os').getuid())+':'+str(__import__('os').getgid()),
    '-v',str(ROOT)+':/project','-w','/project','-e','PYTHONPATH=/project/src','-e','MPLCONFIGDIR=/tmp/matplotlib','hotel-cancel:stage9-check',*command],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  print(p.stdout,flush=True);return p
 protected={p:sha(ROOT/p) for p in inventory['protected_files']}
 protected.update({str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'artifacts/stage9-ubuntu').glob('mlflow.db')})
 p=run(['make','ci','PYTHON=python','QUALITY_OUTPUT=docs/evidence/stage13-ubuntu/quality-gate','KB_OUTPUT=docs/evidence/stage13-ubuntu/shacl'])
 (out/'ci.txt').write_text(p.stdout)
 if f"{inventory['tests_passed']} passed, 6 skipped" not in p.stdout or ' failed' in p.stdout:raise ValueError('Tests differ or failed')
 report=json.loads((out/'quality-gate/report.json').read_text())
 if not report['identity_verified'] or report['hotels']['City Hotel']['gate']!='PASS' or report['hotels']['Resort Hotel']['checks']['calibration_ratio'] is not False:raise ValueError('Unexpected quality gate')
 if not json.loads((out/'shacl/report.json').read_text())['conforms']:raise ValueError('SHACL failed')
 # Quality outcome must remain the known calibration failure, not another error.
 if p.returncode!=2 or 'Quality gate: FAIL' not in p.stdout or 'calibration_ratio' not in p.stdout:raise ValueError('Unexpected CI outcome')
 p=run(['python','-m','hotel_cancel.briefing','replay']);(out/'replay.txt').write_text(p.stdout)
 if p.returncode:raise ValueError('Recorded local model replay failed')
 replay=json.loads(p.stdout)
 if replay!=inventory['expected_replay']:raise ValueError('Replay results differ from Mac')
 if protected!={p:sha(ROOT/p) for p in protected}:raise ValueError('Serving/KB/registry changed')
 result=dict(status='VERIFIED',local_model_run_on='Mac; raw recorded fixtures replayed here offline',live_model_called_on_ubuntu=False,
   replay=replay,tests_passed=inventory['tests_passed'],tests_skipped=6,source_and_recorded_evidence_identical=True,
   serving_registry_core_kb_unchanged=True,make_ci_expected_resort_calibration_failure=True,production_authorized=False)
 (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('STAGE13_UBUNTU_VERIFIED');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
