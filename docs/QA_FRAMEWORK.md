
# QA Framework — backtest honesty checks

## Назначение

Общий слой QA для **любого** бэктеста в репо (funding-carry, PEAD, будущие
стратегии). Отвечает на один вопрос: **можно ли этому бэктесту доверять, если
он вдруг станет торговой стратегией?** Отдельно от `honesty_checks.py`
(paper-trading journal), здесь предмет — **артефакты бэктеста**: `*.metrics.json`,
`*.trades.parquet`, `*_grid_*.csv`.

Запускается:

- в CI (`backtest-qa` job в `.github/workflows/ci.yml`) — на фикстурах,
  reference PASS обязателен;
- локально перед любым merge'ем ветки, которая меняет стратегию;
- ретроактивно при добавлении новой стратегии в репо.

Framework **не** запускает бэктест заново, **не** трогает код стратегии. Он
читает артефакт + метаданные и выносит verdict: **PASS**, **WARN**, **FAIL**.

## 9 checks

| name | severity | проверяет | триггер FAIL | `value` при FAIL |
|---|---|---|---|---|
| `look_ahead` | **critical** | `fill_ts - signal_ts >= 1ms`; `fill_bar > signal_bar`. Если полей `signal_ts`/`fill_ts`/`signal_bar`/`fill_bar` нет и `trades_count > 0` при известном `asset_class` — **fail-closed** | `violations > 0` ИЛИ `missing_signal_ts` | `violations=N` / `missing_signal_ts` |
| `survivorship` | warning | для equities при `years > 2.95`: `delisted_count > 0` И universe не плоский `u0 != u1` | `delisted_count == 0` или `u0 == u1` | `0` или `u0->u1` |
| `adjusted_prices` | warning **/ critical для equity** | наличие `metrics.adjusted == true` ИЛИ `adjclose` в trades | нет ни того ни другого при `asset_class=equity` | `None` |
| `overfitting_signals` | warning | grid > 100 ячеек И top1 − top2 в σ rest-распределения < 3σ | `gap > 3σ` | `gap` (шестимерный) |
| `fee_consistency` | **critical** | `total_fees` vs `sum(qty × price) × fee_bps / 1e4`. `fee_bps` берётся ТОЛЬКО из `params.fee_bps` или `params.fee_schedule` | `deviation > 5%` | `dev_pct` |
| `fill_realism` | warning | `win_rate > 0.70` при `edge_type` не из exempt-списка | high win rate без edge | `win_rate` |
| `sharpe_sanity` | warning | `sharpe > 4.0` при `years >= 3.0` | слишком хорошо для реального капитала | `sharpe` |
| `turnover_consistency` | warning | `trades_count × avg_trade_notional × fee_bps / 1e4` ≈ `total_fees` | `deviation > 20%` | `dev_pct` |
| `dd_vs_vol` | warning | `max_dd / annual_vol >= 0.30` | `ratio < 0.3` | `ratio` |

Exempt edge types (для `fill_realism`): `funding_carry`, `funding-carry`,
`delta_neutral`, `market_neutral`, `arbitrage`, `carry`, `basis`,
`cash_and_carry`. Для них high win rate — ожидаемое свойство.

## 3 слоя дисциплины

### 1. Severity model — critical / warning

Каждый check несёт `severity`. **`critical` роняет вердикт в FAIL независимо
от `--fail-on`.** `warning` — суммируется и срабатывает как FAIL только когда
их ≥ `--fail-on` (по умолчанию 2).

SEVERITY в `src/qa/backtest_checks.py`:

    look_ahead           critical
    fee_consistency      critical
    adjusted_prices      warning  (динамически critical при asset_class=equity)
    все остальные 7      warning

Динамика `adjusted_prices` включается в `run_backtest_checks()`: если
`_is_equity(metrics, trades)` ИЛИ `params.asset_class == 'equity'`, severity
поднимается до `critical`.

### 2. Fail-closed для look_ahead

Раньше: `trades.parquet` без `signal_ts`/`fill_ts` → check возвращал
`passed=True, value=0` (вакуумный PASS). Это делало look-ahead
**непроверяемым по дизайну**.

Сейчас:

- `trades_count == 0` → PASS (`n/a: no trades`), законно;
- `trades_count > 0` И `asset_class ∈ {equity, crypto, perp, futures, …}`
  И нет ни одного из `signal_ts`/`fill_ts`/`signal_bar`/`fill_bar` →
  **FAIL** `value=missing_signal_ts`;
- `asset_class` неизвестен → PASS с `value=unknown_class_skip` — framework
  не знает, применим ли leak-контроль.

**Producer обязан писать `signal_ts` и `fill_ts` в `trades.parquet`** для
equity/crypto.

### 3. Tri-state passed — True / False / None

Проверка может вернуть три статуса:

- `passed=True` — проверено, всё чисто;
- `passed=False` — проверено, red flag;
- `passed=None` — проверить нельзя (нет независимого источника данных).

`None` никогда не превращается в `True`. Сканер печатает его как `WARN`, а
при подсчёте вердикта трактует наравне с `False`.

Единственный явный случай — `fee_consistency`, если `params.fee_bps` нет и
`params.fee_schedule` не передан: framework честно признаёт тавтологию.


## Как читать scan output

Пример:

    ❌ funding_carry_grid_20261017   4/6 passed  → FAIL
        FAIL positive_net_pnl         [warning ] value=-8.3969 thr=>0 :: best_active=-8.40 best_all=0.00 worst=-1965.15 zeros=6/18
        ok   top_gap_sigma            [warning ] value=0.0
        FAIL funding_vs_fees_ratio    [warning ] value=0.0813  thr=1.0 :: best funding/fees=0.0813 across 18 rows

Расшифровка:

- **`4/6 passed`** — сколько из 6 проверок данного формата (grid) прошло.
  `metrics.json`-формат всегда 9, `*_grid_*.csv` — 6.
- **`❌ / ⚠️ / ✅`** — `❌` = есть `critical`, `⚠️` = только warnings (сумма
  дошла до `--fail-on`), `✅` = PASS.
- **`[CRITICAL: ['look_ahead', 'adjusted_prices']]`** — какие критичные
  проверки провалились. Ревьюер обязан разбирать их первыми.
- **`[warn: [...]]`** — `passed=None` (WARN) + `passed=False` (не critical),
  если их меньше `--fail-on` и нет critical.
- **`thr=`** — порог. **`::`** — расшифровка.

Exit code: `0` — все PASS (или `warn_total < --fail-on` без critical);
`1` — FAIL хотя бы одного бэктеста; `2` — конфиг (нет dir, нет файлов).

## Как производителю писать metrics.json

Минимум для честной проверки `metrics.json`:

    {
      "sharpe": 0.68,
      "max_dd": 0.016,
      "annual_vol": 0.013,
      "win_rate": 0.567,
      "trades_count": 67,
      "avg_trade_notional": 36644.38,
      "total_fees": 2968.13,
      "fee_bps": 12.09,
      "years": 3.0,
      "total_return": 0.0256,
      "asset_class": "equity",
      "adjusted": true,
      "delisted_count": 42,
      "universe_count_start": 500,
      "universe_count_end": 480,
      "params": {
        "fee_bps": 12.09,
        "fee_schedule": "binance_spot",
        "edge_type": "pead",
        "universe_size": 20,
        "seed": 42
      }
    }

Обязательные поля (иначе проверки либо vacuous PASS, либо WARN):

| Поле | Зачем | Проверка без него |
|---|---|---|
| `sharpe`, `years` | sanity по abnormally high Sharpe | `sharpe_sanity` |
| `max_dd`, `annual_vol` | форма кривой | `dd_vs_vol` |
| `win_rate` + `params.edge_type` | реалистичность win rate | `fill_realism` |
| `trades_count`, `avg_trade_notional`, `total_fees` | turnover ↔ fee | `turnover_consistency` |
| `total_fees` + **`params.fee_bps`** | независимая сверка fee | `fee_consistency` → без этого WARN, не PASS |
| **`asset_class`** | включить equity-specific | `adjusted_prices` (critical), `survivorship`, `look_ahead` (fail-closed) |
| **`adjusted` (bool) или `adjclose` в trades** | total return adjusted | `adjusted_prices` |
| **`delisted_count`, `universe_count_start/end`** | survivorship bias | `survivorship` |
| **`params.fee_schedule`** (альтернатива `params.fee_bps`) | из `binance_spot=10 bps` / `bybit_linear=5.5` / … | `fee_consistency` |

`trades.parquet` (schema для `look_ahead`):

- `signal_ts` (ISO-8601 или epoch seconds/ms);
- `fill_ts` (обязан быть `>= signal_ts + 1 ms`);
- `signal_bar` (int, >= 0);
- `fill_bar` (int, **> `signal_bar`**);
- `qty`, `price` (нужны для не-тавтологичной `fee_consistency` и
  `turnover_consistency`).

Для `*_grid_*.csv` (grid-scan) обязательны колонки: `min_funding`, `tier`,
`net_pnl_usd`, `trades_count`, `sharpe`, `max_dd`, `hit_rate`, `fees_usd`,
`funding_pnl_usd`. Сканер использует `best_active` (лучший non-zero net_pnl).

Конвертер `scripts/backtest_to_metrics.py` приводит оба формата в единую
схему: `--input <*.csv|*.trades.parquet> --out <*.metrics.json>`. По
умолчанию не перезаписывает существующий файл, `--force` для replace.

## Известные ограничения

1. **`fee_consistency` тавтологична без `params.fee_bps`.** Если fee_bps
   вычислен обратно из тех же `trades`, проверка всегда даёт 0% отклонения.
   Framework теперь возвращает WARN (`passed=None`) вместо PASS, но лечить
   это может только producer, передав `params.fee_bps` или
   `params.fee_schedule` из fee-таблицы биржи.

2. **Grid-scan `positive_net_pnl` использует `best_active`.** Если все
   непустые ячейки grid убыточны, `value` будет отрицательным. `zeros=N/M`
   в сообщении показывает, сколько ячеек не торговали.

3. **Converter `backtest_to_metrics.py` выбирает лучшую строку grid, не
   сумму.** `trades_count` в converted metrics = `trades_count` лучшей по
   `net_pnl_usd` ячейки. Проверено `test_convert_grid_csv`.

4. **`survivorship` и `adjusted_prices` — только для equities.** Для
   crypto/perp — `n/a`. Если producer забыл `asset_class`, framework не
   может включить equity-специфику (частично закрыто через `look_ahead`
   fail-closed).

5. **Grid-проверки не используют `look_ahead`.** У `*_grid_*.csv` нет
   trade-уровня. `look_ahead` работает только на `metrics.json` +
   `trades.parquet`.

## Как добавить новый check

1. **Функция.** В `src/qa/backtest_checks.py` добавь
   `def check_<name>(metrics, trades, params) -> dict`, верни через
   `_r(passed, value, threshold, msg)`. Поля из metrics читай через `_pick`,
   trades через `_rows` уже нормализованы. Исключения не пробрасывай —
   `run_backtest_checks` ловит их и превращает в `passed=False, crash=…`.
2. **Severity.** Добавь имя в `SEVERITY` (warning или critical). Динамическое
   повышение (как у `adjusted_prices`) — правь `run_backtest_checks`.
3. **Регистрация.** Добавь имя в `CHECKS = {…}` в конце файла — иначе
   функция не будет вызвана.
4. **Тест.** В `tests/test_backtest_checks.py` минимум 2 теста: PASS-кейс и
   FAIL-кейс. Новый порог — в `TH`.
5. **Документация.** Обнови эту страницу: строка в таблице 9 checks + при
   необходимости — producer schema.
6. **Сканер.** Если проверка применима к grid-формату — продублируй логику
   в `_check_grid_csv` (`scripts/qa_backtest_scan.py`).
7. **CI.** `make qa-backtest-scan` локально; убедись что
   `tests/fixtures/backtest_results/pass.metrics.json` проходит, а
   синтетический fake — падает.

## История версий

- **2026-10-17** (commit `04f06ec`) — fail-closed `look_ahead`,
  `adjusted_prices` equity-critical, `survivorship` boundary (2.95y),
  non-tautological `fee_consistency`, tri-state `passed`, registry tri-state
  verdict.
- **2026-10-17** (commit `04419b3`) — severity model, `best_active` fix,
  planner.
- **2026-10-16** (commit `607ff4e`) — initial: 9 checks + overfitting +
  registry + scanner + CI job.

