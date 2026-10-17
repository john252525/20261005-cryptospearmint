"""Paper broker unit tests."""
from __future__ import annotations
import pytest

from brokers.paper import PaperBroker


@pytest.fixture
def broker(tmp_path):
    b = PaperBroker(
        db_path=tmp_path / "broker.db",
        config={"initial_cash": 100_000.0, "slippage_bps": 0.0,
                "spot_taker_fee": 0.0, "asset_class": "spot"},
        fill_latency_ms=50.0, auto_tick=False,
    )
    yield b
    b.close()


def test_submit_fills_after_latency(broker):
    broker.set_mark("AAPL", 100.0)
    broker.submit(client_order_id="o1", symbol="AAPL", side="BUY",
                  qty=10, price=100.0)
    assert broker.positions() == {}
    broker.advance(0.049)
    assert broker.positions() == {}
    broker.advance(0.002)
    assert broker.positions() == {"AAPL": 10.0}


def test_submit_idempotent(broker):
    broker.set_mark("AAPL", 100.0)
    bid1 = broker.submit(client_order_id="o1", symbol="AAPL", side="BUY",
                         qty=10, price=100.0)
    bid2 = broker.submit(client_order_id="o1", symbol="AAPL", side="BUY",
                         qty=999, price=999.0)
    assert bid1 == bid2
    broker.advance(1.0)
    assert broker.positions() == {"AAPL": 10.0}


def test_limit_not_filled_when_not_crossed(broker):
    broker.set_mark("AAPL", 100.0)
    broker.submit(client_order_id="l1", symbol="AAPL", side="SELL",
                  qty=1, price=110.0, order_type="LIMIT")
    broker.advance(1.0)
    assert broker.positions() == {}


def test_limit_fills_when_crossed(broker):
    broker.set_mark("AAPL", 100.0)
    broker.submit(client_order_id="l2", symbol="AAPL", side="SELL",
                  qty=1, price=110.0, order_type="LIMIT")
    broker.advance(1.0)
    assert broker.positions() == {}
    broker.set_mark("AAPL", 115.0)
    broker.advance(1.0)
    assert broker.positions() == {"AAPL": -1.0}


def test_limit_buy_fills_at_lower_mark(broker):
    broker.set_mark("AAPL", 100.0)
    broker.submit(client_order_id="lb", symbol="AAPL", side="BUY",
                  qty=2, price=95.0, order_type="LIMIT")
    broker.advance(1.0)
    assert broker.positions() == {}
    broker.set_mark("AAPL", 90.0)
    broker.advance(1.0)
    assert broker.positions() == {"AAPL": 2.0}


def test_fee_charged(tmp_path):
    b = PaperBroker(
        db_path=tmp_path / "b.db",
        config={"initial_cash": 10_000.0, "slippage_bps": 0.0,
                "spot_taker_fee": 0.001, "asset_class": "spot"},
        fill_latency_ms=0.0, auto_tick=False)
    b.set_mark("AAPL", 100.0)
    b.submit(client_order_id="f1", symbol="AAPL", side="BUY",
             qty=10, price=100.0)
    b.advance(0.0)
    assert b.cash() == pytest.approx(10_000.0 - 1_000.0 - 1.0)
    b.close()


def test_fees_accumulate(tmp_path):
    b = PaperBroker(
        db_path=tmp_path / "b.db",
        config={"initial_cash": 10_000.0, "slippage_bps": 0.0,
                "spot_taker_fee": 0.001, "asset_class": "spot"},
        fill_latency_ms=0.0, auto_tick=False)
    b.set_mark("AAPL", 100.0)
    b.submit(client_order_id="fa1", symbol="AAPL", side="BUY",
             qty=10, price=100.0)
    b.submit(client_order_id="fa2", symbol="AAPL", side="BUY",
             qty=10, price=100.0)
    b.advance(0.0)
    assert b.cash() == pytest.approx(10_000.0 - 2_000.0 - 2.0)
    b.close()


def test_slippage_market_buy(tmp_path):
    b = PaperBroker(
        db_path=tmp_path / "b.db",
        config={"initial_cash": 10_000.0, "slippage_bps": 10.0,
                "spot_taker_fee": 0.0, "asset_class": "spot"},
        fill_latency_ms=0.0, auto_tick=False)
    b.set_mark("AAPL", 100.0)
    b.submit(client_order_id="sl1", symbol="AAPL", side="BUY",
             qty=1, price=100.0)
    b.advance(0.0)
    assert (10_000.0 - b.cash()) == pytest.approx(100.1)
    b.close()


def test_cancel_before_fill(broker):
    bid = broker.submit(client_order_id="c1", symbol="AAPL", side="BUY",
                        qty=1, price=100.0)
    assert broker.cancel(bid) is True
    broker.advance(1.0)
    assert broker.positions() == {}


def test_cancel_after_fill_returns_false(broker):
    broker.set_mark("AAPL", 100.0)
    bid = broker.submit(client_order_id="c2", symbol="AAPL", side="BUY",
                        qty=1, price=100.0)
    broker.advance(1.0)
    assert broker.cancel(bid) is False


def test_cancel_unknown_returns_false(broker):
    assert broker.cancel("no_such_order") is False


def test_positions_reflect_book(broker):
    broker.set_mark("AAPL", 100.0)
    broker.set_mark("MSFT", 200.0)
    broker.submit(client_order_id="p1", symbol="AAPL", side="BUY",
                  qty=10, price=100.0)
    broker.submit(client_order_id="p2", symbol="MSFT", side="SELL",
                  qty=5, price=200.0)
    broker.advance(1.0)
    assert broker.positions() == {"AAPL": 10.0, "MSFT": -5.0}


def test_flatten_dry_run_sends_nothing(broker):
    broker.set_mark("AAPL", 100.0)
    broker.submit(client_order_id="g1", symbol="AAPL", side="BUY",
                  qty=10, price=100.0)
    broker.advance(1.0)
    cash_before = broker.cash()
    plan = broker.flatten_all(dry_run=True)
    assert plan and plan[0]["symbol"] == "AAPL" and plan[0]["side"] == "SELL"
    assert broker.cash() == pytest.approx(cash_before)
    assert broker.order_count() == 1


def test_flatten_real_closes_positions(broker):
    broker.set_mark("AAPL", 100.0)
    broker.submit(client_order_id="h1", symbol="AAPL", side="BUY",
                  qty=10, price=100.0)
    broker.advance(1.0)
    assert broker.positions() == {"AAPL": 10.0}
    broker.flatten_all(dry_run=False)
    broker.advance(1.0)
    assert broker.positions() == {}


def test_flatten_empty_book(broker):
    assert broker.flatten_all(dry_run=True) == []
    assert broker.flatten_all(dry_run=False) == []


def test_reconcile_ok_and_alert(broker):
    broker.set_mark("AAPL", 100.0)
    broker.submit(client_order_id="r1", symbol="AAPL", side="BUY",
                  qty=10, price=100.0)
    broker.advance(1.0)
    r_ok = broker.reconcile({"AAPL": 10.0}, tolerance_bps=1.0)
    assert r_ok["ok"] is True
    r_bad = broker.reconcile({"AAPL": 0.1}, tolerance_bps=1.0)
    assert r_bad["ok"] is False
    assert r_bad["detail"][0]["status"] == "alert"


def test_marks_dict(broker):
    broker.set_mark("AAPL", 100.0)
    broker.set_mark("MSFT", 250.0)
    assert broker.marks() == {"AAPL": 100.0, "MSFT": 250.0}


def test_order_count_tracks_submissions(broker):
    assert broker.order_count() == 0
    broker.set_mark("AAPL", 100.0)
    broker.submit(client_order_id="oc1", symbol="AAPL", side="BUY",
                  qty=1, price=100.0)
    assert broker.order_count() == 1
    broker.submit(client_order_id="oc1", symbol="AAPL", side="BUY",
                  qty=1, price=100.0)
    assert broker.order_count() == 1
    broker.submit(client_order_id="oc2", symbol="AAPL", side="BUY",
                  qty=1, price=100.0)
    assert broker.order_count() == 2


def test_market_no_mark_does_not_fill(broker):
    broker.submit(client_order_id="nm1", symbol="AAPL", side="BUY",
                  qty=1, price=0.0)
    broker.advance(1.0)
    assert broker.positions() == {}
