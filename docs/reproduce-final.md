# Reproduce the final technical submission

Current CI and submission status: see [the updated audit](submission-checklist.md) and
[coursework/release separation](coursework-and-release.md). The stage results and
old command outcomes below are historical; `make quality-gate` remains strict,
while current `make ci` verifies expected reproduction before building.

Use a clean checkout/source extraction on Python 3.13.13 with the OS OpenMP runtime
(macOS libomp; Linux container uses its documented runtime). See README for pinned
setup. The Stage 14 audit used an independent local Git clone and fresh venv,
reusing the installed Python/OpenMP runtime and downloaded dependency cache only.
It did not copy the original venv, processed cache, .env, model or LLM weights.

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps --no-build-isolation -e '.[dev]'
.venv/bin/python -m pip check
```

Provide the attributed raw CSV separately at
`data/raw/hotel_bookings/hotel_bookings.csv`. Verify SHA-256
`7c2ae42a7353905ea136e5c2287f17c92c5435826598bfbb8491c6f0c7b1fc06`.
Downloading the dataset from Kaggle is described in `dataset.md`; fresh-clone
verification supplies this existing CSV rather than claiming a new network download.

```sh
make baseline
# Replace RUN_ID with the explicit successful folder printed by that command.
.venv/bin/python scripts/compare_baseline.py --run models/baseline/RUN_ID
.venv/bin/python -m hotel_cancel.serving --run models/baseline/RUN_ID --output models/serving
make ci
```

`make baseline` should succeed; the reference comparison must report all 20 checks
passed. `make ci` intentionally exits nonzero for Resort calibration and recorded
briefing factuality. Tests and SHACL should pass; replay should reproduce 58 accepted
of 66 with eight withheld. Passing reproduction is not passing quality. No live
LLM or hosted quota is used by CI. Six PostgreSQL tests skip unless an explicit
**dedicated test database** is provided; do not point them at the demonstration DB.

## Original runtime and later historical audits

A rebuilt booking learner has identical model bytes in this audit, but its policy
pickle includes machine-specific paths/settings. A different policy-file SHA does
not by itself show different decisions. The original Stage 11–13 run inventories
pin the original serving pair. Use the separate `reference-runtime.tar.gz` when
reproducing those exact historical audits in another checkout. Verify its manifest
hashes before loading trusted project joblib files. Extract at the project root
**before** generating a different `models/serving`; retain regenerated output in
another folder if comparing both. Do not overwrite the original demonstration.

```sh
tar -xzf reference-runtime.tar.gz
make walking-audit
make block-audit
make briefing-replay
```

Core KB/ablation commands, Stage 9 MLflow setup and Stage 6 PostgreSQL/container
instructions remain in their linked reports. Tracking is reproduced with isolated
`requirements-tracking.txt`; original local store paths in historical JSON are
provenance, not portable artifact URLs. Recreate a store using the documented
commands rather than assuming a copied absolute artifact URI works.

For live S1 reproduction install Ollama, pull the recorded `qwen3:4b-instruct` tag,
verify the full configured digest, start `scripts/serve_stage13_local.sh` and run
`make briefing-record`. This replaces fixtures: retain the original run before
re-recording and do not claim new output will be byte-identical across hardware.
The original run costs zero API fees; hardware/electricity are not free. See
`stage13-briefing.md` for all limitations and strict quality checks.

## Reproduce the separate remedies

`make remediation-check` checks the calibrated challenger and the V5 delivery
contract. It requires the reference runtime and the separately provided
`booking-calibration-runtime.tar.gz` (or regenerate the predeclared calibrator
with `python -m hotel_cancel.calibration_challenger run`). Replay uses committed
raw local-model interpretations and calls no model. The live component entry is
`hotel_cancel.briefing_revision.generate(case, settings)`, which returns only
validated assembled facts. `briefing_revision record` uses the original pinned
local Qwen model and V5 prompt, retaining raw interpretations and composed outputs.

`make coursework-release-check` additionally requires formal simulation sign-off.
It remains blocked because the user chose to leave reviewer details for now.
No command here authorises real hotel operation. The dedicated Ubuntu verifier
is `scripts/verify_remediation_ubuntu.py`; it writes independent evidence, fits
only the prespecified calibration window, and never calls the LLM.
