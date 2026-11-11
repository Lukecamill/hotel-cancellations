import copy
import hashlib
import http.client
import json
import threading

import joblib
import numpy as np
import pandas as pd
import pytest

from hotel_cancel.features import build_features
from hotel_cancel.model import fit, save_model
from hotel_cancel.policy import HorizonCalibrator, logit
from hotel_cancel.service import make_server
from hotel_cancel.serving import Predictor, booking_frame
from hotel_cancel.snapshot import seal_snapshot
from hotel_cancel.batch import nightly_batch
from sklearn.linear_model import LogisticRegression


@pytest.fixture
def records():
    return [
        dict(
            hotel=h,
            arrival="2017-08-15",
            lead_time=30,
            stays_in_weekend_nights=0,
            stays_in_week_nights=2,
            adults=2,
            children=0,
            babies=0,
            meal="BB",
            market_segment="Direct",
            distribution_channel="Direct",
            reserved_room_type="A",
            deposit_type="No Deposit",
            customer_type="Transient",
            is_repeated_guest=0,
            previous_cancellations=0,
            previous_bookings_not_canceled=0,
            agent="1",
            company="none",
            adr=100.0,
        )
        for h in ["City Hotel", "Resort Hotel"]
    ] * 60


@pytest.fixture
def runtime(tmp_path, records):
    # Independent training-side dataframe construction, not serving normalisation.
    bk = pd.DataFrame(records)
    bk["arrival"] = pd.to_datetime(bk.arrival)
    bk["booked"] = bk.arrival - pd.to_timedelta(bk.lead_time, unit="D")
    for col in [
        "hotel",
        "meal",
        "market_segment",
        "distribution_channel",
        "reserved_room_type",
        "deposit_type",
        "customer_type",
    ]:
        bk[col] = bk[col].astype("category")
    y = pd.Series(np.tile([0, 1], len(bk) // 2))
    agents = pd.Index(["1"])
    X = build_features(bk, agents)
    model = fit(list(X), pd.Series(True, index=bk.index), X, y, seed=3217)
    path = tmp_path / "runtime"
    path.mkdir()
    save_model(model, path / "booking_model.joblib", top_agents=agents, feature_columns=list(X))
    cal = HorizonCalibrator(
        7,
        LogisticRegression().fit(logit(pd.Series([0.1, 0.3, 0.7, 0.9])).to_frame("z"), [0, 0, 1, 1]),
    )
    hotels = ["City Hotel", "Resort Hotel"]
    cfg = dict(
        decision_lead_days=7,
        calib_end=pd.Timestamp("2016-10-01"),
        recal_weeks_grid=[4, 8, 12],
        hotels=hotels,
        variable_cost_eur=20,
        walk_cost_eur=250,
    )
    state = dict(
        config=cfg,
        chosen_policies={h: "model + blocks + re-level 8 wk" for h in hotels},
        calibrators={h: cal for h in hotels},
        flat_rates={h: 0.1 for h in hotels},
    )
    joblib.dump(state, path / "policy_state.joblib")
    manifest = dict(
        schema_version=1,
        diagnostic_gate={h: "PASS" for h in hotels},
        sha256={
            n: hashlib.sha256((path / n).read_bytes()).hexdigest()
            for n in ["booking_model.joblib", "policy_state.joblib"]
        },
    )
    (path / "manifest.json").write_text(json.dumps(manifest))
    return Predictor(path), bk, model, X


def test_training_serving_parity(runtime, records):
    predictor, bk, model, X = runtime
    actual_features = build_features(booking_frame(records), predictor.bundle["top_agents"])
    pd.testing.assert_frame_equal(X, actual_features)
    np.testing.assert_array_equal(predictor.predict(records), model.predict_proba(X)[:, 1])
    # Batch size and unknown codes must not alter an existing booking's score.
    unseen = dict(records[0], meal="NEW_MEAL", agent="99999", company=None)
    baseline = predictor.predict([records[0]])[0]
    assert predictor.predict([unseen, records[0]])[1] == baseline
    assert np.isfinite(predictor.predict([unseen])[0])


@pytest.mark.parametrize(
    "field,value",
    [
        ("country", "PRT"),
        ("reservation_status", "Canceled"),
        ("booked", "2017-07-01"),
        ("lead_time", -1),
        ("adults", True),
        ("adr", float("nan")),
        ("arrival", "2017-08-15T12:00:00"),
    ],
)
def test_invalid_or_leaking_input(records, field, value):
    row = dict(records[0])
    row[field] = value
    with pytest.raises(ValueError):
        booking_frame([row])


def test_null_semantics(records):
    row = dict(records[0], children=None, agent=None, company=None)
    frame = booking_frame([row])
    assert frame.children.iat[0] == 0 and frame.agent.iat[0] == "none" and frame.company.iat[0] == "none"


def test_artifact_tampering(runtime):
    predictor, *_ = runtime
    with (predictor.directory / "booking_model.joblib").open("ab") as f:
        f.write(b"changed")
    with pytest.raises(ValueError, match="fingerprint"):
        Predictor(predictor.directory)


def test_http_real_prediction_and_errors(runtime, records):
    predictor, *_ = runtime
    server = make_server(predictor, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(method, path, body=None, headers=None):
        conn = http.client.HTTPConnection(*server.server_address, timeout=5)
        conn.request(method, path, body=body, headers=headers or {})
        result = conn.getresponse()
        status = result.status
        data = json.loads(result.read())
        conn.close()
        return status, data

    try:
        assert request("GET", "/health")[0] == 200
        body = json.dumps({"booking": records[0]})
        code, result = request("POST", "/predict", body, {"Content-Type": "application/json"})
        assert code == 200
        assert result["cancellation_probability"] == predictor.predict([records[0]])[0]
        assert result["horizon"] == "booking_to_arrival" and result["decision_authorised"] is False
        assert request("POST", "/predict", body, {"Content-Type": "text/plain"})[0] == 415
        assert request("POST", "/predict", "{bad", {"Content-Type": "application/json"})[0] == 422
        assert request("POST", "/predict", "x" * 65537, {"Content-Type": "application/json"})[0] == 413
        assert request("GET", "/missing")[0] == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def snapshot(runtime, records):
    predictor, *_ = runtime
    return seal_snapshot(
        dict(
            schema_version=1,
            decision_date="2017-08-08",
            arrival="2017-08-15",
            lead_days=7,
            model_version=predictor.version,
            policy_version=predictor.manifest["sha256"]["policy_state.joblib"],
            bookings=[dict(booking_id=str(i), block_id=str(i // 2), booking=r) for i, r in enumerate(records[:4])],
            history=[
                dict(hotel=h, night=str(d.date()), observed=1, predicted=1.0, count=10)
                for h in ["City Hotel", "Resort Hotel"]
                for d in pd.date_range("2017-05-16", "2017-08-07")
            ],
        )
    )


def test_batch_uses_mature_history_and_requires_approval(runtime, snapshot):
    result = nightly_batch(snapshot, runtime[0])
    assert len(result["results"]) == 2
    assert all(
        r["recalibration_factor"] == 1 and r["authorised_oversell"] == 0 and r["requires_human_approval"]
        for r in result["results"]
    )
    changed = copy.deepcopy(snapshot)
    changed["history"][0]["night"] = "2017-08-08"
    changed.pop("snapshot_id")
    changed = seal_snapshot(changed)
    with pytest.raises(ValueError, match="matured"):
        nightly_batch(changed, runtime[0])


@pytest.mark.parametrize(
    "field,value",
    [("lead_days", 14), ("model_version", "wrong"), ("arrival", "2017-08-16")],
)
def test_batch_rejects_mismatches(runtime, snapshot, field, value):
    snapshot.pop("snapshot_id")
    snapshot[field] = value
    snapshot = seal_snapshot(snapshot)
    with pytest.raises(ValueError):
        nightly_batch(snapshot, runtime[0])


def test_snapshot_tampering(runtime, snapshot):
    snapshot["bookings"][0]["booking"]["adr"] = 999.0
    with pytest.raises(ValueError, match="fingerprint"):
        nightly_batch(snapshot, runtime[0])


def test_service_sigterm_exits_cleanly():
    import signal
    import subprocess
    import sys
    import time

    # Isolate signals in a child process; no model fixture is needed for shutdown.
    code = "from hotel_cancel.service import make_server,run_server; server=make_server(None,port=0); print('ready',flush=True); run_server(server)"
    child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "ready"
        # The readiness print precedes handler installation; wait until the child
        # enters its server loop before signalling it.
        time.sleep(0.2)
        started = time.perf_counter()
        child.send_signal(signal.SIGTERM)
        assert child.wait(timeout=2) == 0
        assert time.perf_counter() - started < 1.0
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
