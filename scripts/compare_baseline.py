"""Compare a saved complete baseline run with recorded notebook evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', required=True, help='Saved run directory, relative to repository or absolute')
args = parser.parse_args()
run = Path(args.run)
if not run.is_absolute():
    run = ROOT / run
reference_path = ROOT / 'docs/evidence/reference-run/results.json'
reference = json.loads(reference_path.read_text())
metadata = json.loads((run / 'run.json').read_text())
manifest = json.loads((ROOT / 'docs/evidence/dataset-manifest.json').read_text())
checks = []
def check(name, passed):
    checks.append({'check': name, 'passed': bool(passed)})

def close(left, right):
    return bool(np.allclose(np.asarray(left, dtype=float), np.asarray(right, dtype=float), rtol=1e-14, atol=1e-12))

check('successful run', metadata['status'] == 'passed')
check('raw identity', metadata['raw_sha256'] == manifest['sha256'])
check('holdout identity', metadata['holdout_sha256'] == reference['holdout_sha256'])
check('split counts', metadata['split_counts'] == reference['split_counts'])
metrics = pd.read_csv(run / 'booking_metrics.csv', index_col=[0, 1]).loc['test']
expected_metrics = pd.DataFrame(reference['booking_metrics']).T
check('full-precision test metrics (CSV tolerance)', close(metrics.loc[expected_metrics.index, expected_metrics.columns], expected_metrics))
for hotel, ap, ratio in [('City Hotel', .786, .91), ('Resort Hotel', .628, .68)]:
    check(f'{hotel} printed AUPRC', abs(metrics.loc[hotel, 'AUPRC'] - ap) <= .0005)
    check(f'{hotel} printed calibration', abs(metrics.loc[hotel, 'expected ÷ realised'] - ratio) <= .005)
check('diagnostic gates', metadata['diagnostic_gate'] == {'City Hotel': 'PASS', 'Resort Hotel': 'FAIL'})
check('policy choices', json.loads((run / 'chosen_policies.json').read_text()) == reference['chosen_policies'])
actual = pd.read_csv(run / 'policy_test_summary.csv').set_index(['hotel', 'policy'])
expected = pd.DataFrame(reference['policy_test_results']).set_index(['hotel', 'policy'])
check('all policy summary values (CSV tolerance)', close(actual.loc[expected.index, expected.columns], expected))
for hotel, cost, none, saving in [('City Hotel',264,279,3457), ('Resort Hotel',96,98,458)]:
    chosen = reference['chosen_policies'][hotel]
    check(f'{hotel} printed selected nightly cost', abs(actual.loc[(hotel, chosen),'cost_per_night']-cost)<=.5)
    check(f'{hotel} printed no-overbooking nightly cost', abs(actual.loc[(hotel,'no overbooking'),'cost_per_night']-none)<=.5)
    check(f'{hotel} printed total savings', abs(actual.loc[(hotel,chosen),'saving vs none (€)']-saving)<=.5)
check('all example-night fields exact', json.loads((run / 'tonight.json').read_text()) == reference['tonight'])
check('source files match run hashes', all(hashlib.sha256((ROOT/'src/hotel_cancel'/name).read_bytes()).hexdigest()==digest for name,digest in metadata['source_sha256'].items()))
report = {'status':'passed' if all(c['passed'] for c in checks) else 'failed',
          'run_id':metadata['run_id'], 'checks':checks,
          'tolerances':{'printed_auprc_absolute':.0005,'printed_calibration_absolute':.005,
                        'printed_whole_euro_absolute':.5,'csv_absolute':1e-12,'csv_relative':1e-14},
          'reference_results_sha256':hashlib.sha256(reference_path.read_bytes()).hexdigest(),
          'raw_sha256':metadata['raw_sha256'],'holdout_sha256':metadata['holdout_sha256'],
          'booking_runtime_seconds':metadata['booking_runtime_seconds'],
          'policy_runtime_seconds':metadata['policy_runtime_seconds'],
          'total_runtime_seconds':metadata['total_runtime_seconds']}
(ROOT/'docs/evidence/baseline-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['status']=='passed' else 1)
