"""Validation-only policy sensitivity; never score or select on the 2017 holdout."""

import argparse
import hashlib
from importlib.metadata import version
import platform
import json
from pathlib import Path
import time
from types import SimpleNamespace

import numpy as np
import pandas as pd
import yaml

from hotel_cancel.config import load_config
from hotel_cancel.data import load_bookings, separate_outcome
from hotel_cancel.features import build_features, select_top_agents
from hotel_cancel.model import fit
from hotel_cancel.policy import prepare_policy, released_distribution


def check_grid(grid):
    rules = {
        "lead_days": lambda x: type(x) is int and 0 <= x <= 14,
        "walk_costs_eur": lambda x: type(x) in (int, float) and np.isfinite(x) and x > 0,
        "variable_costs_eur": lambda x: type(x) in (int, float) and np.isfinite(x) and x >= 0,
        "resale_rates": lambda x: type(x) in (int, float) and np.isfinite(x) and 0 <= x <= 1,
        "recal_weeks": lambda x: type(x) is int and x > 0,
    }
    for key, rule in rules.items():
        values = grid.get(key)
        if (
            not isinstance(values, list)
            or not values
            or not all(rule(x) for x in values)
            or len(set(values)) != len(values)
        ):
            raise ValueError(f"Invalid sensitivity grid: {key}")


def effective_room_value(adr, variable_cost, resale_rate):
    """Expected residual empty-room loss under exogenous same-margin resale."""
    return max(float(adr) - variable_cost, 0.0) * (1.0 - resale_rate)


def choose_quantity(dist, room_value, walk_cost):
    return min(
        int(np.searchsorted(np.cumsum(dist), room_value / (room_value + walk_cost) - 1e-12)),
        len(dist) - 1,
    )


def select_winners(scores):
    # Deterministic ties: prefer no overbooking, then policy name.
    keys = ["lead_days", "walk_cost_eur", "variable_cost_eur", "resale_rate", "hotel"]
    s = scores.assign(tie=(scores.policy != "no overbooking").astype(int))
    return s.sort_values(keys + ["cost_per_night", "tie", "policy"]).drop_duplicates(keys).drop(columns="tie")


def validation_booking(config):
    raw = load_bookings(config, use_cache=False)
    # Exclude test rows BEFORE feature selection, fitting, predictions and calibration.
    raw = raw.loc[raw.arrival < config["valid_end"]].copy().reset_index(drop=True)
    for column in raw.select_dtypes(include="category"):
        raw[column] = raw[column].cat.remove_unused_categories()
    bk, outcome = separate_outcome(raw)
    train = bk.arrival < config["train_end"]
    agents = select_top_agents(bk, train)
    X = build_features(bk, agents)
    model = fit(list(X.columns), train, X, outcome.is_canceled, seed=config["seed"])
    return SimpleNamespace(bookings=bk, outcome=outcome, probabilities=model.predict_proba(X)[:, 1])


def run_sensitivity(booking, config, grid):
    check_grid(grid)
    if (booking.bookings.arrival >= config["valid_end"]).any():
        raise ValueError("Sensitivity input must exclude the frozen test period")
    rows, calibration, nightly_rows = [], [], []
    for h in grid["lead_days"]:
        cfg = dict(config, decision_lead_days=h, recal_weeks_grid=grid["recal_weeks"])
        # Every calibration label has matured before the first selection decision.
        fit_end = config["calib_end"] - pd.Timedelta(days=h + 1)
        snap, policies, agg, _, _ = prepare_policy(booking, cfg, fit_end=fit_end)
        selection = snap[(snap.arrival >= config["calib_end"]) & (snap.arrival < config["valid_end"])]
        for hh, g in selection.groupby("hotel"):
            calibration.append(
                dict(
                    hotel=hh,
                    lead_days=h,
                    calibration_end_exclusive=str(fit_end.date()),
                    n=len(g),
                    observed=float(g.y.mean()),
                    predicted=float(g.p_cal.mean()),
                    brier=float(np.mean((g.p_cal - g.y) ** 2)),
                    expected_over_observed=float(g.p_cal.sum() / g.y.sum()) if g.y.sum() else None,
                )
            )
        cache = {}
        for (hh, night), g in selection.groupby(["hotel", "arrival"]):
            b = g.groupby("block").agg(**agg)
            entries = []
            for name, fn in policies.items():
                if fn is None:
                    dist = None
                else:
                    forecast = fn(g, b)
                    if forecast.lead_days != h:
                        raise ValueError("Forecast horizon mismatch")
                    p, n = forecast
                    p = np.asarray(p, float)
                    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
                        raise ValueError("Invalid policy probability")
                    dist = released_distribution(p, np.ones(len(p), int) if n is None else n)
                entries.append((name, dist))
            cache[(hh, night)] = (float(g.adr.median()), int(g.y.sum()), entries)
        for walk in grid["walk_costs_eur"]:
            for variable in grid["variable_costs_eur"]:
                for resale in grid["resale_rates"]:
                    scenario = []
                    for (hh, night), (adr, released, entries) in cache.items():
                        room = effective_room_value(adr, variable, resale)
                        for name, dist in entries:
                            q = 0 if dist is None else choose_quantity(dist, room, walk)
                            walked, empty = max(q - released, 0), max(released - q, 0)
                            row = dict(
                                hotel=hh,
                                night=night,
                                policy=name,
                                q=q,
                                walked=walked,
                                empty=empty,
                                cost=walk * walked + room * empty,
                                no_overbooking_cost=room * released,
                            )
                            scenario.append(row)
                    frame = pd.DataFrame(scenario)
                    summary = (
                        frame.groupby(["hotel", "policy"])
                        .agg(
                            nights=("cost", "size"),
                            cost_per_night=("cost", "mean"),
                            walked_per_night=("walked", "mean"),
                            empty_per_night=("empty", "mean"),
                            oversell_per_night=("q", "mean"),
                            no_overbooking_cost=("no_overbooking_cost", "mean"),
                        )
                        .reset_index()
                    )
                    summary["saving_per_night"] = summary.no_overbooking_cost - summary.cost_per_night
                    summary = summary.assign(
                        lead_days=h,
                        walk_cost_eur=walk,
                        variable_cost_eur=variable,
                        resale_rate=resale,
                    )
                    rows.append(summary)
                    if h == 7 and walk == 250 and variable == 20 and resale == 0:
                        nightly_rows.append(frame)
        print(f"Completed horizon {h} days", flush=True)
    scores = pd.concat(rows, ignore_index=True)
    return (
        scores,
        select_winners(scores),
        pd.DataFrame(calibration),
        pd.concat(nightly_rows, ignore_index=True) if nightly_rows else pd.DataFrame(),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--grid", default="config/stage5.yaml")
    parser.add_argument("--output", default="docs/evidence/stage5")
    args = parser.parse_args()
    cfg = load_config(args.config)
    grid_path = Path(args.grid)
    grid = yaml.safe_load(grid_path.read_text())
    check_grid(grid)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    booking = validation_booking(cfg)
    scores, winners, calibration, nights = run_sensitivity(booking, cfg, grid)
    for name, table in [
        ("all-policies", scores),
        ("selected-policies", winners),
        ("calibration", calibration),
        ("reference-validation-nights", nights),
    ]:
        table.to_csv(output / f"{name}.csv", index=False)
    from hotel_cancel.data import get_raw

    raw = get_raw("hotel_bookings.csv", cfg)
    report = dict(
        status="complete",
        grid=grid,
        python=platform.python_version(),
        packages={p: version(p) for p in ["numpy", "pandas", "lightgbm", "scikit-learn"]},
        config_sha256=hashlib.sha256(
            json.dumps({k: str(v) for k, v in cfg.items()}, sort_keys=True).encode()
        ).hexdigest(),
        training_end_exclusive=str(cfg["train_end"].date()),
        validation_start=str(cfg["calib_end"].date()),
        validation_end_exclusive=str(cfg["valid_end"].date()),
        test_evaluated=False,
        raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
        source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob("*.py")},
        runtime_seconds=time.perf_counter() - started,
        scenario_hotel_count=len(winners),
        selection_warning="In-sample validation selection; savings are not unbiased test estimates. No deployment approval.",
    )
    (output / "run.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Sensitivity evidence: {output.resolve()}")


if __name__ == "__main__":
    main()
