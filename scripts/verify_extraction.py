"""Check the extracted pipeline against captured original-notebook results."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from hotel_cancel.config import load_config
from hotel_cancel.train import run_baseline
from hotel_cancel.policy import run_policy_baseline

root = Path(__file__).resolve().parents[1]
expected = json.loads((root / 'docs/evidence/reference-run/results.json').read_text())
baseline = run_baseline(load_config(), save=False)
policy = run_policy_baseline(baseline, load_config())
assert {k: int(v.sum()) for k, v in baseline.masks.items()} == expected['split_counts']
assert baseline.fingerprint == expected['holdout_sha256']
pd.testing.assert_frame_equal(baseline.metrics.loc['test'], pd.DataFrame(expected['booking_metrics']).T, check_exact=True)
assert policy.chosen == expected['chosen_policies']
actual = policy.summary.reset_index()
reference = pd.DataFrame(expected['policy_test_results'])
pd.testing.assert_frame_equal(actual, reference, check_exact=True)
for hotel, values in expected['tonight'].items():
    for key, value in values.items():
        assert policy.tonight[hotel][key] == value, (hotel, key)
# Compare feature recipe to the actual reference function, including dtypes/order.
import ast
notebook = json.loads((root / 'notebooks/reference/19_hotel_cancellations.ipynb').read_text())
tree = ast.parse(''.join(notebook['cells'][10]['source']))
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build_features')
namespace = {'pd': pd, 'TOP_AGENTS': baseline.top_agents}
exec(compile(ast.Module(body=[fn], type_ignores=[]), '<reference-features>', 'exec'), namespace)
pd.testing.assert_frame_equal(baseline.features, namespace['build_features'](baseline.bookings), check_exact=True)
report = {'status': 'passed', 'comparison': 'exact equality to full-precision original notebook evidence',
          'checks': ['split counts', 'holdout fingerprint', 'booking metrics', 'policy choices', 'all policy summary values', 'all tonight values', 'all-row feature values/dtypes/order'],
          'booking_runtime_seconds': baseline.runtime_seconds, 'policy_runtime_seconds': policy.runtime_seconds}
out = root / 'artifacts/extraction-verification.json'
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
