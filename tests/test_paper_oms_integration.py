"""Paper broker <-> OMS <-> risk-engine integration."""
from __future__ import annotations
import pytest

from risk.kill_switch import KillSwitch
from risk.limits import Limits
from risk.structures import Portfolio
from oms.store import EventStore
from brokers.paper import PaperBroker
from brokers.paper_adapter import PaperOmsRunner


@pytest.fixture
def wire(tmp_path):
    store = EventStore(tmp_path / "risk.db")
    broker = PaperBroker(
        db_path=tmp_path / "risk.db",
        config={"initial_cash": 100_000.0, "slippage_bps": 0.0,
                "spot_taker_fee": 0.0, "asset_class": "spot"},
        fill_latency_ms=50.0, auto_tick=False,
    )
    broker.set_mark("AAPL", 100.0)
    portfolio = Portfolio(cash=100_000.0)
    limits = Limits(max_position_size=1_000_000.0,
                    max_gross_exposure=1_000_000.0,
                    max_net_exposure=1_000_000.0,
                    max_daily_loss=1_000_000.0,
                    max_drawdown_pct=100.0,
                    max_single_symbol_pct=100.0,
                    max_orders_per_minute=1000)
    ks = KillSwitch()
    r = PaperOmsRunner(store=store, broker=broker, portfolio=portfolio,
                       limits=limits, kill_switch=ks)
    yield r, broker, portfolio, ks, store
    store.close()
    broker.close()


def test_submit_fill_updates_portfolio(wire):
    r, broker, portfolio, _, _ = wire
    res = r.submit(symbol="AAPL", side="BUY", qty=10, price=100.0,
                   client_order_id="t1")
    assert res["approved"] is True
    r.advance(0.1)
    st = r.mgr.get("t1")
    assert st.status == "FILLED"
    assert st.filled_qty == 10
    assert portfolio.positions["AAPL"].qty == 10


def test_limits_reject_blocks_broker(tmp_path):
    store = EventStore(tmp_path / "r.db")
    broker = PaperBroker(
        db_path=tmp_path / "r.db",
        config={"initial_cash": 100_000.0},
        fill_latency_ms=50.0, auto_tick=False)
    broker.set_mark("AAPL", 100.0)
    portfolio = Portfolio(cash=100_000.0)
    limits = Limits(max_position_size=500.0, max_single_symbol_pct=100.0,
                    max_orders_per_minute=1000)
    ks = KillSwitch()
    r = PaperOmsRunner(store=store, broker=broker, portfolio=portfolio,
                       limits=limits, kill_switch=ks)

    res = r.submit(symbol="AAPL", side="BUY", qty=10, price=100.0,
                   client_order_id="rej")
    assert res["approved"] is False
    r.advance(0.2)
    assert broker.positions() == {}
    assert r.mgr.get("rej").status == "REJECTED"
    store.close()
    broker.close()


def test_kill_switch_l2_blocks_new_orders(wire):
    r, broker, _, ks, _ = wire
    ks.trigger(2, "test halt")
    res = r.submit(symbol="AAPL", side="BUY", qty=1, price=100.0,
                   client_order_id="ks1")
    assert res["approved"] is False
    assert "kill-switch" in res["reason"]
    r.advance(0.2)
    assert broker.positions() == {}


def test_replay_restores_state(wire):
    r, broker, _, _, store = wire
    r.submit(symbol="AAPL", side="BUY", qty=5, price=100.0,
             client_order_id="rp1")
    r.advance(0.1)
    assert r.mgr.get("rp1").status == "FILLED"

    store._conn.execute("DELETE FROM orders_state")
    store._conn.commit()
    assert store.load_state("rp1") is None

    n = r.replay()
    assert n >= 1
    st = r.mgr.get("rp1")
    assert st.status == "FILLED"
    assert st.filled_qty == 5


def test_reconcile_after_restart(tmp_path):
    db = tmp_path / "risk.db"
    cfg = {"initial_cash": 100_000.0, "slippage_bps": 0.0,
           "spot_taker_fee": 0.0, "asset_class": "spot"}

    store1 = EventStore(db)
    b1 = PaperBroker(db_path=db, config=cfg, fill_latency_ms=50.0,
                     auto_tick=False)
    b1.set_mark("AAPL", 100.0)
    p1 = Portfolio(cash=100_000.0)
    r1 = PaperOmsRunner(store=store1, broker=b1, portfolio=p1,
                        limits=None, kill_switch=None)
    r1.submit(symbol="AAPL", side="BUY", qty=7, price=100.0,
              client_order_id="rr1")
    r1.advance(0.1)
    assert b1.positions() == {"AAPL": 7.0}
    store1.close()
    b1.close()

    b2 = PaperBroker(db_path=db, config=cfg, fill_latency_ms=50.0,
                     auto_tick=False)
    assert b2.positions() == {"AAPL": 7.0}
    rep = b2.reconcile({"AAPL": 7.0}, tolerance_bps=5.0)
    assert rep["ok"] is True
    b2.close()
