"""Index hedge for PEAD: neutralise excess net-long beta with QQQ shorts."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HedgeDecision:
    hedge_required: bool
    hedge_notional: float  # negative = short
    reason: str


def compute_hedge(
    net_long_notional: float,
    nav: float,
    threshold_frac: float = 0.30,
) -> HedgeDecision:
    """If net long exposure exceeds threshold_frac of NAV, short the excess.

    Returns a decision whose hedge_notional is negative (a short) when a hedge
    is needed, or 0.0 when none is required.
    """
    if nav <= 0:
        return HedgeDecision(True, 0.0, "nav_nonpositive")
    if net_long_notional <= threshold_frac * nav:
        return HedgeDecision(False, 0.0, "within_threshold")
    excess = net_long_notional - threshold_frac * nav
    return HedgeDecision(True, -excess, "net_long_exceeds_threshold")
