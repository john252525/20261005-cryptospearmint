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
