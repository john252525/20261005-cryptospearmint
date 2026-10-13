SHELL := /bin/bash
PY ?= python3
TODAY := $(shell date -u +%F)

.PHONY: help install test lint backtest-funding backtest-funding-synthetic \
        paper-funding paper-funding-once report-funding report-funding-json clean-db

help:
	@echo "make install | test | lint"
	@echo "make backtest-funding              # 90d Binance public"
	@echo "make backtest-funding-synthetic    # 90d offline deterministic"
	@echo "make paper-funding                 # Binance testnet"
	@echo "make report-funding                # daily journal report"

install:
	$(PY) -m pip install -U pip
	$(PY) -m pip install pydantic pydantic-settings httpx pandas numpy pyarrow \
	                    pytest pytest-asyncio pyyaml

test:
	$(PY) -m pytest tests -q

lint:
	$(PY) -m compileall -q src

backtest-funding:
	$(PY) -m src.strategies.funding_carry.backtest \
		--days 90 --symbols BTCUSDT,ETHUSDT,SOLUSDT

backtest-funding-synthetic:
	$(PY) -m src.strategies.funding_carry.backtest \
		--days 90 --symbols BTCUSDT,ETHUSDT,SOLUSDT --synthetic

paper-funding:
	mkdir -p journal state
	$(PY) -m src.execution.funding_carry_runner --config configs/funding_carry.yaml

paper-funding-once:
	$(PY) -m src.execution.funding_carry_runner --config configs/funding_carry.yaml --once

report-funding:
	$(PY) -m src.report.funding_carry_report --date $(TODAY)

report-funding-json:
	$(PY) -m src.report.funding_carry_report --date $(TODAY) --json

clean-db:
	rm -f state/funding_carry.db journal/funding_carry.jsonl

# -- pipeline (pipeline-monitoring rebuild) --
.PHONY: pipeline-daily pipeline-nightly pipeline-rollback
pipeline-daily:
	$(PYTHON) -m src.pipeline.orchestrator report --kind daily

pipeline-nightly:
	$(PYTHON) -m src.pipeline.orchestrator fetch --symbol BTCUSDT --interval 1h --days 7
	$(PYTHON) -m src.pipeline.orchestrator audit
	$(PYTHON) -m src.pipeline.orchestrator backtest --strategy funding_carry --since 90d
	$(PYTHON) -m src.pipeline.orchestrator qa --allow-no-creds
	$(PYTHON) -m src.pipeline.orchestrator report --kind daily

pipeline-rollback:
	@if [ -z "$(DATE)" ]; then echo "usage: make pipeline-rollback DATE=YYYY-MM-DD [APPLY=1]"; exit 2; fi
	$(PYTHON) -m scripts.rollback --to-date $(DATE) $(if $(APPLY),,--dry-run)
