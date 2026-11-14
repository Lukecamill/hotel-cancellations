"""Fresh fixed-baseline training, Resort calibration, tracked evidence and optional gated registration."""

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import joblib
import pandas as pd

from hotel_cancel.calibration_challenger import PLAN, fit_calibrator, logit
from hotel_cancel.config import load_config
from hotel_cancel.data import get_raw, load_bookings, separate_outcome
from hotel_cancel.model import save_model
from hotel_cancel.quality_gate import assess, verify_identity, prepare
from hotel_cancel.registry import ROOT, HOTELS, settings, source_state, digest_json, register_run
from hotel_cancel.serving import digest
from hotel_cancel.train import run_baseline


def run(*, register=False, config_path=None):
    import mlflow
    from mlflow.models import infer_signature
    from hotel_cancel.registry_model import HotelBookingModel
    from hotel_cancel.calibrated_registry_model import CalibratedHotelBookingModel

    config = load_config(config_path)
    registry_config = settings()
    mlflow.set_tracking_uri(registry_config["tracking_uri"])
    mlflow.set_registry_uri(registry_config["tracking_uri"])
    mlflow.set_experiment(registry_config["experiment"])
    state = source_state()
    lock = json.loads((ROOT / "config/evaluation-lock.json").read_text())
    runs = {}
    # Training exceptions remain recorded as FAILED in the parent run.
    with mlflow.start_run(run_name="fixed notebook learner and prespecified Resort calibration") as parent:
        mlflow.set_tags({"git_commit": state["commit"] or "unknown", "git_dirty": str(state["dirty"]).lower(),
                         "production_authorized": "false"})
        mlflow.log_params({"seed": config["seed"], "train_end": str(config["train_end"]),
                           "calibration_fit_start": PLAN["fit_start"], "calibration_fit_end": PLAN["fit_end"],
                           "validation_end": PLAN["validation_end"], "method": PLAN["method"]})
        mlflow.log_dict(lock, "evaluation-lock.json")
        mlflow.log_dict(state, "source-state.json")
        # All parameters are prescribed. No selection among windows or tuning on the holdout.
        booking = run_baseline(config, use_cache=False, save=False)
        bk, X, y, masks, identity = prepare(config)
        verify_identity(identity, lock["identity"])
        pd.testing.assert_frame_equal(booking.features, X)
        raw_sha = digest(get_raw("hotel_bookings.csv", config))
        if raw_sha != identity["raw_sha256"]:
            raise ValueError("Raw data changed during training")
        mlflow.log_params({"raw_sha256": raw_sha, "holdout_sha256": identity["holdout_sha256"],
                           **{k: int(v.sum()) for k, v in masks.items()}})
        mlflow.log_params({"learner." + k: str(v) for k, v in booking.model.get_params().items()})
        _, outcomes = separate_outcome(load_bookings(config, use_cache=False))
        base_p = pd.Series(booking.probabilities, index=bk.index)
        resort_ids = bk.index[bk.hotel.astype(str).eq("Resort Hotel")]
        calibrator, fit = fit_calibrator(base_p.loc[resort_ids], y.loc[resort_ids],
                                         bk.loc[resort_ids, "arrival"], outcomes.loc[resort_ids, "status_date"])
        corrected = base_p.copy()
        corrected.loc[resort_ids] = calibrator.predict_proba(logit(base_p.loc[resort_ids]).to_frame("z"))[:, 1]
        validation = bk.arrival.ge(PLAN["fit_end"]) & bk.arrival.lt(PLAN["validation_end"]) & bk.index.isin(resort_ids)
        validation_result = assess(y.loc[validation], corrected.loc[validation],
                                  **lock["thresholds"]["Resort Hotel"])[0]
        mlflow.log_dict(validation_result, "resort-validation.json")
        if validation_result["gate"] != "PASS":
            mlflow.set_tag("gate_passed", "false")
            raise ValueError("Calibration validation failed; no calibrated holdout inspection or registration")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            bundle = folder / "booking_model.joblib"
            save_model(booking.model, bundle, top_agents=booking.top_agents, feature_columns=list(X.columns))
            base_sha = digest(bundle)
            cal_path = folder / "booking-calibrator.joblib"
            joblib.dump({"calibrator": calibrator, "hotel": "Resort Hotel", "horizon": "booking_to_arrival",
                         "base_model_sha256": base_sha, "plan": PLAN}, cal_path)
            for hotel in HOTELS:
                selected = masks["test"] & bk.hotel.astype(str).eq(hotel)
                p = corrected if hotel == "Resort Hotel" else base_p
                result = assess(y.loc[selected], p.loc[selected], **lock["thresholds"][hotel])[0]
                with mlflow.start_run(run_name=hotel, nested=True) as child:
                    artifacts = {"booking_bundle": str(bundle)}
                    wrapper = HotelBookingModel(hotel)
                    prediction_sha = base_sha
                    if hotel == "Resort Hotel":
                        wrapper = CalibratedHotelBookingModel(hotel)
                        artifacts["booking_calibrator"] = str(cal_path)
                        prediction_sha = hashlib.sha256((base_sha + digest(cal_path)).encode()).hexdigest()
                    example = dict(json.loads((ROOT / "examples/predict.json").read_text())["booking"], hotel=hotel, agent="none", company="none")
                    sample = pd.DataFrame([example])
                    info = mlflow.pyfunc.log_model(
                        name="booking-model", python_model=wrapper, artifacts=artifacts,
                        input_example=sample,
                        code_paths=[str(ROOT / "src/hotel_cancel")],
                        signature=infer_signature(sample, pd.DataFrame({"cancellation_probability": [0.5]})),
                        pip_requirements=[line for filename in ["requirements-serving.txt", "requirements-registry.txt"]
                                          for line in (ROOT / filename).read_text().splitlines()
                                          if line and not line.startswith(("#", "-"))],
                    )
                    # Check every held-out booking via the actual raw-input wrapper before eligibility.
                    from hotel_cancel.features import BOOKING_INPUTS
                    frame = bk.loc[selected, [c for c in BOOKING_INPUTS if c != "booked"]].copy()
                    frame["arrival"] = frame.arrival.dt.strftime("%Y-%m-%d")
                    for column in frame.select_dtypes(include="category").columns:
                        frame[column] = frame[column].astype(object)
                    actual = mlflow.pyfunc.load_model(info.model_uri).predict(frame).cancellation_probability.to_numpy()
                    import numpy as np
                    error = float(np.max(np.abs(actual - p.loc[selected].to_numpy())))
                    if error > 1e-12:
                        raise ValueError("Registry input adapter differs from evaluation")
                    evidence = {"schema_version": 1, "hotel": hotel, "source": state, "identity": identity,
                                "lock_sha256": digest_json(lock), "holdout": result,
                                "validation": validation_result if hotel == "Resort Hotel" else None,
                                "horizon": "booking_to_arrival", "base_model_sha256": base_sha,
                                "prediction_sha256": prediction_sha, "model_uri": info.model_uri,
                                "fit_rows": int(fit.sum()) if hotel == "Resort Hotel" else int(masks["train"].sum()),
                                "maximum_adapter_error": error, "production_authorized": False}
                    mlflow.log_dict(evidence, "eligibility.json")
                    mlflow.log_dict(PLAN, "calibration-plan.json")
                    mlflow.log_artifact(str(ROOT / "docs/model-card-session6.md"), artifact_path="documentation")
                    mlflow.log_metrics({k: float(v) for k, v in result.items()
                                        if k not in ("checks", "gate")})
                    mlflow.log_metric("adapter_max_error", error)
                    mlflow.set_tags({"git_commit": state["commit"] or "unknown", "git_dirty": str(state["dirty"]).lower(),
                                     "gate_passed": str(result["gate"] == "PASS").lower(), "hotel": hotel,
                                     "parent_training_run": parent.info.run_id, "production_authorized": "false"})
                    runs[hotel] = child.info.run_id
    registrations = {}
    if register:
        client = mlflow.MlflowClient()
        for hotel, run_id in runs.items():
            registrations[hotel] = register_run(client, run_id, lock, source_state(), mlflow.register_model)
    return {"training_run": parent.info.run_id, "runs": runs, "registrations": registrations,
            "source": state, "production_authorized": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--config")
    args = parser.parse_args()
    print(json.dumps(run(register=args.register, config_path=args.config), indent=2))


if __name__ == "__main__":
    main()
