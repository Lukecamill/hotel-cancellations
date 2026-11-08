"""Nightly review recommendations from an immutable, horizon-matched snapshot."""
import argparse
import json
import os
import time
from uuid import uuid4
from pathlib import Path

import numpy as np
import pandas as pd

from hotel_cancel.policy import released_distribution, oversell
from hotel_cancel.serving import Predictor, booking_frame
from hotel_cancel.snapshot import read_postgres, verify_snapshot


def nightly_batch(snapshot, predictor):
    verify_snapshot(snapshot)
    cfg = predictor.policy['config']
    h = cfg['decision_lead_days']
    decision = pd.Timestamp(snapshot['decision_date'])
    if snapshot['model_version'] != predictor.version or snapshot['policy_version'] != predictor.manifest['sha256']['policy_state.joblib']:
        raise ValueError('Snapshot and runtime artifacts differ')
    if snapshot['lead_days'] != h or pd.Timestamp(snapshot['arrival']) != decision + pd.Timedelta(days=h):
        raise ValueError('Snapshot horizon mismatch')
    if decision <= pd.Timestamp(cfg['calib_end']):
        raise ValueError('Calibration outcomes not mature')
    history = pd.DataFrame(snapshot['history'])
    history['night'] = pd.to_datetime(history.night)
    if (history.night >= decision).any() or history.duplicated(['hotel', 'night']).any():
        raise ValueError('History must contain unique matured hotel nights only')
    for col in ['observed', 'predicted', 'count']:
        if not np.isfinite(history[col]).all() or (history[col] < 0).any():
            raise ValueError('Invalid historical counts')
    if (history.observed > history['count']).any():
        raise ValueError('Invalid historical release counts')
    if not history.hotel.isin(cfg['hotels']).all():
        raise ValueError('Unknown hotel in history')
    bookings = snapshot['bookings']
    if bookings:
        booking_frame([r['booking'] for r in bookings])
    if len({r['booking_id'] for r in bookings}) != len(bookings):
        raise ValueError('Duplicate snapshot booking IDs')
    results = []
    for hotel in cfg['hotels']:
        entries = [row for row in bookings if row['booking']['hotel'] == hotel]
        name = predictor.policy['chosen_policies'][hotel]
        if not entries:
            results.append(dict(hotel=hotel, candidate_policy=name, on_books=0, candidate_oversell=0,
                                authorised_oversell=0, status='no_live_bookings', requires_human_approval=True))
            continue
        records = [entry['booking'] for entry in entries]
        frame = booking_frame(records)
        if (frame.arrival != pd.Timestamp(snapshot['arrival'])).any() or (frame.booked >= decision).any():
            raise ValueError('Snapshot contains a booking outside its as-of boundary')
        p_booking = predictor.predict(records)
        p_cal = predictor.policy['calibrators'][hotel].predict(pd.Series(p_booking), lead_days=h)
        data = pd.DataFrame({'p': p_cal, 'block': [r['block_id'] for r in entries]})
        blocks = data.groupby('block', sort=True).agg(p=('p', 'mean'), n=('p', 'size'))
        factor, rate, window = 1., None, None
        if name.startswith('flat rate (trailing ') or name.startswith('model + blocks + re-level '):
            window = int(name.split()[-2])
            start = decision-pd.Timedelta(weeks=window)
            trail = history[(history.hotel==hotel) & (history.night>=start)]
            if len(trail) != 7*window:
                raise ValueError('Snapshot lacks complete mature recalibration history')
            factor = float(trail.observed.sum()/trail.predicted.sum()) if trail.predicted.sum()>0 else 1.
            rate = float(trail.observed.sum()/trail['count'].sum()) if trail['count'].sum()>0 else None
        if name == 'no overbooking':
            probs, sizes = np.array([]), np.array([], int)
        elif name == 'flat rate (Jul – Sep 2016)':
            probs, sizes = np.full(len(frame), predictor.policy['flat_rates'][hotel]), np.ones(len(frame), int)
        elif name.startswith('flat rate (trailing '):
            if rate is None:
                raise ValueError('No historical bookings for trailing rate')
            probs, sizes = np.full(len(frame), rate), np.ones(len(frame), int)
        elif name == 'model':
            probs, sizes = p_cal, np.ones(len(frame), int)
        elif name == 'model + blocks' or name.startswith('model + blocks + re-level '):
            probs, sizes = np.clip(blocks.p.to_numpy()*factor, 0, 1), blocks.n.to_numpy()
        else:
            raise ValueError('Unsupported policy artifact')
        if not np.isfinite(probs).all() or ((probs<0)|(probs>1)).any():
            raise ValueError('Invalid horizon probabilities')
        dist = released_distribution(probs, sizes)
        value = max(float(frame.adr.median())-cfg['variable_cost_eur'], 0.)
        q = 0 if name == 'no overbooking' else oversell(dist, value, cfg['walk_cost_eur'])
        k = np.arange(len(dist))
        results.append(dict(hotel=hotel, candidate_policy=name, on_books=len(frame),
                            rooms_in_blocks=int(blocks.loc[blocks.n>1, 'n'].sum()),
                            expected_releases=float(dist@k), empty_room_cost_eur=value,
                            candidate_oversell=q, probability_walk_anyone=float(dist[:q].sum()),
                            expected_cost_eur=float(cfg['walk_cost_eur']*(np.maximum(q-k,0)@dist)+value*(np.maximum(k-q,0)@dist)),
                            recalibration_weeks=window, recalibration_factor=factor,
                            authorised_oversell=0, requires_human_approval=True, status='review_required',
                            diagnostic_gate=predictor.manifest['diagnostic_gate'][hotel]))
    return dict(schema_version=1, snapshot_id=snapshot['snapshot_id'], decision_date=snapshot['decision_date'],
                arrival=snapshot['arrival'], lead_days=h, model_version=predictor.version,
                policy_version=snapshot['policy_version'], results=results)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', default=os.environ.get('SERVING_BUNDLE', 'models/serving'))
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument('--snapshot-file')
    source.add_argument('--snapshot-id', help='Read PostgreSQL using DATABASE_URL')
    p.add_argument('--output', required=True)
    p.add_argument('--monitor',action='store_true',help='Persist versioned batch output using DATABASE_URL')
    args = p.parse_args()
    snapshot = json.loads(Path(args.snapshot_file).read_text()) if args.snapshot_file else read_postgres(args.snapshot_id, os.environ['DATABASE_URL'])
    started=time.perf_counter()
    result = nightly_batch(snapshot, Predictor(args.bundle))
    runtime=time.perf_counter()-started
    if args.monitor:
        from hotel_cancel.monitoring import Telemetry
        from psycopg.types.json import Jsonb
        telemetry=Telemetry(os.environ['DATABASE_URL'])
        with telemetry.connect() as c:
            c.execute('INSERT INTO hotel_batch_logs (run_id,payload) VALUES (%s,%s)',(uuid4().hex,Jsonb(dict(result,runtime_seconds=runtime))))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    temp.replace(path)
    print(path)


if __name__ == '__main__':
    main()
