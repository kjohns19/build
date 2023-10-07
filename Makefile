PYTHON := python3.10

VENV_DIR := venv
ACTIVATE := . $(VENV_DIR)/bin/activate

.PHONY: all
all: lint


.PHONY: create-venv
create-venv:
	rm -rf $(VENV_DIR)
	$(PYTHON) -m venv $(VENV_DIR)
	$(ACTIVATE)
	pip install -r requirements-dev.txt

.PHONY: check-venv
check-venv:
	@ test -d venv || make create-venv


.PHONY: lint
lint: black mypy pylint

.PHONY: black
black: check-venv
	$(ACTIVATE)
	black src

.PHONY: mypy
mypy: check-venv
	$(ACTIVATE)
	mypy src

.PHONY: pylint
pylint: check-venv
	$(ACTIVATE)
	pylint src
