"""Historical diagnostic replay of frozen artifacts; no retraining or policy selection."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace

import numpy as np
import pandas as pd
from psycopg.types.json import Jsonb

from hotel_cancel.config import load_config
from hotel_cancel.data import load_bookings, separate_outcome, get_raw
from hotel_cancel.features import build_features
from hotel_cancel.policy import (
    prepare_policy,
    run_policies,
    summarise,
    night_room_value,
)
from hotel_cancel.serving import Predictor
from hotel_cancel.monitoring import Telemetry


def psi_num(ref, cur, bins=10):
    if len(ref) == 0 or len(cur) == 0:
        raise ValueError("PSI requires two nonempty samples")
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) == 1:
        edges = np.array(
            [
                -np.inf,
                np.nextafter(float(edges[0]), -np.inf),
                np.nextafter(float(edges[0]), np.inf),
                np.inf,
            ]
        )
    else:
        edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / len(ref) + 1e-6
    c = np.histogram(cur, edges)[0] / len(cur) + 1e-6
    return float(np.sum((c - r) * np.log(c / r)))


def psi_cat(ref, cur):
    if len(ref) == 0 or len(cur) == 0:
        raise ValueError("PSI requires two nonempty samples")
    r = pd.Series(ref).value_counts(normalize=True)
    c = pd.Series(cur).value_counts(normalize=True)
    idx = r.index.union(c.index)
    r, c = r.reindex(idx, fill_value=0) + 1e-4, c.reindex(idx, fill_value=0) + 1e-4
    return float(np.sum((c - r) * np.log(c / r)))


def weekly(frame, horizon, as_of):
    f = frame.copy()
    f["week"] = f.arrival.dt.to_period("W-SUN").dt.start_time
    f = f[f.week + pd.Timedelta(days=7) <= as_of]
    grouped = (
        f.groupby(["hotel", "week"], observed=True)
        .agg(expected=("p", "sum"), observed=("y", "sum"), n=("y", "size"))
        .reset_index()
    )
    grouped["horizon"] = horizon
    grouped["ratio"] = grouped.expected / grouped.observed.replace(0, np.nan)
    grouped["enough_labels"] = (grouped.n >= 30) & (grouped.observed >= 20)
    grouped["alert"] = grouped.enough_labels & ~grouped.ratio.between(0.85, 1.15)
    return grouped


def run_replay(config, predictor, as_of, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    raw = load_bookings(config, use_cache=False)
    bk, outcome = separate_outcome(raw)
    X = build_features(bk, predictor.bundle["top_agents"])
    p = predictor.bundle["model"].predict_proba(X[predictor.bundle["feature_columns"]])[:, 1]
    cfg = dict(
        config,
        **{
            k: predictor.policy["config"][k]
            for k in [
                "decision_lead_days",
                "recal_weeks_grid",
                "walk_cost_eur",
                "variable_cost_eur",
            ]
        },
    )
    snap, policies, agg, _, _ = prepare_policy(
        SimpleNamespace(bookings=bk, outcome=outcome, probabilities=p),
        cfg,
        calibrators=predictor.policy["calibrators"],
        flat_rates=predictor.policy["flat_rates"],
    )
    mature = (bk.arrival + pd.Timedelta(days=1) <= as_of) & ((outcome.is_canceled == 0) | (outcome.status_date < as_of))
    later = mature & (bk.arrival >= config["train_end"])
    booking = pd.DataFrame(dict(hotel=bk.hotel.astype(str), arrival=bk.arrival, p=p, y=outcome.is_canceled)).loc[later]
    weeks = [weekly(booking, "booking_to_arrival", as_of)]
    late = snap[(snap.arrival >= config["train_end"]) & (snap.arrival + pd.Timedelta(days=1) <= as_of)].copy()
    # Do not consume a cancellation status that had not yet been recorded at replay time.
    late = late.loc[(outcome.is_canceled.loc[late.index] == 0) | (outcome.status_date.loc[late.index] < as_of)]
    weeks.append(weekly(late.rename(columns={"p_cal": "p"}), "active_7_day", as_of))
    all_weeks = pd.concat(weeks, ignore_index=True)
    all_weeks.to_csv(output / "weekly-calibration.csv", index=False)
    train = bk.arrival < config["train_end"]
    qtr = bk.arrival.dt.to_period("Q")
    top = bk.loc[train, "country"].value_counts().index[:20]
    country = bk.country.astype(str).where(bk.country.isin(top), "other")
    drift = []
    for hotel in config["hotels"]:
        ref = train & (bk.hotel == hotel)
        for quarter in sorted(qtr[later].unique()):
            cur = later & (qtr == quarter) & (bk.hotel == hotel)
            if not cur.any():
                continue
            for feature in [
                "lead_time",
                "market_segment",
                "distribution_channel",
                "country",
                "deposit_type",
            ]:
                series = country if feature == "country" else bk[feature]
                value = (
                    psi_num(series[ref], series[cur])
                    if feature == "lead_time"
                    else psi_cat(series[ref].astype(str), series[cur].astype(str))
                )
                drift.append(
                    dict(
                        hotel=hotel,
                        quarter=str(quarter),
                        feature=feature,
                        psi=value,
                        n=int(cur.sum()),
                        period_start=str(quarter.start_time.date()),
                        period_end_exclusive=str(
                            min(
                                quarter.end_time.normalize() + pd.Timedelta(days=1),
                                as_of,
                                config["window_end"],
                            ).date()
                        ),
                    )
                )
    drift = pd.DataFrame(drift)
    drift.to_csv(output / "quarterly-drift.csv", index=False)
    nights = snap[(snap.arrival >= config["valid_end"]) & (snap.arrival + pd.Timedelta(days=1) <= as_of)]
    nights = nights.loc[(outcome.is_canceled.loc[nights.index] == 0) | (outcome.status_date.loc[nights.index] < as_of)]
    costs = []
    for hotel in config["hotels"]:
        name = predictor.policy["chosen_policies"][hotel]
        costs.append(
            run_policies(
                nights[nights.hotel == hotel],
                {"no overbooking": None, name: policies[name]},
                lambda g: night_room_value(g, cfg["variable_cost_eur"]),
                block_agg=agg,
                walk_cost=cfg["walk_cost_eur"],
                decision_lead_days=cfg["decision_lead_days"],
            )
        )
    costs = pd.concat(costs, ignore_index=True)
    costs.to_csv(output / "policy-nights.csv", index=False)
    summary = summarise(costs).reset_index()
    summary.to_csv(output / "policy-summary.csv", index=False)
    latest = all_weeks.sort_values("week").groupby(["hotel", "horizon"]).tail(1)
    latest_drift = drift.sort_values("quarter").groupby(["hotel", "feature"]).tail(1)
    report = dict(
        scope="historical_dataset_replay_not_live_quality",
        as_of_exclusive=str(as_of.date()),
        source_sha256={
            n: hashlib.sha256((Path(__file__).parent / n).read_bytes()).hexdigest()
            for n in ["monitor_replay.py", "policy.py", "model.py", "features.py"]
        },
        generated_at_epoch=time.time(),
        model_version=predictor.version,
        policy_version=predictor.manifest["sha256"]["policy_state.joblib"],
        raw_sha256=hashlib.sha256(get_raw("hotel_bookings.csv", config).read_bytes()).hexdigest(),
        thresholds=dict(
            calibration_low=0.85,
            calibration_high=1.15,
            min_bookings=30,
            min_observed_cancellations=20,
            psi_warning=0.1,
            psi_action=0.25,
        ),
        latest_week=json.loads(latest.to_json(orient="records", date_format="iso")),
        latest_drift=json.loads(latest_drift.to_json(orient="records")),
        policy_costs=json.loads(
            summary[["hotel", "policy", "cost_per_night", "saving vs none (€)"]].to_json(orient="records")
        ),
        fitted_or_selected_on_holdout=False,
        limitations=[
            "Final-state features do not establish event-time availability",
            "Country is offline diagnostic only and never an online input",
            "2017Q3 is partial July-August",
            "Capacity unknown; arrival-night sold-out/no-resale cost proxy",
            "No new learner or calibrator fitting; saved policy choices reused",
        ],
    )
    identifier = hashlib.sha256(json.dumps(report, sort_keys=True, allow_nan=False).encode()).hexdigest()
    report["report_id"] = identifier
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", default="models/serving")
    p.add_argument("--as-of", default="2017-09-02")
    p.add_argument("--output", default="docs/evidence/stage7/replay")
    p.add_argument("--postgres", action="store_true")
    args = p.parse_args()
    report = run_replay(load_config(), Predictor(args.bundle), pd.Timestamp(args.as_of), args.output)
    if args.postgres:
        telemetry = Telemetry(os.environ["DATABASE_URL"])
        with telemetry.connect() as c:
            c.execute(
                "INSERT INTO hotel_monitoring_reports (report_id,payload) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (report["report_id"], Jsonb(report)),
            )
    print(json.dumps(dict(report_id=report["report_id"], scope=report["scope"])))


if __name__ == "__main__":
    main()
