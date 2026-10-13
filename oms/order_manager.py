"""High-level order lifecycle manager.

All mutations go through events. `orders_state` is a materialized cache
that can be rebuilt from `order_events` via replay()/rebuild_all().
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Optional
from uuid import uuid4

from oms.events import (
    Event, OrderAcknowledged, OrderCanceled, OrderFilled,
    OrderPartiallyFilled, OrderRejected, OrderSubmitted,
    new_event_id, utcnow,
)
from oms.fsm import InvalidTransition, is_terminal, next_status
from oms.store import EventStore


@dataclass
class OrderState:
    client_order_id: str
    symbol: Optional[str] = None
    side: Optional[str] = None
    qty: Optional[float] = None
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    broker_order_id: Optional[str] = None
    status: str = "NEW"
    last_event_ts: Optional[str] = None
    reject_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class OrderManager:
    def __init__(self, store: EventStore) -> None:
        self.store = store

    # ---- public API --------------------------------------------------
    def submit(self, *, symbol: str, side: str, qty: float, price: float,
               client_order_id: Optional[str] = None,
               order_type: str = "MARKET",
               approved: bool = True,
               reject_reason: str = "") -> str:
        """Register an order.

        approved=False writes an immediate REJECTED (pre-trade reject).
        Re-submitting the same client_order_id is a no-op (returns the id).
        """
        coid = client_order_id or f"c_{uuid4().hex[:16]}"

        if self.store.load_events(coid):
            return coid

        self._apply(OrderSubmitted(
            event_id=new_event_id(), client_order_id=coid, ts=utcnow(),
            symbol=symbol, side=side, qty=float(qty), price=float(price),
            order_type=order_type))

        if not approved:
            self._apply(OrderRejected(
                event_id=new_event_id(), client_order_id=coid, ts=utcnow(),
                reason=reject_reason or "pre-trade reject"))
        return coid

    def ack(self, client_order_id: str, broker_order_id: str) -> None:
        self._apply(OrderAcknowledged(
            event_id=new_event_id(), client_order_id=client_order_id,
            ts=utcnow(), broker_order_id=broker_order_id))

    def fill(self, client_order_id: str, qty: float, price: float,
             broker_fill_id: str = "") -> None:
        st = self._state_or_raise(client_order_id)
        remaining = (st.qty or 0.0) - st.filled_qty
        if remaining <= 0:
            raise InvalidTransition(f"{client_order_id} already fully filled")

        fill_qty = min(float(qty), remaining)
        is_final = fill_qty >= remaining - 1e-9
        cls = OrderFilled if is_final else OrderPartiallyFilled
        self._apply(cls(
            event_id=new_event_id(), client_order_id=client_order_id,
            ts=utcnow(), fill_qty=fill_qty, fill_price=float(price),
            broker_fill_id=broker_fill_id or f"fill_{uuid4().hex[:8]}"))

    def reject(self, client_order_id: str, reason: str) -> None:
        self._apply(OrderRejected(
            event_id=new_event_id(), client_order_id=client_order_id,
            ts=utcnow(), reason=reason))

    def cancel(self, client_order_id: str, reason: str = "manual") -> None:
        self._apply(OrderCanceled(
            event_id=new_event_id(), client_order_id=client_order_id,
            ts=utcnow(), reason=reason))

    # ---- reads / replay ----------------------------------------------
    def get(self, client_order_id: str) -> Optional[OrderState]:
        d = self.store.load_state(client_order_id)
        if not d:
            return None
        return OrderState(**{k: v for k, v in d.items()
                             if k in OrderState.__dataclass_fields__})

    def replay(self, client_order_id: str) -> Optional[OrderState]:
        events = self.store.load_events(client_order_id)
        return self._fold(events) if events else None

    def rebuild_all(self) -> int:
        """Recompute orders_state from scratch. Returns number of orders."""
        coids = {e.client_order_id for e in self.store.all_events()}
        for coid in coids:
            st = self.replay(coid)
            if st:
                self.store.upsert_state(st.to_dict())
        return len(coids)

    # ---- internals ---------------------------------------------------
    def _state_or_raise(self, client_order_id: str) -> OrderState:
        st = self.get(client_order_id) or self.replay(client_order_id)
        if st is None:
            raise InvalidTransition(f"unknown order {client_order_id}")
        if is_terminal(st.status):
            raise InvalidTransition(
                f"{client_order_id} in terminal status {st.status}")
        return st

    def _apply(self, event: Event) -> None:
        coid = event.client_order_id
        if self.store.has_event(event.event_id):
            return

        current = self.replay(coid)

        if isinstance(event, OrderSubmitted):
            if current is not None:
                raise InvalidTransition(f"{coid} already submitted")
        else:
            if current is None:
                raise InvalidTransition(f"{coid} unknown — submit first")
            next_status(current.status, event.event_type)

        if not self.store.append(event):
            return

        updated = self._fold_one(current, event)
        self.store.upsert_state(updated.to_dict())

    @staticmethod
    def _fold(events: list[Event]) -> OrderState:
        st: Optional[OrderState] = None
        for e in events:
            st = OrderManager._fold_one(st, e)
        assert st is not None
        return st

    @staticmethod
    def _fold_one(st: Optional[OrderState], event: Event) -> OrderState:
        ts_iso = event.ts.isoformat()

        if isinstance(event, OrderSubmitted):
            return OrderState(
                client_order_id=event.client_order_id,
                symbol=event.symbol, side=event.side, qty=event.qty,
                status="NEW", last_event_ts=ts_iso)

        assert st is not None, "non-submit event without prior state"
        new_status = next_status(st.status, event.event_type)

        if isinstance(event, OrderAcknowledged):
            st.broker_order_id = event.broker_order_id
        elif isinstance(event, (OrderPartiallyFilled, OrderFilled)):
            new_qty = st.filled_qty + event.fill_qty
            prev_notional = st.avg_fill_price * st.filled_qty
            st.avg_fill_price = (
                (prev_notional + event.fill_price * event.fill_qty) / new_qty
                if new_qty else 0.0)
            st.filled_qty = new_qty
        elif isinstance(event, (OrderRejected, OrderCanceled)):
            st.reject_reason = event.reason

        st.status = new_status
        st.last_event_ts = ts_iso
        return st
