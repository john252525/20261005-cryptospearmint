"""G10 FX carry signal generation.

Edge hypothesis: interest-rate differentials between G10 currencies are a
compensated risk premium (carry).  Long the high-yielder, short the
low-yielder, rebalanced weekly, with a volatility crash filter.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

from .config import FXCarrySettings

# ---------------------------------------------------------------------------
# Pair -> (base_ccy, quote_ccy) mapping
# ---------------------------------------------------------------------------
PAIR_CCY: Dict[str, Tuple[str, str]] = {
    "EURUSD=X": ("EUR", "USD"),
    "GBPUSD=X": ("GBP", "USD"),
    "JPY=X": ("USD", "JPY"),
    "AUDUSD=X": ("AUD", "USD"),
    "NZDUSD=X": ("NZD", "USD"),
    "USDCAD=X": ("USD", "CAD"),
    "USDCHF=X": ("USD", "CHF"),
    "USDNOK=X": ("USD", "NOK"),
    "USDSEK=X": ("USD", "SEK"),
}


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
def fetch_rates(settings: Optional[FXCarrySettings] = None,
                use_cache: bool = True) -> pd.DataFrame:
    """Download 3M interbank rates from FRED (direct CSV endpoint).

    Returns a monthly-ish DataFrame indexed by date, columns = ccy codes,
    values = annualised percent.
    """
    s = settings or FXCarrySettings()
    cache = s.rates_cache_path
    if use_cache and os.path.exists(cache):
        df = pd.read_parquet(cache)
        if not df.empty:
            return df

    frames = {}
    for ccy, series in s.rate_series.items():
        url = s.g10_rates_url.format(series=series)
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
        except Exception:
            continue
        from io import StringIO
        raw = pd.read_csv(StringIO(r.text))
        if raw.shape[1] < 2:
            continue
        date_col, val_col = raw.columns[0], raw.columns[1]
        raw[date_col] = pd.to_datetime(raw[date_col], errors="coerce")
        raw[val_col] = pd.to_numeric(raw[val_col], errors="coerce")
        ser = raw.dropna().set_index(date_col)[val_col].sort_index()
        if len(ser):
            frames[ccy] = ser

    if not frames:
        return pd.DataFrame()

    rates = pd.DataFrame(frames).sort_index()
    rates = rates.ffill()
    os.makedirs(os.path.dirname(cache) or ".", exist_ok=True)
    rates.to_parquet(cache)
    return rates


def fetch_fx_prices(pairs: List[str], days: int = 1095,
                    settings: Optional[FXCarrySettings] = None,
                    use_cache: bool = True) -> pd.DataFrame:
    """Daily close prices from yfinance for the last `days` calendar days."""
    s = settings or FXCarrySettings()
    cache = s.cache_path
    if use_cache and os.path.exists(cache):
        df = pd.read_parquet(cache)
        have = [p for p in pairs if p in df.columns]
        if len(have) == len(pairs) and len(df) > days * 0.5:
            return df[pairs]

    import yfinance as yf

    end = pd.Timestamp.utcnow().normalize()
    start = end - pd.Timedelta(days=int(days) + 30)
    raw = yf.download(pairs, start=start.strftime("%Y-%m-%d"),
                      end=end.strftime("%Y-%m-%d"),
                      progress=False, auto_adjust=True, threads=True)
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = raw[["Close"]]
        close.columns = pairs[:1]
    close = close.dropna(how="all").ffill()
    os.makedirs(os.path.dirname(cache) or ".", exist_ok=True)
    close.to_parquet(cache)
    return close


# ---------------------------------------------------------------------------
# Core math
# ---------------------------------------------------------------------------
def compute_vol_filter(prices_series: pd.Series, lookback: int = 30) -> float:
    """Annualised realised vol in percent (not fraction).

    log-return std over `lookback` days * sqrt(252) * 100.
    """
    p = prices_series.dropna()
    if len(p) < lookback + 1:
        return float("nan")
    ret = np.log(p / p.shift(1)).dropna().tail(lookback)
    if len(ret) < 2:
        return float("nan")
    return float(ret.std(ddof=1) * np.sqrt(252) * 100.0)


def compute_carry(pair: str, rates_df: pd.DataFrame,
                  as_of: Optional[pd.Timestamp] = None,
                  lag_days: int = 45) -> dict:
    """Interest differential for a pair, expressed as (base - quote) in bps.

    Positive carry_bps => base currency yields more => go long the pair.

    FRED `IR3TIB01*M156N` rows are indexed at the *start* of the month they
    describe and are published only around the middle of the following month.
    Reading the month-M row on a date inside month M is therefore look-ahead,
    so we shift the cut-off back by `lag_days` (default 45).
    """
    base, quote = PAIR_CCY[pair]
    if base not in rates_df.columns or quote not in rates_df.columns:
        return {"pair": pair, "base_ccy": base, "quote_ccy": quote,
                "carry_bps": float("nan"), "rate_base": float("nan"),
                "rate_quote": float("nan"), "direction": None}

    cutoff = as_of - pd.Timedelta(days=int(lag_days)) if as_of is not None else None
    sub = rates_df[[base, quote]].dropna()
    if cutoff is not None:
        sub = sub.loc[:cutoff]
    if sub.empty:
        return {"pair": pair, "base_ccy": base, "quote_ccy": quote,
                "carry_bps": float("nan"), "rate_base": float("nan"),
                "rate_quote": float("nan"), "direction": None}

    if as_of is not None and cutoff is None:
        sub = sub.loc[:as_of]
        if sub.empty:
            return {"pair": pair, "base_ccy": base, "quote_ccy": quote,
                    "carry_bps": float("nan"), "rate_base": float("nan"),
                    "rate_quote": float("nan"), "direction": None}

    r_base = float(sub[base].iloc[-1])   # percent
    r_quote = float(sub[quote].iloc[-1])
    diff_pct = r_base - r_quote
    return {
        "pair": pair,
        "base_ccy": base,
        "quote_ccy": quote,
        "carry_bps": diff_pct * 100.0,   # percent -> bps
        "rate_base": r_base,
        "rate_quote": r_quote,
        "direction": None,  # filled by generate_signals
    }


@dataclass
class FXCarrySignal:
    ts: pd.Timestamp
    pair: str
    base_ccy: str
    quote_ccy: str
    direction: Optional[str]   # 'long' | 'short' | None
    carry_bps: float
    ann_vol_pct: float
    confidence: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ts"] = pd.Timestamp(self.ts).isoformat()
        return d


def generate_signals(rates_df: pd.DataFrame, prices_df: pd.DataFrame,
                     settings: Optional[FXCarrySettings] = None,
                     as_of: Optional[pd.Timestamp] = None) -> List[FXCarrySignal]:
    """Map carry to direction, apply min-carry + vol crash filter.

    Rules per pair (base/quote):
      carry_bps > +min_carry_bps -> long pair
      carry_bps < -min_carry_bps -> short pair
    Vol filter: skip if pair's ann vol > vol_filter_max_pct * cross-sectional
    median vol, or if vol is NaN.
    """
    s = settings or FXCarrySettings()
    ts = as_of if as_of is not None else pd.Timestamp.utcnow().normalize()

    # Vol panel first (needed for cross-sectional median filter).
    vols: Dict[str, float] = {}
    for pair in s.pairs:
        if pair not in prices_df.columns:
            continue
        series = prices_df[pair]
        if as_of is not None:
            series = series.loc[:as_of]
        vols[pair] = compute_vol_filter(series, s.vol_filter_lookback_days)

    valid_vols = [v for v in vols.values() if np.isfinite(v) and v > 0]
    median_vol = float(np.median(valid_vols)) if valid_vols else float("nan")
    vol_cap = median_vol * s.vol_filter_max_pct if np.isfinite(median_vol) else float("inf")

    out: List[FXCarrySignal] = []
    for pair in s.pairs:
        c = compute_carry(pair, rates_df, as_of=as_of,
                          lag_days=s.rate_publication_lag_days)
        carry_bps = c["carry_bps"]
        vol = vols.get(pair, float("nan"))

        direction: Optional[str] = None
        if np.isfinite(carry_bps):
            if carry_bps > s.min_carry_bps:
                direction = "long"
            elif carry_bps < -s.min_carry_bps:
                direction = "short"

        # Crash filter: drop whenever vol unavailable or above the cap.
        if direction is not None:
            if not np.isfinite(vol) or vol > vol_cap:
                direction = None

        if direction is None:
            confidence = 0.0
        else:
            mag = min(abs(carry_bps) / 400.0, 1.0)
            vol_pen = 0.0 if not np.isfinite(vol) or vol_cap <= 0 else min(vol / vol_cap, 1.0)
            confidence = round(float(mag * (1.0 - 0.5 * vol_pen)), 4)

        out.append(FXCarrySignal(
            ts=pd.Timestamp(ts),
            pair=pair,
            base_ccy=c["base_ccy"],
            quote_ccy=c["quote_ccy"],
            direction=direction,
            carry_bps=float(carry_bps) if np.isfinite(carry_bps) else float("nan"),
            ann_vol_pct=float(vol) if np.isfinite(vol) else float("nan"),
            confidence=confidence,
        ))
    return out
