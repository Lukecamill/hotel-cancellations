"""Track the frozen baseline and register per-hotel versions, without refitting."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd

from hotel_cancel.config import load_config
from hotel_cancel.model import model_parameters
from hotel_cancel.quality_gate import (
    prepare,
    verify_identity,
    assess,
    plot_reliability,
    sha,
)
from hotel_cancel.serving import Predictor

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_NAMES = {
    "City Hotel": "task19-city-booking",
    "Resort Hotel": "task19-resort-booking",
}


def json_write(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def checked_gate(result, thresholds):
    """Recompute eligibility from numeric evidence, not a mutable PASS label."""
    values = [result.get(k) for k in ["auprc", "expected_observed_ratio", "ece"]]
    return (
        result.get("checks", {}).get("two_classes") is True
        and all(isinstance(v, (int, float)) and np.isfinite(v) for v in values)
        and values[0] >= thresholds["min_auprc"]
        and thresholds["ratio_band"][0] <= values[1] <= thresholds["ratio_band"][1]
        and 0 <= values[2] <= thresholds["max_ece"]
    )


def assign_aliases(client, name, candidate, result, thresholds):
    """Every candidate can be reviewed; only a passing model becomes champion.

    Existing champion is preserved. No automatic seasonal replacement or release.
    """
    client.set_registered_model_alias(name, "challenger", candidate)
    model = client.get_registered_model(name)
    if checked_gate(result, thresholds) and "champion" not in model.aliases:
        client.set_registered_model_alias(name, "champion", candidate)
    # Fail closed if an existing champion has been marked as failing.
    model = client.get_registered_model(name)
    if "champion" in model.aliases:
        champion = client.get_model_version(name, model.aliases["champion"])
        if champion.tags.get("quality_gate") != "PASS":
            raise ValueError(f"{name}: existing champion lacks a passing gate; registry needs review")
    return dict(client.get_registered_model(name).aliases)


def git_state(root):
    try:
        return dict(
            commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip(),
            dirty=bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True)),
        )
    except (OSError, subprocess.CalledProcessError):
        return dict(commit=None, dirty=None)


def evaluate_bundle(config, predictor, lock, output):
    bk, X, y, masks, identity = prepare(config)
    verify_identity(identity, lock["identity"])
    if predictor.manifest["raw_sha256"] != identity["raw_sha256"]:
        raise ValueError("Serving bundle raw-data identity differs from frozen data")
    # Reconstruct both feature paths and prove vocabulary/schema agreement.
    from hotel_cancel.features import build_features

    saved_X = build_features(bk, predictor.bundle["top_agents"])
    pd.testing.assert_frame_equal(saved_X, X)
    if predictor.bundle["feature_columns"] != list(X.columns):
        raise ValueError("Model feature order differs from frozen evaluation")
    expected_parameters = model_parameters(config["seed"])
    actual_parameters = predictor.bundle["model"].get_params()
    if any(actual_parameters[k] != v for k, v in expected_parameters.items()):
        raise ValueError("Only the supplied learner and fixed parameters may be tracked here")
    p = predictor.bundle["model"].predict_proba(X)[:, 1]
    metrics, tables = {}, {}
    for hotel in config["hotels"]:
        metrics[hotel] = {}
        for split in ["valid", "test"]:
            select = (masks[split] & bk.hotel.astype(str).eq(hotel)).to_numpy()
            metrics[hotel][split], bins = assess(y.to_numpy()[select], p[select], **lock["thresholds"][hotel])
            if split == "test":
                tables[hotel] = bins
    plot_reliability(tables, output)
    pd.DataFrame([dict(hotel=h, **row) for h, rows in tables.items() for row in rows]).to_csv(
        output / "reliability.csv", index=False
    )
    report = dict(
        identity_verified=True,
        identity=identity,
        hotels=metrics,
        bundle_sha256=predictor.manifest["sha256"],
        thresholds=lock["thresholds"],
        trained_or_selected_on_holdout=False,
        refitted=False,
        scope="saved_booking_to_arrival_model; policy is separate active-seven-day horizon",
    )
    json_write(output / "evaluation.json", report)
    return report, bk, X


def track(config, *, bundle, lock_path, output, store):
    os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "true")
    # Importing MLflow is optional for the production service and baseline environment.
    import mlflow
    import mlflow.pyfunc
    from mlflow import MlflowClient
    from mlflow.models import infer_signature
    from hotel_cancel.registry_model import HotelBookingModel
    from hotel_cancel.monitor_replay import run_replay

    output, store, bundle = (
        Path(output).resolve(),
        Path(store).resolve(),
        Path(bundle).resolve(),
    )
    output.mkdir(parents=True, exist_ok=True)
    store.mkdir(parents=True, exist_ok=True)
    # Prevent a stale successful verification being mistaken for this attempt.
    (output / "verification.json").unlink(missing_ok=True)
    lock = json.loads(Path(lock_path).read_text())
    if lock["schema_version"] != 1 or set(lock["thresholds"]) != set(config["hotels"]):
        raise ValueError("Invalid evaluation lock")
    predictor = Predictor(bundle)
    provenance = json.loads((ROOT / "config/reference-training-provenance.json").read_text())
    if (
        provenance["run_id"] != predictor.manifest["source_run"]
        or provenance["bundle_sha256"] != predictor.manifest["sha256"]
        or provenance["raw_sha256"] != predictor.manifest["raw_sha256"]
        or provenance["holdout_sha256"] != lock["identity"]["holdout_sha256"]
    ):
        raise ValueError("Original training provenance does not match the supplied reference bundle")
    for key in [
        "decision_lead_days",
        "walk_cost_eur",
        "variable_cost_eur",
        "recal_weeks_grid",
    ]:
        if config[key] != predictor.policy["config"][key]:
            raise ValueError(f"Current policy configuration differs from saved bundle: {key}")
    report, bk, X = evaluate_bundle(config, predictor, lock, output)
    replay = run_replay(config, predictor, pd.Timestamp("2017-09-02"), output / "replay")
    # Local SQLite backend supports registry APIs; artifacts never leave this machine.
    tracking_uri = "sqlite:///" + str(store / "mlflow.db")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_registry_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri, registry_uri=tracking_uri)
    experiment_name = "task19-frozen-baseline"
    experiment = client.get_experiment_by_name(experiment_name)
    experiment_id = (
        experiment.experiment_id
        if experiment
        else client.create_experiment(experiment_name, artifact_location=(store / "mlartifacts").as_uri())
    )
    state = git_state(ROOT)
    source_hashes = {p.name: sha(p) for p in sorted((ROOT / "src/hotel_cancel").glob("*.py"))}
    source_digest = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
    packages = {
        name: version(name)
        for name in [
            "mlflow",
            "numpy",
            "pandas",
            "scikit-learn",
            "lightgbm",
            "pyarrow",
            "joblib",
        ]
    }
    effective = {
        key: str(config[key]) if isinstance(config[key], pd.Timestamp) else config[key]
        for key in [
            "seed",
            "window_start",
            "train_end",
            "calib_end",
            "valid_end",
            "test_end",
            "decision_lead_days",
            "walk_cost_eur",
            "variable_cost_eur",
            "recal_weeks_grid",
            "calibration_band",
            "gate_min_auprc",
        ]
    }
    lineage = dict(
        source_run=predictor.manifest["source_run"],
        original_training_provenance=provenance,
        source_hashes=source_hashes,
        bundle_manifest=predictor.manifest,
        git=state,
        packages=packages,
        policy_selection_period="2016-10-01 inclusive to 2017-01-01 exclusive",
        horizon_calibration_period="2016-07-01 inclusive to 2016-10-01 exclusive",
        adr_rule="per-night median ADR minus variable cost, floored at zero; raw model ADR unchanged",
        policy_selection="existing saved choices only; never reselected on test",
    )
    json_write(output / "lineage.json", lineage)
    records = {}
    # Both registrations reference the same pooled learner, with hotel-specific adapters.
    for hotel, name in REGISTRY_NAMES.items():
        results = report["hotels"][hotel]
        eligible = checked_gate(results["test"], lock["thresholds"][hotel])
        tags = dict(
            hotel=hotel,
            quality_gate="PASS" if eligible else "FAIL",
            deployment_scope="offline_coursework_only",
            production_authorized="false",
            model_sha256=predictor.version,
            policy_sha256=predictor.manifest["sha256"]["policy_state.joblib"],
            holdout_sha256=report["identity"]["holdout_sha256"],
            raw_sha256=report["identity"]["raw_sha256"],
            source_sha256=source_digest,
            source_run=predictor.manifest["source_run"],
        )
        with mlflow.start_run(experiment_id=experiment_id, run_name=hotel + " frozen reference", tags=tags) as active:
            mlflow.log_params({"learner." + k: str(v) for k, v in predictor.bundle["model"].get_params().items()})
            mlflow.log_params(
                {k: json.dumps(v) if isinstance(v, (list, dict)) else str(v) for k, v in effective.items()}
            )
            mlflow.log_params(
                dict(
                    hotel=hotel,
                    policy=predictor.policy["chosen_policies"][hotel],
                    model_sha256=predictor.version,
                    policy_sha256=tags["policy_sha256"],
                    raw_sha256=tags["raw_sha256"],
                    holdout_sha256=tags["holdout_sha256"],
                    evaluation_lock_sha256=sha(lock_path),
                    horizon_calibration="Platt; Jul-Sep 2016; saved",
                    prediction_horizon="booking_to_arrival",
                    policy_horizon="active_7_day",
                    source_git_commit=state["commit"] or "not_available",
                    source_dirty=str(state["dirty"]),
                )
            )
            for split, values in results.items():
                mlflow.log_metrics(
                    {
                        split + "." + k: float(v)
                        for k, v in values.items()
                        if k not in ["checks", "gate"] and isinstance(v, (int, float))
                    }
                )
            mlflow.log_metric("test.gate_pass", float(eligible))
            for field in ["booking_runtime_seconds", "policy_runtime_seconds"]:
                if field in provenance:
                    mlflow.log_metric("original_training." + field, provenance[field])
            costs = [row for row in replay["policy_costs"] if row["hotel"] == hotel]
            for row in costs:
                prefix = "policy.none" if row["policy"] == "no overbooking" else "policy.selected"
                mlflow.log_metrics(
                    {
                        prefix + ".cost_per_night": row["cost_per_night"],
                        prefix + ".saving_total_eur": row["saving vs none (€)"],
                    }
                )
            mlflow.log_dict(effective, "effective-config.json")
            mlflow.log_dict(lineage, "lineage.json")
            mlflow.log_dict(lock, "evaluation-lock.json")
            mlflow.log_dict(predictor.policy["chosen_policies"], "chosen-policies.json")
            for artifact in ["evaluation.json", "reliability.csv", "reliability.png"]:
                mlflow.log_artifact(str(output / artifact), artifact_path="evaluation")
            mlflow.log_artifacts(str(output / "replay"), artifact_path="historical-replay")
            mlflow.log_artifact(str(bundle / "policy_state.joblib"), artifact_path="runtime")
            mlflow.log_artifact(str(bundle / "manifest.json"), artifact_path="runtime")
            for filename in [
                "model-card.md",
                "decisions/0011-model-tracking-and-registry.md",
            ]:
                mlflow.log_artifact(str(ROOT / "docs" / filename), artifact_path="documentation")
            mlflow.log_artifact(str(ROOT / "requirements-tracking.txt"), artifact_path="environment")
            # Synthetic schema sample only; never store dataset bookings as examples.
            example = dict(
                json.loads((ROOT / "examples/predict.json").read_text())["booking"],
                hotel=hotel,
                agent="none",
                company="none",
            )
            sample = pd.DataFrame([example])
            sample_p = predictor.predict([example])
            signature = infer_signature(sample, pd.DataFrame({"cancellation_probability": sample_p}))
            info = mlflow.pyfunc.log_model(
                name="booking-model",
                python_model=HotelBookingModel(hotel),
                artifacts={"booking_bundle": str(bundle / "booking_model.joblib")},
                code_paths=[str(ROOT / "src/hotel_cancel")],
                signature=signature,
                pip_requirements=[
                    line
                    for line in (ROOT / "requirements-tracking.txt").read_text().splitlines()
                    if line and not line.startswith(("#", "-"))
                ],
                metadata=tags,
            )
            # Loading the logged artifact must reproduce the actual scoring path.
            loaded = mlflow.pyfunc.load_model(info.model_uri)
            from hotel_cancel.features import BOOKING_INPUTS

            mask = bk.hotel.astype(str).eq(hotel) & bk.arrival.ge(config["valid_end"])
            frame = bk.loc[mask, [c for c in BOOKING_INPUTS if c != "booked"]].copy()
            frame["arrival"] = frame.arrival.dt.strftime("%Y-%m-%d")
            # Registry input is a request table, not the loader's categorical frame.
            for column in frame.select_dtypes(include="category").columns:
                frame[column] = frame[column].astype(object)
            expected = predictor.bundle["model"].predict_proba(X.loc[mask])[:, 1]
            actual = loaded.predict(frame)["cancellation_probability"].to_numpy()
            error = float(np.max(np.abs(actual - expected)))
            if error > 1e-12:
                raise ValueError(f"{hotel}: registered model probability parity failed: {error}")
            mlflow.log_metric("registry_reload.max_probability_error", error)
            registered = mlflow.register_model(info.model_uri, name, tags=tags)
            aliases = assign_aliases(
                client,
                name,
                registered.version,
                results["test"],
                lock["thresholds"][hotel],
            )
            # Verify persistence/readback, not merely successful API responses.
            saved_run = client.get_run(active.info.run_id)
            assert saved_run.data.metrics["test.ece"] == results["test"]["ece"]
            assert client.get_model_version_by_alias(name, "challenger").version == registered.version
            registered_loaded = mlflow.pyfunc.load_model(f"models:/{name}@challenger")
            np.testing.assert_allclose(
                registered_loaded.predict(sample).cancellation_probability.to_numpy(),
                sample_p,
                atol=1e-12,
                rtol=0,
            )
            records[hotel] = dict(
                name=name,
                version=registered.version,
                run_id=active.info.run_id,
                gate=tags["quality_gate"],
                aliases=aliases,
                holdout_bookings_verified=len(frame),
                maximum_probability_error=error,
                champion_withheld_reason=None
                if eligible
                else "Frozen calibration gate failed; manual review/no-overbooking fallback",
                production_authorized=False,
            )
    result = dict(
        status="VERIFIED",
        environment="local tracking execution",
        tracking_uri=tracking_uri,
        mlflow_version=version("mlflow"),
        experiment_id=experiment_id,
        models=records,
        source_digest=source_digest,
        source_run=predictor.manifest["source_run"],
        refitted=False,
        serving_bundle_changed=False,
        mlflow_ece_readback_verified=True,
        completed_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    json_write(output / "verification.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--bundle", default=str(ROOT / "models/serving"))
    parser.add_argument("--lock", default=str(ROOT / "config/evaluation-lock.json"))
    parser.add_argument("--output", default=str(ROOT / "docs/evidence/stage9"))
    parser.add_argument("--store", default=str(ROOT / "artifacts/stage9"))
    args = parser.parse_args()
    result = track(
        load_config(args.config),
        bundle=args.bundle,
        lock_path=args.lock,
        output=args.output,
        store=args.store,
    )
    print(json.dumps(result, indent=2))
    return 0  # Tracking a failed-quality reference is successful logging, never CI approval.


if __name__ == "__main__":
    raise SystemExit(main())
