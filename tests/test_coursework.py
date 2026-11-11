"""Expected coursework failures must never hide errors or changed results."""

import copy
import json
from pathlib import Path

import pytest

from hotel_cancel.coursework import verify_reference, verify_replays

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads((ROOT / "config/coursework-reference.json").read_text())


def reference():
    return json.loads((ROOT / "docs/evidence/stage8/report.json").read_text())


def test_expected_reference_failure_is_verified_without_release_approval():
    verify_reference(1, reference(), EXPECTED["reference_gate"])


@pytest.mark.parametrize("change", ["error", "pass", "identity", "lock", "metric", "reason", "coverage", "nan"])
def test_unexpected_failures_and_changed_results_cannot_pass_coursework(change):
    report, code = reference(), 1
    if change == "error":
        code, report = 2, {"status": "ERROR"}
    elif change == "pass":
        code, report["status"] = 0, "PASS"
    elif change == "identity":
        report["identity_verified"] = False
    elif change == "lock":
        report["lock_sha256"] = "edited"
    elif change == "coverage":
        del report["hotels"]["City Hotel"]
    elif change == "reason":
        report["hotels"]["Resort Hotel"]["checks"]["auprc"] = False
    else:
        report["hotels"]["Resort Hotel"]["ece"] = float("nan") if change == "nan" else 0.5
    with pytest.raises(ValueError):
        verify_reference(code, report, EXPECTED["reference_gate"])


def test_changed_briefing_scores_are_not_accepted_as_expected_failures():
    original, revised = copy.deepcopy(EXPECTED["original_briefing"]), copy.deepcopy(EXPECTED["revised_briefing"])
    verify_replays(original, revised, EXPECTED)
    revised["injection_safe"] = 5
    with pytest.raises(ValueError, match="injection_safe"):
        verify_replays(original, revised, EXPECTED)
