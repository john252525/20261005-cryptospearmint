# risk-engine

Prop-trading risk module: pre-trade limits, kill-switch L0-L4,
event-sourced order management, in-process paper broker.

## Layout

- risk/          pre-trade limits, portfolio, kill-switch, structures
- oms/           event-sourced order management (events, fsm, store, manager)
- brokers/       broker adapters (base protocol, paper simulator)
- tests/         pytest suite for risk + oms + paper
- config.py      YAML loader (pydantic optional)
- config.yaml    default limits / kill-switch thresholds / broker

## Design notes

- Event-sourcing. order_events is append-only; orders_state is a cache.
  rebuild_all() recreates the cache from the log.
- Idempotency. client_order_id on submit; event_id UNIQUE in store.
  Re-submitting the same id is a no-op.
- Pre-trade integration. OrderManager.submit(approved=False, reject_reason=...)
  writes a submit + immediate reject pair, same event log.
- Paper broker. Fills returned synchronously via on_fill callback.

## Quickstart

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest -q
python -m oms

## Status

WIP. Real broker adapter, monitoring exporter, and scheduled snapshots
land on branches off risk-engine.

## Monitoring

Prometheus on :9090, Grafana on :3000, exporter on :9100.

Run the exporter:

    python -m src.monitoring.http_exporter --db risk.db --port 9100

Docker stack:

    docker compose up -d

Grafana dashboard: http://localhost:3000/d/trading-risk-v0
