"""Verify recorded assignment outcomes without approving the model for release."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from hotel_cancel import briefing, briefing_revision, quality_gate
from hotel_cancel.config import load_config

ROOT = Path(__file__).resolve().parents[2]


def verify_reference(code, report, expected):
    """An expected quality failure is accepted only with matching identity and metrics."""
    if code != expected["exit_code"] or report.get("status") != expected["status"]:
        raise ValueError("Reference gate outcome changed or evaluation failed")
    if report.get("identity_verified") is not True:
        raise ValueError("Frozen holdout identity was not verified")
    if report.get("lock_sha256") != expected["lock_sha256"]:
        raise ValueError("Evaluation lock changed; coursework expectation must not move the gate")
    if report.get("selected_on_holdout") is not False:
        raise ValueError("Holdout selection is forbidden")
    if set(report.get("hotels", {})) != set(expected["hotels"]):
        raise ValueError("Reference hotel coverage changed")
    for hotel, target in expected["hotels"].items():
        actual = report["hotels"][hotel]
        for key, value in target.items():
            if isinstance(value, float):
                valid = isinstance(actual.get(key), (int, float)) and math.isclose(
                    actual[key], value, abs_tol=1e-12, rel_tol=1e-14
                )
            else:
                valid = actual.get(key) == value
            if not valid:
                raise ValueError(f"Reference result changed: {hotel}/{key}")


def verify_replays(original, revised, expected):
    for name, actual in [("original_briefing", original), ("revised_briefing", revised)]:
        for key, value in expected[name].items():
            if actual.get(key) != value:
                raise ValueError(f"Recorded briefing contract changed: {name}/{key}")


def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    result = dict(status="ERROR", release_approved=False, production_authorized=False)
    try:
        expectation_path = ROOT / "config/coursework-reference.json"
        expected = json.loads(expectation_path.read_text())
        code, reference = quality_gate.run(
            load_config(), ROOT / "config/evaluation-lock.json", output / "reference-gate"
        )
        verify_reference(code, reference, expected["reference_gate"])
        original, revised = briefing.replay(), briefing_revision.replay()
        verify_replays(original, revised, expected)
        result.update(
            status="PASS",
            meaning="Assignment reference reproduced and revised briefing delivery contract verified",
            reference_gate_status=reference["status"],
            reference_gate_exit_code=code,
            reference_identity_verified=True,
            original_briefing=original,
            revised_briefing=revised,
            expectation_sha256=hashlib.sha256(expectation_path.read_bytes()).hexdigest(),
            live_model_called=False,
        )
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error))
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return (0 if result["status"] == "PASS" else 1), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="artifacts/ci/coursework")
    args = parser.parse_args()
    code, result = run(args.output)
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
