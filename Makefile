PY := .venv/bin/python

.PHONY: all setup ingest staging validate marts figures notebooks report excel exports test lint

all: ingest validate marts figures notebooks report excel exports

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

notebooks:
	cd notebooks && ../$(PY) -m nbconvert --to notebook --execute --inplace \
		01_h1_decomposition.ipynb 02_h2_gold_energy_waterfall.ipynb 03_h3_redirection.ipynb \
		04_h4_extensive_margin.ipynb 05_sector_exposure.ipynb

report:
	$(PY) -m src.report

excel:
	$(PY) -m src.excel

exports:
	$(PY) -m src.export

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check src tests
