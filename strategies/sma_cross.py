"""SMA crossover: чистые сигналы, без портфельной логики."""
from __future__ import annotations

import pandas as pd

DEFAULT_PARAMS: dict[str, int] = {"fast": 20, "slow": 50}

def sma_cross_signals(
    close: pd.Series, *, fast: int = DEFAULT_PARAMS["fast"], slow: int = DEFAULT_PARAMS["slow"]
) -> tuple[pd.Series, pd.Series]:
    if fast <= 0 or slow <= 0:
        raise ValueError("fast/slow must be positive")
    if fast >= slow:
        raise ValueError(f"fast ({fast}) must be < slow ({slow})")
    fast_ma = close.rolling(fast, min_periods=fast).mean()
    slow_ma = close.rolling(slow, min_periods=slow).mean()
    above = (fast_ma > slow_ma).fillna(False).astype(bool)
    prev = above.shift(1, fill_value=False).astype(bool)
    return above & ~prev, ~above & prev

__all__ = ["DEFAULT_PARAMS", "sma_cross_signals"]
