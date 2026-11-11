"""One booking contract and feature path shared by HTTP and nightly scoring."""

import hashlib
import json
from pathlib import Path
import shutil
import threading

import joblib
import numpy as np
import pandas as pd

from hotel_cancel.features import BOOKING_INPUTS, FEATURE_COLUMNS, build_features

CATEGORIES = [
    "hotel",
    "meal",
    "market_segment",
    "distribution_channel",
    "reserved_room_type",
    "deposit_type",
    "customer_type",
]
COUNTS = [
    "lead_time",
    "stays_in_weekend_nights",
    "stays_in_week_nights",
    "adults",
    "children",
    "babies",
    "is_repeated_guest",
    "previous_cancellations",
    "previous_bookings_not_canceled",
]
REQUEST_FIELDS = set(BOOKING_INPUTS) - {"booked"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def booking_frame(records):
    if not isinstance(records, list) or not records:
        raise ValueError("At least one booking is required")
    clean = []
    for row in records:
        if not isinstance(row, dict) or set(row) != REQUEST_FIELDS:
            raise ValueError("Booking must contain exactly: " + ", ".join(sorted(REQUEST_FIELDS)))
        row = dict(row)
        if row["hotel"] not in ["City Hotel", "Resort Hotel"]:
            raise ValueError("Unknown hotel")
        if not isinstance(row["arrival"], str):
            raise ValueError("arrival must be YYYY-MM-DD")
        try:
            date = pd.Timestamp(row["arrival"])
            if row["arrival"] != date.strftime("%Y-%m-%d") or pd.isna(date):
                raise ValueError()
        except (ValueError, TypeError, OverflowError):
            raise ValueError("arrival must be YYYY-MM-DD") from None
        row["arrival"] = date
        if row["children"] is None:
            row["children"] = 0
        for name in COUNTS:
            if type(row[name]) is not int or not 0 <= row[name] <= 100000:
                raise ValueError(f"{name} must be a non-negative integer <= 100000")
        if row["is_repeated_guest"] not in (0, 1):
            raise ValueError("is_repeated_guest must be 0 or 1")
        if type(row["adr"]) not in (int, float) or not np.isfinite(row["adr"]):
            raise ValueError("adr must be finite")
        row["adr"] = float(row["adr"])  # Preserve the baseline, including flagged negative/zero ADR.
        for name in CATEGORIES:
            if not isinstance(row[name], str) or not row[name].strip() or len(row[name]) > 128:
                raise ValueError(f"{name} must be a nonempty code of at most 128 characters")
        for name in ["agent", "company"]:
            value = row[name]
            if value is None:
                value = "none"
            if type(value) is int and value >= 0:
                value = str(value)
            if not isinstance(value, str) or not value or len(value) > 128:
                raise ValueError(f"{name} must be a string code, integer ID or null")
            row[name] = value
        try:
            row["booked"] = date - pd.Timedelta(days=row["lead_time"])
        except (OverflowError, ValueError):
            raise ValueError("lead_time overflows supported dates") from None
        clean.append(row)
    frame = pd.DataFrame(clean)
    for name in CATEGORIES:
        frame[name] = frame[name].astype("category")
    return frame.loc[:, BOOKING_INPUTS]


class Predictor:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.manifest = json.loads((self.directory / "manifest.json").read_text())
        if self.manifest.get("schema_version") != 1:
            raise ValueError("Unsupported serving manifest")
        for name in ["booking_model.joblib", "policy_state.joblib"]:
            if digest(self.directory / name) != self.manifest["sha256"][name]:
                raise ValueError(f"Artifact fingerprint mismatch: {name}")
        self.bundle = joblib.load(self.directory / "booking_model.joblib")
        if self.bundle["feature_columns"] != FEATURE_COLUMNS:
            raise ValueError("Artifact feature schema mismatch")
        self.policy = joblib.load(self.directory / "policy_state.joblib")
        self.version = self.manifest["sha256"]["booking_model.joblib"]
        self.lock = threading.Lock()

    def predict(self, records):
        frame = booking_frame(records)
        X = build_features(frame, self.bundle["top_agents"])
        # Serialise model calls; HTTP handling may run in separate threads.
        with self.lock:
            p = self.bundle["model"].predict_proba(X[self.bundle["feature_columns"]])[:, 1]
        return p


def export_runtime(run, output):
    """Export an explicitly chosen baseline run; never guess the latest model."""
    run, output = Path(run), Path(output)
    report = json.loads((run / "run.json").read_text())
    if report["status"] != "passed":
        raise ValueError("Only a completed reference baseline can be exported")
    output.mkdir(parents=True, exist_ok=False)
    names = ["booking_model.joblib", "policy_state.joblib"]
    for name in names:
        shutil.copy2(run / name, output / name)
    manifest = dict(
        schema_version=1,
        source_run=report["run_id"],
        raw_sha256=report["raw_sha256"],
        diagnostic_gate=report["diagnostic_gate"],
        policy_source="given C2 reference baseline; review only",
        sha256={name: digest(output / name) for name in names},
    )
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    Predictor(output)  # Fail immediately if artifacts cannot be loaded together.


def main():
    import argparse

    p = argparse.ArgumentParser(description="Export trusted local reference model and policy artifacts")
    p.add_argument("--run", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    export_runtime(args.run, args.output)


if __name__ == "__main__":
    main()
