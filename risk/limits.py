"""Pre-trade limits engine."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta, timezone
from typing import Optional

from risk.structures import Order, Portfolio


@dataclass
class CheckResult:
    approved: bool
    reason: str = "OK"

    def __bool__(self) -> bool:
        return self.approved


@dataclass
class Limits:
    max_position_size: float = 100_000.0
    max_gross_exposure: float = 500_000.0
    max_net_exposure: float = 400_000.0
    max_daily_loss: float = 5_000.0
    max_drawdown_pct: float = 4.0
    max_single_symbol_pct: float = 20.0
    max_orders_per_minute: int = 30
    _order_ts: deque = field(default_factory=deque, repr=False, compare=False)

    @classmethod
    def from_dict(cls, d: dict) -> "Limits":
        known = {f.name for f in fields(cls) if not f.name.startswith("_")}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})

    def _rate_limit_ok(self, now: datetime) -> bool:
        cutoff = now - timedelta(seconds=60)
        while self._order_ts and self._order_ts[0] < cutoff:
            self._order_ts.popleft()
        return len(self._order_ts) < self.max_orders_per_minute

    def check_order(self, order: Order, portfolio: Portfolio,
                    now: Optional[datetime] = None) -> CheckResult:
        now = now or datetime.now(timezone.utc)

        if not self._rate_limit_ok(now):
            return CheckResult(False,
                f"rate limit >{self.max_orders_per_minute}/min")

        cur = portfolio.positions.get(order.symbol)
        cur_qty = cur.qty if cur else 0.0
        old_px = cur.mark if cur else order.price
        new_qty = cur_qty + order.signed_qty
        px = order.price or old_px

        if abs(new_qty) * px > self.max_position_size:
            return CheckResult(False,
                f"position size {abs(new_qty) * px:.0f} > "
                f"{self.max_position_size:.0f}")

        nav = max(portfolio.nav, 1e-9)
        pct = abs(new_qty) * px / nav * 100.0
        if pct > self.max_single_symbol_pct:
            return CheckResult(False,
                f"symbol {order.symbol} {pct:.1f}% > "
                f"{self.max_single_symbol_pct}%")

        delta_gross = abs(new_qty) * px - abs(cur_qty * old_px)
        new_gross = portfolio.gross_exposure + delta_gross
        if new_gross > self.max_gross_exposure:
            return CheckResult(False,
                f"gross exposure {new_gross:.0f} > "
                f"{self.max_gross_exposure:.0f}")

        new_net = portfolio.net_exposure - (cur_qty * old_px) + new_qty * px
        if abs(new_net) > self.max_net_exposure:
            return CheckResult(False,
                f"net exposure {new_net:.0f} > {self.max_net_exposure:.0f}")

        if portfolio.daily_loss > abs(self.max_daily_loss):
            return CheckResult(False,
                f"daily loss {portfolio.daily_loss:.0f} > "
                f"{self.max_daily_loss:.0f}")

        if portfolio.drawdown_pct > self.max_drawdown_pct:
            return CheckResult(False,
                f"drawdown {portfolio.drawdown_pct:.2f}% > "
                f"{self.max_drawdown_pct}%")

        self._order_ts.append(now)
        return CheckResult(True, "OK")
