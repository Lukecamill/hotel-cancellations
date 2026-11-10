# Final submission checklist and evidence map

Prepared 10 November 2026. The user has only the existing course materials. The
supplied rubric covers Diary Entry 1, not the final project. This checklist follows
the supplied Task 19 notebook and agreed 14-stage plan; final VLE format, deadlines,
word/page limits and later diary requirements remain unconfirmed. It is not a
claim that submission has occurred or that all quality gates pass.

| Requirement | Main review entry | Evidence / outcome |
| --- | --- | --- |
| C1 data and leakage | `data-contract.md`, `stage4-validation.md` | Six notebook traps, as-of reconstruction and final-state limitations; automated tests |
| C2 unchanged baseline | `baseline-reproduction.md`, `model-card.md` | Frozen reference results; Stage 14 independent clone reproduces all 20 checks |
| C3 overbooking policy | `stage5-policy-evaluation.md`, ADR 0005 | Validation-only sensitivities; sign-off outstanding; original service policies retained |
| C4 operationalisation | `stage6-operational-service.md`, `manager-approval.md`, `stage8-evaluation.md` | Prior Ubuntu/PostgreSQL/container parity; current six DB tests skipped without a dedicated database |
| C5 tracking/monitoring | `stage7-monitoring.md`, `stage9-tracking.md` | Saved load/dashboard/alert evidence and MLflow registry checks; no new live load run claimed |
| E1 KB extension | `stage10-knowledge-base.md` | Provenance, temporal semantics, SHACL, learner-input ablations and live S1 comparison |
| E2 walking/governance | `stage11-walking-fairness.md`, `stage11-governance.md` | Allocation audits, nationality excluded from ranking, conditional burden and legal analysis |
| E3 quality gates | `stage8-evaluation.md`, `stage8-test-reconciliation.md` | Frozen holdout identity; Resort calibration FAIL deliberately retained |
| E4 group blocks | `stage12-group-blocks.md`, ADR 0014 | 1,748 inferred multi-row blocks, full generated RDF validation, conditional cost/split analysis |
| S1 required local LLM | `stage13-briefing.md`, ADR 0015 | Real local Qwen run, 30 paired nights, six attacks, costs/MLflow, versioned prompt/raw fixtures; exact-night target **27/30, FAIL** |
| Manager recommendation | `revenue-manager-recommendation.md` | One-page text target; no operational approval claimed |
| Reproduction | `stage14-final-verification.md`, `reproduce-final.md` | Independent clean clone/environment, raw CSV supplied separately, baseline and CI outcomes |
| Diaries/format | Existing Diary 1 assets | Recording/submission and later diary materials not verified; final rubric/brief unavailable |

## Outstanding items that must remain visible

- Resort calibration ratio 0.682 fails the recorded band; do not promote a Resort champion.
- Local briefing exactness is 27/30 nights; no retries/hidden repairs; strict gate FAIL.
- Policy-wide manager sign-off is outstanding. A simulated nightly decision does not replace it.
- Capacity, event-time field truth and verified parties are unavailable in the public snapshot.
- Current final-run database tests are skipped, not passed; earlier DB evidence is historical.
- Final-project rubric/milestone instructions are unavailable; confirm the VLE hand-in contract.
- Do not assert later diaries or any VLE submission are complete without evidence.

## Handoff

Review the source archive manifest and recommendation, commit the Stage 14 files,
and identify the final commit in the hand-in. The prepared archive includes a
labelled uncommitted documentation overlay; it is not a claim that the later files
were in the tested Stage 13 commit. Dataset, credentials, model weights, caches and
local databases are excluded from the source archive. The supplied predictive
reference runtime is a separate hash-checked archive. The local LLM is downloaded
using its recorded tag/digest; its raw fixtures suffice for offline CI replay.

The visually checked one-page PDF is `output/pdf/revenue-manager-recommendation.pdf`.
After the final commit, regenerate review archives with:

```sh
python3 scripts/build_submission_bundle.py --output /path/to/submission-output
```

The builder records source/tested commits, any uncommitted overlay and per-file
SHA-256 hashes, verifies archive contents, and writes separate source/runtime
archives plus checksum files. It does not publish, upload or commit anything.
