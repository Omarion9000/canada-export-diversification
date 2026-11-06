PY := .venv/bin/python

.PHONY: all setup ingest staging validate marts figures exports test lint

all: ingest validate marts figures exports

setup:
	python3.14 -m venv .venv
	$(PY) -m pip install -r requirements.txt

ingest:
	$(PY) -m src.ingest

staging:
	$(PY) -m src.build staging

validate: staging
	$(PY) -m src.validate

marts:
	$(PY) -m src.build mart

figures:
	$(PY) -m src.figures

exports:
	$(PY) -m src.export

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check src tests
