"""Immutable event log entries for the order lifecycle."""
from __future__ import annotations
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Union


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_event_id() -> str:
    return "evt_" + uuid.uuid4().hex[:16]


@dataclass(frozen=True)
class OrderSubmitted:
    event_id: str
    client_order_id: str
    ts: datetime
    symbol: str
    side: str
    qty: float
    price: float
    order_type: str = "MARKET"
    event_type: str = field(default="ORDER_SUBMITTED", init=False)


@dataclass(frozen=True)
class OrderAcknowledged:
    event_id: str
    client_order_id: str
    ts: datetime
    broker_order_id: str
    event_type: str = field(default="ORDER_ACKNOWLEDGED", init=False)


@dataclass(frozen=True)
class OrderPartiallyFilled:
    event_id: str
    client_order_id: str
    ts: datetime
    fill_qty: float
    fill_price: float
    broker_fill_id: str
    event_type: str = field(default="ORDER_PARTIALLY_FILLED", init=False)


@dataclass(frozen=True)
class OrderFilled:
    event_id: str
    client_order_id: str
    ts: datetime
    fill_qty: float
    fill_price: float
    broker_fill_id: str
    event_type: str = field(default="ORDER_FILLED", init=False)


@dataclass(frozen=True)
class OrderRejected:
    event_id: str
    client_order_id: str
    ts: datetime
    reason: str
    event_type: str = field(default="ORDER_REJECTED", init=False)


@dataclass(frozen=True)
class OrderCanceled:
    event_id: str
    client_order_id: str
    ts: datetime
    reason: str
    event_type: str = field(default="ORDER_CANCELED", init=False)


Event = Union[
    OrderSubmitted, OrderAcknowledged, OrderPartiallyFilled,
    OrderFilled, OrderRejected, OrderCanceled,
]

_BY_TYPE = {
    "ORDER_SUBMITTED":        OrderSubmitted,
    "ORDER_ACKNOWLEDGED":     OrderAcknowledged,
    "ORDER_PARTIALLY_FILLED": OrderPartiallyFilled,
    "ORDER_FILLED":           OrderFilled,
    "ORDER_REJECTED":         OrderRejected,
    "ORDER_CANCELED":         OrderCanceled,
}


def serialize(event: Event) -> str:
    d = asdict(event)
    d["ts"] = event.ts.isoformat()
    return json.dumps(d)


def deserialize(payload: str) -> Event:
    d = json.loads(payload)
    cls = _BY_TYPE[d["event_type"]]
    d["ts"] = datetime.fromisoformat(d["ts"])
    d.pop("event_type", None)
    return cls(**d)
