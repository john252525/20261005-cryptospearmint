SHELL := /bin/bash
.DEFAULT_GOAL := help

UV     ?= uv
PYTHON ?= $(UV) run python
CONFIG ?= configs/example.yaml

SYMBOL   ?= BTCUSDT
INTERVAL ?= 1m
DAYS     ?= 7

LIVE_CONFIRM ?=

.PHONY: help setup lint fmt type test fetch-crypto backtest paper live-dev live-prod clean

help:
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup:
	@if [ -f .env ]; then echo ".env уже существует"; else cp .env.example .env && echo "создан .env"; fi
	$(UV) sync

lint:
	$(UV) run ruff check .

fmt:
	$(UV) run ruff check --fix .
	$(UV) run black .

type:
	$(UV) run mypy src tests

test:
	$(UV) run pytest -q

fetch-crypto:
	$(PYTHON) -m src.data.fetch_crypto --symbol $(SYMBOL) --interval $(INTERVAL) --days $(DAYS)

backtest:
	$(PYTHON) -m src.research.backtest_sma --config $(CONFIG)

paper:
	$(PYTHON) -m src.execution.paper_runner --config $(CONFIG)

live-dev:
	@echo "[live-dev] stub: paper_runner с live-настройками"
	APP_ENV=paper $(PYTHON) -m src.execution.paper_runner --config $(CONFIG)

live-prod:
	@echo "[live-prod] stub: требует LIVE_CONFIRM=YES-I-AM-LIVE"
	APP_ENV=live $(PYTHON) -m src.execution.live_runner --config $(CONFIG)

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build .coverage htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
