# trading-desk

Monorepo: dev -> paper -> small live.

## Quickstart

    git clone <REPO_URL> trading-desk
    cd trading-desk
    make setup
    $EDITOR .env
    make test
    make lint
    make type
    make fetch-crypto SYMBOL=BTCUSDT INTERVAL=1m DAYS=7
    make backtest
    make paper

## Раскладка

| Путь | Роль |
|---|---|
| src/ | весь Python-код |
| configs/ | yaml-конфиги |
| data/ | runtime: parquet-бары |
| research/ | ad-hoc анализ |
| backtest/ | артефакты прогонов |
| strategies/ | пользовательские стратегии |
| execution/ | runtime lock/sock |
| risk/ | runtime kill-switch файл |
| journal/ | append-only JSONL |
| infra/ | Docker, systemd |
| docs/ | архитектура, runbook |

## Правила

- Live нельзя запустить без APP_ENV=live и LIVE_CONFIRM=YES-I-AM-LIVE.
- Все ордера проходят src/risk/limits.py::check_order.
- Kill switch — файл risk/KILL_SWITCH.

## QA honesty guardrails

Run: `make qa-once` (12 checks against `data/journal.jsonl`).

Without live testnet credentials, `reconcile_with_testnet` reports FAIL
and the suite passes **11/12** — this is the expected, correct baseline
(fail-closed). Real green requires one successful hourly round-trip:

    cp .env.example .env       # fill real testnet keys, never commit
    make qa-hourly-verify      # auth probe, no DB writes
    make qa-hourly-once        # one real tick, writes reconcile_log
    make qa-once               # 12/12

Long-running: `make qa-hourly` under tmux/systemd (not `timeout`).
