"""Жёсткие лимиты. Все ордера проходят check_order."""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

Side = Literal["buy", "sell"]


class LimitBreach(RuntimeError):
    """Нарушен жёсткий лимит — ордер отклоняется."""


class RiskLimits(BaseModel):
    max_order_notional: float = Field(default=1_000.0, gt=0)
    max_position_notional: float = Field(default=10_000.0, gt=0)
    max_open_positions: int = Field(default=5, ge=1)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> RiskLimits:
        src = os.environ if env is None else env

        def _f(k: str, d: float) -> float:
            v = src.get(k)
            return d if v in (None, "") else float(v)

        def _i(k: str, d: int) -> int:
            v = src.get(k)
            return d if v in (None, "") else int(v)

        return cls(
            max_order_notional=_f("MAX_ORDER_NOTIONAL_USD", 1_000.0),
            max_position_notional=_f("MAX_POSITION_NOTIONAL_USD", 10_000.0),
            max_open_positions=_i("MAX_OPEN_POSITIONS", 5),
        )


@dataclass(frozen=True)
class Order:
    symbol: str
    side: Side
    qty: float
    price: float

    @property
    def notional(self) -> float:
        return abs(self.qty) * float(self.price)


@dataclass(frozen=True)
class AccountState:
    equity: float
    open_positions: int = 0
    position_notional: float = 0.0


def check_order(order: Order, state: AccountState, limits: RiskLimits) -> None:
    if order.qty <= 0:
        raise LimitBreach(f"non-positive qty: {order.qty}")
    if order.price <= 0:
        raise LimitBreach(f"non-positive price: {order.price}")

    if order.notional > limits.max_order_notional:
        raise LimitBreach(
            f"order notional {order.notional:.2f} > max_order_notional "
            f"{limits.max_order_notional:.2f} [{order.symbol}]")

    opening = order.side == "buy" and state.position_notional <= 0
    if opening and state.open_positions >= limits.max_open_positions:
        raise LimitBreach(
            f"open positions {state.open_positions} >= max_open_positions "
            f"{limits.max_open_positions} [{order.symbol}]")

    projected = (state.position_notional + order.notional
                 if order.side == "buy" else state.position_notional)
    if projected > limits.max_position_notional:
        raise LimitBreach(
            f"projected position notional {projected:.2f} > "
            f"max_position_notional {limits.max_position_notional:.2f} [{order.symbol}]")


__all__ = ["AccountState", "LimitBreach", "Order", "RiskLimits", "Side", "check_order"]
