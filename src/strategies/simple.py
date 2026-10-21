"""Ten simple TA strategies.

Every strategy is a function that takes a DataFrame with columns
[open, high, low, close, volume] (DatetimeIndex or RangeIndex) and
returns (entries, exits) as boolean pd.Series aligned to df.index.
Left edge (warm-up NaNs) always yields False.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from strategies.indicators import sma, ema, rsi, bollinger, macd, roc, donchian, obv


def _clean(series_bool: pd.Series) -> pd.Series:
    return series_bool.fillna(False).astype(bool)


def _cross_up(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a > b) & (a.shift(1) <= b.shift(1))


def _cross_dn(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a < b) & (a.shift(1) >= b.shift(1))


# 1 -------------------------------------------------------------------------
def sma_cross(df: pd.DataFrame, fast: int = 20, slow: int = 50):
    s_f, s_s = sma(df['close'], fast), sma(df['close'], slow)
    entries = _clean(_cross_up(s_f, s_s))
    exits = _clean(_cross_dn(s_f, s_s))
    return entries, exits


# 2 -------------------------------------------------------------------------
def ema_cross(df: pd.DataFrame, fast: int = 12, slow: int = 26):
    s_f, s_s = ema(df['close'], fast), ema(df['close'], slow)
    return _clean(_cross_up(s_f, s_s)), _clean(_cross_dn(s_f, s_s))


# 3 -------------------------------------------------------------------------
def rsi_obos(df: pd.DataFrame, n: int = 14, low: float = 30.0, high: float = 70.0):
    r = rsi(df['close'], n)
    entries = _clean((r < low) & (r.shift(1) >= low))
    exits = _clean((r > 50) & (r.shift(1) <= 50))
    return entries, exits


# 4 -------------------------------------------------------------------------
def bb_bounce(df: pd.DataFrame, n: int = 20, k: float = 2.0):
    up, mid, lo = bollinger(df['close'], n, k)
    entries = _clean(df['close'] < lo)
    exits = _clean(df['close'] > mid)
    return entries, exits


# 5 -------------------------------------------------------------------------
def macd_cross(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    line, sig, _ = macd(df['close'], fast, slow, signal)
    return _clean(_cross_up(line, sig)), _clean(_cross_dn(line, sig))


# 6 -------------------------------------------------------------------------
def momentum(df: pd.DataFrame, n: int = 10, thr: float = 2.0):
    r = roc(df['close'], n)
    entries = _clean((r > thr) & (r.shift(1) <= thr))
    exits = _clean((r < 0) & (r.shift(1) >= 0))
    return entries, exits


# 7 -------------------------------------------------------------------------
def mean_rev(df: pd.DataFrame, n: int = 20, k: float = 2.5):
    up, mid, lo = bollinger(df['close'], n, k)
    entries = _clean(df['close'] < (mid - (mid - lo)))
    exits = _clean(df['close'] > mid)
    return entries, exits


# 8 -------------------------------------------------------------------------
def donchian_break(df: pd.DataFrame, n: int = 20):
    hi_n, lo_n = donchian(df['high'], df['low'], n)
    # Use shifted channel so today's bar cannot self-trigger
    hi_prev, lo_prev = hi_n.shift(1), lo_n.shift(1)
    entries = _clean(df['close'] >= hi_prev)
    exits = _clean(df['close'] <= lo_prev)
    return entries, exits


# 9 -------------------------------------------------------------------------
def rsi_bb_combo(df: pd.DataFrame, n: int = 20, k: float = 2.0, rsi_n: int = 14):
    r = rsi(df['close'], rsi_n)
    up, mid, lo = bollinger(df['close'], n, k)
    entries = _clean((r < 40) & (df['close'] < lo))
    exits = _clean(r > 50)
    return entries, exits


# 10 ------------------------------------------------------------------------
def obv_divergence(df: pd.DataFrame, n: int = 20):
    o = obv(df['close'], df['volume'])
    o_ma = sma(o, n)
    s_ma = sma(df['close'], n)
    entries = _clean((o > o_ma) & _cross_up(df['close'], s_ma))
    exits = _clean(df['close'] < s_ma)
    return entries, exits


REGISTRY = {
    'sma_cross': sma_cross,
    'ema_cross': ema_cross,
    'rsi_obos': rsi_obos,
    'bb_bounce': bb_bounce,
    'macd_cross': macd_cross,
    'momentum': momentum,
    'mean_rev': mean_rev,
    'donchian_break': donchian_break,
    'rsi_bb_combo': rsi_bb_combo,
    'obv_divergence': obv_divergence,
}
