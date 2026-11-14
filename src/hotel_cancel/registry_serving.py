"""Startup-only registry resolution; atomic hotel routing and retry without policy execution."""

import json
import logging
import os
import threading

import numpy as np
import pandas as pd

from hotel_cancel.registry import ROOT, HOTELS, settings, verify_version
from hotel_cancel.serving import booking_frame, digest

logger = logging.getLogger(__name__)


class RegistryPredictor:
    def __init__(self, client, loader, lock):
        self.client, self.loader, self.evaluation_lock = client, loader, lock
        self._loaded = None
        self._lock = threading.Lock()
        self.stop = threading.Event()
        self.thread = None

    @property
    def ready(self):
        return self._loaded is not None

    @property
    def version(self):
        return "registry"  # Per-hotel versions are returned by score(), never this label.

    @property
    def manifest(self):
        return {"diagnostic_gate": {hotel: "PASS" for hotel in HOTELS} if self.ready else {}}

    def readiness(self):
        loaded = self._loaded
        return {"ready": loaded is not None, "models": {} if loaded is None else {
            hotel: item[1] for hotel, item in loaded.items()}, "policy_execution_enabled": False}

    def load_once(self):
        loaded = {}
        for hotel, name in HOTELS.items():
            version = self.client.get_model_version_by_alias(name, "champion")
            evidence, model_version = verify_version(self.client, name, version.version, self.evaluation_lock)
            uri = f"models:/{name}/{version.version}"
            model = self.loader(uri)
            # The wrapper's bundled files must match the evidence, before untrusted input is scored.
            raw = model.unwrap_python_model()
            paths = raw.artifact_paths
            if digest(paths["booking_bundle"]) != evidence["base_model_sha256"]:
                raise ValueError("Loaded base model differs from gate evidence")
            actual = evidence["base_model_sha256"]
            if "booking_calibrator" in paths:
                import hashlib
                actual = hashlib.sha256((actual + digest(paths["booking_calibrator"])).encode()).hexdigest()
            if actual != evidence["prediction_sha256"]:
                raise ValueError("Loaded prediction artifacts differ from gate evidence")
            loaded[hotel] = (model, {"model_version": f"{name}/{version.version}",
                                    "run_id": model_version.run_id, "model_sha256": actual,
                                    "base_model_sha256": evidence["base_model_sha256"],
                                    "git_commit": evidence["source"]["commit"]})
        # No partially loaded routing table ever becomes ready.
        with self._lock:
            self._loaded = loaded

    def start(self, wait=5):
        if self.thread is not None:
            raise ValueError("Loader already started")
        def retry():
            while not self.stop.is_set() and not self.ready:
                try:
                    self.load_once()
                except Exception as error:
                    logger.warning("Registry model unavailable (%s); retrying", type(error).__name__)
                    self.stop.wait(wait)
        self.thread = threading.Thread(target=retry, daemon=True)
        self.thread.start()

    def score(self, records):
        frame = booking_frame(records)  # Strict contract before MLflow can discard extra fields.
        with self._lock:
            loaded = self._loaded
            if loaded is None:
                raise RuntimeError("No registry model loaded")
            probabilities, lineage = [], []
            for index, row in enumerate(records):
                # Preserve the original service's nullable count/ID semantics before signature validation.
                row = dict(row, children=int(frame.children.iloc[index]),
                           agent=str(frame.agent.iloc[index]), company=str(frame.company.iloc[index]))
                model, identity = loaded[row["hotel"]]
                output = model.predict(pd.DataFrame([row]))
                p = float(output["cancellation_probability"].iloc[0])
                if not np.isfinite(p) or not 0 <= p <= 1:
                    raise ValueError("Model returned an invalid probability")
                probabilities.append(p)
                lineage.append(dict(identity))
            return np.array(probabilities), lineage

    def predict(self, records):
        return self.score(records)[0]

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=6)


def main():
    import mlflow
    from hotel_cancel.service import make_server, run_server
    from hotel_cancel.monitoring import Telemetry

    config = settings()
    os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "5")
    mlflow.set_tracking_uri(config["tracking_uri"])
    mlflow.set_registry_uri(config["tracking_uri"])
    predictor = RegistryPredictor(mlflow.MlflowClient(), mlflow.pyfunc.load_model,
                                 json.loads((ROOT / "config/evaluation-lock.json").read_text()))
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # This service deliberately exposes no nightly approvals or seven-day policy execution.
    telemetry = Telemetry(os.environ.get("DATABASE_URL"))
    server = make_server(predictor, os.environ.get("SERVICE_HOST", "127.0.0.1"),
                         int(os.environ.get("SERVICE_PORT", "8082")), telemetry=telemetry)
    predictor.start()
    try:
        run_server(server)
    finally:
        predictor.close()


if __name__ == "__main__":
    main()
