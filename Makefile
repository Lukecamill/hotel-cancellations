export PYTHONPATH := $(CURDIR)/src$(if $(PYTHONPATH),:$(PYTHONPATH))
PYTHON ?= .venv/bin/python
IMAGE ?= hotel-cancel:stage7
CONFIG ?= config/config.yaml
SNAPSHOT ?= artifacts/stage6/snapshot.json
OUTPUT ?= artifacts/stage6/batch.json
QUALITY_OUTPUT ?= docs/evidence/stage8
KB_OUTPUT ?= docs/evidence/stage10/shacl

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
	$(PYTHON) -m hotel_cancel.quality_gate --output "$(QUALITY_OUTPUT)"

ci: test kb-check
	@status=0; $(MAKE) quality-gate PYTHON="$(PYTHON)" || status=1; $(MAKE) briefing-quality PYTHON="$(PYTHON)" || status=1; exit $$status

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
