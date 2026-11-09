"""Frozen, per-hotel booking-horizon evaluation; never select on holdout."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss

from hotel_cancel.config import load_config
from hotel_cancel.data import load_bookings, separate_outcome
from hotel_cancel.evaluate import split_masks, holdout_fingerprint, guard_temporal_splits
from hotel_cancel.features import build_features, select_top_agents
from hotel_cancel.model import fit

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reliability(y, p, bins=10):
    """Equal-width [0,1] bins; p=1 belongs to the final bin. Empty bins retained."""
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    if y.ndim != 1 or p.shape != y.shape or not len(y):
        raise ValueError('Labels and probabilities must be nonempty aligned vectors')
    if not np.isin(y, [0, 1]).all() or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('Expected binary labels and finite probabilities in [0,1]')
    if type(bins) is not int or bins < 1:
        raise ValueError('bins must be a positive integer')
    ids = np.minimum((p * bins).astype(int), bins - 1)
    rows = []
    ece = 0.0
    for i in range(bins):
        mask = ids == i
        n = int(mask.sum())
        predicted = float(p[mask].mean()) if n else None
        observed = float(y[mask].mean()) if n else None
        if n:
            ece += n / len(y) * abs(predicted - observed)
        rows.append(dict(bin=i, low=i / bins, high=(i + 1) / bins,
                         n=n, mean_probability=predicted, observed_rate=observed))
    return rows, float(ece)


def assess(y, p, *, min_auprc, ratio_band, max_ece, bins=10):
    rows, ece = reliability(y, p, bins)
    y, p = np.asarray(y), np.asarray(p)
    usable = len(np.unique(y)) == 2
    auprc = float(average_precision_score(y, p)) if usable else None
    ratio = float(p.sum() / y.sum()) if y.sum() else None
    checks = dict(two_classes=usable, auprc=usable and auprc >= min_auprc,
                  calibration_ratio=ratio is not None and ratio_band[0] <= ratio <= ratio_band[1],
                  ece=ece <= max_ece)
    return dict(n=len(y), cancellations=int(y.sum()), auprc=auprc,
                expected_observed_ratio=ratio, ece=ece, brier=float(brier_score_loss(y, p)),
                checks=checks, gate='PASS' if all(checks.values()) else 'FAIL'), rows


def verify_identity(actual, expected):
    if set(actual) != set(expected):
        raise ValueError("Frozen evaluation identity keys differ")
    for key in expected:
        if actual.get(key) != expected[key]:
            raise ValueError(f'Frozen evaluation identity mismatch: {key}; do not regenerate the lock to pass CI')


def prepare(config):
    # No download and no unchecked processed cache in the evaluation path.
    raw_path = config['raw_dir'] / 'hotel_bookings.csv'
    if not raw_path.is_file():
        raise ValueError('Install the attributed raw dataset locally before running CI')
    raw = load_bookings(config, use_cache=False)
    bk, outcome = separate_outcome(raw)
    masks = split_masks(bk, config)
    guard_temporal_splits(raw, masks)
    agents = select_top_agents(bk, masks['train'])
    X = build_features(bk, agents)
    y = outcome.is_canceled
    dates = bk.loc[masks['test'], ['arrival', 'hotel']]
    date_hash = hashlib.sha256(pd.util.hash_pandas_object(dates, index=True).values.tobytes()).hexdigest()
    identity = dict(raw_sha256=sha(raw_path), holdout_sha256=holdout_fingerprint(X, y, masks['test']),
                    holdout_dates_sha256=date_hash, feature_columns=list(X.columns),
                    split_counts={k: int(v.sum()) for k, v in masks.items()},
                    per_hotel_test_counts=bk.loc[masks['test'], 'hotel'].value_counts().sort_index().to_dict(),
                    boundaries={k: str(config[k].date()) for k in ['window_start', 'train_end', 'calib_end', 'valid_end', 'test_end', 'window_end']},
                    seed=config['seed'])
    return bk, X, y, masks, identity


def plot_reliability(tables, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(tables), figsize=(10, 4), squeeze=False)
    for ax, (hotel, rows) in zip(axes[0], tables.items()):
        populated = [r for r in rows if r['n']]
        ax.plot([0, 1], [0, 1], '--', color='gray', label='Perfect calibration')
        ax.plot([r['mean_probability'] for r in populated], [r['observed_rate'] for r in populated], 'o-', label='Frozen test')
        ax.set(xlim=(0, 1), ylim=(0, 1), xlabel='Mean predicted cancellation', ylabel='Observed cancellation rate', title=hotel)
        ax.legend()
    fig.suptitle('Booking-to-arrival horizon · Jan–Aug 2017 · 10 equal-width bins')
    fig.tight_layout()
    fig.savefig(output / 'reliability.png', dpi=160)
    plt.close(fig)


def run(config, lock, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Remove obsolete successful evidence before any input or model check.
    for name in ['report.json', 'reliability.csv', 'reliability.png']:
        (output / name).unlink(missing_ok=True)
    try:
        frozen = json.loads(Path(lock).read_text())
        if frozen['schema_version'] != 1:
            raise ValueError('Unsupported evaluation lock')
        bk, X, y, masks, identity = prepare(config)
        verify_identity(identity, frozen['identity'])
        if set(frozen['thresholds']) != set(config['hotels']):
            raise ValueError('Gate must cover both hotels')
        # Fixed supplied learner. Only training rows enter fit; no calibrator or policy fitting.
        model = fit(list(X.columns), masks['train'], X, y, seed=config['seed'])
        p = model.predict_proba(X.loc[masks['test']])[:, 1]
        test = bk.loc[masks['test']]
        labels = y.loc[masks['test']].to_numpy()
        tables, hotels = {}, {}
        for hotel, thresholds in frozen['thresholds'].items():
            select = test.hotel.astype(str).eq(hotel).to_numpy()
            hotels[hotel], tables[hotel] = assess(labels[select], p[select], **thresholds)
        if set(hotels) != set(config['hotels']):
            raise ValueError('Gate must cover both hotels')
        passed = all(h['gate'] == 'PASS' for h in hotels.values())
        report = dict(status='PASS' if passed else 'FAIL', scope='booking_to_arrival_historical_holdout',
                      identity_verified=True, identity=identity, lock_sha256=sha(lock),
                      thresholds=frozen['thresholds'], hotels=hotels,
                      fitted_on='train only: Jul 2015–Jun 2016', selected_on_holdout=False,
                      packages={k: version(k) for k in ['pandas', 'numpy', 'scikit-learn', 'lightgbm']},
                      python=platform.python_version(),
                      source_sha256={p.name: sha(p) for p in Path(__file__).parent.glob('*.py')},
                      failure_response='Block promotion for a failing hotel; retain review-only simulation. Investigate with training/validation data; never tune on this holdout.')
        pd.DataFrame([dict(hotel=h, **row) for h, rows in tables.items() for row in rows]).to_csv(output / 'reliability.csv', index=False)
        plot_reliability(tables, output)
        code = 0 if passed else 1
    except Exception as error:
        report = dict(status='ERROR', identity_verified=False, error_type=type(error).__name__, error=str(error))
        code = 2
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return code, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config')
    parser.add_argument('--lock', default=str(ROOT / 'config/evaluation-lock.json'))
    parser.add_argument('--output', default=str(ROOT / 'docs/evidence/stage8'))
    args = parser.parse_args()
    code, report = run(load_config(args.config), args.lock, args.output)
    print(json.dumps(report.get('hotels', report), indent=2))
    print(f'Quality gate: {report["status"]}; evidence: {args.output}')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
