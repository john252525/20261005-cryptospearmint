# HANDOFF — передача проекта

Всё, что описано ниже, проверено выполнением, не декларацией.

## Что сделано

### Инфраструктура

- uv + pyproject.toml, lock, Python 3.11
- Makefile: setup, lint, test, fetch, backtest, wf, funding-*, paper-funding, live-funding-*, kill/resume
- CI (GitHub Actions): ruff + black + pytest + smoke risk-layer + smoke order-chain (mock)
- Docker: `infra/Dockerfile`; systemd units: `infra/systemd/*`
- Logging: loguru + append-only JSONL в `journal/trades/YYYY-MM-DD.jsonl`

### Слои

- `data/` — fetch OHLCV (Binance spot), fetch funding (Binance USDⓈ-M futures). Публичные API, ключи для fetch не нужны.
- `research/` — pandas backtest engine, walk-forward (grid + OOS chaining), funding portfolio, reconcile.
- `strategies/` — sma_cross, momentum_roc, donchian_breakout, mean_reversion_z (все — задокументированный отрицательный вердикт) и funding_carry (работает).
- `execution/` — paper_runner_funding (REST опрос), live_runner_funding (ccxt + mock), live_funding_daemon (snap-loop 00/08/16 UTC), exchanges.py (mock + real адаптеры).
- `risk/` — limits.py (position/order/open-count), kill_switch.py (file-based), daily_loss.py (day_pnl accrual + enforcement).
- `journal/` — append-only JSONL, разделение event/trade, mode=paper|live_testnet.

### Стратегия-победитель: funding carry delta-neutral

- Universe: LINKUSDT, BTCUSDT, LTCUSDT, DOGEUSDT, ETHUSDT
- Параметры: lookback=42 (14 дней), stat=median, entry_thr=0.00007, exit_thr=-0.00003, deploy_ratio=0.9
- Backtest 2022-01-01 .. 2024-12-31: CAGR 7.01%, max_dd -0.25%, funding/fees ratio 30.35
- Backtest только 2024: CAGR 11.12%, max_dd -0.14%
- Модель: лонг спот + шорт перп равными ноционалами; общий капитал 90%, слот = deploy_ratio / 5 на пару.

Детали — `docs/STRATEGY.md`.

## Как запускать

    cd /root/trading-desk
    make setup                            # .env + uv sync
    make test                             # 20+ тестов
    make backtest                         # pandas engine
    make funding-portfolio                # carry backtest
    make paper-funding DURATION_HOURS=72  # 9 snap'ов paper-цикла

Live testnet — только с ключами (см. ниже).

## Что НЕ проверено против реальной биржи

1. **Реальный order flow на testnet** — mock-цепочка работает; `make live-funding-testnet` не запускался (нет ключей).
2. **Комиссии брокера** — модель закладывает spot 10 bps + perp 5 bps taker; реальные ставки могут отличаться.
3. **Reconcile strict** — реализован, не запускался на реальных балансах.
4. **Daily-loss в бою** — проверен инжектом -600 в state; реальный сценарий не испытан.
5. **Small live с деньгами** — не запускался.

## Basis: измерен, учтён, throttled

Проверено на живых публичных данных (oct-2026, 5 пар):

- Диапазон basis = (perp/spot − 1) × 10000: **−3.1 … −7.1 bps**, устойчиво отрицательный (backwardation перпа)
- `risk/daily_loss.py::basis_pnl_usd(entry, exit, notional)` учитывает convergence: `(entry − exit) / 10000 × notional`
- `day_basis` — 4-я компонента day_pnl рядом с funding и fees
- **basis-throttle**: `max_basis_bps=15.0` в `configs/funding_portfolio.yaml` — открытие пропускается при `|basis| > порог`, событие `basis_throttle` в journal
- `execution/paper_runner_shadow.py` сэмплирует basis по всем парам на каждом snap'е → `artifacts/paper_shadow/basis.jsonl`

## Известные ограничения

- Paper-runner без daily-loss — у него dataclass State, отдельная интеграция.
- Unrealized PnL открытых позиций не учитывается в day_pnl (правильно для delta-neutral, не покрывает basis-расширение).
- Sharpe 16 в backtest — артефакт нулевой волатильности 8h funding-шагов; реалистичная оценка 3–5.
- Reconcile с брокером — реализован в двух режимах: log-only (по умолчанию) и strict (RECONCILE_STRICT=true). В strict не запускался.

## Получение testnet-ключей

Один блок, редактируешь кавычки, копируешь целиком:

    cd /root/trading-desk
    python3 - <<'PY'
    SPOT_KEY    = ""
    SPOT_SECRET = ""
    FUT_KEY     = ""
    FUT_SECRET  = ""
    import re
    from pathlib import Path
    vals = {"BINANCE_TESTNET_SPOT_KEY": SPOT_KEY, "BINANCE_TESTNET_SPOT_SECRET": SPOT_SECRET,
            "BINANCE_TESTNET_FUTURES_KEY": FUT_KEY, "BINANCE_TESTNET_FUTURES_SECRET": FUT_SECRET}
    empty = [k for k, v in vals.items() if not v.strip()]
    if empty:
        raise SystemExit("empty: " + ", ".join(empty))
    p = Path(".env")
    s = p.read_text(encoding="utf-8")
    for k, v in vals.items():
        if re.search(rf"^{k}=.*$", s, flags=re.M):
            s = re.sub(rf"^{k}=.*$", f"{k}={v.strip()}", s, flags=re.M)
        else:
            s += f"\n{k}={v.strip()}\n"
    p.write_text(s, encoding="utf-8")
    print("ok")
    PY

Сайты:

- Spot: https://testnet.binance.vision  → API Management → Generate HMAC-SHA-256
- Futures: https://testnet.binancefuture.com → API Key → Generate
- Faucet на futures: главная → Get USDT (2–3 раза)

## Инцидент: `.venv` под root → Permission denied для service

**Симптом**: `systemctl status trading-shadow-basis` → `Failed to query Python interpreter / canonicalize /opt/trading-desk/.venv/bin/python: Permission denied (os error 13)`.

**Причина**: `.venv` создавался под root. `uv` при этом скачал managed CPython в `/root/.local/share/uv/python/...`, а `.venv/bin/python` — симлинк туда. Пользователь `trader` не имеет доступа в `/root`.

**Решение**: пересоздать venv от trader:

    sudo rm -rf /opt/trading-desk/.venv /opt/trading-desk/uv.lock
    sudo chown -R trader:trader /opt/trading-desk
    sudo -u trader -H bash -lc 'cd /opt/trading-desk && uv sync'

`uv` развернёт Python в `/home/trader/.local/share/uv/python/...`, `.venv` станет доступен сервису.

**Профилактика**: `infra/systemd/install.sh` проверяет `readlink -f .venv/bin/python` и падает с предупреждением, если цель начинается с `/root/`.

**Правило дальнейшей работы в репо**: всё делать от `trader`:

    sudo -u trader -H bash -lc 'cd /opt/trading-desk && make <goal>'

Не запускать `uv sync` и `make` от root — каждый такой запуск пересоздаёт симлинки под root.

## Инциденты

| Симптом | Действие |
|---|---|
| KILL_SWITCH файл существует | cat KILL_SWITCH → устранить причину → make resume |
| daily_loss_breach в journal | разобрать day_pnl/day_funding/day_fees; проверить funding fetch |
| reconcile_mismatch | сверить state.positions[].base_amount с брокерским стейтментом |
| live_funding_open_failed | проверить, что spot-нога откатилась (rollback в place_delta_neutral) |
| RuntimeError: reentrant call в логе daemon | невозможно с текущим кодом (signal-safe handler) — если увидел, файл обновился не полностью |

## Что дальше

1. **Сбор 30-дневной статистики базиса** — `sudo systemctl start trading-shadow-basis` (или `make shadow-once` вручную). Даст реальный хвост распределения basis → data-driven threshold вместо 15 bps.
2. **Testnet-прогон** — заполнить .env, `LIVE_CONFIRM=YES-I-AM-LIVE make live-funding-testnet`, сравнить с mock. Ждёт твоих ключей.
3. **Paper 72 ч** — `make paper-funding DURATION_HOURS=72`, сравнить с backtest на тех же днях.
4. **Small live** — после (2) и (3): реальные 200–500 USD, MAX_DAILY_LOSS=50, MAX_POSITION_NOTIONAL=200, наблюдение 30 дней.
5. **Research расширение** — basis carry или cross-exchange funding arb (см. STRATEGY.md).

## Где что искать в коде

- Точка входа live: `execution/live_runner_funding.py::main`
- Ядро сигналов: `strategies/funding_carry.py::funding_carry_signals`
- Ядро бэктеста: `research/funding_core.py::simulate_funding`
- Риск: `risk/limits.py`, `risk/kill_switch.py`, `risk/daily_loss.py`
- Mock-биржа: `execution/exchanges.py`
- Алерты: `infra/alerts.py`

## Переменные окружения (критичные)

- APP_ENV=live, LIVE_CONFIRM=YES-I-AM-LIVE — оба обязательны для live-режима
- USE_TESTNET=true, USE_MOCK_EXCHANGE=false — testnet без mock
- DRY_RUN=false — реальные ордера
- MAX_DAILY_LOSS_USD, MAX_POSITION_NOTIONAL_USD, MAX_ORDER_NOTIONAL_USD — risk.limits
- RECONCILE_STRICT=true — hard-fail при рассинхроне state и брокера
- ALERT_WEBHOOK_URL — опционально, JSON POST на webhook
