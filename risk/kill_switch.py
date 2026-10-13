"""Kill-switch with L0..L4 escalation and flatten-all placeholder."""
from __future__ import annotations
from typing import Callable, Iterable, Optional

from risk.structures import Portfolio, Position, TriggerEvent, utcnow

LEVEL_NAMES = {
    0: "L0_NORMAL",
    1: "L1_WARN",
    2: "L2_HALT_NEW_ORDERS",
    3: "L3_FLATTEN_ALL",
    4: "L4_HARD_STOP",
}

DEFAULT_THRESHOLDS = {
    "daily_loss_l1": 5_000.0,
    "drawdown_l2": 4.0,
    "drawdown_l3": 6.0,
    "drawdown_l4": 8.0,
}


class KillSwitch:
    def __init__(self, thresholds: Optional[dict] = None,
                 alert_fn: Optional[Callable[[TriggerEvent], None]] = None) -> None:
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.level: int = 0
        self.events: list = []
        self.alert_fn = alert_fn
        self.flattened: bool = False

    def trigger(self, level: int, reason: str,
                metrics: Optional[dict] = None) -> Optional[TriggerEvent]:
        if level <= self.level:
            return None
        ev = TriggerEvent(utcnow(), int(level), str(reason), dict(metrics or {}))
        self.events.append(ev)
        self.level = int(level)
        if self.alert_fn:
            try:
                self.alert_fn(ev)
            except Exception:
                pass
        return ev

    def auto_check(self, portfolio: Portfolio) -> list:
        th = self.thresholds
        dd = portfolio.drawdown_pct
        dl = portfolio.daily_loss
        fired = []

        if dd >= th["drawdown_l4"]:
            fired.append(self.trigger(4, f"drawdown {dd:.2f}% >= L4",
                                      {"drawdown_pct": dd, "nav": portfolio.nav}))
        elif dd >= th["drawdown_l3"]:
            fired.append(self.trigger(3, f"drawdown {dd:.2f}% >= L3",
                                      {"drawdown_pct": dd, "nav": portfolio.nav}))
        elif dd >= th["drawdown_l2"]:
            fired.append(self.trigger(2, f"drawdown {dd:.2f}% >= L2",
                                      {"drawdown_pct": dd, "nav": portfolio.nav}))

        if dl >= th["daily_loss_l1"]:
            fired.append(self.trigger(1, f"daily loss {dl:.2f} >= L1",
                                      {"daily_loss": dl, "nav": portfolio.nav}))

        return [e for e in fired if e is not None]

    def status(self) -> dict:
        return {
            "level": self.level,
            "name": LEVEL_NAMES.get(self.level, f"L{self.level}"),
            "flattened": self.flattened,
            "thresholds": dict(self.thresholds),
            "events": [e.to_dict() for e in self.events],
        }

    def requires_flatten(self) -> bool:
        return self.level >= 3

    def blocks_new_orders(self) -> bool:
        return self.level >= 2

    def reset(self, reason: str = "manual") -> None:
        if self.level > 0:
            self.events.append(TriggerEvent(
                utcnow(), 0, f"RESET from L{self.level}: {reason}"))
        self.level = 0
        self.flattened = False


def flatten_all(positions: Iterable[Position], *, dry_run: bool = True) -> list:
    """Build a market-order plan that closes every open position.

    TODO(broker): plug IBKR / Alpaca / Binance submission.
    TODO(oms):    cancel working orders before submitting flatten orders.
    TODO(safety): throttle by symbol, respect exchange halts, retry on reject.
    """
    plan = []
    for p in positions:
        if not p.qty:
            continue
        plan.append({
            "symbol": p.symbol,
            "side": "SELL" if p.qty > 0 else "BUY",
            "qty": abs(p.qty),
            "type": "MARKET",
            "current_px": p.mark,
        })
    if dry_run:
        return plan
    raise NotImplementedError("broker integration TODO — see flatten_all docstring")
