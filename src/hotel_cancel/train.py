"""Run the supplied booking-time baseline without notebook state."""
import argparse
from dataclasses import dataclass
import json
import logging
import time

import pandas as pd

from hotel_cancel.config import load_config
from hotel_cancel.data import load_bookings, separate_outcome
from hotel_cancel.features import build_features, select_top_agents
from hotel_cancel.model import fit, save_model
from hotel_cancel.evaluate import split_masks, per_hotel, holdout_fingerprint, diagnostic_gate, guard_temporal_splits
from hotel_cancel.logging_setup import setup_logging

logger = logging.getLogger(__name__)


@dataclass
class BaselineResult:
    bookings: pd.DataFrame
    outcome: pd.DataFrame
    features: pd.DataFrame
    masks: dict
    model: object
    top_agents: object
    probabilities: object
    metrics: pd.DataFrame
    gate: pd.DataFrame
    fingerprint: str
    runtime_seconds: float


def run_baseline(config, *, use_cache=False, save=True):
    """Fit the pooled notebook model and report per-hotel validation/test scores.

    Rebuild from raw data by default: the notebook's processed cache has no
    source/window identity. No policy selection or model tuning occurs here.
    """
    started = time.perf_counter()
    raw = load_bookings(config, use_cache=use_cache)
    bk, outcome = separate_outcome(raw)
    y = outcome.is_canceled
    masks = split_masks(bk, config)
    guard_temporal_splits(raw, masks)
    top_agents = select_top_agents(bk, masks["train"])
    X = build_features(bk, top_agents)
    columns = list(X.columns)
    model = fit(columns, masks["train"], X, y, seed=config["seed"])
    probabilities = model.predict_proba(X[columns])[:, 1]
    metrics = pd.concat({name: per_hotel(probabilities[mask.values], mask, bk, y, config["hotels"])
                         for name, mask in masks.items() if name != "train"})
    gate = diagnostic_gate(metrics.loc["test"], config)
    fingerprint = holdout_fingerprint(X, y, masks["test"])
    elapsed = time.perf_counter() - started
    result = BaselineResult(bk, outcome, X, masks, model, top_agents,
                            probabilities, metrics, gate, fingerprint, elapsed)
    if save:
        output = config["model_dir"]
        save_model(model, output / "baseline.joblib", top_agents=top_agents, feature_columns=columns)
        metrics.to_csv(output / "baseline_metrics.csv")
        gate.to_csv(output / "baseline_gate.csv")
        report = {"split_counts": {k: int(v.sum()) for k, v in masks.items()},
                  "holdout_sha256": fingerprint, "runtime_seconds": elapsed,
                  "seed": config["seed"], "model_parameters": model.get_params()}
        (output / "baseline_run.json").write_text(json.dumps(report, indent=2) + "\n")
    logger.info("Baseline finished in %.1fs; split counts %s", elapsed,
                {k: int(v.sum()) for k, v in masks.items()})
    logger.info("Test gate:\n%s", gate.to_string())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--project-root")
    args = parser.parse_args()
    config = load_config(args.config, project_root=args.project_root)
    setup_logging(config["log_level"])
    run_baseline(config)
    # A diagnostic Resort FAIL is an expected baseline result, not a command error.
    # A deployment/CI quality gate will be implemented separately.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
