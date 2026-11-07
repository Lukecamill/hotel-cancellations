PYTHON ?= .venv/bin/python
CONFIG ?= config/config.yaml

.PHONY: baseline
baseline:
	$(PYTHON) -m hotel_cancel.baseline --config "$(CONFIG)"

.PHONY: data-check
data-check:
	$(PYTHON) -m hotel_cancel.validate --config "$(CONFIG)"

.PHONY: policy-sensitivity
policy-sensitivity:
	$(PYTHON) -m hotel_cancel.sensitivity --config "$(CONFIG)"
