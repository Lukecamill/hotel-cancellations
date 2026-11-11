export PYTHONPATH := $(CURDIR)/src$(if $(PYTHONPATH),:$(PYTHONPATH))
PYTHON ?= .venv/bin/python
VERSION := $(shell $(PYTHON) -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
GIT_SHA := $(shell git rev-parse --short=12 HEAD 2>/dev/null || echo nogit)
IMAGE ?= hotel-cancel
SOURCE ?=
LABELS = $(if $(SOURCE),--label org.opencontainers.image.source=$(SOURCE))
CONFIG ?= config/config.yaml
SNAPSHOT ?= artifacts/stage6/snapshot.json
OUTPUT ?= artifacts/stage6/batch.json
QUALITY_OUTPUT ?= docs/evidence/stage8
DATA_CHECK_OUTPUT ?= docs/evidence/stage4
KB_OUTPUT ?= docs/evidence/stage10/shacl

.PHONY: baseline
baseline:
	$(PYTHON) -m hotel_cancel.baseline --config "$(CONFIG)"

.PHONY: data-check
data-check:
	$(PYTHON) -m hotel_cancel.validate --config "$(CONFIG)" --output "$(DATA_CHECK_OUTPUT)"

.PHONY: policy-sensitivity
policy-sensitivity:
	$(PYTHON) -m hotel_cancel.sensitivity --config "$(CONFIG)"

.PHONY: serve nightly-batch container
serve:
	$(PYTHON) -m hotel_cancel.service

nightly-batch:
	$(PYTHON) -m hotel_cancel.batch --snapshot-file "$(SNAPSHOT)" --output "$(OUTPUT)"

container: build

.PHONY: monitoring-replay
monitoring-replay:
	$(PYTHON) -m hotel_cancel.monitor_replay

# Strict gate: the supplied Resort model currently fails calibration.
.PHONY: test quality-gate ci
test:
	$(PYTHON) -m pytest -q

quality-gate:
	$(PYTHON) -m hotel_cancel.quality_gate --output "$(QUALITY_OUTPUT)"

# Recursive calls keep the pipeline sequential even with make -j.
ci:
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) data-check DATA_CHECK_OUTPUT=artifacts/ci/data-check
	$(MAKE) kb-check KB_OUTPUT=artifacts/ci/shacl
	$(MAKE) quality-gate QUALITY_OUTPUT=artifacts/ci/quality-gate
	$(MAKE) briefing-quality
	$(MAKE) build

TRACKING_PYTHON ?= .venv-tracking/bin/python
.PHONY: track-models
track-models:
	$(TRACKING_PYTHON) -m hotel_cancel.tracking


.PHONY: kb-check kb-ablation kb-briefing-check
kb-check:
	$(PYTHON) -m hotel_cancel.knowledge --output "$(KB_OUTPUT)"

kb-ablation:
	$(PYTHON) -m hotel_cancel.kb_ablation

kb-briefing-check:
	$(PYTHON) -m hotel_cancel.kb_briefing_eval

.PHONY: walking-audit
walking-audit:
	$(PYTHON) -m hotel_cancel.walking


.PHONY: block-audit
block-audit:
	$(PYTHON) -m hotel_cancel.blocks

.PHONY: briefing-record briefing-replay
briefing-record:
	$(PYTHON) -m hotel_cancel.briefing record

briefing-replay:
	$(PYTHON) -m hotel_cancel.briefing replay

.PHONY: briefing-quality
briefing-quality:
	$(PYTHON) -m hotel_cancel.briefing replay --require-model-pass

CALIBRATION_OUTPUT ?= docs/evidence/remediation/calibration
.PHONY: calibration-challenger revised-briefing-quality remediation-check
calibration-challenger:
	$(PYTHON) -m hotel_cancel.calibration_challenger verify --output "$(CALIBRATION_OUTPUT)"

revised-briefing-quality:
	$(PYTHON) -m hotel_cancel.briefing_revision replay

remediation-check: test calibration-challenger revised-briefing-quality

.PHONY: simulation-signoff-check coursework-release-check
simulation-signoff-check:
	$(PYTHON) scripts/record_simulation_signoff.py verify

coursework-release-check: remediation-check simulation-signoff-check

.PHONY: install lint version build publish up ci-data
install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install --no-deps --no-build-isolation -e ".[dev]"

lint:
	$(PYTHON) -m ruff check src tests scripts/prepare_ci_data.py

version:
	@echo $(VERSION)

ci-data:
	$(PYTHON) scripts/prepare_ci_data.py

build:
	docker build --build-arg MODEL_VERSION=$(VERSION) --label org.opencontainers.image.version=$(VERSION) --label org.opencontainers.image.revision=$(GIT_SHA) $(LABELS) -t "$(IMAGE):$(VERSION)" -t "$(IMAGE):$(VERSION)-$(GIT_SHA)" .

# Publication is called by CI only after make ci succeeds in the same job.
publish:
	docker push "$(IMAGE):$(VERSION)"
	docker push "$(IMAGE):$(VERSION)-$(GIT_SHA)"

up:
	MODEL_VERSION=$(VERSION) IMAGE=$(IMAGE) docker compose up -d --build
