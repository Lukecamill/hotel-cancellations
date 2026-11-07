# Stage 3 baseline reproduction report

Date: 7 November 2026. **Result: the given booking model and overbooking policy were successfully reproduced on the supplied dataset.** All 20 saved-run comparison checks passed. This establishes local reproduction of the supplied method, not production suitability or completion of every C2 requirement.

## Evidence and method

Reference: all 38 original notebook cells executed unchanged in the project environment; full-precision evidence is in [reference results](evidence/reference-run/results.json) and [execution metadata](evidence/reference-run/execution.json). Original source SHA-256 remained `a623a0eb83a295b3e9feadde454157e442f62ab6b3b717ff4ef8db3c028d4377`.

Compared run: `20261107T121407Z-b2e30461`, started at 13:14:07 Malta time on 7 November 2026 (12:14:07 UTC). The student executed `make baseline` in the working repository. Small text outputs are preserved in [packaged-run evidence](evidence/packaged-run/run.json); generated models and full nightly files remain ignored under `models/baseline/20261107T121407Z-b2e30461/`.

The package preserves the supplied loading transformations, 22 ordered features, training-selected agent vocabulary, seed 3217, pooled LightGBM settings, horizon calibration, block definition, release distribution, cost function and temporal policy selection. Jul–Sep 2016 calibrates; Oct–Dec 2016 selects policies; Jan–Aug 2017 reports the frozen choices. No tuning, replacement learner or added features were used.

## Data and split identity

| Property | Reference / expected | Packaged run | Result |
|---|---|---|---|
| Input rows | 119,390 | 119,390 | Match |
| Training | 49,157 | 49,157 | Exact |
| Validation | 29,546 | 29,546 | Exact |
| Test | 40,687 | 40,687 | Exact |
| Raw SHA-256 | Dataset manifest | Same digest | Exact |
| Holdout SHA-256 | Original local execution | Same digest | Exact |

Raw SHA-256: `7c2ae42a7353905ea136e5c2287f17c92c5435826598bfbb8491c6f0c7b1fc06`.

Holdout SHA-256: `ac37475750f8f24abb767a78f7775b905a6ce0dce90d364402074181a9db017b`. Its prefix matches the supplied notebook’s printed fingerprint. Source/attribution, local file identity and the unconfirmed numeric upstream Kaggle version are documented in [dataset.md](dataset.md).

## Booking-model comparison

| Hotel / measure | Supplied printed result | Packaged result | Result |
|---|---:|---:|---|
| City AUPRC | 0.786 | 0.785721886318 | Within tolerance |
| Resort AUPRC | 0.628 | 0.627907608841 | Within tolerance |
| City ROC-AUC | 0.799 | 0.798905138003 | Matches rounded output |
| Resort ROC-AUC | 0.780 | 0.780414540687 | Matches rounded output |
| City expected / realised | 0.91 | 0.911281032106 | Within tolerance |
| Resort expected / realised | 0.68 | 0.681723343738 | Within tolerance |
| City gate | PASS | PASS | Exact |
| Resort gate | FAIL | FAIL | Exact |

The comparison also checks all full-precision test metrics, including pooled metrics and base rates, against the original local execution. CSV serialisation uses the tiny numerical tolerance below. Earlier in-memory extraction verification matched the reference exactly, including every feature row, dtype and column order. See [extraction evidence](evidence/extraction-verification.json).

Both hotels exceed their AUPRC thresholds, but Resort expected/realised is below the required 0.85–1.15 calibration band. Successful reproduction must retain that failure. A zero command exit status means execution succeeded; it is not approval to deploy the Resort model.

## Overbooking-policy comparison

| Output | Supplied printed result | Packaged result | Result |
|---|---|---|---|
| City chosen policy | Flat Jul–Sep 2016 rate | Same | Exact |
| Resort chosen policy | Model + blocks + 8-week re-levelling | Same | Exact |
| City chosen cost/night | EUR264 | EUR264.424650 | Within printed precision |
| City no-overbooking cost/night | EUR279 | EUR278.649465 | Within printed precision |
| City total savings | EUR3,457 | EUR3,456.63 | Within printed precision |
| Resort chosen cost/night | EUR96 | EUR96.183128 | Within printed precision |
| Resort no-overbooking cost/night | EUR98 | EUR98.068539 | Within printed precision |
| Resort total savings | EUR458 | EUR458.155 | Within printed precision |
| City oversell, 15 August | 3 | 3 | Exact |
| Resort oversell, 15 August | 0 | 0 | Exact |

Every numeric field in the four test-summary rows was compared with full-precision reference results. All example-night fields match exactly, including 66 City bookings, 15 Resort bookings and the numerical walk probabilities. Whole-euro nightly figures are rounded; multiplying their displayed difference by the number of nights will not reproduce the full-precision total savings.

## Tolerances

- Counts, policy names, gate outcomes, integer decisions and fingerprints: exact equality.
- Supplied three-decimal AUPRC: absolute difference <= 0.0005, as already stated in ADR 0002.
- Supplied two-decimal expected/realised ratio: absolute difference <= 0.005, as already stated in ADR 0002.
- Whole-euro displayed policy costs/savings: absolute difference <= EUR0.50, reflecting rounding rather than a business allowance.
- Full-precision numeric evidence after CSV roundtrip: absolute tolerance 1e-12 plus relative tolerance 1e-14. Exact checks remain for categorical and integer decisions; JSON example-night fields match exactly.

Policy/CSV tolerances were formalised in this report after execution, based on output precision. They were not preregistered. No method or settings were changed to satisfy them. These are reproduction tolerances, not operational performance thresholds.

## Runtime and environment

| Execution | Observed wall time | Scope |
|---|---:|---|
| Supplied notebook build | 85 s | Full teaching notebook, different machine |
| Original notebook on this Mac | 19.38 s | Full teaching notebook timer |
| Original notebook including kernel startup | 22.09 s | Launcher + full execution |
| Packaged booking pipeline | 1.44 s | Loading, one pooled model, scoring |
| Packaged policy pipeline | 1.00 s | Calibration, selection, test/example reporting |
| Complete packaged command | 2.50 s | Both pipelines and artifact writing |

These are single observations, not controlled speedup measurements. The full notebook additionally runs separate-hotel learners, deliberate trap experiments, drift/retraining demonstrations, KB ablations and plots. Their omission explains the scope difference; timings should not be presented as an equivalent-workload speedup.

Python 3.13.13 on macOS arm64. Core packages match the supplied printed versions: pandas 3.1.0, NumPy 2.5.4, LightGBM 4.7.0 and scikit-learn 1.9.1. Additional versions and source hashes are preserved in the run evidence. The original notebook emitted no cell stderr/error output; its launcher emitted a TCP-encryption warning. FutureWarning is suppressed by the notebook itself.

## Documented differences from notebook execution

1. Notebook globals become explicit arguments and returned state; configuration lives in YAML. Formulae and order are preserved. See [ADR 0002](decisions/0002-baseline-extraction.md) and [ADR 0003](decisions/0003-policy-extraction.md).
2. Raw data is reloaded by default rather than trusting the notebook’s unvalidated Parquet cache. Transformed data and holdout identity match.
3. The packaged command runs the baseline computations; educational comparisons, plotting, monitoring demonstrations and knowledge-base experiments remain in the reference notebook.
4. Model/preprocessing and policy state, metrics, configuration, fingerprints and runtime are persisted per run. This adds evidence handling, not a changed model.
5. The Mac editable-install path file repeatedly became hidden. A relative source-package link in the ignored local environment now makes normal imports work without PYTHONPATH. The repair changes package discovery only; it contains no credentials. README instructions cover recreating it.

## Verification and repeatability

The existing suite plus analytical block/policy checks passed: 16 tests. The thin notebook executed successfully. Saved booking models and policy state were reloaded; predictions and booking test metrics matched. See [command verification](evidence/baseline-command-verification.json).

Run from the repository root:

```bash
make baseline
# Use the path printed by the command for a new run:
.venv/bin/python scripts/compare_baseline.py --run models/baseline/20261107T121407Z-b2e30461
```

The comparison does not train or select policies; it reads saved results and writes [baseline-comparison.json](evidence/baseline-comparison.json), exiting nonzero if a check fails. It also checks source hashes, so comparing a historical run after changing source will report that difference rather than silently claiming the current code produced it.

## Scope and outstanding requirements

Stage 3’s six local reproduction steps are complete. This does not complete all of C2: the raw-data contract is scheduled in Stage 4, and the final frozen evaluation/CI gate is later. Full original-plus-policy execution from a newly published Git clone has not been demonstrated here; earlier repository documentation records a clean-copy booking-model check only. Linux/container behaviour remains unverified.

The input remains a final-state snapshot with booking-time assumptions, proxy group blocks and unknown hotel capacity. The given policy assumes sold-out nights and no resale. Those assumptions were preserved for reproduction and require later testing/sensitivity/governance work.

This run records base commit `9f8659f691088eae7b1c314ceedfac5d5dce6d68` plus a dirty working tree. New code and evidence have not been committed during this work; do not cite that base commit alone as containing the reproduced pipeline. Per-file source hashes identify the code used. Commit the reviewed implementation and evidence together before citing it in assessment materials.

## Follow-up: committed fresh-clone verification

After this report, commit `39fb510d427809fa0737d9ba58970f8223f96990` was verified from a fresh local Git clone and new environment. All 16 tests, the complete baseline command, 20 comparisons and the thin notebook passed without import repair. See [verification record](fresh-clone-verification.md). This supersedes the earlier local-clone and uncommitted-code limitations; GitHub publication/download and remaining C2 work are still unverified.
