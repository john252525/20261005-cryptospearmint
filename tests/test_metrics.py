"""6 assertions over the prometheus REGISTRY after publish()/count_order()."""

from __future__ import annotations

from prometheus_client import REGISTRY


def _s(name: str, labels: dict | None = None):
    return REGISTRY.get_sample_value(name, labels or {})


def test_publish_sets_nav():
    from src.monitoring.metrics import publish
    publish({"nav": 123456.0})
    assert _s("risk_nav") == 123456.0


def test_publish_sets_drawdown():
    from src.monitoring.metrics import publish
    publish({"drawdown_pct": 1.25})
    assert _s("risk_drawdown_pct") == 1.25


def test_publish_sets_kill_level():
    from src.monitoring.metrics import publish
    publish({"kill_level": 2})
    assert _s("risk_kill_level") == 2.0


def test_publish_position_sizes_per_symbol():
    from src.monitoring.metrics import publish
    publish({"position_size_usd": {"BTCUSDT": 1000.0, "ETHUSDT": 2000.0}})
    assert _s("risk_position_size_usd", {"symbol": "BTCUSDT"}) == 1000.0
    assert _s("risk_position_size_usd", {"symbol": "ETHUSDT"}) == 2000.0


def test_count_order_increments_counter():
    from src.monitoring.metrics import count_order
    before = _s("risk_orders_total",
                {"symbol": "SOLUSDT", "side": "buy", "status": "ok"}) or 0.0
    count_order("SOLUSDT", "buy", "ok")
    after = _s("risk_orders_total",
               {"symbol": "SOLUSDT", "side": "buy", "status": "ok"})
    assert after == before + 1


def test_observe_order_latency_increments_histogram():
    from src.monitoring.metrics import observe_order_latency
    before = _s("risk_order_latency_seconds_count") or 0.0
    observe_order_latency(0.42)
    after = _s("risk_order_latency_seconds_count")
    assert after == before + 1
