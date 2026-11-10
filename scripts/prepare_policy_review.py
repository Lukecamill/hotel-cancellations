"""Prepare a concrete review packet; never records approval."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 calibration=ROOT/'docs/evidence/remediation/calibration/report.json'
 briefing=ROOT/'docs/evidence/remediation/briefing-v5/report.json'
 c=json.loads(calibration.read_text());b=json.loads(briefing.read_text())
 if c['status']!='PASS' or b['component_quality_gate']!='PASS':raise ValueError('Quality remediation must finish and pass before review')
 packet=dict(version=1,scope='Coursework-wide historical simulation review only',
  proposed_decision='approve_simulation',reviewer_role='coursework simulation reviewer',
  policies=json.loads((ROOT/'models/serving/policy_state.joblib').with_name('manifest.json').read_text()).get('policy_source'),
  hotel_policies={'City Hotel':'flat rate (Jul – Sep 2016)','Resort Hotel':'model + blocks + re-level 8 wk'},
  assumed_costs_eur=dict(walking=250,variable=20),decision_lead_days=7,resale_fraction=0,
  capacity_assumption='Sold-out arrival-night proxy only; real room-night capacity unverified',
  parties='Exact-key inferred groups; no verified party identity',
  proposal_scope='Reference nightly quantities may be displayed for coursework analysis; no new economic candidate or live policy is promoted',
  calibrated_model_scope='Separate booking-to-arrival Resort research challenger; no change to seven-day policy or original learner',
  quality=dict(calibration='PASS',resort_ratio=c['hotels']['Resort Hotel']['expected_observed_ratio'],resort_ece=c['hotels']['Resort Hotel']['ece'],
    original_30_briefing_regression=b['groups']['regression'],additional_30_with_kb=b['groups']['with_kb'],without_kb=b['groups']['without_kb'],injection=b['groups']['injection']),
  max_authorized_extra_rooms=0,automatic_relocation_authorized=False,guest_messages_authorized=False,production_authorized=False,
  constraints=['Reviewer accepts these values as coursework assumptions, not verified operating costs',
   'Original model and prompt failures remain in the evidence',
   'Each guest draft still requires its own human review; no sending capability exists',
   'Real operating approval needs actual inventory, costs, event-time validation and an authorised hotel manager',
   'Stage 5 alternative economic policy candidates are not approved by this packet'],
  evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in [calibration,briefing,ROOT/'prompts/revenue-manager-v5.txt']})
 out=ROOT/'docs/reviews';out.mkdir(parents=True,exist_ok=True);p=out/'coursework-policy-review-v1.json'
 if p.exists() and json.loads(p.read_text())!=packet:raise ValueError('Existing review packet differs; create a new version')
 p.write_text(json.dumps(packet,indent=2,ensure_ascii=False)+'\n');print('Packet SHA-256:',sha(p));print(json.dumps(packet,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
