"""Immutable dataset-derived as-of snapshots, in files or PostgreSQL JSONB."""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from hotel_cancel.serving import Predictor, REQUEST_FIELDS

BLOCK_KEY = [
    "hotel",
    "arrival",
    "booked",
    "market_segment",
    "distribution_channel",
    "deposit_type",
    "agent",
    "company",
    "reserved_room_type",
    "customer_type",
    "meal",
    "adults",
    "children",
    "adr",
    "stays_in_weekend_nights",
    "stays_in_week_nights",
]
DDL = """CREATE TABLE IF NOT EXISTS hotel_snapshots (
 snapshot_id TEXT PRIMARY KEY,
 decision_date DATE NOT NULL,
 lead_days INTEGER NOT NULL CHECK (lead_days BETWEEN 0 AND 14),
 payload JSONB NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""


def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def seal_snapshot(payload):
    result = dict(payload)
    result["snapshot_id"] = hashlib.sha256(canonical(payload).encode()).hexdigest()
    return result


def verify_snapshot(snapshot):
    payload = dict(snapshot)
    identifier = payload.pop("snapshot_id")
    if hashlib.sha256(canonical(payload).encode()).hexdigest() != identifier:
        raise ValueError("Snapshot fingerprint mismatch")
    if snapshot["schema_version"] != 1:
        raise ValueError("Unsupported snapshot version")
    return snapshot


def write_postgres(snapshot, database_url):
    import psycopg
    from psycopg.types.json import Jsonb

    verify_snapshot(snapshot)
    with psycopg.connect(database_url, connect_timeout=10) as conn:
        conn.execute(DDL)
        conn.execute(
            "INSERT INTO hotel_snapshots (snapshot_id,decision_date,lead_days,payload) VALUES (%s,%s,%s,%s) ON CONFLICT (snapshot_id) DO NOTHING",
            (
                snapshot["snapshot_id"],
                snapshot["decision_date"],
                snapshot["lead_days"],
                Jsonb(snapshot),
            ),
        )
        existing = conn.execute(
            "SELECT payload FROM hotel_snapshots WHERE snapshot_id=%s",
            (snapshot["snapshot_id"],),
        ).fetchone()[0]
        if existing != snapshot:
            raise ValueError("Existing database snapshot differs")


def read_postgres(identifier, database_url):
    import psycopg

    with psycopg.connect(database_url, connect_timeout=10) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        row = conn.execute("SELECT payload FROM hotel_snapshots WHERE snapshot_id=%s", (identifier,)).fetchone()
    if row is None:
        raise ValueError("Snapshot not found")
    return verify_snapshot(row[0])


def create_snapshot(config, predictor, decision_date):
    # Raw loader is deliberately absent from HTTP/batch runtime paths.
    from hotel_cancel.data import load_bookings, separate_outcome, get_raw
    from hotel_cancel.history import reconstruct_as_of

    decision = pd.Timestamp(decision_date)
    if str(decision_date) != decision.strftime("%Y-%m-%d"):
        raise ValueError("decision_date must be YYYY-MM-DD")
    cfg = predictor.policy["config"]
    h = int(cfg["decision_lead_days"])
    if decision <= pd.Timestamp(cfg["calib_end"]):
        raise ValueError("Decision must be after the policy calibration period has matured")
    arrival = decision + pd.Timedelta(days=h)
    if not config["window_start"] <= arrival < config["window_end"]:
        raise ValueError("Target arrival is outside the source dataset window")
    raw = load_bookings(config, use_cache=False)
    bk, outcome = separate_outcome(raw)
    if (
        hashlib.sha256(get_raw("hotel_bookings.csv", config).read_bytes()).hexdigest()
        != predictor.manifest["raw_sha256"]
    ):
        raise ValueError("Dataset differs from runtime artifact provenance")
    _, live, late = reconstruct_as_of(bk, outcome, h)
    # Retain all rows of reconstructed blocks; synthetic row IDs preserve exact duplicates.
    block = bk.groupby(BLOCK_KEY, observed=True, dropna=False).ngroup()
    start = decision - pd.Timedelta(weeks=max(cfg["recal_weeks_grid"]))
    history_mask = live & (bk.arrival >= start) & (bk.arrival < decision)
    target = live & (bk.arrival == arrival)
    needed = history_mask | target
    records = []
    selected = bk.loc[needed, sorted(REQUEST_FIELDS)].copy()
    selected["arrival"] = selected.arrival.dt.strftime("%Y-%m-%d")
    payloads = json.loads(selected.to_json(orient="records"))
    probs = predictor.predict(payloads) if payloads else np.array([])
    temp = bk.loc[needed, ["hotel", "arrival"]].copy()
    temp["p_booking"] = probs
    temp["p_cal"] = np.nan
    # Only labels observable before the current decision enter historical aggregates.
    temp["y"] = (late & (outcome.status_date < decision)).loc[needed].astype(int)
    for hotel in cfg["hotels"]:
        mask = temp.hotel.astype(str) == hotel
        if mask.any():
            temp.loc[mask, "p_cal"] = predictor.policy["calibrators"][hotel].predict(
                temp.loc[mask, "p_booking"], lead_days=h
            )
    for (index, _), payload in zip(selected.iterrows(), payloads):
        if target.loc[index]:
            records.append(
                dict(
                    booking_id=f"row-{index}",
                    block_id=str(int(block.loc[index])),
                    booking=payload,
                )
            )
    hist = (
        temp.loc[temp.arrival < decision]
        .groupby(["hotel", "arrival"], observed=True)
        .agg(observed=("y", "sum"), predicted=("p_cal", "sum"), count=("y", "size"))
    )
    history = []
    for hotel in cfg["hotels"]:
        for night in pd.date_range(start, decision - pd.Timedelta(days=1)):
            key = (hotel, night)
            values = hist.loc[key] if key in hist.index else None
            history.append(
                dict(
                    hotel=hotel,
                    night=str(night.date()),
                    observed=int(values.observed) if values is not None else 0,
                    predicted=float(values.predicted) if values is not None else 0.0,
                    count=int(values["count"]) if values is not None else 0,
                )
            )
    return seal_snapshot(
        dict(
            schema_version=1,
            decision_date=str(decision.date()),
            arrival=str(arrival.date()),
            lead_days=h,
            model_version=predictor.version,
            policy_version=predictor.manifest["sha256"]["policy_state.joblib"],
            source_sha256=predictor.manifest["raw_sha256"],
            reconstruction="final-state retrospective approximation; same-day entries excluded",
            bookings=records,
            history=history,
        )
    )


def main():
    from hotel_cancel.config import load_config

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config")
    p.add_argument("--bundle", default=os.environ.get("SERVING_BUNDLE", "models/serving"))
    p.add_argument("--decision-date", required=True)
    p.add_argument("--output", required=True, help="Local JSON snapshot for review/replay")
    p.add_argument("--postgres", action="store_true", help="Also persist using DATABASE_URL")
    args = p.parse_args()
    snapshot = create_snapshot(load_config(args.config), Predictor(args.bundle), args.decision_date)
    if args.postgres:
        write_postgres(snapshot, os.environ["DATABASE_URL"])
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, allow_nan=False) + "\n")
    print(snapshot["snapshot_id"])


if __name__ == "__main__":
    main()
