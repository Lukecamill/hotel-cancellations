"""Digest-bound, self-declared coursework review; never grants live authority."""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PACKET=ROOT/'docs/reviews/coursework-policy-review-v1.json'
RECORD=ROOT/'docs/reviews/coursework-policy-signoff-v1.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def validate_record(record,packet_hash):
 if record['packet_sha256']!=packet_hash:raise ValueError('Review packet changed; a new review is required')
 if record['production_authorized'] is not False or record['max_authorized_extra_rooms']!=0 or record['reviewer_role']!='coursework simulation reviewer':raise ValueError('Simulation cannot grant live authority')
 if record['decision']!='approve_simulation':raise ValueError('Simulation not approved')
 if len(record['reviewer'].strip())<2 or len(record['reason'].strip())<5:raise ValueError('Reviewer and reason required')
 return dict(status='PASS',scope='coursework simulation only',production_authorized=False,max_authorized_extra_rooms=0)

def verify_saved_review(root=ROOT):
 """Prefer the explicit ADR 0005 v2 decision; never reinterpret the unsigned v1 packet."""
 packet_path=root/'docs/reviews/coursework-policy-review-v2.json'
 record_path=root/'docs/reviews/coursework-policy-signoff-v2.json'
 if packet_path.exists() or record_path.exists():
  packet=json.loads(packet_path.read_text());record=json.loads(record_path.read_text())
  result=validate_record(record,sha(packet_path))
  expected_policies={h:'no additional overbooking (q=0)' for h in ['City Hotel','Resort Hotel']}
  if (packet.get('version')!=2 or packet.get('review_outcome')!='accepted_with_changes'
      or record.get('review_outcome')!=packet['review_outcome']
      or packet.get('hotel_policies')!=expected_policies
      or packet.get('production_authorized') is not False
      or packet.get('max_authorized_extra_rooms')!=0
      or packet.get('guest_messages_authorized') is not False
      or record.get('guest_messages_authorized') is not False
      or not record.get('ai_disclosure')):
   raise ValueError('ADR 0005 simulated decision scope or AI disclosure changed')
  transcript=record.get('transcript')
  if transcript not in packet.get('evidence_sha256',{}):
   raise ValueError('Review transcript is not bound to the packet')
  for name,checksum in packet['evidence_sha256'].items():
   target=(root/name).resolve()
   if not target.is_relative_to(root.resolve()) or sha(target)!=checksum:
    raise ValueError('Reviewed evidence changed: '+name)
  return dict(result,review_outcome=record['review_outcome'],reviewer=record['reviewer'],
              policy_scope='ADR 0005; zero additional overbooking for both hotels',
              transcript=transcript,ai_simulated=True)
 if not (root/'docs/reviews/coursework-policy-signoff-v1.json').exists():
  return dict(status='PENDING_USER_REQUEST',formal_signoff_recorded=False,production_authorized=False,
              reason='No signed review record')
 return validate_record(json.loads((root/'docs/reviews/coursework-policy-signoff-v1.json').read_text()),
                        sha(root/'docs/reviews/coursework-policy-review-v1.json'))

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['record','verify']);p.add_argument('--reviewer');p.add_argument('--reason');p.add_argument('--packet-sha256');p.add_argument('--decision',choices=['approve_simulation','reject']);args=p.parse_args()
 if args.mode=='verify':
  result=verify_saved_review()
  print(json.dumps(result,indent=2));return 0 if result['status']=='PASS' else 1
 if RECORD.exists():raise ValueError('Review record is immutable; create a separately versioned superseding review')
 if not args.packet_sha256 or args.packet_sha256!=sha(PACKET):raise ValueError('Exact packet digest must be explicitly reviewed')
 if not args.reviewer or not args.reason or not args.decision:raise ValueError('Named reviewer, own reason and decision required')
 record=dict(reviewer=args.reviewer,reviewer_role='coursework simulation reviewer',reason=args.reason,decision=args.decision,
  packet_sha256=args.packet_sha256,reviewed_at_utc=datetime.now(timezone.utc).isoformat(),production_authorized=False,
  max_authorized_extra_rooms=0,identity='Self-declared in user response; not authenticated hotel authority',guest_messages_authorized=False)
 if args.decision=='approve_simulation':validate_record(record,sha(PACKET))
 RECORD.parent.mkdir(parents=True,exist_ok=True);RECORD.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':raise SystemExit(main())
