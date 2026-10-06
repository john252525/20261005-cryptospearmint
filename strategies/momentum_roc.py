"""Momentum ROC: лонг при росте N-барного ROC выше порога, выход на развороте."""
from __future__ import annotations

import pandas as pd

DEFAULT_PARAMS = {"lookback": 20, "threshold": 0.0}

def momentum_roc_signals(close: pd.Series, *, lookback: int = 20,
                         threshold: float = 0.0) -> tuple[pd.Series, pd.Series]:
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    roc = close.pct_change(lookback)
    above = (roc > threshold).fillna(False).astype(bool)
    prev = above.shift(1, fill_value=False).astype(bool)
    return above & ~prev, ~above & prev

__all__ = ["DEFAULT_PARAMS", "momentum_roc_signals"]
