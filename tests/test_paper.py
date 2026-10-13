"""Paper broker tests: fills update book; wiring to OMS via on_fill."""
from brokers.paper import PaperBroker
from oms.order_manager import OrderManager
from oms.store import EventStore


def test_fill_updates_book():
    b = PaperBroker(initial_cash=10_000, latency_ms=0)
    b.submit(client_order_id="x1", symbol="AAPL", side="BUY", qty=10, price=100)
    assert b.positions()["AAPL"] == 10
    assert b.cash() == 9_000


def test_sell_updates_book():
    b = PaperBroker(initial_cash=10_000, latency_ms=0)
    b.submit(client_order_id="s1", symbol="AAPL", side="SELL", qty=4, price=100)
    assert b.positions()["AAPL"] == -4
    assert b.cash() == 10_400


def test_fill_callback_wired_to_oms(tmp_path):
    store = EventStore(tmp_path / "oms.db")
    mgr = OrderManager(store)
    b = PaperBroker(initial_cash=10_000, latency_ms=0)

    def on_fill(f):
        mgr.ack(f["client_order_id"], f["broker_order_id"])
        mgr.fill(f["client_order_id"], f["qty"], f["price"], "paper_fill")

    b.on_fill(on_fill)

    c = mgr.submit(symbol="AAPL", side="BUY", qty=5, price=100,
                   client_order_id="paper_1")
    b.submit(client_order_id=c, symbol="AAPL", side="BUY", qty=5, price=100)

    st = mgr.get(c)
    assert st.status == "FILLED"
    assert st.filled_qty == 5
    assert st.broker_order_id == "paper_paper_1"
    store.close()


def test_paper_cancel_after_fill_returns_false():
    b = PaperBroker(initial_cash=10_000, latency_ms=0)
    bid = b.submit(client_order_id="x2", symbol="AAPL", side="BUY", qty=1, price=100)
    assert b.cancel(bid) is False


def test_paper_cancel_unknown_returns_false():
    b = PaperBroker(initial_cash=10_000, latency_ms=0)
    assert b.cancel("no_such_order") is False
