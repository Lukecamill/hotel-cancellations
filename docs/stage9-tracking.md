# Stage 9 — MLflow tracking, registry and model card

Implemented 9 November 2026. This document distinguishes local verification
from a separate Ubuntu VM verification. No serving image is replaced.

## Local setup and execution

Use a separate environment; leave the reproducible baseline `.venv` untouched:

```sh
python3.13 -m venv .venv-tracking
.venv-tracking/bin/python -m pip install -r requirements-tracking.txt
PYTHONPATH=src make track-models
```

The provided requirements pin MLflow 3.18.0 and the resolved tracking environment.
`make track-models` uses `.venv-tracking/bin/python`. `PYTHONPATH=src` supports
running without reinstalling the project. Original raw data and the trusted
`models/serving` bundle must be present. Do not load untrusted pickle artifacts.
The default command writes `docs/evidence/stage9` and an ignored local SQLite
registry plus artifact store in `artifacts/stage9`. It disables MLflow usage
telemetry for this process. No account, API key or hosted destination is used.

The command does not fit a learner/calibrator, choose a policy, change serving
or update the evaluation lock. It verifies raw/holdout identity, saved feature
vocabulary/schema, supplied learner parameters and saved operating constants.
It recomputes validation/test metrics for the saved model, replays the saved
policy choices and logs the complete lineage and aggregate artifacts.

## What is logged and verified

One run per hotel records learner parameters; split dates/seed; raw, holdout,
model, policy and source fingerprints; Git revision/dirty state; package
versions; horizon/calibration periods; selected policy; walking/variable costs;
ADR rule; AUPRC, aggregate calibration, ECE, Brier score and policy costs.

Runs include evaluation JSON, reliability diagrams/bins, replay aggregates,
original saved policy, model manifest, learned preprocessing/model artifact,
model card, ADR and pinned environment. No raw dataset or real booking example
is logged. A model signature is inferred from a synthetic request. Source code
travels with the MLflow model so it can reuse the service preprocessing.

The saved model is scored on the frozen holdout (no refitting); reloaded
registered wrappers reproduce all 27,508 City and 13,179 Resort probabilities
within 1e-12. Verification includes persisted ECE readback and model loading
through each challenger alias. Tracking success does not imply quality pass:
`make ci` remains nonzero for Resort's expected/observed ratio failure.

| Registered model | Initial challenger | Initial champion | Scope |
|---|---|---|---|
| task19-city-booking | Reference baseline | Same reference version | Offline, quality passed |
| task19-resort-booking | Reference baseline | **Unset** | Calibration failed, promotion blocked |

Both entries use the same supplied pooled learner with hotel-specific request
adapters. No improved learner is invented. New tracking executions create audit
versions; existing champions are preserved. City bootstrap does not authorise
production or close the outstanding policy-wide revenue-manager sign-off.
Resort's missing champion is deliberate and enforced; never assign one just
to complete a checklist. See ADR 0011 and model-card.md.

## Inspect the local tracking UI

From the project root, start a localhost-only UI against the existing database:

```sh
.venv-tracking/bin/mlflow server --host 127.0.0.1 --port 5001 \
  --backend-store-uri "sqlite:///$(pwd)/artifacts/stage9/mlflow.db"
```

Open http://127.0.0.1:5001 . Inspect experiment `task19-frozen-baseline`, its
per-hotel runs and registered models/aliases. The registry uses local artifact
URIs, so retain the original artifact location. Back up the database and
mlartifacts together. The default SQLite URI is absolute in evidence and is
machine-specific. Neither the database nor the artifact store belongs in Git.

## Ubuntu verification

Transfer the supplied Stage 9 package, backing up current code first. The
package includes every source and test file plus a pinned expected test
inventory, avoiding the earlier incomplete transfer.

```sh
cd ~/hotel-stage6
python3 scripts/verify_stage9_ubuntu.py
```

This builds `hotel-cancel:stage9-check` from the existing Stage 8 check image,
compares source/test hashes and every collected test identifier, runs `make ci`,
then runs real tracking/registry readback in a separate local SQLite store.
It preserves the Stage 7 runtime/Compose files. Test database integration
remains skipped unless explicitly configured; skipped tests are not passed.

Expected software result: 140 passed, six database skips, 146 collected. City
quality passes; Resort quality fails. Tracking returns success after recording
both outcomes. Native Ubuntu evidence goes to `docs/evidence/stage9-ubuntu`;
its SQLite/artifacts remain in ignored `artifacts/stage9-ubuntu`. Only claim
Ubuntu verification after the script prints `STAGE9_UBUNTU_VERIFIED`.

Stage 8's test manifest is a historical snapshot of that stage, not a rolling
latest inventory. Stage 9 uses `config/stage9-run-inventory.json` instead.

## Confirmed Ubuntu result

The supplied Ubuntu terminal transcript confirms STAGE9_UBUNTU_VERIFIED: 146
collected, 140 passed and six database skips. All source/test fingerprints
match; MLflow readback and every holdout probability match; City has a champion
and Resort champion is withheld. Serving/Compose files are unchanged.
The transcript and parsed verification are saved under docs/evidence/stage9-ubuntu.
Native VM evidence files can be copied back separately. Git/user-environment
warnings in the container do not change these results; original training
provenance and matching source hashes remain recorded.
