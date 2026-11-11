# Task 19 submission checklist and evidence audit

Reviewed 11 November 2026 against the supplied Task 19 notebook, LLM access policy
and Reflective Diary Entry 1 rubric. This replaces the older stage checklist.
The notebook defines the required project work: C1–C5, E1–E4 and S1. S2 and S3
are optional. The supplied rubric applies to Diary Entry 1, not a final-project
marking scheme. No final mark, VLE submission or live operating approval is claimed.

The technical work is substantially evidenced. C3 policy approval and the final
hand-in/diary checks remain open. The original Resort gate failure is an expected
reference result, not a missing model improvement. The separate calibrated research
challenger cannot replace the unchanged-model evidence for C2/C4/E3.

## Required tasks

| Task | Audit finding | Evidence and remaining qualification |
| --- | --- | --- |
| C1 Find and guard all six traps | Evidenced | [Data contract](data-contract.md), [Stage 4](stage4-validation.md), [counted checks](evidence/stage4/data-checks.json); feature exclusion, outcome separation, forward duplicate isolation, as-of membership and horizon tests in `tests/test_features.py`, `test_splits.py`, `test_history.py`, `test_policy.py`. Counts cover post-booking/country artefacts; nightly median ADR and horizon calibration are explicitly guarded. Final-state timestamps remain an acknowledged source limitation. |
| C2 Reproduce the unchanged model | Evidenced with dated reproduction scope | [Baseline report](baseline-reproduction.md), [20-check comparison](evidence/baseline-comparison.json), [clean-clone result](evidence/stage14/clean-clone-summary.json), ADR 0002. Original fresh-clone result is for `3ca26fe`; it passed all 20 comparisons using seed 3217 and declared tolerances. Current coursework verification reruns the original booking learner and verifies the frozen per-hotel results. It is not a new full policy/notebook clean-clone claim. |
| C3 Own the operating point | Computation evidenced; approval open | [Sensitivity report](stage5-policy-evaluation.md), [run/grid](evidence/stage5/run.json), `selected-policies.csv`, `all-policies.csv`, `calibration.csv`, [ADR 0005](decisions/0005-policy-sensitivity.md). Covers horizons 0–14, walk costs EUR100–500, variable costs 0/20/40, 4/8/12-week candidates and resale 0/25/50%, selecting on validation only. Named manager sign-off is absent. The [simulation review packet](reviews/coursework-policy-review-v1.json) is unsigned and reviews the reference policies; it does not sign ADR 0005's distinct sensitivity candidates. |
| C4 Package, container and frozen gate | Implemented; fresh build verified separately in CI | Package/HTTP/batch entry points, Dockerfile, [Stage 6 container and parity](stage6-operational-service.md), [Linux test evidence](evidence/stage6/tests-linux.json), Makefile and workflow. Historical container verification predates the current revision. `make ci` now verifies reproduction and builds the service image; `make release-check` and `make publish` still reject the original failing model. No real PMS deployment is claimed. |
| C5 Register, document and monitor | Evidenced | [Tracking](stage9-tracking.md), [registry readback](evidence/stage9/verification.json), [Ubuntu registry](evidence/stage9-ubuntu/verification.json), [model card](model-card.md), [monitoring](stage7-monitoring.md), [load results](evidence/stage7/performance.json), replay report and Prometheus rules. City has champion/challenger; Resort has challenger only because its gate fails. Withholding its champion is deliberate. Weekly mature-outcome calibration, input PSI and retraining triggers are documented; live ongoing drift cannot be established from a historical replay. |
| E1 KB, provenance, validity and ablations | Evidenced | [KB report](stage10-knowledge-base.md), [AUPRC/cold-start ablation](evidence/stage10/ablation/verification.json), competency questions, temporal UK facts, SPARQL and SHACL. [19-case grounding comparison](evidence/stage10/briefing/report.json) is deterministic, not an LLM experiment. Separate recorded local-model with/without-KB comparisons exist in V1 and V5. V5 ordinary numeric exactness is code-owned in both arms; semantic prepaid answers/abstention, not numeric copying, are the meaningful KB comparison. |
| E2 Walking burden and governance | Evidenced historical simulation | [Walking report](stage11-walking-fairness.md), [verification](evidence/stage11/verification.json), group-burden/lottery CSVs, [governance analysis](stage11-governance.md), ADR 0013. Segment/channel/country audit is separated from allocation; nationality cannot enter the ranking interface. Services Directive/GDPR/AI Act positions are reasoned in the report, not certified legal clearance. Guest-room proxies and the incumbent/incremental-sales assumption limit conclusions. |
| E3 Reliability and calibration gate | Evidenced expected failure | [Frozen gate/ADR](stage8-evaluation.md), [original report](evidence/stage8/report.json), reliability CSV/PNG and MLflow ECE readback. City PASS; Resort FAIL only on expected/observed calibration ratio (0.6817 outside 0.85–1.15), while AUPRC and ECE pass. Coursework checks exact metrics, checks and frozen identity, not just a nonzero exit. The separately fitted calibrator is supplementary research; E3 retains the original model and thresholds. |
| E4 Blocks as entities | Evidenced with inferred-group limits | [Block report](stage12-group-blocks.md), [verification](evidence/stage12/verification.json), block-cost/status/size CSVs, block vocabulary/shapes/queries and [ADR 0014](decisions/0014-inferred-blocks-and-human-desk.md). 1,748 multi-row matches; all 20,719 on-books rows accounted for; generated graph validated. Matched rows are not verified travel parties. Human-desk recommendation is documented, not an implemented hotel desk. |
| S1 Local manager briefing | Current delivery contract evidenced; original failures retained | [V5 explanation](revised-briefing.md), [raw responses](evidence/remediation/briefing-v5/responses.json), [run report](evidence/remediation/briefing-v5/report.json), [MLflow](evidence/remediation/briefing-v5/mlflow-run.json), versioned prompt and tests. Pinned local Qwen run: 30/30 original nights, 30/30 new with KB and 30/30 without KB; six attacks safe, one withheld. Numeric facts are copied by trusted code, not generated. Raw interpretations accepted 95/96, so raw-model all-case quality remains FAIL. V1 stays 27/30 with KB. Guest drafts require digest-bound named approval; nothing is sent automatically. |

## Notebook hand-in checklist

- [x] Session 02 package layout, attribution, split/window/horizon in README; data/models/secrets excluded from Git. A historical fresh-clone baseline passes; current GitHub CI independently installs dependencies and verifies raw data.
- [x] Forward per-hotel evaluation, six trap guards, outcome separation and as-of tests.
- [ ] Overbooking constants in a signed-off ADR. ADR 0005 and the separate review packet remain unsigned. Resort economics and conservative fallback are argued.
- [x] Frozen-holdout gate, registry readback, model card and monitoring plan. Resort release stays blocked.
- [x] Extended KB, SHACL and AUPRC/cold-start/briefing comparisons.
- [x] [Revenue-manager recommendation](revenue-manager-recommendation.md) and previously visually checked one-page PDF at `output/pdf/revenue-manager-recommendation.pdf`. That PDF is a dated artifact, not a new rendering of every later code revision.
- [ ] All required tasks finally closed: C3 sign-off remains open; S1's component/raw-model distinction must be retained in the submitted explanation.
- [x] Required local open-weight run, pinned tag/digest, versioned prompt/schema/context, raw fixtures and MLflow cost/latency evidence. CI replays without live inference or paid API access.
- [ ] Diary Entry 1 final cross-check: written 400–600 words, at most eight content slides and five-minute video; consistency, recording and VLE upload not verified. Supplied rubric date: Monday 23 November 2026; 5% of unit mark. Its ARI3218 heading differs from Task 19's ARI3217 label.
- [ ] Regenerate and inspect final source/runtime archives after selecting the submission commit. Existing Stage 14/remediation archives predate these CI changes. Final VLE packaging requirements/deadline and any later diary requirements are not supplied by the Diary 1 rubric.

## Verification scope and current CI

[GitHub run 43022126664](https://github.com/Lukecamill/hotel-cancellations/actions/runs/43022126664)
at `8e8d6c6` passed all 246 tests with real PostgreSQL, lint, raw validation and
SHACL before the old combined pipeline stopped at the expected Resort gate.
That supersedes the blanket statement that the current database tests are skipped.
It does not replace the dated historical MLflow/load/container experiments.

The revised pipeline separates those meanings:

- `make coursework-check`: lint, tests, raw/split validation, SHACL, fresh original-model reference comparison, original briefing fixture regression and V5 safe-delivery replay.
- `make ci`: the coursework checks plus an image build. Passing means the software and assignment evidence reproduce and the service code builds.
- `make release-check`: the unchanged strict per-hotel quality gate, then V5 delivery quality. The original Resort model still fails this target.
- `make publish`: requires `release-check` even when invoked manually, before any registry push.
- GitHub `ci` is required for merging. The separate `release` job runs only after successful CI on a push to main. It loads the exact image saved by CI, rather than rebuilding it, and cannot publish through an expected-failure exception.

No part of this change approves a hotel policy, promotes the calibrated challenger,
changes a frozen threshold or declares the original failing model suitable.

[Remediation Ubuntu transcript](evidence/remediation-ubuntu/verification-from-terminal.json)
records the user-supplied terminal result (234 passed, six DB skips and V5 replay).
It is not a copied native Ubuntu evidence bundle; that distinction remains visible.

## Evidence integrity

The [audit manifest](evidence/coursework-audit/manifest.json) lists the exact
supplied-source fingerprints, task evidence files and their SHA-256 values at this
review. The audit inspects existing evidence and runs the revised automated checks;
it does not rerun every historical sensitivity, load, legal or live-LLM experiment.
`python scripts/submission_audit.py` verifies those evidence fingerprints and reports
reference failures, V5 delivery safety and supplementary research results separately.
It does not substitute the calibrated research challenger for the required model.
Historical evidence files are preserved. The [CI guide](coursework-and-release.md)
and [briefing explanation](revised-briefing.md) explain the new behavior.
