"""Entry/exit/rebalance gating — pure logic."""
from __future__ import annotations

from datetime import datetime, timedelta

from .config import FundingCarrySettings
from .signal import DIR_FLAT, Signal


class CooldownGate:
    def __init__(self, cooldown_sec: float) -> None:
        self.cooldown_sec = float(cooldown_sec)
        self._last: dict[str, datetime] = {}

    def allow(self, key: str, now: datetime) -> bool:
        last = self._last.get(key)
        if last is None:
            return True
        return (now - last) >= timedelta(seconds=self.cooldown_sec)

    def mark(self, key: str, now: datetime) -> None:
        self._last[key] = now

    def try_consume(self, key: str, now: datetime) -> bool:
        if not self.allow(key, now):
            return False
        self.mark(key, now); return True

    def seconds_left(self, key: str, now: datetime) -> float:
        last = self._last.get(key)
        if last is None:
            return 0.0
        return max(0.0, self.cooldown_sec - (now - last).total_seconds())


def passes_entry_filters(sig: Signal, s: FundingCarrySettings) -> bool:
    if sig.direction == DIR_FLAT:
        return False
    if abs(sig.funding_bps_8h) <= s.min_funding_bps:
        return False
    if abs(sig.basis_bps) >= s.max_basis_bps:
        return False
    return True


def should_exit(sig: Signal, current_direction: str, s: FundingCarrySettings) -> bool:
    if abs(sig.basis_bps) > s.max_basis_bps:
        return True
    if sig.direction == DIR_FLAT:
        return True
    return sig.direction != current_direction


def needs_rebalance(drift_bps: float, s: FundingCarrySettings) -> bool:
    return abs(drift_bps) > s.rebalance_threshold_bps
