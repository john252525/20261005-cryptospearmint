"""OMS tests: FSM, lifecycle, idempotency, replay, rebuild."""
import pytest

from oms.events import OrderAcknowledged, new_event_id, utcnow
from oms.fsm import InvalidTransition, is_terminal, next_status
from oms.order_manager import OrderManager
from oms.store import EventStore


@pytest.fixture
def store(tmp_path):
    s = EventStore(tmp_path / "oms.db")
    yield s
    s.close()


@pytest.fixture
def mgr(store):
    return OrderManager(store)


# ---- FSM --------------------------------------------------------------
def test_fsm_allows_expected():
    assert next_status("NEW", "ORDER_ACKNOWLEDGED") == "ACK"
    assert next_status("ACK", "ORDER_FILLED") == "FILLED"
    assert next_status("PARTIAL", "ORDER_PARTIALLY_FILLED") == "PARTIAL"


def test_fsm_rejects_illegal():
    with pytest.raises(InvalidTransition):
        next_status("FILLED", "ORDER_ACKNOWLEDGED")
    with pytest.raises(InvalidTransition):
        next_status("REJECTED", "ORDER_FILLED")


def test_fsm_terminal_flags():
    assert is_terminal("FILLED")
    assert is_terminal("REJECTED")
    assert is_terminal("CANCELED")
    assert not is_terminal("NEW")
    assert not is_terminal("PARTIAL")


# ---- lifecycle --------------------------------------------------------
def test_lifecycle_new_ack_filled(mgr):
    c = mgr.submit(symbol="AAPL", side="BUY", qty=100, price=180.0)
    assert mgr.get(c).status == "NEW"

    mgr.ack(c, "broker_42")
    st = mgr.get(c)
    assert st.status == "ACK"
    assert st.broker_order_id == "broker_42"

    mgr.fill(c, 100, 180.5, "f1")
    st = mgr.get(c)
    assert st.status == "FILLED"
    assert st.filled_qty == 100
    assert st.avg_fill_price == pytest.approx(180.5)


def test_partial_fills_weighted_avg(mgr):
    c = mgr.submit(symbol="TSLA", side="SELL", qty=10, price=200.0)
    mgr.ack(c, "b1")
    mgr.fill(c, 3, 200.0, "f1")
    mgr.fill(c, 4, 202.0, "f2")

    st = mgr.get(c)
    assert st.status == "PARTIAL"
    assert st.filled_qty == 7
    assert st.avg_fill_price == pytest.approx((200 * 3 + 202 * 4) / 7)

    mgr.fill(c, 3, 198.0, "f3")
    st = mgr.get(c)
    assert st.status == "FILLED"
    assert st.filled_qty == 10


def test_overfill_is_capped(mgr):
    c = mgr.submit(symbol="X", side="BUY", qty=10, price=100)
    mgr.ack(c, "b1")
    mgr.fill(c, 999, 100, "f1")
    st = mgr.get(c)
    assert st.status == "FILLED"
    assert st.filled_qty == 10


# ---- rejections -------------------------------------------------------
def test_pretrade_reject_terminal(mgr):
    c = mgr.submit(symbol="AAPL", side="BUY", qty=100_000, price=180.0,
                   approved=False, reject_reason="position size")
    st = mgr.get(c)
    assert st.status == "REJECTED"
    assert "position size" in (st.reject_reason or "")
    with pytest.raises(InvalidTransition):
        mgr.cancel(c)


def test_fill_after_reject_raises(mgr):
    c = mgr.submit(symbol="X", side="BUY", qty=10, price=100)
    mgr.reject(c, "no liquidity")
    with pytest.raises(InvalidTransition):
        mgr.fill(c, 10, 100)


# ---- idempotency ------------------------------------------------------
def test_submit_is_idempotent(mgr):
    c = mgr.submit(symbol="AAPL", side="BUY", qty=10, price=100,
                   client_order_id="fixed_id")
    n = len(list(mgr.store.all_events()))

    again = mgr.submit(symbol="DIFFERENT", side="SELL", qty=999, price=1,
                       client_order_id="fixed_id")
    assert again == c
    assert len(list(mgr.store.all_events())) == n


def test_store_dedupes_event_id(store):
    mgr = OrderManager(store)
    c = mgr.submit(symbol="A", side="BUY", qty=10, price=100)
    ev = OrderAcknowledged(event_id=new_event_id(),
                           client_order_id=c, ts=utcnow(),
                           broker_order_id="b1")
    assert store.append(ev) is True
    assert store.append(ev) is False


# ---- replay / rebuild -------------------------------------------------
def test_replay_matches_materialized(mgr):
    c = mgr.submit(symbol="MSFT", side="BUY", qty=20, price=300)
    mgr.ack(c, "b7")
    mgr.fill(c, 5, 301, "f1")
    mgr.fill(c, 15, 299, "f2")

    a = mgr.get(c)
    b = mgr.replay(c)
    assert a.status == b.status
    assert a.filled_qty == b.filled_qty
    assert a.avg_fill_price == pytest.approx(b.avg_fill_price)


def test_rebuild_all_from_event_log(mgr, store):
    ids = []
    for i in range(3):
        c = mgr.submit(symbol=f"S{i}", side="BUY", qty=10, price=100 + i)
        mgr.ack(c, f"b{i}")
        mgr.fill(c, 10, 101 + i)
        ids.append(c)

    store._conn.execute("DELETE FROM orders_state")
    store._conn.commit()
    assert store.load_state(ids[0]) is None

    assert mgr.rebuild_all() == 3
    for c in ids:
        assert store.load_state(c)["status"] == "FILLED"
