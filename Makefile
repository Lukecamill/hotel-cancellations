PYTHON ?= .venv/bin/python
CONFIG ?= config/config.yaml

.PHONY: baseline
baseline:
	$(PYTHON) -m hotel_cancel.baseline --config "$(CONFIG)"
