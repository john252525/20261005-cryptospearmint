"""Prometheus metrics for the trading desk."""

from __future__ import annotations

from typing import Any

from prometheus_client import Counter, Gauge, Histogram

risk_nav = Gauge("risk_nav", "Net asset value, USDT")
risk_drawdown_pct = Gauge("risk_drawdown_pct", "Current drawdown, percent")
risk_kill_level = Gauge("risk_kill_level", "Kill-switch level, 0..4")
risk_orders_per_min = Gauge("risk_orders_per_min", "Observed orders per minute")
risk_position_size_usd = Gauge(
    "risk_position_size_usd", "Open position notional, USDT", ["symbol"],
)
risk_daily_loss_pct = Gauge("risk_daily_loss_pct", "Daily PnL, percent of NAV")
risk_funding_accrued_usd = Gauge(
    "risk_funding_accrued_usd", "Accrued funding income, USDT",
)
risk_delta_exposure_bps = Gauge(
    "risk_delta_exposure_bps", "Net delta exposure, bps of NAV",
)

risk_orders_total = Counter(
    "risk_orders_total", "Order submissions", ["symbol", "side", "status"],
)
risk_order_latency_seconds = Histogram(
    "risk_order_latency_seconds", "Order round-trip latency",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

_GAUGE_BY_KEY = {
    "nav":                 risk_nav,
    "drawdown_pct":        risk_drawdown_pct,
    "kill_level":          risk_kill_level,
    "orders_per_min":      risk_orders_per_min,
    "daily_loss_pct":      risk_daily_loss_pct,
    "funding_accrued_usd": risk_funding_accrued_usd,
    "delta_exposure_bps":  risk_delta_exposure_bps,
}


def publish(state: dict[str, Any]) -> None:
    """Set gauges from a state dict. Unknown keys are ignored."""
    for key, gauge in _GAUGE_BY_KEY.items():
        if key in state and state[key] is not None:
            try:
                gauge.set(float(state[key]))
            except (TypeError, ValueError):
                continue
    pos = state.get("position_size_usd")
    if isinstance(pos, dict):
        seen = set()
        for sym, v in pos.items():
            sym = str(sym)
            seen.add(sym)
            try:
                risk_position_size_usd.labels(symbol=sym).set(float(v))
            except (TypeError, ValueError):
                continue
        _reset_stale_symbols(seen)


def count_order(symbol: str, side: str, status: str) -> None:
    risk_orders_total.labels(
        symbol=str(symbol), side=str(side), status=str(status),
    ).inc()


def observe_order_latency(seconds: float) -> None:
    try:
        risk_order_latency_seconds.observe(float(seconds))
    except (TypeError, ValueError):
        pass


def _reset_stale_symbols(seen: set[str]) -> None:
    """Best-effort reset of labels absent from the current snapshot."""
    try:
        existing = list(risk_position_size_usd._metrics)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return
    for metric in existing:
        if metric not in seen:
            try:
                risk_position_size_usd.labels(symbol=metric).set(0.0)
            except Exception:  # noqa: BLE001
                pass
