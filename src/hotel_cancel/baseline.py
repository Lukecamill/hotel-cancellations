"""Run and save the complete given booking and overbooking baseline."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import logging
from pathlib import Path
import platform
import subprocess
import time
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd

from hotel_cancel.config import load_config
from hotel_cancel.data import get_raw
from hotel_cancel.logging_setup import setup_logging
from hotel_cancel.model import save_model
from hotel_cancel.policy import run_policy_baseline
from hotel_cancel.train import run_baseline

logger = logging.getLogger(__name__)


def write_json(path, value):
    def encode(item):
        if isinstance(item, (Path, pd.Timestamp)):
            return str(item)
        if isinstance(item, np.generic):
            return item.item()
        raise TypeError(f"Cannot encode {type(item).__name__}")

    path.write_text(json.dumps(value, indent=2, default=encode, allow_nan=False) + "\n")


def run_complete_baseline(config):
    """Fresh raw loading; unique run directory; no policy/model tuning."""
    started = time.perf_counter()
    np.random.seed(config["seed"])
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    output = config["model_dir"] / "baseline" / run_id
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "run_id": run_id,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
    }
    write_json(output / "run.json", report)
    try:
        raw = get_raw("hotel_bookings.csv", config)
        report["raw_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
        report["raw_path"] = str(raw)
        # Save effective, non-secret settings; never capture environment variables.
        settings = {
            k: config[k]
            for k in (
                "seed",
                "kaggle_handle",
                "window_start",
                "window_end",
                "train_end",
                "calib_end",
                "valid_end",
                "test_end",
                "decision_lead_days",
                "tonight",
                "walk_cost_eur",
                "variable_cost_eur",
                "recal_weeks_grid",
                "hotels",
                "gate_min_auprc",
                "calibration_band",
                "data_dir",
                "model_dir",
                "log_level",
            )
        }
        write_json(output / "config.json", settings)
        booking = run_baseline(config, use_cache=False, save=False)
        policy = run_policy_baseline(booking, config)
        save_model(
            booking.model,
            output / "booking_model.joblib",
            top_agents=booking.top_agents,
            feature_columns=list(booking.features.columns),
        )
        joblib.dump(
            {
                "calibrators": policy.calibrators,
                "flat_rates": policy.flat_rates,
                "chosen_policies": policy.chosen,
                "config": settings,
            },
            output / "policy_state.joblib",
        )
        booking.metrics.to_csv(output / "booking_metrics.csv")
        booking.gate.to_csv(output / "booking_gate.csv")
        policy.selection.to_csv(output / "policy_validation.csv")
        policy.nights.to_csv(output / "policy_test_nights.csv", index=False)
        policy.summary.to_csv(output / "policy_test_summary.csv")
        write_json(output / "tonight.json", policy.tonight)
        write_json(output / "chosen_policies.json", policy.chosen)
        report.update(
            status="passed",
            split_counts={k: int(v.sum()) for k, v in booking.masks.items()},
            holdout_sha256=booking.fingerprint,
            booking_runtime_seconds=booking.runtime_seconds,
            policy_runtime_seconds=policy.runtime_seconds,
            diagnostic_gate=booking.gate["gate"].to_dict(),
            python=platform.python_version(),
            platform=platform.platform(),
            packages={
                p: version(p)
                for p in [
                    "numpy",
                    "pandas",
                    "lightgbm",
                    "scikit-learn",
                    "pyarrow",
                    "joblib",
                ]
            },
        )
        sources = Path(__file__).resolve().parent
        report["source_sha256"] = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources.glob("*.py"))
        }
        root = sources.parents[1]
        try:
            report["git_commit"] = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            report["git_status"] = subprocess.check_output(["git", "status", "--short"], cwd=root, text=True)
        except (OSError, subprocess.CalledProcessError):
            report["git_commit"] = None
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        report["total_runtime_seconds"] = time.perf_counter() - started
        write_json(output / "run.json", report)
    logger.info("Complete baseline saved to %s", output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--project-root")
    args = parser.parse_args()
    config = load_config(args.config, project_root=args.project_root)
    setup_logging(config["log_level"])
    output = run_complete_baseline(config)
    print(f"Baseline saved: {output}")
    print("Resort diagnostic FAIL is expected; this command is not a deployment gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
