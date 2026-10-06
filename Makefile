SHELL := /bin/bash
.DEFAULT_GOAL := help

UV     ?= uv
PYTHON := /root/trading-desk/.venv/bin/python
CONFIG ?= configs/example.yaml

SYMBOL   ?= BTCUSDT
INTERVAL ?= 1m
DAYS     ?= 7
SECONDS  ?= 0

LIVE_CONFIRM ?=

.PHONY: help setup lint fmt type test fetch-crypto backtest paper-smoke paper live-dev live-prod clean qa-check qa-once qa-hourly qa-report

help: ## список целей
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## .env + uv sync
	@if [ -f .env ]; then echo ".env уже существует"; else cp .env.example .env && echo "создан .env"; fi
	$(UV) sync

lint: ## ruff check
	$(UV) run ruff check .

fmt: ## ruff --fix + black
	$(UV) run ruff check --fix .
	$(UV) run black .

type: ## mypy src tests
	$(UV) run mypy src tests

test: ## pytest -q
	$(UV) run pytest -q

fetch-crypto: ## Binance public REST -> data/bars/ (SYMBOL= INTERVAL= DAYS=)
	$(PYTHON) -m src.data.fetch_crypto --symbol $(SYMBOL) --interval $(INTERVAL) --days $(DAYS)

backtest: ## SMA(fast/slow) pandas engine
	$(PYTHON) -m src.research.backtest_sma --config $(CONFIG)

paper: ## paper runner: Binance testnet WS -> journal/ (SECONDS=0 -> бесконечно)
	$(PYTHON) -m src.execution.paper_runner --config $(CONFIG) --seconds $(SECONDS)

paper-smoke: ## paper runner 15 секунд (проверка WS соединения)
	$(PYTHON) -m src.execution.paper_runner --config $(CONFIG) --seconds 15
live-dev: ## stub: paper окружение под live-конфигом
	@echo "[live-dev] stub: paper_runner с live-настройками"
	APP_ENV=paper $(PYTHON) -m src.execution.paper_runner --config $(CONFIG)

live-prod: ## stub: требует LIVE_CONFIRM=YES-I-AM-LIVE
	@echo "[live-prod] stub: без LIVE_CONFIRM=YES-I-AM-LIVE не стартует"
	APP_ENV=live $(PYTHON) -m src.execution.live_runner --config $(CONFIG)

clean: ## кэши и артефакты (data/, journal/ НЕ трогает)
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build .coverage htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +


.PHONY: qa-check qa-once qa-hourly qa-report
qa-check: ## sanity: qa sources present (silent on success)
	@test -f qa/honesty_checks.py       || { echo "missing qa/honesty_checks.py"       >&2; exit 1; }
	@test -f qa/hourly_reconcile.py     || { echo "missing qa/hourly_reconcile.py"     >&2; exit 1; }
	@test -f scripts/qa_daily_report.py || { echo "missing scripts/qa_daily_report.py" >&2; exit 1; }

qa-once: qa-check ## run all 12 honesty checks on data/journal.jsonl
	@$(PYTHON) -m qa.honesty_checks --journal data/journal.jsonl --db data/state.db
qa-once-ci: qa-check ## CI variant: exit 0 if only reconcile is unverified
	@$(PYTHON) -m qa.honesty_checks --journal data/journal.jsonl --db data/state.db --allow-no-creds


qa-hourly: qa-check ## long-running hourly reconciler (run in separate terminal)
	$(PYTHON) -m qa.hourly_reconcile

.PHONY: qa-hourly-once qa-hourly-preflight
qa-hourly-once: qa-check ## reconcile once, then exit (CI/smoke)
	@$(PYTHON) -m qa.hourly_reconcile --once

qa-hourly-preflight: qa-check ## config-only check, no network
	@$(PYTHON) -m qa.hourly_reconcile --preflight
qa-hourly-verify: qa-check ## auth-only probe (no DB write)
	@$(PYTHON) -m qa.hourly_reconcile --verify-credentials
qa-hourly-clock: qa-check ## compare local vs venue server time (no auth)
	@$(PYTHON) -m qa.hourly_reconcile --check-clock



qa-report: qa-check ## write docs/reports/qa_YYYYMMDD.md
	@$(PYTHON) scripts/qa_daily_report.py

qa-once-strict: qa-check ## exit 1 if any check fails (CI gate)
	@$(PYTHON) -m qa.honesty_checks --journal data/journal.jsonl --db data/state.db

# ────────────────────────────────────────────────────────────────────────
#  Pipeline glue v2 (no heredocs; audit delegated to scripts/data_audit.py)
# ────────────────────────────────────────────────────────────────────────
.PHONY: check-env data-fetch data-audit research-backtest \
        strategies-pull pipeline-smoke full-cycle

check-env:
	@echo "CWD=$(CURDIR)  PY=$(PYTHON)"
	@$(PYTHON) -V
	@$(PYTHON) -c "import src, qa, scripts; print('imports ok')"

data-fetch: fetch-crypto
research-backtest: backtest

data-audit:
	@$(PYTHON) scripts/data_audit.py

strategies-pull:
	@if [ -d /opt/trading-desk/strategies ]; then \
	  cp -n /opt/trading-desk/strategies/*.py strategies/ 2>/dev/null || true; \
	  echo "strategies: $$(ls strategies/*.py 2>/dev/null | wc -l) file(s)"; \
	fi

pipeline-smoke: check-env data-audit qa-once-ci daily-report snapshot
	@echo "[pipeline-smoke] OK"

full-cycle: fetch-crypto data-audit backtest qa-once-ci daily-report
	@echo "[full-cycle] OK @ $$(date -u +%FT%TZ)"

daily-report:
	@$(PYTHON) -m src.pipeline.daily_report

snapshot:
	@$(PYTHON) -m scripts.rollback snapshot
