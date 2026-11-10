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

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['record','verify']);p.add_argument('--reviewer');p.add_argument('--reason');p.add_argument('--packet-sha256');p.add_argument('--decision',choices=['approve_simulation','reject']);args=p.parse_args()
 if args.mode=='verify':
  if not RECORD.exists():
   print(json.dumps(dict(status='PENDING_USER_REQUEST',formal_signoff_recorded=False,production_authorized=False,reason='Reviewer name/reason left for later'),indent=2));raise SystemExit(1)
  print(json.dumps(validate_record(json.loads(RECORD.read_text()),sha(PACKET)),indent=2));return
 if RECORD.exists():raise ValueError('Review record is immutable; create a separately versioned superseding review')
 if not args.packet_sha256 or args.packet_sha256!=sha(PACKET):raise ValueError('Exact packet digest must be explicitly reviewed')
 if not args.reviewer or not args.reason or not args.decision:raise ValueError('Named reviewer, own reason and decision required')
 record=dict(reviewer=args.reviewer,reviewer_role='coursework simulation reviewer',reason=args.reason,decision=args.decision,
  packet_sha256=args.packet_sha256,reviewed_at_utc=datetime.now(timezone.utc).isoformat(),production_authorized=False,
  max_authorized_extra_rooms=0,identity='Self-declared in user response; not authenticated hotel authority',guest_messages_authorized=False)
 if args.decision=='approve_simulation':validate_record(record,sha(PACKET))
 RECORD.parent.mkdir(parents=True,exist_ok=True);RECORD.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
