PYTHON ?= .venv/bin/python
IMAGE ?= hotel-cancel:stage7
CONFIG ?= config/config.yaml
SNAPSHOT ?= artifacts/stage6/snapshot.json
OUTPUT ?= artifacts/stage6/batch.json

.PHONY: baseline
baseline:
	$(PYTHON) -m hotel_cancel.baseline --config "$(CONFIG)"

.PHONY: data-check
data-check:
	$(PYTHON) -m hotel_cancel.validate --config "$(CONFIG)"

.PHONY: policy-sensitivity
policy-sensitivity:
	$(PYTHON) -m hotel_cancel.sensitivity --config "$(CONFIG)"

.PHONY: serve nightly-batch container
serve:
	$(PYTHON) -m hotel_cancel.service

nightly-batch:
	$(PYTHON) -m hotel_cancel.batch --snapshot-file "$(SNAPSHOT)" --output "$(OUTPUT)"

container:
	docker build -t "$(IMAGE)" .

.PHONY: monitoring-replay
monitoring-replay:
	$(PYTHON) -m hotel_cancel.monitor_replay

# Strict gate: the supplied Resort model currently fails calibration.
.PHONY: test quality-gate ci
test:
	$(PYTHON) -m pytest -q

quality-gate:
	$(PYTHON) -m hotel_cancel.quality_gate

ci: test
	$(MAKE) quality-gate PYTHON="$(PYTHON)"

TRACKING_PYTHON ?= .venv-tracking/bin/python
.PHONY: track-models
track-models:
	$(TRACKING_PYTHON) -m hotel_cancel.tracking
