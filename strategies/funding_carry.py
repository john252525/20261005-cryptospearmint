"""Funding carry: вход в delta-neutral при устойчиво положительном funding.

stat: "mean" (по умолчанию) или "median". Median защищает от одиночных
катастрофических event'ов (SOL имел min=-0.02 при median +0.000083).
"""
from __future__ import annotations

import pandas as pd

DEFAULT_PARAMS = {
    "lookback": 21,
    "entry_thr": 0.00005,
    "exit_thr": -0.00003,
    "stat": "median",   # mean | median
}


def funding_carry_signals(funding: pd.Series, *, lookback: int = 21,
                          entry_thr: float = 0.00005,
                          exit_thr: float = -0.00003,
                          stat: str = "median") -> tuple[pd.Series, pd.Series]:
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    if entry_thr <= exit_thr:
        raise ValueError("entry_thr must be > exit_thr")
    if stat not in ("mean", "median"):
        raise ValueError(f"stat must be mean|median, got {stat!r}")

    roll = funding.rolling(lookback, min_periods=lookback)
    rs = roll.median() if stat == "median" else roll.mean()

    above = (rs > entry_thr).fillna(False).astype(bool)
    below = (rs < exit_thr).fillna(False).astype(bool)
    entries = above & ~above.shift(1, fill_value=False).astype(bool)
    exits = below & ~below.shift(1, fill_value=False).astype(bool)
    return entries, exits


__all__ = ["DEFAULT_PARAMS", "funding_carry_signals"]
