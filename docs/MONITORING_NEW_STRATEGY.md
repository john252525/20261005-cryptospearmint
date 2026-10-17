# Как добавить новую стратегию в monitoring

## Предпосылки

У тебя есть работающая стратегия, которая:

- пишет state в SQLite (`state/<strategy>.db` — любые таблицы, где можно
  найти `nav`, `drawdown_pct`, `kill_level`, `symbol` + `notional_usd`);
- имеет runner — долгоживущий процесс
  (`python -m src.execution.<strategy>_runner`) или периодический tick,
  который знает числа портфеля в текущий момент.

Всё, что нужно monitoring'у — чтобы эти числа **попали в `publish()`**.
Exporter уже ходит в БД раз в 5 секунд и обновляет gauges; Prometheus
скрейпит exporter; Grafana рисует дашборд.

Ниже четыре шага, которые нужны на каждую новую стратегию. Первые три
обязательные, четвёртый — по желанию.

---

## Шаг 1. Вызвать `publish()` из runner'а (обязательный)

`src/monitoring/metrics.py::publish(state: dict)` — единственная точка
входа. Runner вызывает её **на каждом tick'е**: после исполнения ордеров,
после начисления funding'а, в конце цикла.

# === Блок 5 ===
cd /root/trading-desk && cat >> docs/MONITORING_NEW_STRATEGY.md <<'__DOC_P3__'

---

## Шаг 2. Проверить, что exporter читает правильную БД

**Сейчас `src/monitoring/http_exporter.py` жёстко читает
`state/funding_carry.db`** (константа `STATE_DB` в начале файла) плюс
`data/kill_events.jsonl`. Два пути для новой стратегии.

### Путь A (рекомендуемый) — общая БД

Складывай таблицы новой стратегии в `state/funding_carry.db` (или
переименуй в `state/trading.db` — это одна константа `STATE_DB` в
exporter'е). Exporter сам найдёт колонки `nav`, `drawdown_pct`,
`symbol` + `notional_usd`/`size_usd` и подхватит значения.

Ничего не надо менять в коде exporter'а.

### Путь B — параметризовать путь через env

Если хочется физически разделить БД по стратегиям:

# === Блок 6 ===
cd /root/trading-desk && cat >> docs/MONITORING_NEW_STRATEGY.md <<'__DOC_P4__'

---

## Шаг 3. Скопировать и переименовать dashboard

`infra/grafana/provisioning/dashboards/trading.json` — рабочий образец.
Для новой стратегии:

1. Скопируй файл:
   ```
   cp infra/grafana/provisioning/dashboards/trading.json \
      infra/grafana/provisioning/dashboards/<strategy>.json
   ```
2. Открой копию, в первых строках измени:
   - `"uid": "<strategy>-desk"` (напр. `"pead-desk"`),
   - `"title": "<STRATEGY> Desk"` (напр. `"PEAD Desk"`),
   - опционально `"tags": ["trading", "<strategy>"]`.
3. Прозвони titles панелей. Если у новой стратегии нет, например,
   «Funding accrued», переименуй панель под свой смысл или удали
   (`id=7` — каждая панель независима).
4. Примени на dev-сервере:
   ```
   cp infra/grafana/provisioning/dashboards/<strategy>.json \
      /opt/grafana/conf/provisioning/dashboards/
   systemctl restart grafana
   ```
5. Grafana подхватит файл автоматически (provisioning обновляется
   каждые 30с без рестарта, см. `updateIntervalSeconds: 30` в
   `dashboards.yml`).

**Не переименовывай `trading.json`.** Стратегии живут параллельно:
funding-carry на `trading-desk` uid, PEAD на `pead-desk` и т.д.

### Расширение панелей и метрик

Если стратегии нужна своя метрика (не пересекающаяся с funding-carry):

1. Добавь Gauge в `src/monitoring/metrics.py`:
   ```python
   pead_signal_strength = Gauge("pead_signal_strength", "PEAD signal z-score")
   ```
2. Добавь ключ в `_GAUGE_BY_KEY` там же:
   ```python
   _GAUGE_BY_KEY = {
       # ... существующие
       "pead_signal_strength": pead_signal_strength,
   }
   ```
3. Runner публикует `publish({"pead_signal_strength": ...})` — gauge
   обновится. Панель в дашборде читает `pead_signal_strength`.

`_GAUGE_BY_KEY` — единственная точка расширения скалярных метрик.
`position_size_usd` обрабатывается отдельно (label `symbol`).
__DOC_P4__
wc -l docs/MONITORING_NEW_STRATEGY.md

# === Блок 7 ===
cd /root/trading-desk && cat >> docs/MONITORING_NEW_STRATEGY.md <<'__DOC_P5__'

---

## Шаг 4 (опционально). systemd unit для runner'а стратегии

Если у стратегии долгоживущий процесс — отдельный unit полезен для
reboot survival. Шаблон — `infra/systemd/trading-metrics.service`.

# === Блок 8 ===
cd /root/trading-desk && cat >> docs/MONITORING_NEW_STRATEGY.md <<'__DOC_P6__'

---

## Известные ограничения

**Один exporter на все стратегии.** `trading-metrics.service` слушает
:9100 и читает одну БД (сейчас `state/funding_carry.db`). Если две
стратегии делят один exporter, их метрики должны попадать в одну БД
(путь A шага 2) — тогда `risk_nav` будет отражать последнего
записавшего, что бессмысленно для cross-strategy анализа.

Для двух стратегий с отдельными `risk_nav` нужны **два exporter'а на
разных портах**:

# === Блок 9 ===
cd /root/trading-desk && echo "=== SIZE ===" && wc -l docs/MONITORING_NEW_STRATEGY.md && echo "=== SECTIONS ===" && grep -n '^## \|^### ' docs/MONITORING_NEW_STRATEGY.md && echo "=== HEAD ===" && head -8 docs/MONITORING_NEW_STRATEGY.md && echo "=== TAIL ===" && tail -8 docs/MONITORING_NEW_STRATEGY.md

# === Блок 10 ===
cd /root/trading-desk && git status --short && echo "---" && git add docs/MONITORING_NEW_STRATEGY.md && git diff --cached --stat

# === Блок 11 ===
cd /root/trading-desk && git commit -m 'docs(monitoring): onboarding guide for adding a new strategy (publish + exporter + dashboard + systemd)' && git rev-parse HEAD

# === Блок 12 ===
cd /root/trading-desk && git push origin pipeline-monitoring 2>&1 | tail -6 && echo "---" && git log --oneline -3

# === Блок 13 ===
cd /root/trading-desk && echo "local   = $(git rev-parse HEAD)" && echo "origin  = $(git rev-parse origin/pipeline-monitoring)" && echo "ahead   = $(git rev-list --count origin/pipeline-monitoring..HEAD)" && echo "branch  = $(git branch --show-current)" && echo "clean   = $(git status --short | wc -l) uncommitted line(s)" && echo "doc-lines = $(wc -l < docs/MONITORING_NEW_STRATEGY.md)"

---

## Шаг 1. Вызвать `publish()` из runner'а (обязательный)

`src/monitoring/metrics.py::publish(state: dict)` — единственная точка
входа. Runner вызывает её **на каждом tick'е**: после исполнения ордеров,
после начисления funding'а, в конце цикла.

    from src.monitoring.metrics import publish

    publish({
        "nav":                 float(account.nav),
        "drawdown_pct":        float(risk.drawdown_pct),
        "kill_level":          int(risk.kill_level),
        "orders_per_min":      float(stats.orders_per_min),
        "daily_loss_pct":      float(stats.daily_loss_pct),
        "funding_accrued_usd": float(pnl.funding_accrued),
        "delta_exposure_bps":  float(risk.delta_bps),
        "position_size_usd":   {sym: float(pos) for sym, pos in portfolio.items()},
    })

### Обязательные поля `state_dict`

| поле | тип | смысл |
|---|---|---|
| `nav` | `float` | Net asset value в USDT |
| `drawdown_pct` | `float` | Текущая просадка от peak NAV, проценты |
| `kill_level` | `int` | 0..4; `src/risk/kill_switch.py::KillSwitch.check()` |
| `orders_per_min` | `float` | Скользящее среднее за окно |
| `daily_loss_pct` | `float` | Дневной PnL в % от NAV (положительное = убыток) |
| `funding_accrued_usd` | `float` | Накопленный income (или аналог) |
| `delta_exposure_bps` | `float` | Нетто-дельта в bps от NAV |
| `position_size_usd` | `dict[str, float]` | `{symbol: notional_usd}` — gauge на символ |

Пропущенные поля **не сбрасывают** gauge в ноль — `publish` трогает только
переданные ключи. Если `funding_accrued_usd` приходит реже `nav`, он не
обнулится между вызовами. Сделано намеренно.

### Что происходит при `publish()`

- Каждый `state[key]` → `.set(float(state[key]))` на соответствующем Gauge.
- `position_size_usd` → `risk_position_size_usd.labels(symbol=sym).set(...)`
  для каждого ключа; символы, отсутствующие в новом снапшоте, сбрасываются
  в 0 (см. `_reset_stale_symbols`).

### Если у стратегии нет всех полей

Передавай только те, что реально есть — остальные останутся на предыдущем
значении или на 0. Не передавай `float("nan")` — gauge примет, но панель
нарисует дырку. Лучше не передавать ключ вовсе.

---

## Шаг 2. Проверить, что exporter читает правильную БД

**Сейчас `src/monitoring/http_exporter.py` жёстко читает
`state/funding_carry.db`** (константа `STATE_DB` в начале файла) плюс
`data/kill_events.jsonl`. Два пути для новой стратегии.

### Путь A (рекомендуемый) — общая БД

Складывай таблицы новой стратегии в `state/funding_carry.db` (или
переименуй в `state/trading.db` — это одна константа `STATE_DB` в
exporter'е). Exporter сам найдёт колонки `nav`, `drawdown_pct`,
`symbol` + `notional_usd`/`size_usd` и подхватит значения.

Ничего не надо менять в коде exporter'а.

### Путь B — параметризовать путь через env

Если хочется физически разделить БД по стратегиям:

    # в начале http_exporter.py
    import os
    STATE_DB = Path(os.getenv("EXPORTER_DB_PATH",
                              ROOT / "state" / "funding_carry.db"))

В systemd-юните:

    Environment="EXPORTER_DB_PATH=/root/trading-desk/state/pead.db"

Затем `systemctl daemon-reload && systemctl restart trading-metrics`.

**Ограничение:** один exporter — одна БД. Две стратегии в двух БД —
два exporter'а на разных портах (см. «Известные ограничения»).

---

## Шаг 3. Скопировать и переименовать dashboard

`infra/grafana/provisioning/dashboards/trading.json` — рабочий образец.
Для новой стратегии:

1. Скопируй файл:

       cp infra/grafana/provisioning/dashboards/trading.json \
          infra/grafana/provisioning/dashboards/<strategy>.json

2. Открой копию, в первых строках измени:
   - `"uid": "<strategy>-desk"` (например `"pead-desk"`),
   - `"title": "<STRATEGY> Desk"` (например `"PEAD Desk"`),
   - опционально `"tags": ["trading", "<strategy>"]`.

3. Прозвони titles панелей. Если у новой стратегии нет, например,
   «Funding accrued», переименуй панель под свой смысл или удали
   (`id=7` — каждая панель независима).

4. Примени на dev-сервере:

       cp infra/grafana/provisioning/dashboards/<strategy>.json \
          /opt/grafana/conf/provisioning/dashboards/
       systemctl restart grafana

5. Grafana подхватит файл автоматически (provisioning обновляется
   каждые 30с без рестарта, см. `updateIntervalSeconds: 30` в
   `dashboards.yml`).

**Не переименовывай `trading.json`.** Стратегии живут параллельно:
funding-carry на `trading-desk` uid, PEAD на `pead-desk` и т.д.

### Расширение панелей и метрик

Если стратегии нужна своя метрика (не пересекающаяся с funding-carry):

1. Добавь Gauge в `src/monitoring/metrics.py`:

       pead_signal_strength = Gauge("pead_signal_strength", "PEAD signal z-score")

2. Добавь ключ в `_GAUGE_BY_KEY` там же:

       _GAUGE_BY_KEY = {
           # ... существующие
           "pead_signal_strength": pead_signal_strength,
       }

3. Runner публикует `publish({"pead_signal_strength": ...})` — gauge
   обновится. Панель в дашборде читает `pead_signal_strength`.

`_GAUGE_BY_KEY` — единственная точка расширения скалярных метрик.
`position_size_usd` обрабатывается отдельно (label `symbol`).

---

## Шаг 4 (опционально). systemd unit для runner'а стратегии

Если у стратегии долгоживущий процесс — отдельный unit полезен для
reboot survival. Шаблон — `infra/systemd/trading-metrics.service`.

    # /etc/systemd/system/pead-runner.service
    [Unit]
    Description=PEAD Runner
    After=network-online.target
    Wants=network-online.target

    [Service]
    Type=simple
    User=root
    WorkingDirectory=/root/trading-desk
    Environment="PYTHONPATH=/root/trading-desk"
    ExecStart=/usr/bin/python3 -m src.execution.pead_runner
    Restart=on-failure
    RestartSec=5
    StandardOutput=journal
    StandardError=journal
    SyslogIdentifier=pead-runner

    [Install]
    WantedBy=multi-user.target

Активация:

    systemctl daemon-reload
    systemctl enable pead-runner
    systemctl start pead-runner
    systemctl status pead-runner

Экспортер при этом остаётся **один** — `trading-metrics.service` уже
поднят на :9100 и продолжает читать БД раз в 5 секунд. Runner'у нужен
только `publish()` (шаг 1).

---

## Если что-то не так

### Дашборд пустой

    curl http://127.0.0.1:9100/metrics | grep '^risk_'

Должно быть 11 `risk_*` строк (или больше, если добавил свои gauges).
Если метрик нет — exporter упал: `systemctl status trading-metrics`.

### Метрики нулевые

Runner не вызывает `publish()`:

    grep -rn 'publish(' src/execution/<strategy>_runner.py

Если пусто — вставь вызов в конце tick'а. Если есть, но нули — проверь,
что путь до `state/<strategy>.db` совпадает с тем, что читает exporter
(шаг 2).

### Prometheus target down

    curl http://127.0.0.1:57447/api/v1/targets | python3 -m json.tool | grep -A2 health

- `health=up` — следующий шаг, открывай дашборд.
- `health=down` — exporter не отвечает: `curl http://127.0.0.1:9100/metrics`.
  Если 000 — `systemctl restart trading-metrics`.

### Grafana не видит dashboard

    curl -u admin:admin http://127.0.0.1:36308/api/search

Должен быть `uid=<strategy>-desk` в списке. Если нет — проверь
`/opt/grafana/conf/provisioning/dashboards/<strategy>.json` (или скопируй
заново из `infra/grafana/provisioning/dashboards/`), подожди 30с,
`systemctl restart grafana` если не помогло.

---

## Известные ограничения

**Один exporter на все стратегии.** `trading-metrics.service` слушает
:9100 и читает одну БД (сейчас `state/funding_carry.db`). Если две
стратегии делят один exporter, их метрики должны попадать в одну БД
(путь A шага 2) — тогда `risk_nav` будет отражать последнего
записавшего, что бессмысленно для cross-strategy анализа.

Для двух стратегий с отдельными `risk_nav` нужны **два exporter'а на
разных портах**:

    # порт 9100 → funding-carry (текущий)
    # порт 9101 → pead (новый)

Каждый — свой systemd unit с `--port 9101`, свой Prometheus target
(добавь в `/opt/prometheus/prometheus.yml` новый `static_configs`),
свой dashboard.

**Dashboard сейчас 8 panels** (NAV, Drawdown %, Kill level, Orders/min,
Latency p50/p95/p99, Positions by symbol, Funding USD, Delta bps). Для
новых стратегий — либо переиспользуй целиком (если семантика совпадает),
либо добавь/удали панели (каждая независима, `id` уникален).

---

## Чего НЕ моделируется

**Cross-strategy aggregation.** Сейчас нет единого `nav` по всем
стратегиям — каждая стратегия отдельным dashboard'ом. Если понадобится
«total book NAV» — отдельная задача:

- либо третья метрика `risk_total_nav` в отдельном exporter'е, который
  читает обе БД;
- либо PromQL в Grafana: `sum(risk_nav{strategy=~"funding_carry|pead"})` —
  требует добавить label `strategy` на все gauges (расширение `publish()`).

Обе опции возможны без ломки текущего, но это отдельный PR.

---

## PEAD-specific (когда будет готов)

- **state/pead.db** — таблицы `positions(symbol, notional_usd)`,
  `pnl_snapshots(ts, nav, drawdown_pct, daily_loss_pct)`,
  `kill_events(ts, level, reason)` — по образцу funding-carry.
- **runner**: `src/execution/pead_runner.py` — на каждом tick вызывает
  `publish({...})` в конце цикла (шаг 1 выше).
- **dashboard uid**: `pead-desk` — копия `trading.json` с переименованием
  uid/title; панель «Funding USD» переименовать в «Earnings surprise
  attribution» (или свой аналог PnL accrual).
- **метрики**: те же 11 `risk_*` (если один exporter — как минимум
  `risk_nav`, `risk_drawdown_pct`, `risk_position_size_usd{symbol=...}`).
  Расширить через `_GAUGE_BY_KEY` в `metrics.py` (шаг 3).
- **systemd**: `pead-runner.service` — по шаблону шага 4.
