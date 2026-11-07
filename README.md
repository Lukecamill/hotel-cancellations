# Hotel cancellations and overbooking

ARI3217 Task 19: package, reproduce, evaluate and operationalise the supplied hotel cancellation model and overbooking policy.

## Setup status

Repository structure and Python 3.13.13 environment prepared following Session 02. Dependencies are pinned in `requirements.txt`; configuration loading and the booking-time baseline training command are implemented. Overbooking policy, monitoring and knowledge-base packaging remain for later stages.

## Structure

- `src/hotel_cancel/`: reusable loading, features, model persistence, training and evaluation; policy and batch modules will follow.
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

The supplied model must be reproduced without tuning or replacing it. The local packaged booking-time baseline matches the notebook's reported split counts and rounded per-hotel metrics. Clean-source-copy setup is verified; full policy reproduction and verification from a published GitHub clone remain pending.

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

The environment has been checked on macOS Apple Silicon. A new environment in a clean source copy passed installation, all tests, training and notebook execution. Linux/container compatibility and verification from a published GitHub clone remain pending.

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

## Run the booking-time baseline

With the environment active, run from the project root:

```bash
hotel-train
# Equivalent:
python -m hotel_cancel.train
```

The local CSV belongs at `data/raw/hotel_bookings/hotel_bookings.csv`. If absent, the loader uses the notebook's KaggleHub download method. Training rebuilds processed data from the raw CSV by default and writes a model/preprocessing bundle, per-hotel metrics, diagnostic gate and runtime report under ignored `models/`. The cached loader remains available with `use_cache=True`; its inherited notebook cache is not source-fingerprinted, so avoid it after changing data or date windows.

Open `notebooks/hotel_cancellations.ipynb` for a thin presentation client. It calls the same pipeline, displays results and plots feature importance. The full supplied notebook remains unchanged in `notebooks/reference/`.

`hotel-train` returns success when training runs, even when the baseline's Resort diagnostic gate says FAIL. This reproduces the reference result; the deployment-blocking CI gate belongs to a later stage. Do not use the holdout to tune the model.

A saved `baseline.joblib` contains the model, training-selected top-agent vocabulary and ordered feature names. `hotel_cancel.model.predict_bookings` applies that preprocessing to the already-normalised booking frame produced by the loader. A raw booking API is not implemented yet.

### Notebook kernel and Mac troubleshooting

Select the project `.venv/bin/python` in VS Code. A named kernel can also be installed inside the environment:

```bash
python -m ipykernel install --sys-prefix --name hotel-cancellations --display-name "Python 3 (hotel-cancellations)"
```

On this Mac, the editable install's `.pth` file acquired the macOS hidden flag; Python 3.13 skips hidden `.pth` files. If importing `hotel_cancel` fails despite installation, clear that flag before starting Python:

```bash
chflags nohidden .venv/lib/python3.13/site-packages/__editable__.hotel_cancellations-0.1.0.pth
```

This is a local environment repair, not a change to the model. The independent clean environment did not require it.

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

The initial baseline is published in commit `92cb28fa518c262a2fd6f89bd9e1279f4e69dbc1`, verified against GitHub. The setup check used a clean source copy; verification from a GitHub clone remains pending. Kaggle download access and Linux/container support have not yet been verified.

## Counted data-quirk evidence

Run `python -m hotel_cancel.audit` to regenerate [the quirk table](docs/evidence/data-quirks.md) and its JSON companion from the original CSV. It counts outcome leakage, duplicates, nationality patterns, non-refundable cancellations, ADR anomalies, country-code inconsistencies and invalid guest/stay combinations. The audit checks outcome separation, forbidden feature names and temporal train/test duplicate overlap; it does not clean the data or change the learner.

Reports record the dataset hash, audit-source hash, base commit and whether the working tree had uncommitted changes. Commit the audit code, tests and generated evidence together before citing them in the diary. Guard coverage and remaining work are stated per quirk; the complete six-trap suite and raw-data contract remain pending.
