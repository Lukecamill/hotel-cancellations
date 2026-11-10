"""Read-only final evidence audit. It never calls a model, database or service."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--require-ready',action='store_true');args=p.parse_args()
 required=['docs/submission-checklist.md','docs/reproduce-final.md','docs/revenue-manager-recommendation.md',
  'docs/stage14-final-verification.md','docs/evidence/stage14/clean-clone-summary.json','docs/evidence/stage14/quality-gate/report.json',
  'docs/evidence/stage13-ubuntu/verification.json','docs/evidence/stage13/report.json',
  'docs/evidence/stage12-ubuntu/ubuntu-verification.json','docs/model-card.md','docs/llm-access.md']
 missing=[name for name in required if not (ROOT/name).is_file()]
 report=dict(evidence_present=not missing,missing_files=missing,production_authorized=False,
   limitations=['Final-project rubric/milestone brief not supplied','Policy-wide manager sign-off outstanding',
    'Final run skips six PostgreSQL tests; prior PostgreSQL checks remain historical',
    'Later diary requirements/submission not verified','VLE hand-in not performed'])
 if not missing:
  gate=json.loads((ROOT/'docs/evidence/stage14/quality-gate/report.json').read_text())
  briefing=json.loads((ROOT/'docs/evidence/stage13/report.json').read_text())
  clone=json.loads((ROOT/'docs/evidence/stage14/clean-clone-summary.json').read_text())
  report.update(hotel_quality_gates={h:r['gate'] for h,r in gate['hotels'].items()},
   briefing_quality_gate=briefing['model_quality_gate'],briefing_exact_nights=briefing['groups']['with_kb']['accepted'],
   clean_clone_verified=clone['baseline_reference_checks_passed']==20 and clone['tests_passed']==215,
   tested_commit=clone['tested_commit'])
 remediation=ROOT/'docs/evidence/remediation/verification.json'
 if remediation.exists():
  current=json.loads(remediation.read_text())
  report['reference_hotel_quality_gates']=report.get('hotel_quality_gates')
  report['reference_briefing_quality_gate']=report.get('briefing_quality_gate')
  corrected=json.loads((ROOT/'docs/evidence/remediation/calibration/report.json').read_text())
  report['hotel_quality_gates']={h:v['gate'] for h,v in corrected['hotels'].items()}
  report['briefing_quality_gate']=current['briefing_component_gate']
  report['briefing_exact_nights']=current['additional_nights_exact']
  report['current_worktree_tests_passed']=current['tests_passed']
  report['current_remedy_ubuntu_verification']=current['ubuntu_verification']
  report['coursework_signoff']=current['coursework_signoff']
  report['raw_model_numeric_copy_perfection_claimed']=False
  report['limitations'][1]='Formal coursework sign-off left pending at user request; real hotel sign-off also absent'
 try:
  report['current_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
 except (OSError,subprocess.CalledProcessError):report['current_commit']=None
 report['ready_for_unconditional_submission']=not missing and not report['limitations'] and report.get('briefing_quality_gate')=='PASS' and all(v=='PASS' for v in report.get('hotel_quality_gates',{}).values())
 report['review_file_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in required if (ROOT/name).is_file()}
 print(json.dumps(report,indent=2))
 return 1 if missing or (args.require_ready and not report['ready_for_unconditional_submission']) else 0
if __name__=='__main__':raise SystemExit(main())
