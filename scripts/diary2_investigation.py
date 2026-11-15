"""Reproduce the recorded Entry 2 evidence; see docs/diary2-preparation-and-open-items.md."""


def main():
    """Entry 2 diagnostic random split, fixed forward holdout, clustered intervals and monthly drift."""
    import os
    import json
    from pathlib import Path
    import numpy as np
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import average_precision_score, accuracy_score, brier_score_loss
    import mlflow
    from hotel_cancel.config import load_config
    from hotel_cancel.quality_gate import prepare, verify_identity, assess
    from hotel_cancel.data import load_bookings
    from hotel_cancel.features import build_features, select_top_agents
    from hotel_cancel.model import fit, save_model, model_parameters
    from hotel_cancel.monitor_replay import psi_num, psi_cat
    from hotel_cancel.audit import duplicate_overlap
    from hotel_cancel.registry import source_state

    ROOT = Path(__file__).resolve().parents[1]
    OUT = ROOT / "docs/evidence/diary2"
    OUT.mkdir(parents=True, exist_ok=True)
    STORE = ROOT / "artifacts/diary2"
    os.environ["MLFLOW_DISABLE_TELEMETRY"] = "true"
    mlflow.set_tracking_uri("sqlite:///" + str(STORE / "mlflow.db"))
    mlflow.set_registry_uri(mlflow.get_tracking_uri())
    mlflow.set_experiment("task19-diary2-investigation")
    plan = dict(
        seed=3217,
        random_test_fraction=0.3,
        bootstrap=1000,
        bootstrap_unit="arrival date within each hotel; percentile 95% intervals",
        forward_holdout="2017-01-01 inclusive to 2017-09-01 exclusive",
        training="2015-07-01 to 2016-07-01 exclusive",
        gate="retain existing ratio band [.85,1.15], AUPRC floors City .70/Resort .55 and ECE .10; no tuning",
        model="unchanged supplied fixed LightGBM; random diagnostic isolated, never registered or deployed",
        purpose="Previously exposed historical regression evidence, not a new pristine test",
    )
    (OUT / "prespecified-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    config = load_config()
    bk, X, y, masks, identity = prepare(config)
    lock = json.loads((ROOT / "config/evaluation-lock.json").read_text())
    verify_identity(identity, lock["identity"])
    raw = load_bookings(config, use_cache=False)
    rows = []
    predictions = {}
    run_ids = {}
    for split in ["random", "forward"]:
        train = masks["train"].copy()
        test = masks["test"].copy()
        if split == "random":
            tr, te = train_test_split(bk.index, test_size=0.3, random_state=3217, stratify=y)
            train = pd.Series(bk.index.isin(tr), index=bk.index)
            test = pd.Series(bk.index.isin(te), index=bk.index)
        agents = select_top_agents(bk, train)
        features = build_features(bk, agents)
        with mlflow.start_run(run_name="unchanged learner " + split + " split") as run:
            model = fit(list(features), train, features, y, seed=3217)
            p = model.predict_proba(features)[:, 1]
            predictions[split] = p
            run_ids[split] = run.info.run_id
            mlflow.log_params(
                {
                    **{k: str(v) for k, v in model_parameters(3217).items()},
                    "split": split,
                    "train_rows": int(train.sum()),
                    "test_rows": int(test.sum()),
                    "raw_sha256": identity["raw_sha256"],
                    "frozen_holdout_sha256": identity["holdout_sha256"],
                }
            )
            mlflow.log_dict(plan, "prespecified-plan.json")
            mlflow.log_dict(source_state(), "source-state.json")
            mlflow.log_dict(identity, "frozen-identity.json")
            mlflow.log_artifact(__file__, "source")
            for hotel in config["hotels"]:
                select = test & bk.hotel.astype(str).eq(hotel)
                yy = y.loc[select].to_numpy()
                pp = p[select]
                score, _ = assess(yy, pp, **lock["thresholds"][hotel])
                base_rate = float(y.loc[train & bk.hotel.astype(str).eq(hotel)].mean())
                majority = int(base_rate >= 0.5)
                row = dict(
                    split=split,
                    hotel=hotel,
                    **{k: v for k, v in score.items() if k != "checks"},
                    accuracy=float(accuracy_score(yy, pp >= 0.5)),
                    majority_accuracy=float(np.mean(yy == majority)),
                    baseline_auprc=float(yy.mean()),
                    baseline_expected_observed_ratio=base_rate / float(yy.mean()),
                    baseline_brier=float(brier_score_loss(yy, np.full(len(yy), base_rate))),
                    duplicate_shared_signatures=duplicate_overlap(raw, raw.index[train], raw.index[test]),
                    run_id=run.info.run_id,
                )
                rows.append(row)
                mlflow.log_metrics(
                    {hotel.replace(" ", "_") + "." + k: float(v) for k, v in row.items() if isinstance(v, (int, float))}
                )
            bundle = OUT / (split + "-booking-model.joblib")
            save_model(model, bundle, top_agents=agents, feature_columns=list(features))
            mlflow.log_artifact(str(bundle), "model")
            bundle.unlink()
            mlflow.log_dict(rows[-2:], "split-results.json")
    pd.DataFrame(rows).to_csv(OUT / "split-comparison.csv", index=False)
    # Cluster bootstrap preserves same-day dependence; no IID booking-row interval is claimed.
    intervals = []
    periods = []
    with mlflow.start_run(run_name="fixed forward metric intervals and monthly drift") as run:
        run_ids["monitoring_and_intervals"] = run.info.run_id
        mlflow.log_dict(plan, "prespecified-plan.json")
        mlflow.log_dict(source_state(), "source-state.json")
        mlflow.log_dict(identity, "frozen-identity.json")
        mlflow.log_artifact(__file__, "source")
        for hotel in config["hotels"]:
            select = masks["test"] & bk.hotel.astype(str).eq(hotel)
            yy = y.loc[select].to_numpy()
            pp = predictions["forward"][select]
            dates = bk.loc[select, "arrival"]
            codes, unique = pd.factorize(dates)
            g = len(unique)
            rng = np.random.default_rng(3217)
            order = np.argsort(-pp, kind="stable")
            ys = yy[order]
            ps = pp[order]
            ends = np.r_[np.flatnonzero(np.diff(ps)), len(ps) - 1]
            values = []
            for i in range(1000):
                counts = np.bincount(rng.integers(g, size=g), minlength=g)
                w = counts[codes]
                ws = w[order]
                pos = float(w @ yy)
                n = float(w.sum())
                tp = np.cumsum(ws * ys)[ends]
                allw = np.cumsum(ws)[ends]
                precision = np.divide(tp, allw, out=np.zeros_like(tp, dtype=float), where=allw > 0)
                recall = tp / pos
                ap = float(np.sum(np.diff(np.r_[0, recall]) * precision))
                values.append([ap, float(w @ pp / pos), float(w @ ((pp - yy) ** 2) / n), pos / n])
            val = np.asarray(values)
            for j, metric in enumerate(["auprc", "expected_observed_ratio", "brier", "prevalence_baseline_auprc"]):
                low, high = np.quantile(val[:, j], [0.025, 0.975])
                intervals.append(
                    dict(hotel=hotel, metric=metric, lower=float(low), upper=float(high), clusters=g, replicates=1000)
                )
                mlflow.log_metrics(
                    {
                        hotel.replace(" ", "_") + "." + metric + ".ci_low": float(low),
                        hotel.replace(" ", "_") + "." + metric + ".ci_high": float(high),
                    }
                )
            reference = masks["train"] & bk.hotel.astype(str).eq(hotel)
            for month in sorted(bk.loc[select, "arrival"].dt.to_period("M").unique()):
                current = select & bk.arrival.dt.to_period("M").eq(month)
                pred = predictions["forward"][current]
                labels = y.loc[current]
                periods.append(
                    dict(
                        hotel=hotel,
                        month=str(month),
                        n=int(current.sum()),
                        observed=int(labels.sum()),
                        auprc=float(average_precision_score(labels, pred)),
                        expected_observed_ratio=float(pred.sum() / labels.sum()),
                        lead_time_psi=psi_num(bk.loc[reference, "lead_time"], bk.loc[current, "lead_time"]),
                        market_segment_psi=psi_cat(
                            bk.loc[reference, "market_segment"].astype(str),
                            bk.loc[current, "market_segment"].astype(str),
                        ),
                    )
                )
        pd.DataFrame(intervals).to_csv(OUT / "bootstrap-intervals.csv", index=False)
        pd.DataFrame(periods).to_csv(OUT / "monthly-drift-quality.csv", index=False)
        for name in ["split-comparison.csv", "bootstrap-intervals.csv", "monthly-drift-quality.csv"]:
            mlflow.log_artifact(str(OUT / name))
    result = dict(
        plan=plan,
        identity=identity,
        runs=run_ids,
        source=source_state(),
        split_results=rows,
        intervals=intervals,
        monthly=periods,
        bootstrap_limitation="Arrival-date clusters preserve within-date dependence, not serial dependence between dates; intervals are conditional historical uncertainty, not future guarantees.",
        random_limitation="Random test is diagnostic and has a different time mix/sample size. It includes future-era rows in training, so it is never a release candidate.",
        data_changed=False,
        reference_model_or_thresholds_changed=False,
    )
    (OUT / "investigation.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
