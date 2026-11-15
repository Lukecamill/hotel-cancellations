"""Reproduce the recorded Entry 2 evidence; see docs/diary2-preparation-and-open-items.md."""


def main():
    import json
    import os
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    store = root / "artifacts/diary2"
    store.mkdir(parents=True, exist_ok=True)
    os.environ["MLFLOW_TRACKING_URI"] = "sqlite:///" + str(store / "mlflow.db")
    os.environ["MLFLOW_DISABLE_TELEMETRY"] = "true"
    import mlflow
    import pandas as pd
    from hotel_cancel.registry_training import run
    from hotel_cancel.registry import source_state, require_clean, register_run, move_alias, ROOT, HOTELS

    state = source_state()
    require_clean(state)
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_registry_uri(os.environ["MLFLOW_TRACKING_URI"])
    client = mlflow.MlflowClient()
    if client.get_experiment_by_name("task19-session6-training") is None:
        client.create_experiment("task19-session6-training", artifact_location=(store / "mlartifacts").as_uri())
    lock = json.loads((ROOT / "config/evaluation-lock.json").read_text())
    results = [run() for _ in range(3)]
    registrations = [
        register_run(client, result["runs"]["City Hotel"], lock, source_state(), mlflow.register_model)
        for result in results[:2]
    ]
    name = HOTELS["City Hotel"]
    example = pd.DataFrame(
        [dict(json.loads((ROOT / "examples/predict.json").read_text())["booking"], agent="none", company="none")]
    )
    audit = []
    for version in [registrations[1]["version"], registrations[0]["version"], registrations[1]["version"]]:
        change = move_alias(client, name, version, "champion", lock)
        actual = client.get_model_version_by_alias(name, "champion")
        loaded = mlflow.pyfunc.load_model(f"models:/{name}/{actual.version}")
        change["probability"] = float(loaded.predict(example).cancellation_probability.iloc[0])
        change["run_id"] = actual.run_id
        audit.append(change)
    mlflow.set_experiment("task19-diary2-rollback")
    with mlflow.start_run(run_name="actual City versions 2 to 1 to 2; same prescribed learner") as active:
        mlflow.log_dict(audit, "rollback.json")
        mlflow.log_dict(state, "source-state.json")
        rollback_run = active.info.run_id
    result = dict(
        source=state,
        training_runs=results,
        registered_city_versions=registrations,
        rollback=audit,
        rollback_mlflow_run=rollback_run,
        synthetic_fixtures=False,
        resort_promoted=False,
        peer_review="pending actual other student",
        production_authorized=False,
    )
    (store / "clean-registration.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
