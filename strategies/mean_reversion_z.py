"""Mean reversion z-score: вход при z < -k (перепродано), выход при z > 0 (возврат к средней)."""
from __future__ import annotations

import pandas as pd

DEFAULT_PARAMS = {"lookback": 20, "k": 2.0}

def mean_reversion_z_signals(close: pd.Series, *, lookback: int = 20,
                             k: float = 2.0) -> tuple[pd.Series, pd.Series]:
    if lookback <= 1 or k <= 0:
        raise ValueError("bad lookback/k")
    ma = close.rolling(lookback, min_periods=lookback).mean()
    sd = close.rolling(lookback, min_periods=lookback).std()
    z = (close - ma) / sd.replace(0.0, float("nan"))
    entries = ((z < -k) & (z.shift(1, fill_value=0.0) >= -k)).fillna(False).astype(bool)
    exits = ((z > 0.0) & (z.shift(1, fill_value=0.0) <= 0.0)).fillna(False).astype(bool)
    return entries, exits

__all__ = ["DEFAULT_PARAMS", "mean_reversion_z_signals"]
