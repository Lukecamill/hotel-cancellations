"""Measure fixed-model fit and equivalent online/batch booking scoring; no promotion."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    sys.path.insert(0, str(root / 'src'))
    from hotel_cancel.config import load_config
    import hotel_cancel.train as train
    from hotel_cancel.serving import Predictor, REQUEST_FIELDS
    from hotel_cancel.service import make_server
    from hotel_cancel.monitoring import Telemetry

    config = load_config(project_root=root)
    measured_fits = []
    original_fit = train.fit

    def timed_fit(*a, **kw):
        start, cpu = time.perf_counter(), time.process_time()
        result = original_fit(*a, **kw)
        measured_fits.append({'wall_seconds': time.perf_counter()-start,
                              'cpu_seconds': time.process_time()-cpu})
        return result

    started = datetime.now(timezone.utc).isoformat()
    protected = [root/'models/serving'/n for n in ['manifest.json', 'booking_model.joblib', 'policy_state.joblib']]
    protected_before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    with tempfile.TemporaryDirectory(prefix='hotel-diary-measure-') as tmp:
        config['processed_dir'] = Path(tmp)/'processed'
        train.fit = timed_fit
        try:
            result = train.run_baseline(config, use_cache=False, save=False)
        finally:
            train.fit = original_fit
    # Booking entry day is reconstructed from arrival minus lead time. Include zero days.
    bk = result.bookings
    days = np.arange(np.datetime64('2016-01-01'), np.datetime64('2017-01-01'))
    import pandas as pd
    counts = bk.groupby('booked', observed=True).size().reindex(pd.to_datetime(days), fill_value=0)
    target = float(np.quantile(counts.to_numpy(), .95))
    selected_day = min(counts.index, key=lambda d: (abs(float(counts[d])-target), d))
    sample = bk.loc[bk.booked.eq(selected_day)].copy()
    records = []
    for row in sample.to_dict(orient='records'):
        record = {k: row[k] for k in REQUEST_FIELDS}
        record['arrival'] = record['arrival'].strftime('%Y-%m-%d')
        for k, v in record.items():
            if isinstance(v, np.generic):
                record[k] = v.item()
        records.append(record)
    print(f'Benchmarking {len(records)} records at 5 requests/s; isolated fit {measured_fits[0]}', flush=True)
    # Both paths consume the same serving artifact and exact raw booking contract.
    predictor = Predictor(root/'models/serving')
    telemetry = Telemetry()  # No database: isolated loopback computation benchmark.
    server = make_server(predictor, port=0, telemetry=telemetry)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f'http://127.0.0.1:{server.server_port}/predict'

    def request_one(record, scheduled):
        wait = scheduled-time.perf_counter()
        if wait > 0:
            time.sleep(wait)
        data = json.dumps({'booking': record}, allow_nan=False).encode()
        req = urllib.request.Request(endpoint, data=data, headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req, timeout=20) as response:
            answer = json.load(response)
        return time.perf_counter()-scheduled, answer['cancellation_probability'], answer['prediction_logged']

    try:
        for row in records[:10]:
            request_one(row, time.perf_counter())
        wall, cpu = time.perf_counter(), time.process_time()
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(request_one, row, wall+i/5) for i, row in enumerate(records)]
            answers = [f.result() for f in futures]
        online_wall, online_cpu = time.perf_counter()-wall, time.process_time()-cpu
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    batches = []
    batch_predictions = None
    for _ in range(5):
        wall, cpu = time.perf_counter(), time.process_time()
        fresh = Predictor(root/'models/serving')
        batch_predictions = fresh.predict(records)
        batches.append({'wall_seconds':time.perf_counter()-wall, 'cpu_seconds':time.process_time()-cpu})
    online_predictions = np.array([a[1] for a in answers])
    np.testing.assert_allclose(online_predictions, batch_predictions, atol=1e-12, rtol=1e-12)
    metric_names = {'auprc': 'AUPRC', 'expected_observed_ratio': 'expected ÷ realised'}
    expected = json.loads((root/'config/coursework-reference.json').read_text())['reference_gate']['hotels']
    for hotel in config['hotels']:
        for key in ['auprc', 'expected_observed_ratio']:
            np.testing.assert_allclose(result.metrics.loc[('test', hotel), metric_names[key]], expected[hotel][key], atol=1e-10, rtol=1e-10)
    protected_after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    assert protected_before == protected_after
    batch_median = float(np.median([b['wall_seconds'] for b in batches]))
    batch_cpu = float(np.median([b['cpu_seconds'] for b in batches]))
    report = {
        'started_utc':started, 'completed_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Local loopback HTTP versus direct daily batch, same raw records and fixed artifact; DB/network/PMS excluded',
        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'working_tree_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()),
        'measurement_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'hardware':{'platform':platform.platform(),'processor':platform.machine(),'python':platform.python_version()},
        'packages':{p:version(p) for p in ['numpy','pandas','lightgbm','scikit-learn']},
        'fit': measured_fits[0], 'booking_pipeline_wall_seconds':result.runtime_seconds,
        'split_counts':{k:int(v.sum()) for k,v in result.masks.items()},
        'holdout_sha256':result.fingerprint,
        'metrics':{h:{k:float(result.metrics.loc[('test',h),metric_names[k]]) for k in ['auprc','expected_observed_ratio']} for h in config['hotels']},
        'workload':{'definition':'All observed rows entered on selected reconstructed 2016 booking date; both hotels; no sampling',
                    'reference_days':len(counts),'mean_daily_entries':float(counts.mean()),'p95_daily_entries':target,
                    'max_daily_entries':int(counts.max()),'selected_booked_date':str(selected_day.date()),
                    'records':len(records),'offered_requests_per_second':5,'workers':8,'warmup_requests':10,
                    'records_sha256':hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest()},
        'online':{'wall_seconds':online_wall,'cpu_seconds':online_cpu,'measured_requests':len(answers),
                  'p50_seconds':float(np.percentile([a[0] for a in answers],50)),
                  'p95_seconds':float(np.percentile([a[0] for a in answers],95)),
                  'p99_seconds':float(np.percentile([a[0] for a in answers],99)),
                  'all_requests_succeeded':True,'database_persistence_enabled':False},
        'batch':{'runs':batches,'median_wall_seconds':batch_median,'median_cpu_seconds':batch_cpu,
                 'median_records_per_second':len(records)/batch_median,'includes_artifact_loading':True},
        'parity_max_absolute_difference':float(np.max(np.abs(online_predictions-batch_predictions))),
        'reference_metric_comparison':'PASS','serving_artifacts_unchanged':True,'serving_sha256':protected_before,
        'cost_scenarios':{'status':'Estimates using measured duration; prices/billing rules assumed, not an electricity meter or invoice',
                          'assumed_eur_per_allocated_hour':0.10,'assumed_batch_minimum_billing_seconds':60,
                          'dedicated_online_24h_eur_per_day':2.4,
                          'on_demand_batch_eur_per_day':math.ceil(batch_median/60)*60/3600*.1,
                          'shared_already_running_host_incremental_invoice_saving_eur_per_day':0,
                          'online_measured_cpu_hours_per_workload':online_cpu/3600,
                          'batch_measured_cpu_hours_per_workload':batch_cpu/3600},
        'limitations':['Single local run, not the historical Ubuntu load experiment',
                      'Batch repeated five times with warm OS cache; each repetition loads artifacts',
                      'No PostgreSQL persistence or live PMS/channel integration in this benchmark',
                      'Booking entry dates are reconstructed final-snapshot dates, not an event log',
                      '5 requests/s is a deliberately compressed burst, not observed interarrival timing',
                      'Elapsed batch time excludes up-to-one-day scheduling wait',
                      'Staffing, electricity, hardware amortisation and hosting invoices are unmeasured',
                      'Both-hotel reference quality gate remains blocked by Resort; no promotion']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2,allow_nan=False))


if __name__ == '__main__':
    main()
