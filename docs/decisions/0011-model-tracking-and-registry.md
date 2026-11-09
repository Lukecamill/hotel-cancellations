# ADR 0011 — Local MLflow tracking, per-hotel registry and guarded aliases

Date: 9 November 2026. Status: implemented; offline coursework scope.

Use MLflow 3.18.0 in a separate pinned tracking environment. Keep baseline and
production-serving dependencies unchanged. Use a local SQLite backend and
local filesystem artifacts under ignored artifacts/stage9; no hosted service,
new credentials or public ports. Record all resolved dependencies in
requirements-tracking.txt. MLflow supports registry aliases with a database
backend: https://mlflow.org/docs/latest/ml/model-registry/workflow/ .

Track the actual saved reference bundle, recompute metrics on the fingerprinted
holdout, reuse saved policy/calibrators, and never fit or select on test. Log
learner parameters, split dates/seed, raw/feature/model/policy/source hashes,
Git state, runtime package versions, Platt period, validation-only policy
choices, ADR rule, costs, reliability bins/plots, model card and this decision.
Validation metrics are separate from test metrics. Replaying original fixed
choices does not claim to rerun the entire Stage 5 sensitivity grid. E3 ECE is
logged and read back from MLflow; Stage 8 remains a strict nonzero quality gate.

Register task19-city-booking and task19-resort-booking as hotel-specific raw
booking adapters around the same pooled learner, using the exact online
booking validation and feature path. Embed the original learned preprocessing
and model bundle. Include a signature inferred from a synthetic request but
no dataset example rows. Preserve saved policy state as a run artifact.
Verify all 40,687 test probabilities after reloading the logged models and
verify registry alias loading. The model/policy artifacts do not change.

Every run can create a new reviewable challenger version; repeated runs are
explicit audit versions, not new learners or improvements. Only a candidate
whose numeric AUPRC, aggregate ratio, ECE and two-class checks pass can
bootstrap a missing champion. Existing champions are preserved; replacing
one requires a later explicit reviewed workflow. Registry bootstrap does not
change serving or provide policy-wide sign-off. All versions are tagged
production_authorized=false and offline_coursework_only.

Resort's champion remains deliberately unset. Giving a failed model that alias
would contradict the frozen promotion gate. The registry supports the alias
when a valid candidate exists; an empty champion slot is the truthful outcome.
A known-failing existing champion triggers an error rather than silent reuse.
City initially uses one reference version for both aliases, explicitly avoiding
a claim that an independently improved challenger was trained.

MLflow run FINISHED means logging succeeded; quality_gate=FAIL still blocks
promotion. Tracking returning zero must never be used in place of make ci.
This change records models, not guest-level recommendations or notifications.
Database and filesystem stores must move/back up together; Git contains only
code, documentation, fingerprints and aggregate evidence, not the live store.
