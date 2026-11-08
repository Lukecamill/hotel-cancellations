# Hotel cancellations and overbooking

ARI3217 Task 19: package, reproduce, evaluate and operationalise the supplied hotel cancellation model and overbooking policy.

## Setup status

Repository structure and Python 3.13.13 environment prepared following Session 02. Dependencies are pinned in `requirements.txt`; configuration loading and the booking-time baseline training command are implemented. The given overbooking policy is now packaged; monitoring and knowledge-base packaging remain for later stages.

## Structure

- `src/hotel_cancel/`: reusable loading, features, model persistence, training and evaluation; the given policy is packaged; the operational batch module will follow.
- `config/`: shared non-secret configuration.
- `notebooks/reference/`: unchanged supplied notebook.
- `tests/`: automated checks.
- `docs/decisions/`: architecture decision records.
- `data/`: local raw and processed data, excluded from Git.
- `models/`: generated model artifacts, excluded from Git.

## Dataset and evaluation

Source: [Hotel booking demand on Kaggle](https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand), CC BY 4.0, as identified in the supplied notebook.

Citation: Antonio, N., de Almeida, A., Nunes, L. (2019). Hotel booking demand datasets. Data in Brief, 22, 41–49.

Arrival window: July 2015–August 2017. Training: July 2015–June 2016. Validation: July–December 2016; July–September calibrates and October–December selects policies. Frozen test holdout: January–August 2017. Default nightly decision horizon: seven days before arrival.

The supplied model must be reproduced without tuning or replacing it. The local packaged booking-time baseline matches the notebook's reported split counts and rounded per-hotel metrics. Clean-source-copy setup is verified; the policy extraction now exactly matches captured reference outputs; verification from a published GitHub clone remains pending.

## Course materials

Allocation is complete. The LLM access policy and Reflective Diary Entry 1 rubric have now been supplied. The rubric is specifically for Diary Entry 1; its heading says ARI3218 whereas the task notebook says ARI3217, so confirm the unit label against the VLE. The final-project rubric and full milestone brief remain unconfirmed.

## Python environment

Use Python 3.13.13 (`.python-version`). The supported project series is Python 3.13.

On macOS, install LightGBM's system dependency first: `brew install libomp` (verified with libomp 23.1.5). Linux will need its corresponding OpenMP runtime when the container is built.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install --no-deps --no-build-isolation -e ".[dev]"
python -m pip check
```

`requirements.txt` pins the complete working environment, including development and notebook tools. `pyproject.toml` defines the installable package and dependency ranges. `notebook-constraints.txt` records the six versions printed by the reference notebook. The exact Python patch release is available through your Python installer; this environment was created with uv and seeded with pip.

In VS Code, select `.venv/bin/python` as the Python interpreter and notebook kernel. The package is installed in editable mode, so edits in `src/` take effect immediately.

The environment has been checked on macOS Apple Silicon. A new environment in a clean source copy passed installation, all tests, training and notebook execution. Linux container serving and batch compatibility are now verified in Stage 6; verification from a published GitHub clone remains pending.

## Configuration

`config/config.yaml` contains the supplied notebook's baseline settings. Dates use exclusive end boundaries. Policy costs and gate thresholds remain the supplied assumptions, pending the later business decision record.

Optionally copy `env.example` to `.env` in the project root. Override data/model locations and log level there. `.env` is excluded from Git. Precedence: shell environment, then `.env`, then YAML; an explicit configuration path passed to `load_config()` overrides `CONFIG_PATH`.

```python
from hotel_cancel.config import load_config
config = load_config()
print(config["raw_dir"])
```

Relative paths resolve from the project root rather than the current working directory. The editable source checkout is the default root; pass `project_root` explicitly for another deployment directory. Loading configuration does not create directories or change the process environment.

Run the configuration checks with `python -m pytest`.

## Run the complete baseline

From the repository root, after environment setup and providing the verified raw CSV:

```bash
make baseline
```

This runs the given pooled booking model, horizon calibration, validation-only policy selection and frozen test reporting. It rebuilds processed data from raw input, uses settings in `config/config.yaml`, and creates a unique ignored `models/baseline/<UTC timestamp>-<id>/` folder. Previous runs are retained.

Equivalent command and optional overrides:

```bash
.venv/bin/python -m hotel_cancel.baseline
make baseline CONFIG=config/config.yaml
# With another prepared interpreter:
make baseline PYTHON=/absolute/path/to/python
```

Each successful run saves:

| File | Contents |
|---|---|
| `booking_model.joblib` | Model, learned agent vocabulary and feature order |
| `policy_state.joblib` | Per-hotel calibrators, flat rates, chosen policies and effective settings |
| `booking_metrics.csv`, `booking_gate.csv` | Validation/test metrics and diagnostic hotel gates |
| `policy_validation.csv` | All validation candidates and selected policies |
| `policy_test_nights.csv`, `policy_test_summary.csv` | Frozen-policy nightly and aggregate test results |
| `tonight.json`, `chosen_policies.json` | Example-night quantities and selected policies |
| `config.json` | Effective non-secret settings; environment variables are not captured |
| `run.json` | Status, raw/holdout fingerprints, split counts, stage/total timings, package versions and source/Git provenance |

A successful baseline run exits zero even when the Resort diagnostic gate says FAIL, matching the supplied reference. Execution failures exit nonzero and retain a failed run report; incomplete run folders must not be treated as successful results. This is not the later deployment/CI quality gate. Generated files remain ignored under the default model directory; keep any custom output directory out of version control too. Joblib files should only be loaded from trusted runs.

The command was checked against the reference results, including reloading the saved model and policy state. See [command verification](docs/evidence/baseline-command-verification.json). The six local reproduction steps are complete; see [baseline reproduction report](docs/baseline-reproduction.md) for results, tolerances, differences and remaining fresh-clone/C2 requirements.

## Run the booking-time baseline

With the environment active, run from the project root:

```bash
hotel-train
# Equivalent:
python -m hotel_cancel.train
```

The local CSV belongs at `data/raw/hotel_bookings/hotel_bookings.csv`. If absent, the loader uses the notebook's KaggleHub download method. Training rebuilds processed data from the raw CSV by default and writes a model/preprocessing bundle, per-hotel metrics, diagnostic gate and runtime report under ignored `models/`. The cached loader remains available with `use_cache=True`; cache reuse now requires validated raw data plus matching source/window/loader metadata and Parquet byte identity; stale caches are rebuilt.

Open `notebooks/hotel_cancellations.ipynb` for a thin presentation client. It calls the same pipeline, displays results and plots feature importance. The full supplied notebook remains unchanged in `notebooks/reference/`.

`hotel-train` returns success when training runs, even when the baseline's Resort diagnostic gate says FAIL. This reproduces the reference result; the deployment-blocking CI gate belongs to a later stage. Do not use the holdout to tune the model.

A saved `baseline.joblib` contains the model, training-selected top-agent vocabulary and ordered feature names. `hotel_cancel.model.predict_bookings` applies that preprocessing to the already-normalised booking frame produced by the loader. A raw booking API is not implemented yet.

### Notebook kernel and Mac troubleshooting

Select the project `.venv/bin/python` in VS Code. A named kernel can also be installed inside the environment:

```bash
python -m ipykernel install --sys-prefix --name hotel-cancellations --display-name "Python 3 (hotel-cancellations)"
```

On this Mac, editable-install `.pth` files repeatedly acquire the hidden flag, which Python 3.13 skips. Clearing the flag did not persist during investigation. The local environment now uses a relative source-package link inside `.venv` so imports do not depend on `.pth` discovery. Source edits still take effect immediately.

If this recurs after recreating the environment, run from the repository root:

```bash
.venv/bin/python scripts/repair_local_import.py
```

The script requires this checkout’s environment and refuses to overwrite an existing package or a link to another source. It changes only the ignored local environment; normal package installation remains the fresh-checkout workflow. No PYTHONPATH setting is needed after repair. Restart an already-open notebook kernel.

## Setup verification and remaining work

See [setup verification](docs/setup-verification.md) for the clean-copy procedure and results. On 7 November 2026, dependency installation, 11 tests, outside-folder imports, `hotel-train` and the thin notebook all passed in a new Python environment. Per-hotel metrics and the holdout fingerprint matched the original local run exactly.

For a new checkout, create the environment as above, then provide the CSV separately:

```bash
mkdir -p data/raw/hotel_bookings
# Copy your downloaded hotel_bookings.csv into that directory.
python -m pytest -q
hotel-train
```

Select the new environment's Python interpreter before opening the notebook. No processed dataset or saved model from another environment is needed.

The initial baseline is published in commit `92cb28fa518c262a2fd6f89bd9e1279f4e69dbc1`, verified against GitHub. The setup check used a clean source copy; verification from a GitHub clone remains pending. Kaggle download access remains unverified. Linux container serving and batch support were subsequently verified in Stage 6.

## Counted data-quirk evidence

Run `python -m hotel_cancel.audit` to regenerate [the quirk table](docs/evidence/data-quirks.md) and its JSON companion from the original CSV. It counts outcome leakage, duplicates, nationality patterns, non-refundable cancellations, ADR anomalies, country-code inconsistencies and invalid guest/stay combinations. The audit checks outcome separation, forbidden feature names and temporal train/test duplicate overlap; it does not clean the data or change the learner.

Reports record the dataset hash, audit-source hash, base commit and whether the working tree had uncommitted changes. Commit the audit code, tests and generated evidence together before citing them in the diary. That initial audit report is historical. The complete six-trap suite and raw-data contract were subsequently implemented and verified in Stage 4; see docs/stage4-validation.md for current guard coverage.

## Baseline data identity

See [dataset source and setup](docs/dataset.md) and the [verified dataset manifest](docs/evidence/dataset-manifest.json) for the exact supplied CSV fingerprint, attribution, fresh-checkout instructions and version-control checks.

## Original notebook reference run

Stage 3 Step 3 completed: see [reference-run results and instructions](docs/reference-run.md). All original notebook cells executed successfully; booking metrics and policy outputs match the supplied rounded results.

## Packaged policy and extraction verification

The thin notebook now calls `hotel_cancel.policy.run_policy_baseline(result, config)` after `run_baseline(config)`. It returns snapshot/calibration state, validation selection, frozen-policy test results and example-night quantities. See [ADR 0003](docs/decisions/0003-policy-extraction.md).

Run the full-data extraction comparison from the repository root:

```bash
.venv/bin/python scripts/verify_extraction.py
```

This trains the given model and compares features and outputs with the original notebook evidence; it does not tune anything. Results are written to ignored `artifacts/extraction-verification.json`. The recorded [verification result](docs/evidence/extraction-verification.json) reports exact matches. The local import repair above removes the need for a source-path override.

## Stage 3 reproduction report

[Baseline reproduction report](docs/baseline-reproduction.md): all 20 saved-run comparison checks passed for the student’s terminal run. It includes booking and policy comparisons, timing scope, tolerances and outstanding assessment requirements.

## Fresh-clone verification of Stage 3

A fresh local Git clone of commit `39fb510d427809fa0737d9ba58970f8223f96990` passed dependency checks, all 16 tests, `make baseline`, all 20 comparisons and the thin notebook in a new environment with separately supplied raw data. No import repair was needed. See [fresh-clone verification](docs/fresh-clone-verification.md). This verifies committed local files; GitHub push/download remains unverified. Stage 6 later verified Linux container serving and batch execution, independently of this historical fresh-clone run.

## Stage 4: data validation and leakage guards

See [Stage 4 validation](docs/stage4-validation.md), [raw-data contract](docs/data-contract.md) and [ADR 0004](docs/decisions/0004-data-and-history-guards.md). Training now enforces the raw contract, booking-feature boundaries and temporal split guards; policies require matching decision-horizon forecasts. Known baseline anomalies are counted and retained. No model or baseline output changed.

```bash
.venv/bin/python -m pytest -q
make data-check
```

The 64-test suite covers malformed data/cache identity, all six traps and historical reconstruction boundaries. `make data-check` produces counted evidence using the local CSV. The CSV cannot establish historical feature values or intraday ordering; the documented reconstruction remains a tested convention.

## Stage 5: overbooking sensitivity

Run `make policy-sensitivity` to compare policies using October–December 2016 validation nights across the grid in `config/stage5.yaml`. This command excludes 2017 rows before modelling and does not score the holdout. Results and limitations are in [the Stage 5 report](docs/stage5-policy-evaluation.md); manager sign-off remains pending in [ADR 0005](docs/decisions/0005-policy-sensitivity.md). The original `make baseline` reproduction remains available.

## Stage 6: booking API, nightly batch and PostgreSQL snapshot

The booking API and nightly batch share the existing feature recipe. Export an explicit completed reference baseline with `python -m hotel_cancel.serving --run models/baseline/<run-id> --output models/serving`, then run `make serve`. See the [Stage 6 runbook and verification](docs/stage6-operational-service.md) for complete request examples, snapshot export, PostgreSQL and container commands. Nightly quantities are review-only; unsigned Stage 5 candidates are not promoted. HTTP, PostgreSQL, training/serving parity and Docker image build/runtime/size are verified on the course Ubuntu ARM64 VM. All 93 Linux tests passed; the image is 212.16 MB and stopped cleanly in 0.219 seconds.

## Simulated nightly manager approval

Open `http://127.0.0.1:8080/review` through the Ubuntu SSH tunnel to review the prepared hotel recommendations. Approve, reduce or reject each one with your name and reason; PostgreSQL saves the immutable simulated decision and its snapshot/model versions. Real operational authorisation remains zero. See [manager approval instructions](docs/manager-approval.md) and [ADR 0007](docs/decisions/0007-simulated-manager-approval.md). The expanded Linux/PostgreSQL suite has 112 passing tests.

## Stage 7: monitoring and performance

The Compose stack now includes Prometheus and Grafana. Versioned prediction and batch logs persist in PostgreSQL; `/metrics` exposes request/error/latency and input metrics. The provisioned dashboard separates live service/input measurements from historical calibration, PSI and policy-cost replay. See [Stage 7 report](docs/stage7-monitoring.md) and [ADR 0008](docs/decisions/0008-monitoring-and-performance.md). The final burst experiment verified 600/600 measured predictions in PostgreSQL with no HTTP errors and p95 under 35ms; 118 Linux tests and all 20 baseline reproduction checks passed. Alerts and the retraining response are documented; external notifications and the Stage 8 CI gate are not configured here.

## Diary 1: additional data-quirk investigation

The [additional stay/status-date investigation](docs/diary1-additional-quirk.md) finds 27 Check-Out rows whose status date differs from arrival plus recorded nights. Run `python -m hotel_cancel.stay_audit` to reproduce the counts. This is an offline diagnostic with explicit uncertainty; rows and cancellation labels are preserved, and no model/policy changes are made.

## Diary 1: enterprise architecture map

The [four-layer architecture map](docs/diary1-architecture.md) places the implemented package, data records, manager-review screen, database engine, containers and dashboard in the course's Business, Data, Application and Technology domains. PNG, SVG and Mermaid versions are under `docs/figures/`. Future PMS/channel-manager integrations and simulated approvals are clearly marked.

## Diary 1: capability-pattern comparison

The [pattern comparison](docs/diary1-pattern-comparison.md) assesses current nightly human approval against hypothetical automatic acceptance on latency, daily running cost, decision ownership and failure behaviour. It separates measured performance from illustrative labour assumptions and records a conditional break-even calculation. It does not implement automatic overselling or claim a measured human performance advantage.

## Diary 1: AI Act classification

The [AI Act research note](docs/diary1-ai-act-classification.md) records a scoped other/non-high-risk assessment for prospective ordinary hotel cancellation/overbooking advice, a separate conditional analysis of current pre-deployment testing, provider/deployer roles and reassessment triggers. It uses official EU sources and the July 2026 amended text; this is not production regulatory clearance. See [ADR 0009](docs/decisions/0009-intended-use-ai-act.md).
