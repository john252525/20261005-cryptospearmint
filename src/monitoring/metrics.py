"""Prometheus metrics for the risk module.

Gauges: risk_nav, risk_drawdown_pct, risk_kill_level, risk_orders_per_min,
        risk_daily_loss_pct, risk_position_size{symbol}
Counter: risk_orders_total{symbol, side, status}
Histogram: risk_order_latency_seconds (buckets 0.01..5.0)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from prometheus_client import REGISTRY, Counter, Gauge, Histogram

LATENCY_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

_DEFS = {
    "risk_nav":                   (Gauge,     "Net asset value", {}),
    "risk_drawdown_pct":          (Gauge,     "Drawdown from peak, percent", {}),
    "risk_kill_level":            (Gauge,     "Kill switch level 0..4", {}),
    "risk_orders_per_min":        (Gauge,     "Orders in last 60s", {}),
    "risk_daily_loss_pct":        (Gauge,     "Daily loss / NAV start, percent", {}),
    "risk_orders_total":          (Counter,   "Order requests",
                                   {"labelnames": ("symbol", "side", "status")}),
    "risk_order_latency_seconds": (Histogram, "Order round-trip latency, seconds",
                                   {"buckets": LATENCY_BUCKETS}),
    "risk_position_size":         (Gauge,     "Position notional (signed)",
                                   {"labelnames": ("symbol",)}),
}

_metrics: dict = {}
_known_symbols: set = set()


@dataclass
class RiskState:
    nav: float = 0.0
    drawdown_pct: float = 0.0
    kill_level: int = 0
    orders_per_min: float = 0.0
    daily_loss_pct: float = 0.0
    positions: dict = field(default_factory=dict)


def _build() -> None:
    _metrics.clear()
    for name, (cls, doc, kw) in _DEFS.items():
        _metrics[name] = cls(name, doc, **kw)


def reset() -> None:
    """Test hook: unregister and rebuild all collectors."""
    global _known_symbols
    for name in _DEFS:
        coll = REGISTRY._names_to_collectors.get(name)
        if coll is not None:
            try:
                REGISTRY.unregister(coll)
            except (KeyError, ValueError):
                pass
    _known_symbols = set()
    _build()


_build()


def _m(name: str):
    return _metrics[name]


def publish(state: RiskState) -> None:
    """Push scalar gauges; sync position labels; prune stale symbols."""
    _m("risk_nav").set(float(state.nav))
    _m("risk_drawdown_pct").set(float(state.drawdown_pct))
    _m("risk_kill_level").set(int(state.kill_level))
    _m("risk_orders_per_min").set(float(state.orders_per_min))
    _m("risk_daily_loss_pct").set(float(state.daily_loss_pct))

    current = set(state.positions)
    for sym, val in state.positions.items():
        _m("risk_position_size").labels(sym).set(float(val))
    for sym in _known_symbols - current:
        try:
            _m("risk_position_size").remove(sym)
        except (KeyError, ValueError):
            pass
    _known_symbols.clear()
    _known_symbols.update(current)


def record_order(symbol: str, side: str, status: str,
                 latency_seconds: Optional[float] = None) -> None:
    _m("risk_orders_total").labels(symbol, side, status).inc()
    if latency_seconds is not None:
        _m("risk_order_latency_seconds").observe(float(latency_seconds))
