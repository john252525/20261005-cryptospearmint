# Как добавить новую стратегию в monitoring

## Предпосылки

У тебя есть работающая стратегия, которая:

- пишет state в SQLite (`state/<strategy>.db` — любые таблицы, где есть
  `nav`, `drawdown_pct`, `kill_level`, `symbol` + `notional_usd`);
- имеет runner — долгоживущий процесс
  (`python -m src.execution.<strategy>_runner`) или периодический tick.

Мониторинг сводится к одному: числа портфеля должны попасть в
`publish()`. Exporter раз в 5 секунд читает БД, обновляет gauges;
Prometheus скрейпит exporter; Grafana рисует дашборд.

Дальше — четыре шага на каждую новую стратегию. Первые три обязательны,
четвёртый опционален.

---

## Шаг 1. Вызвать `publish()` из runner'а (обязательный)

Интерфейс: `src/monitoring/metrics.py::publish(state: dict)`. Вызывать на
каждом tick'е — после исполнения ордеров, после начисления funding'а, в
конце цикла:

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
| `drawdown_pct` | `float` | Просадка от peak NAV, проценты |
| `kill_level` | `int` | 0..4; `src/risk/kill_switch.py::KillSwitch.check()` |
| `orders_per_min` | `float` | Скользящее среднее, orders/min |
| `daily_loss_pct` | `float` | Дневной PnL в % от NAV (плюс = убыток) |
| `funding_accrued_usd` | `float` | Накопленный income (или аналог) |
| `delta_exposure_bps` | `float` | Нетто-дельта, bps от NAV |
| `position_size_usd` | `dict[str, float]` | `{symbol: notional_usd}` |

Семантика `publish()`:

- каждый `state[key]` → `.set(float(state[key]))` на соответствующем Gauge;
- `position_size_usd` → `risk_position_size_usd.labels(symbol=sym).set(...)`;
- **пропущенные ключи не сбрасывают** gauge — значение остаётся от прошлого
  вызова. Если `funding_accrued_usd` приходит реже `nav`, он не обнулится.
  Это сделано намеренно;
- символы, отсутствующие в новом `position_size_usd`, сбрасываются в 0
  (см. `_reset_stale_symbols`).

Если у стратегии нет всех полей — передавай только существующие.
Не передавай `float("nan")`: gauge примет, но панель нарисует дырку.

---

## Шаг 2. Проверить, что exporter читает правильную БД

Сейчас `src/monitoring/http_exporter.py` жёстко читает
`state/funding_carry.db` (константа `STATE_DB` в начале файла) и
`data/kill_events.jsonl`. Для новой стратегии — два пути.

### Путь A (рекомендуемый) — общая БД

Складывай таблицы новой стратегии в `state/funding_carry.db` (или
переименуй в `state/trading.db`: одна константа `STATE_DB` в exporter'е).
Exporter сам найдёт колонки `nav`, `drawdown_pct`,
`symbol` + `notional_usd`/`size_usd`, подхватит значения.

Ничего в коде exporter'а менять не нужно.

### Путь B — параметризовать путь через env

Если нужно физически разделить БД по стратегиям:

    # в начале http_exporter.py
    import os
    STATE_DB = Path(os.getenv("EXPORTER_DB_PATH",
                              ROOT / "state" / "funding_carry.db"))

В systemd-юните:

    Environment="EXPORTER_DB_PATH=/root/trading-desk/state/pead.db"

Затем:

    systemctl daemon-reload
    systemctl restart trading-metrics

**Ограничение:** один exporter — одна БД. Две стратегии в двух БД
требуют двух exporter'ов на разных портах (см. «Известные ограничения»).

---

## Шаг 3. Скопировать и переименовать dashboard

`infra/grafana/provisioning/dashboards/trading.json` — рабочий образец.

1. Скопируй:

       cp infra/grafana/provisioning/dashboards/trading.json \
          infra/grafana/provisioning/dashboards/<strategy>.json

2. В первых строках копии измени:
   - `"uid": "<strategy>-desk"` (например `"pead-desk"`);
   - `"title": "<STRATEGY> Desk"` (например `"PEAD Desk"`);
   - опционально `"tags": ["trading", "<strategy>"]`.

3. Прозвони titles панелей: если у стратегии нет «Funding accrued»,
   переименуй панель под свой смысл или удали (`id=7`; каждая панель
   независима).

4. Примени на dev-сервере:

       cp infra/grafana/provisioning/dashboards/<strategy>.json \
          /opt/grafana/conf/provisioning/dashboards/
       systemctl restart grafana

5. Grafana подхватит файл автоматически: provisioning обновляется каждые
   30с без рестарта (`updateIntervalSeconds: 30` в `dashboards.yml`).

**Не переименовывай `trading.json`.** Стратегии живут параллельно:
funding-carry на `trading-desk` uid, PEAD на `pead-desk` и т.д.

### Расширение метрик

Если стратегии нужна своя метрика (не пересекающаяся с funding-carry):

1. Добавь Gauge в `src/monitoring/metrics.py`:

       pead_signal_strength = Gauge("pead_signal_strength", "PEAD signal z-score")

2. Добавь ключ в `_GAUGE_BY_KEY` там же:

       _GAUGE_BY_KEY = {
           # ... существующие
           "pead_signal_strength": pead_signal_strength,
       }

3. Runner публикует `publish({"pead_signal_strength": ...})` — gauge
   обновится, панель прочитает `pead_signal_strength`.

`_GAUGE_BY_KEY` — единственная точка расширения скалярных метрик.

---

## Шаг 4 (опционально). systemd unit для runner'а стратегии

Шаблон — `infra/systemd/trading-metrics.service`.

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

Экспортер остаётся **один**: `trading-metrics.service` уже поднят на :9100
и продолжает читать БД раз в 5 секунд. Runner'у нужен только `publish()`.

---

## Если что-то не так

### Дашборд пустой

    curl http://127.0.0.1:9100/metrics | grep '^risk_'

Должно быть 11 `risk_*` строк (или больше, если добавлены свои gauges).
Если метрик нет — exporter упал: `systemctl status trading-metrics`.

### Метрики нулевые

    grep -rn 'publish(' src/execution/<strategy>_runner.py

Пусто — вставь вызов в конце tick'а. Есть, но нули — сверь путь до
`state/<strategy>.db` с тем, что читает exporter (шаг 2).

### Prometheus target down

    curl http://127.0.0.1:57447/api/v1/targets | python3 -m json.tool | grep -A2 health

- `health=up` — открывай дашборд.
- `health=down` — exporter не отвечает: `curl http://127.0.0.1:9100/metrics`.
  Если 000 — `systemctl restart trading-metrics`.

### Grafana не видит dashboard

    curl -u admin:admin http://127.0.0.1:36308/api/search

`uid=<strategy>-desk` должен быть в списке. Если нет — проверь
`/opt/grafana/conf/provisioning/dashboards/<strategy>.json`, подожди 30с,
`systemctl restart grafana` если не помогло.

---

## Известные ограничения

**Один exporter на все стратегии.** `trading-metrics.service` слушает
:9100 и читает одну БД (сейчас `state/funding_carry.db`). Если две
стратегии делят exporter, их метрики должны попадать в одну БД (путь A
шага 2) — тогда `risk_nav` отражает последнего записавшего, что
бессмысленно для cross-strategy.

Для двух стратегий с отдельными `risk_nav` нужны **два exporter'а на
разных портах**:

    # порт 9100 → funding-carry (текущий)
    # порт 9101 → pead (новый)

Каждый — свой systemd unit с `--port 9101`, свой Prometheus target
(новый `static_configs` в `/opt/prometheus/prometheus.yml`), свой
dashboard.

**Dashboard сейчас 8 panels**: NAV, Drawdown %, Kill level, Orders/min,
Latency p50/p95/p99, Positions by symbol, Funding USD, Delta bps. Для
новых стратегий — либо переиспользуй целиком, либо добавь/удали панели.

---

## Чего НЕ моделируется

**Cross-strategy aggregation.** Нет единого `nav` по всем стратегиям —
каждая стратегия отдельным dashboard'ом. «Total book NAV» — отдельная
задача:

- третья метрика `risk_total_nav` в отдельном exporter'е, который
  читает обе БД;
- либо PromQL: `sum(risk_nav{strategy=~"funding_carry|pead"})` — требует
  label `strategy` на всех gauges (расширение `publish()`).

Обе опции совместимы с текущим, но это отдельный PR.

---

## PEAD-specific (когда будет готов)

- **state/pead.db** — таблицы `positions(symbol, notional_usd)`,
  `pnl_snapshots(ts, nav, drawdown_pct, daily_loss_pct)`,
  `kill_events(ts, level, reason)` — по образцу funding-carry.
- **runner**: `src/execution/pead_runner.py` — на каждом tick вызывает
  `publish({...})` в конце цикла (шаг 1).
- **dashboard uid**: `pead-desk` — копия `trading.json` с переименованием
  uid/title; «Funding USD» → «Earnings surprise attribution» (или свой
  аналог PnL accrual).
- **метрики**: те же 11 `risk_*` (если один exporter — минимум `risk_nav`,
  `risk_drawdown_pct`, `risk_position_size_usd{symbol=...}`); расширение
  через `_GAUGE_BY_KEY`.
- **systemd**: `pead-runner.service` — по шаблону шага 4.
