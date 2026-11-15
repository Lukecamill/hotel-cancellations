"""Disposable real MLflow registry and HTTP rollback; fixture metrics are synthetic, not project eligibility."""

import json
import threading

import pytest

from hotel_cancel.registry import ROOT, HOTELS, digest_json, register_run, move_alias
from hotel_cancel.registry_serving import RegistryPredictor
from hotel_cancel.serving import digest
from hotel_cancel.service import make_server
from test_registry_workflow import request
from test_serving import runtime as runtime, records as records


def test_real_registry_reload_alias_rollback_and_prediction_lineage(tmp_path, runtime, records):
    # The repository's mlflow/ SQL directory is also a namespace package.
    # Require the actual optional runtime before treating MLflow as installed.
    pytest.importorskip("mlflow.pyfunc")
    import mlflow
    from hotel_cancel.registry_model import HotelBookingModel
    from mlflow.models import infer_signature
    import pandas as pd
    import os

    os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
    uri = os.environ.get("SESSION6_INTEGRATION_URI", "sqlite:///" + str(tmp_path / "mlflow.db"))
    old_uri = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment("synthetic-session6-integration")
    client = mlflow.MlflowClient()
    lock = json.loads((ROOT / "config/evaluation-lock.json").read_text())
    state = {"commit": "a"*40, "dirty": False}  # Synthetic fixture provenance only.
    bundle = runtime[0].directory / "booking_model.joblib"
    sha = digest(bundle)
    versions = {}
    try:
        for hotel in HOTELS:
            for attempt in (1, 2):
                with mlflow.start_run(run_name=f"synthetic {hotel} version {attempt}") as active:
                    sample = pd.DataFrame([dict(records[0], hotel=hotel)])
                    info = mlflow.pyfunc.log_model(name="booking", python_model=HotelBookingModel(hotel),
                                                  artifacts={"booking_bundle": str(bundle)},
                                                  signature=infer_signature(sample, pd.DataFrame({"cancellation_probability":[.5]})),
                                                  pip_requirements=[])
                    metrics = dict(auprc=.8, expected_observed_ratio=1., ece=.02, checks={"two_classes":True})
                    evidence = dict(schema_version=1, hotel=hotel, source=state, identity=lock["identity"],
                                    lock_sha256=digest_json(lock), horizon="booking_to_arrival", holdout=metrics,
                                    validation=metrics, base_model_sha256=sha, prediction_sha256=sha,
                                    model_uri=info.model_uri, synthetic_fixture=True)
                    mlflow.log_dict(evidence, "eligibility.json")
                registered = register_run(client, active.info.run_id, lock, state, mlflow.register_model)
                versions[(hotel, attempt)] = registered["version"]
            move_alias(client, HOTELS[hotel], versions[(hotel, 2)], "champion", lock)
        def start():
            predictor = RegistryPredictor(client, mlflow.pyfunc.load_model, lock)
            predictor.load_once()
            from hotel_cancel.monitoring import Telemetry
            server = make_server(predictor, port=0, telemetry=Telemetry(os.environ.get("TEST_DATABASE_URL")))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            return predictor, server, thread
        predictor, server, thread = start()
        try:
            assert request(server, "GET", "/ready")[0] == 200
            code, before = request(server, "POST", "/predict", {"booking": records[0]})
            assert code == 200 and before["model_version"].endswith('/2')
            move_alias(client, HOTELS["City Hotel"], "1", "champion", lock)
            # Startup pinning: alias movement alone does not silently change serving.
            assert request(server, "POST", "/predict", {"booking": records[0]})[1]["model_version"].endswith('/2')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            predictor.close()
        predictor, server, thread = start()
        try:
            code, after = request(server, "POST", "/predict", {"booking": records[0]})
            assert code == 200 and after["model_version"].endswith('/1')
            assert before["cancellation_probability"] == after["cancellation_probability"]
            assert before["model_lineage"]["run_id"] != after["model_lineage"]["run_id"]
            if os.environ.get("TEST_DATABASE_URL"):
                import psycopg
                assert before["prediction_logged"] and after["prediction_logged"]
                with psycopg.connect(os.environ["TEST_DATABASE_URL"]) as connection:
                    for payload in (before, after):
                        row = connection.execute("SELECT model_version,model_lineage FROM hotel_predictions WHERE prediction_id=%s",
                                                 (payload["prediction_id"],)).fetchone()
                        assert row == (payload["model_version"], payload["model_lineage"])
            move_alias(client, HOTELS["City Hotel"], "2", "champion", lock)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            predictor.close()
    finally:
        mlflow.set_tracking_uri(old_uri)
