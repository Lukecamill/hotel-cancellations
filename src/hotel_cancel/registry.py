"""Coursework registry operations: numeric eligibility and clean code before registration."""

import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from dotenv import dotenv_values
import yaml

from hotel_cancel.tracking import checked_gate

ROOT = Path(__file__).resolve().parents[2]
HOTELS = {"City Hotel": "task19-session6-city-booking", "Resort Hotel": "task19-session6-resort-booking"}


def settings(root=ROOT):
    path = root / "config/registry.yaml"
    config = yaml.safe_load(path.read_text())
    env = {**dotenv_values(root / ".env"), **os.environ}
    config["tracking_uri"] = env.get("MLFLOW_TRACKING_URI", config["tracking_uri"])
    if not config["tracking_uri"] or config["tracking_uri"] == "none":
        raise ValueError("Registry operations require an explicit tracking server or database URI")
    return config


def source_state(root=ROOT):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    try:
        return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def require_clean(state):
    commit = state.get("commit")
    if state.get("dirty") is not False or not isinstance(commit, str) or len(commit) != 40:
        raise ValueError("Registration requires a known clean commit; commit the completed changes and train again")


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def check_evidence(evidence, lock):
    if evidence.get("schema_version") != 1 or evidence.get("hotel") not in HOTELS:
        raise ValueError("Invalid registration evidence")
    require_clean(evidence.get("source", {}))
    if evidence.get("lock_sha256") != digest_json(lock) or evidence.get("identity") != lock["identity"]:
        raise ValueError("Frozen data identity or evaluation lock differs")
    hotel = evidence["hotel"]
    if evidence.get("horizon") != "booking_to_arrival":
        raise ValueError("Registry endpoint accepts booking-horizon models only")
    if not checked_gate(evidence.get("holdout", {}), lock["thresholds"][hotel]):
        raise ValueError("Quality gate failed: run stays tracked and cannot be registered")
    if hotel == "Resort Hotel" and not checked_gate(evidence.get("validation", {}), lock["thresholds"][hotel]):
        raise ValueError("Resort calibration must pass its prespecified validation gate")
    for key in ("base_model_sha256", "prediction_sha256"):
        if len(evidence.get(key, "")) != 64:
            raise ValueError("Missing artifact identity")
    if not evidence.get("model_uri"):
        raise ValueError("Missing logged model")
    return evidence


def read_evidence(client, run_id):
    with tempfile.TemporaryDirectory() as directory:
        return json.loads(Path(client.download_artifacts(run_id, "eligibility.json", directory)).read_text())


def register_run(client, run_id, lock, state, register_model):
    require_clean(state)
    run = client.get_run(run_id)
    if run.info.status != "FINISHED":
        raise ValueError("Only finished runs may be registered")
    evidence = check_evidence(read_evidence(client, run_id), lock)
    if evidence["source"] != state:
        raise ValueError("Registration checkout must match the clean training commit")
    name = HOTELS[evidence["hotel"]]
    tags = {
        "quality_gate": "PASS", "git_commit": state["commit"], "git_dirty": "false",
        "hotel": evidence["hotel"], "horizon": evidence["horizon"],
        "evidence_sha256": digest_json(evidence), "prediction_sha256": evidence["prediction_sha256"],
        "base_model_sha256": evidence["base_model_sha256"],
        "deployment_scope": "coursework_booking_prediction_only", "production_authorized": "false",
    }
    version = register_model(evidence["model_uri"], name, tags=tags)
    # Card is version-linked, not merely a file in the run's artifact folder.
    card = (ROOT / "docs/model-card-session6.md").read_text()
    client.update_model_version(name, version.version, description=card)
    client.set_registered_model_alias(name, "challenger", version.version)
    return {"name": name, "version": str(version.version), "run_id": run_id, "champion_set": False}


def verify_version(client, name, version, lock):
    model = client.get_model_version(name, str(version))
    if str(model.status) != "READY":
        raise ValueError("Model version is not ready")
    if name not in HOTELS.values() or not model.run_id:
        raise ValueError("Unrecognised model or missing lineage")
    if client.get_run(model.run_id).info.status != "FINISHED":
        raise ValueError("Model run is not finished")
    evidence = check_evidence(read_evidence(client, model.run_id), lock)
    if HOTELS[evidence["hotel"]] != name:
        raise ValueError("Hotel route and evidence disagree")
    tags = model.tags
    if (tags.get("evidence_sha256") != digest_json(evidence)
            or tags.get("git_commit") != evidence["source"]["commit"]
            or tags.get("git_dirty") != "false" or tags.get("quality_gate") != "PASS"
            or tags.get("prediction_sha256") != evidence["prediction_sha256"]
            or tags.get("deployment_scope") != "coursework_booking_prediction_only"):
        raise ValueError("Registered version metadata does not match its numerical evidence")
    return evidence, model


def move_alias(client, name, version, alias, lock):
    if alias not in ("champion", "challenger"):
        raise ValueError("Supported aliases: champion and challenger")
    verify_version(client, name, version, lock)
    before = dict(client.get_registered_model(name).aliases).get(alias)
    client.set_registered_model_alias(name, alias, str(version))
    actual = str(client.get_model_version_by_alias(name, alias).version)
    if actual != str(version):
        raise ValueError("Alias readback mismatch")
    return {"name": name, "alias": alias, "previous": before, "version": actual,
            "actor": getpass.getuser(), "at_utc": datetime.now(timezone.utc).isoformat(),
            "production_authorized": False}


def main():
    import mlflow
    from mlflow import MlflowClient

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("register")
    reg.add_argument("--run-id", required=True)
    alias = sub.add_parser("alias")
    alias.add_argument("--hotel", choices=HOTELS, required=True)
    alias.add_argument("--version", required=True, type=int)
    alias.add_argument("--alias", choices=["champion", "challenger"], default="champion")
    sub.add_parser("show")
    sub.add_parser("check")
    args = parser.parse_args()
    config = settings()
    mlflow.set_tracking_uri(config["tracking_uri"])
    mlflow.set_registry_uri(config["tracking_uri"])
    client = MlflowClient()
    lock = json.loads((ROOT / "config/evaluation-lock.json").read_text())
    if args.command == "register":
        result = register_run(client, args.run_id, lock, source_state(), mlflow.register_model)
    elif args.command == "alias":
        # Create the audit run before changing an alias, so an audit-store outage blocks the change.
        mlflow.set_experiment(config["audit_experiment"])
        with mlflow.start_run(run_name="coursework alias change"):
            mlflow.log_dict({"name": HOTELS[args.hotel], "version": args.version, "alias": args.alias}, "intent.json")
            result = move_alias(client, HOTELS[args.hotel], args.version, args.alias, lock)
            mlflow.log_dict(result, "alias-change.json")
        result["restart_required"] = True
    elif args.command == "check":
        result = {}
        for hotel, name in HOTELS.items():
            version = client.get_model_version_by_alias(name, "champion")
            evidence, _ = verify_version(client, name, version.version, lock)
            result[hotel] = {"name": name, "version": version.version, "gate": "PASS",
                             "prediction_sha256": evidence["prediction_sha256"]}
    else:
        result = {m.name: dict(m.aliases) for m in client.search_registered_models()
                  if m.name in HOTELS.values()}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
