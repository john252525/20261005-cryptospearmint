"""Donchian breakout: вход при пробое N-барного максимума, выход при пробое M-барного минимума."""
from __future__ import annotations

import pandas as pd

DEFAULT_PARAMS = {"entry_lookback": 20, "exit_lookback": 10}

def donchian_breakout_signals(close: pd.Series, *, entry_lookback: int = 20,
                              exit_lookback: int = 10) -> tuple[pd.Series, pd.Series]:
    if entry_lookback <= 0 or exit_lookback <= 0:
        raise ValueError("lookbacks must be positive")
    upper = close.rolling(entry_lookback, min_periods=entry_lookback).max().shift(1)
    lower = close.rolling(exit_lookback, min_periods=exit_lookback).min().shift(1)
    entries = (close > upper).fillna(False).astype(bool)
    exits = (close < lower).fillna(False).astype(bool)
    return entries, exits

__all__ = ["DEFAULT_PARAMS", "donchian_breakout_signals"]
