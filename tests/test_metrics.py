"""Metrics tests via REGISTRY.get_sample_value."""
from __future__ import annotations
import pytest
from prometheus_client import REGISTRY

from src.monitoring import metrics
from src.monitoring.metrics import RiskState, publish, record_order


@pytest.fixture(autouse=True)
def _fresh_registry():
    metrics.reset()
    yield
    metrics.reset()


def _val(name, labels=None):
    return REGISTRY.get_sample_value(name, labels or {})


def test_gauges_are_published():
    publish(RiskState(nav=98_000.0, drawdown_pct=2.0, kill_level=1,
                      orders_per_min=7.0, daily_loss_pct=2.04))
    assert _val("risk_nav") == pytest.approx(98_000.0)
    assert _val("risk_drawdown_pct") == pytest.approx(2.0)
    assert _val("risk_kill_level") == pytest.approx(1.0)
    assert _val("risk_orders_per_min") == pytest.approx(7.0)
    assert _val("risk_daily_loss_pct") == pytest.approx(2.04)


def test_position_size_labels_and_stale_cleanup():
    publish(RiskState(positions={"AAPL": 16_000.0, "MSFT": -5_000.0}))
    assert _val("risk_position_size", {"symbol": "AAPL"}) == pytest.approx(16_000.0)
    assert _val("risk_position_size", {"symbol": "MSFT"}) == pytest.approx(-5_000.0)

    publish(RiskState(positions={"AAPL": 16_500.0}))
    assert _val("risk_position_size", {"symbol": "AAPL"}) == pytest.approx(16_500.0)
    assert _val("risk_position_size", {"symbol": "MSFT"}) is None


def test_orders_total_counter_labels():
    record_order("AAPL", "BUY", "approved")
    record_order("AAPL", "BUY", "approved")
    record_order("TSLA", "SELL", "rejected")

    assert _val("risk_orders_total",
                {"symbol": "AAPL", "side": "BUY", "status": "approved"}) == 2.0
    assert _val("risk_orders_total",
                {"symbol": "TSLA", "side": "SELL", "status": "rejected"}) == 1.0


def test_latency_histogram_buckets_cumulative():
    for v in (0.005, 0.05, 0.2, 3.0):
        record_order("AAPL", "BUY", "filled", latency_seconds=v)

    assert _val("risk_order_latency_seconds_bucket", {"le": "0.01"}) == 1.0
    assert _val("risk_order_latency_seconds_bucket", {"le": "0.05"}) == 2.0
    assert _val("risk_order_latency_seconds_bucket", {"le": "0.1"})  == 2.0
    assert _val("risk_order_latency_seconds_bucket", {"le": "0.25"}) == 3.0
    assert _val("risk_order_latency_seconds_bucket", {"le": "2.5"})  == 3.0
    assert _val("risk_order_latency_seconds_bucket", {"le": "+Inf"}) == 4.0
    assert _val("risk_order_latency_seconds_count") == 4.0


def test_reset_between_tests_isolates_state():
    publish(RiskState(nav=123_456.0))
    assert _val("risk_nav") == pytest.approx(123_456.0)
    metrics.reset()
    publish(RiskState(nav=1.0))
    assert _val("risk_nav") == pytest.approx(1.0)
