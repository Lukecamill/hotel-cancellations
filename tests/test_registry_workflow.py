"""Registration, routing and HTTP boundaries; all metadata here is synthetic test evidence."""

import http.client
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import pandas as pd
import pytest

from hotel_cancel.registry import (HOTELS, ROOT, check_evidence, digest_json, require_clean,
                                   register_run, move_alias, verify_version)
from hotel_cancel.registry_serving import RegistryPredictor
from hotel_cancel.service import make_server
from test_serving import records as records


@pytest.fixture
def evidence():
    lock = json.loads((ROOT / "config/evaluation-lock.json").read_text())
    return dict(schema_version=1, hotel="City Hotel", source={"commit": "a" * 40, "dirty": False},
                identity=lock["identity"], lock_sha256=digest_json(lock), horizon="booking_to_arrival",
                holdout=dict(auprc=.8, expected_observed_ratio=1., ece=.02, checks={"two_classes": True}),
                base_model_sha256="b" * 64, prediction_sha256="b" * 64, model_uri="models:/synthetic")


@pytest.mark.parametrize("state", [{"commit": None, "dirty": None}, {"commit": "a"*40,"dirty": True},
                                    {"commit": None,"dirty":False}])
def test_dirty_and_unknown_training_cannot_register(state):
    with pytest.raises(ValueError, match="clean commit"):
        require_clean(state)


@pytest.mark.parametrize("mutation", ["failed", "lock", "identity", "horizon", "dirty", "resort_validation"])
def test_registration_recomputes_facts_instead_of_trusting_pass_tag(evidence, mutation):
    lock = json.loads((ROOT / "config/evaluation-lock.json").read_text())
    if mutation == "failed":
        evidence["holdout"].update(expected_observed_ratio=.68, gate="PASS")
    elif mutation == "lock":
        evidence["lock_sha256"] = "bad"
    elif mutation == "identity":
        evidence["identity"] = {}
    elif mutation == "horizon":
        evidence["horizon"] = "active_7_day"
    elif mutation == "dirty":
        evidence["source"]["dirty"] = True
    else:
        evidence["hotel"] = "Resort Hotel"
        evidence["validation"] = dict(evidence["holdout"], expected_observed_ratio=.7)
    with pytest.raises(ValueError):
        check_evidence(evidence, lock)


class Client:
    def __init__(self, evidence):
        self.evidence = evidence
        self.aliases = {}
        self.version = SimpleNamespace(status="READY", run_id="synthetic-run", tags={})
        self.cards = []
    def download_artifacts(self, run_id, name, directory):
        p = Path(directory) / name
        p.write_text(json.dumps(self.evidence))
        return str(p)
    def get_run(self, run_id):
        return SimpleNamespace(info=SimpleNamespace(status="FINISHED"))
    def get_model_version(self, name, version):
        return self.version
    def update_model_version(self, name, version, description):
        self.cards.append(description)
    def set_registered_model_alias(self, name, alias, version):
        self.aliases[alias] = str(version)
    def get_registered_model(self, name):
        return SimpleNamespace(aliases=self.aliases)
    def get_model_version_by_alias(self, name, alias):
        return SimpleNamespace(version=self.aliases[alias])


def test_register_then_alias_revalidates_and_attaches_card(evidence):
    client = Client(evidence)
    lock = json.loads((ROOT / "config/evaluation-lock.json").read_text())
    def register(uri, name, tags):
        client.version.tags = tags
        return SimpleNamespace(version="1")
    registered = register_run(client, "synthetic-run", lock, evidence["source"], register)
    assert not registered["champion_set"] and client.aliases == {"challenger": "1"}
    assert "Rollback" in client.cards[0]
    result = move_alias(client, HOTELS["City Hotel"], "1", "champion", lock)
    assert result["version"] == "1" and not result["production_authorized"]
    client.evidence["holdout"]["expected_observed_ratio"] = .6
    with pytest.raises(ValueError, match="Quality gate"):
        move_alias(client, HOTELS["City Hotel"], "1", "champion", lock)


def test_register_never_invokes_registry_for_failed_run(evidence):
    evidence["holdout"]["ece"] = .9
    client = Client(evidence)
    def unexpected(*a, **kw):
        pytest.fail("Failed candidate reached the registry")
    with pytest.raises(ValueError):
        register_run(client, "synthetic-run", json.loads((ROOT / "config/evaluation-lock.json").read_text()),
                     evidence["source"], unexpected)


def test_changed_version_metadata_is_rejected(evidence):
    client = Client(evidence)
    with pytest.raises(ValueError, match="metadata"):
        verify_version(client, HOTELS["City Hotel"], "1",
                       json.loads((ROOT / "config/evaluation-lock.json").read_text()))


def request(server, method, route, body=None):
    c = http.client.HTTPConnection(*server.server_address, timeout=5)
    c.request(method, route, None if body is None else json.dumps(body), {"Content-Type": "application/json"})
    response = c.getresponse()
    result = response.status, json.loads(response.read())
    c.close()
    return result


def test_alive_while_unready_then_exact_routing_and_lineage(records):
    predictor = RegistryPredictor(None, None, {})
    saved = []
    from hotel_cancel.monitoring import Telemetry
    telemetry = Telemetry()
    def persist(booking, probability, version, *, lineage):
        saved.append((version, lineage))
        return "synthetic-prediction", True
    telemetry.prediction = persist
    server = make_server(predictor, port=0, telemetry=telemetry)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    class Model:
        def __init__(self, p):
            self.p = p
        def predict(self, frame):
            return pd.DataFrame({"cancellation_probability": [self.p]})
    try:
        assert request(server, "GET", "/health")[0] == 200
        assert request(server, "GET", "/ready")[0] == 503
        assert request(server, "POST", "/predict", {"booking": records[0]})[0] == 503
        predictor._loaded = {h: (Model(.2+i*.1), {"model_version": f"{name}/1", "run_id":"test", "model_sha256":"b"*64})
                             for i, (h, name) in enumerate(HOTELS.items())}
        assert request(server, "GET", "/ready")[0] == 200
        for row in records[:2]:
            status, payload = request(server, "POST", "/predict", {"booking": row})
            assert status == 200 and payload["model_version"] == f"{HOTELS[row['hotel']]}/1"
            assert saved[-1][0] == payload["model_version"]
            assert saved[-1][1] == payload["model_lineage"]
        assert request(server, "POST", "/predict", {"booking": dict(records[0], children=None, agent=None, company=None)})[0] == 200
        assert request(server, "POST", "/predict", {"booking": dict(records[0], country="PRT")})[0] == 422
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_startup_retry_recovers_without_api_restart():
    predictor = RegistryPredictor(None, None, {})
    calls = []
    recovered = threading.Event()
    def load():
        calls.append(True)
        if len(calls) == 1:
            raise ConnectionError("synthetic registry outage")
        predictor._loaded = {"synthetic": (None, {})}
        recovered.set()
    predictor.load_once = load
    try:
        predictor.start(wait=.01)
        assert recovered.wait(3) and predictor.ready and len(calls) == 2
    finally:
        predictor.close()


def test_partial_hotel_load_never_publishes_readiness(tmp_path, monkeypatch, evidence):
    import hotel_cancel.registry_serving as serving
    from hotel_cancel.serving import digest
    model_path = tmp_path / "model"
    model_path.write_bytes(b"synthetic test bundle")
    evidence["base_model_sha256"] = evidence["prediction_sha256"] = digest(model_path)
    def verify(client, name, version, lock):
        if name == HOTELS["Resort Hotel"]:
            raise ValueError("Synthetic Resort eligibility failure")
        return evidence, SimpleNamespace(run_id="test")
    monkeypatch.setattr(serving, "verify_version", verify)
    model = SimpleNamespace(unwrap_python_model=lambda: SimpleNamespace(artifact_paths={"booking_bundle":model_path}))
    client = SimpleNamespace(get_model_version_by_alias=lambda *a: SimpleNamespace(version="1"))
    predictor = RegistryPredictor(client, lambda uri: model, {})
    with pytest.raises(ValueError, match="Resort eligibility"):
        predictor.load_once()
    assert not predictor.ready and predictor.readiness()["models"] == {}
