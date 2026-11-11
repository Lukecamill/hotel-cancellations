"""Read-only coursework evidence audit; never substitutes a research challenger."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def audit():
    manifest_path = ROOT / "docs/evidence/coursework-audit/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    missing, changed = [], []
    for task in manifest["tasks"].values():
        for entry in task["files"]:
            path = ROOT / entry["path"]
            if not path.is_file():
                missing.append(entry["path"])
            elif hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                changed.append(entry["path"])
    reference = json.loads((ROOT / "docs/evidence/stage8/report.json").read_text())
    original = json.loads((ROOT / "docs/evidence/stage13/report.json").read_text())
    revised = json.loads((ROOT / "docs/evidence/remediation/briefing-v5/report.json").read_text())
    clone = json.loads((ROOT / "docs/evidence/stage14/clean-clone-summary.json").read_text())
    research = json.loads((ROOT / "docs/evidence/remediation/calibration/report.json").read_text())
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    return dict(
        evidence_present=not missing,
        evidence_fingerprints_match=not changed,
        missing_files=sorted(set(missing)),
        changed_files=sorted(set(changed)),
        reference_hotel_quality_gates={h: r["gate"] for h, r in reference["hotels"].items()},
        reference_release_quality=reference["status"],
        original_briefing_quality=original["model_quality_gate"],
        original_briefing_exact_with_kb_nights=original["groups"]["with_kb"]["accepted"],
        revised_briefing_delivery_quality=revised["component_quality_gate"],
        revised_briefing_ordinary_exact=revised["ordinary_accepted"],
        revised_briefing_attacks_safe=revised["injection_safe"],
        revised_briefing_attacks_withheld=revised["injection_withheld"],
        revised_raw_model_all_cases_quality=revised["quality_gate"],
        supplemental_calibrated_research_gates={h: v["gate"] for h, v in research["hotels"].items()},
        research_substituted_for_reference=False,
        historical_clean_clone=dict(
            tested_commit=clone["tested_commit"],
            baseline_reference_checks_passed=clone["baseline_reference_checks_passed"],
        ),
        prior_github_database_run=dict(
            tested_commit="8e8d6c697d1f0aa99a9c0e0541a990df00cede22", passed=246, skipped=0, run_id=43022126664
        ),
        current_commit=commit,
        open_requirements=manifest["open_requirements"],
        ready_for_unconditional_submission=False,
        release_approved=False,
        production_authorized=False,
        scope="Evidence-file inspection, not fresh execution of every historical experiment or VLE submission",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    try:
        report = audit()
    except (OSError, ValueError, KeyError) as error:
        print(json.dumps(dict(status="ERROR", error=str(error), release_approved=False)))
        return 1
    print(json.dumps(report, indent=2))
    return int(
        not report["evidence_present"]
        or not report["evidence_fingerprints_match"]
        or (args.require_ready and not report["ready_for_unconditional_submission"])
    )


if __name__ == "__main__":
    raise SystemExit(main())
