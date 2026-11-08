"""Booking-shaped open-loop burst and lead-time shift; standard library only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import time
import urllib.error
import urllib.request


def percentile(values,q):
    values=sorted(values)
    pos=(len(values)-1)*q;lo=math.floor(pos);hi=math.ceil(pos)
    return values[lo]+(values[hi]-values[lo])*(pos-lo)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',default='http://127.0.0.1:8080/predict')
    p.add_argument('--fixture',default='artifacts/stage6/parity.json')
    p.add_argument('--seconds',type=int,default=60,help='Duration of each of two phases')
    p.add_argument('--rate',type=int,default=5)
    p.add_argument('--output',default='docs/evidence/stage7/performance.json')
    args=p.parse_args()
    if args.seconds<=0 or args.rate<=0:raise ValueError('Positive duration and rate required')
    records=json.loads(Path(args.fixture).read_text())['bookings']
    def send(record,scheduled=None):
        start=time.perf_counter() if scheduled is None else scheduled
        try:
            req=urllib.request.Request(args.url,json.dumps({'booking':record}).encode(),{'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=5) as response:
                body=json.load(response);status=response.status
            return dict(seconds=time.perf_counter()-start,status=status,hotel=record['hotel'],prediction_id=body['prediction_id'],persisted=body['prediction_logged'])
        except (urllib.error.URLError,OSError,ValueError) as error:
            return dict(seconds=time.perf_counter()-start,status=getattr(error,'code',0),hotel=record['hotel'],error=type(error).__name__,persisted=False)
    for r in records[:20]:send(r)
    phases=[];all_ids=[];started=time.time()
    for phase in ['booking_block_burst','lead_time_shift']:
        phase_epoch=time.time();start=time.perf_counter();futures=[]
        with ThreadPoolExecutor(max_workers=8) as pool:
            for i in range(args.rate*args.seconds):
                pause=start+i/args.rate-time.perf_counter()
                if pause>0:time.sleep(pause)
                record=dict(records[i%len(records)])
                if phase=='lead_time_shift':record['lead_time']=min(1000,2*record['lead_time']+30)
                futures.append(pool.submit(send,record,start+i/args.rate))
            rows=[f.result() for f in futures]
        elapsed=time.perf_counter()-start
        lat=[r['seconds'] for r in rows];ok=[r for r in rows if r['status']==200]
        all_ids += [r['prediction_id'] for r in ok]
        phases.append(dict(phase=phase,started_at_epoch=phase_epoch,ended_at_epoch=time.time(),sent=len(rows),successful=len(ok),errors=len(rows)-len(ok),
                           database_persisted=sum(r['persisted'] for r in rows),duration_seconds=elapsed,
                           throughput_per_second=len(ok)/elapsed,p50_seconds=percentile(lat,.5),p95_seconds=percentile(lat,.95),
                           p99_seconds=percentile(lat,.99),by_hotel={h:dict(requests=sum(r['hotel']==h for r in rows),p95_seconds=percentile([r['seconds'] for r in rows if r['hotel']==h],.95)) for h in ['City Hotel','Resort Hotel']}))
        print(json.dumps(phases[-1]),flush=True)
    result=dict(scope='historical_booking_payloads_for_service_burst_test_not_live_quality',started_at_epoch=started,ended_at_epoch=time.time(),
                rate_per_second=args.rate,workers=8,client_timeout_seconds=5,warmup_requests=20,phases=phases,
                budget_p95_seconds=.25,budget_pass=all(x['p95_seconds']<=.25 and x['errors']==0 for x in phases),
                source_fixture_sha256=__import__('hashlib').sha256(Path(args.fixture).read_bytes()).hexdigest(),
                load_rationale='Five booking entries/second is a short tour-operator/group-block burst, not the hotels daily average. Replay retains observed fields and hotel mix. Phase two deliberately changes lead times.',
                measurement='Open-loop offered rate; eight client workers; queueing and HTTP/database time included; warmups excluded from percentiles')
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+'\n')
    ids=Path('artifacts/stage7/prediction-ids.json');ids.parent.mkdir(parents=True,exist_ok=True);ids.write_text(json.dumps(all_ids))
    if not result['budget_pass']:raise SystemExit('Performance budget failed; report is retained')


if __name__=='__main__':main()
