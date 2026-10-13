"""Paper broker: in-process simulator, immediate fills, no keys.

TODO(real): adapter parity with IBKR / Alpaca / Binance:
  - idempotent client_order_id on submit
  - partial-fill streaming via on_fill callback
  - cancel semantics, open-order reconciliation, throttling
"""
from __future__ import annotations
import threading
import time
from dataclasses import dataclass, field


@dataclass
class _Book:
    cash: float = 100_000.0
    positions: dict = field(default_factory=dict)


class PaperBroker:
    def __init__(self, initial_cash: float = 100_000.0,
                 latency_ms: float = 50.0) -> None:
        self._book = _Book(cash=float(initial_cash))
        self._latency = max(0.0, latency_ms / 1000.0)
        self._lock = threading.Lock()
        self._fills: list = []
        self._orders: dict = {}

    def submit(self, *, client_order_id: str, symbol: str, side: str,
               qty: float, price: float,
               order_type: str = "MARKET") -> str:
        time.sleep(self._latency)
        broker_id = f"paper_{client_order_id}"
        with self._lock:
            self._orders[broker_id] = dict(
                symbol=symbol, side=side, qty=float(qty),
                price=float(price), status="FILLED")
            signed = float(qty) if side == "BUY" else -float(qty)
            self._book.positions[symbol] = (
                self._book.positions.get(symbol, 0.0) + signed)
            self._book.cash -= signed * float(price)

        ev = dict(broker_order_id=broker_id, client_order_id=client_order_id,
                  symbol=symbol, side=side, qty=float(qty), price=float(price))
        for cb in list(self._fills):
            try:
                cb(ev)
            except Exception:
                pass
        return broker_id

    def cancel(self, broker_order_id: str) -> bool:
        with self._lock:
            o = self._orders.get(broker_order_id)
            if not o:
                return False
            if o["status"] != "FILLED":
                o["status"] = "CANCELED"
                return True
        return False

    def positions(self) -> dict:
        return dict(self._book.positions)

    def cash(self) -> float:
        return float(self._book.cash)

    def on_fill(self, cb) -> None:
        self._fills.append(cb)
