# Trading Desk Runbook

## Pipeline Runbook

**Pipeline failed.** Check the `PIPELINE_FAIL` notification — it carries `stage` and `code`. In CI open the failing step; locally read `logs/qa_last.log` and `artifacts/data_audit.json`. If the failure is in `fetch`, verify exchange reachability and rate-limits, then rerun. If it is in `backtest`, reproduce locally with the same CLI, fix, and open a PR; CI must be green before merge. While unresolved, `make paper-stop` and leave FSM where it is — no transitions.

**QA fail 3 times in a row.** `src/qa/honesty_checks.py` writes a per-check streak counter into `data/qa_state.json`; a key present in that file means that check failed in the last run. Do not run `python -m src.pipeline.state_machine advance` — the gate will deny and log a denied transition. Open `docs/reports/qa_latest.md`, read the failing checks, fix the actual issue, rerun `python -m src.pipeline.orchestrator qa --allow-no-creds` until clean, then attempt `advance`.

**Kill-switch L2.** An L2 means new entries are blocked by `src/risk/limits.py` while existing positions are allowed to run. Do not manually re-arm; let the de-risked position breathe. Inspect `data/kill_events.jsonl` and the Grafana risk panel (when available): `drawdown_pct`, `funding_reversal_hours`. If drawdown approaches the L3 threshold in `src/risk/limits.py`, flatten manually and stop runners (`make paper-stop`). Re-arm only for L1/L2 after metric returns to green; L3/L4 require manual incident note in `data/kill_events.jsonl` and human sign-off.

**Missing data.** `make data-audit` returns exit 1 with non-zero `gaps`, `dupes`, `non_monotonic` or `ohlc_violations`. Do not run backtest or QA on top of corrupt bars — downstream is blocked. Refetch against the exchange; if the gap is real exchange downtime, backfill from a secondary vendor and mark the range as `backfilled=true` in `data/raw/*.meta.json` so QA degrades confidence. Only when `data_audit.json` reports zeros across all bars do downstream targets reopen.

**Funding reversal extended.** In `strategies/funding_carry`, the premise is positive funding on the short leg. If `funding_reversal_hours` stays above the threshold in `src/strategies/funding_carry/config.py` for more than two hours, the trade is negative carry plus market risk. Close both legs manually (`funding_carry_runner --flatten --reason funding_reversal`), write an incident to `data/kill_events.jsonl`, and add the affected symbols to `src/risk/limits.py::symbol_blocklist` for 24 hours. Do not wait for strategy logic — funding flips are risk events.

## Monitoring

Bring the stack up: `make monitoring-up` (prometheus :9090, grafana :3000).
Start the metrics endpoint: `make metrics-server` or
`systemctl --user start trading-metrics`. Tail container logs:
`make monitoring-logs`. Tear down: `make monitoring-down`.

Grafana: `http://localhost:3000` — dashboards under the `Trading` folder
(provisioned from `infra/grafana/provisioning/dashboards/trading.json`).
Prometheus: `http://localhost:9090` — targets page shows `trading-app`.

If the target is DOWN in Prometheus, confirm the exporter is bound on the
host (`curl -s localhost:9100/metrics | head`) and, on Linux, that the
`172.17.0.1:9100` target matches your docker bridge gateway
(`ip -4 addr show docker0`).
