"""Core data structures for the risk engine."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

    @property
    def sign(self) -> int:
        return 1 if self is Side.BUY else -1


@dataclass(frozen=True)
class Order:
    order_id: str
    symbol: str
    side: Side
    qty: float
    price: float
    ts: datetime = field(default_factory=utcnow)
    order_type: str = "MARKET"

    @property
    def signed_qty(self) -> float:
        return self.qty * self.side.sign

    @property
    def notional(self) -> float:
        return abs(self.qty) * self.price


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    last_price: float = 0.0

    @property
    def mark(self) -> float:
        return self.last_price or self.avg_price

    @property
    def notional(self) -> float:
        return self.qty * self.mark

    @property
    def unrealized_pnl(self) -> float:
        if not self.last_price:
            return 0.0
        return (self.last_price - self.avg_price) * self.qty


@dataclass
class Portfolio:
    cash: float = 0.0
    positions: dict = field(default_factory=dict)
    realized_pnl: float = 0.0
    fees: float = 0.0
    nav_start_of_day: float = 0.0
    peak_nav: float = 0.0

    def __post_init__(self) -> None:
        if self.nav_start_of_day <= 0:
            self.nav_start_of_day = self.nav
        if self.peak_nav <= 0:
            self.peak_nav = self.nav

    @property
    def nav(self) -> float:
        return self.cash + sum(p.notional for p in self.positions.values())

    @property
    def gross_exposure(self) -> float:
        return sum(abs(p.notional) for p in self.positions.values())

    @property
    def net_exposure(self) -> float:
        return sum(p.notional for p in self.positions.values())

    @property
    def unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    @property
    def daily_pnl(self) -> float:
        return self.nav - self.nav_start_of_day

    @property
    def daily_loss(self) -> float:
        return max(0.0, self.nav_start_of_day - self.nav)

    @property
    def drawdown_pct(self) -> float:
        if self.peak_nav <= 0:
            return 0.0
        return max(0.0, (self.peak_nav - self.nav) / self.peak_nav * 100.0)

    def mark(self, prices: dict) -> None:
        for s, px in prices.items():
            if s in self.positions:
                self.positions[s].last_price = float(px)
        if self.nav > self.peak_nav:
            self.peak_nav = self.nav

    def apply_fill(self, order: Order, fill_price: Optional[float] = None,
                   fee: float = 0.0) -> float:
        px = float(fill_price if fill_price is not None else order.price)
        signed = order.signed_qty
        pos = self.positions.get(order.symbol) or Position(symbol=order.symbol)
        old_qty = pos.qty
        new_qty = old_qty + signed
        realized = 0.0
        if old_qty == 0 or (old_qty > 0) == (signed > 0):
            tc = pos.avg_price * abs(old_qty) + px * abs(signed)
            pos.avg_price = tc / abs(new_qty) if new_qty else 0.0
        else:
            closed = min(abs(signed), abs(old_qty))
            realized = (px - pos.avg_price) * closed if old_qty > 0 \
                       else (pos.avg_price - px) * closed
            self.realized_pnl += realized
            if new_qty != 0 and (new_qty > 0) != (old_qty > 0):
                pos.avg_price = px
        pos.qty = new_qty
        pos.last_price = px
        self.cash -= signed * px + fee
        self.fees += fee
        if pos.qty == 0.0:
            self.positions.pop(order.symbol, None)
        else:
            self.positions[order.symbol] = pos
        if self.nav > self.peak_nav:
            self.peak_nav = self.nav
        return realized


@dataclass(frozen=True)
class TriggerEvent:
    ts: datetime
    level: int
    reason: str
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ts"] = self.ts.isoformat()
        return d
