"""Earnings-surprise signal construction for PEAD.

We pull real earnings dates / EPS estimates / reported EPS from yfinance,
compute the surprise, and gate on surprise magnitude plus the post-earnings
relative volume (announcement-day volume vs trailing average).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

log = logging.getLogger(__name__)

DIR_LONG = "long"
DIR_SHORT = "short"
DIR_FLAT = "flat"


@dataclass(slots=True)
class PEADSignal:
    symbol: str
    earnings_date: date
    surprise_pct: float
    eps_estimate: float | None
    eps_actual: float | None
    relative_volume: float
    direction: str
    confidence: float = 0.0
    meta: dict = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        return self.direction in (DIR_LONG, DIR_SHORT)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "earnings_date": self.earnings_date.isoformat(),
            "surprise_pct": self.surprise_pct,
            "eps_estimate": self.eps_estimate,
            "eps_actual": self.eps_actual,
            "relative_volume": self.relative_volume,
            "direction": self.direction,
            "confidence": self.confidence,
        }


def compute_surprise(actual: float | None, est: float | None) -> float:
    """Percent surprise = (actual - est) / |est| * 100.

    Returns nan when inputs are missing or the estimate is zero.
    """
    if actual is None or est is None:
        return float("nan")
    try:
        actual = float(actual)
        est = float(est)
    except (TypeError, ValueError):
        return float("nan")
    if not math.isfinite(actual) or not math.isfinite(est):
        return float("nan")
    if est == 0:
        return float("nan")
    return (actual - est) / abs(est) * 100.0


def fetch_earnings_calendar(
    tickers: list[str], start: date, end: date
) -> pd.DataFrame:
    """Fetch earnings events for tickers within [start, end].

    Returns a DataFrame with columns:
        symbol, earnings_date, eps_estimate, eps_actual, surprise_pct
    Uses yfinance; rows with missing reported EPS are dropped (future events).
    """
    import yfinance as yf

    rows: list[dict] = []
    for sym in tickers:
        try:
            tk = yf.Ticker(sym)
            ed = tk.get_earnings_dates(limit=48)
        except Exception as exc:  # noqa: BLE001 - network/library variability
            log.warning("earnings fetch failed for %s: %s", sym, exc)
            continue
        if ed is None or len(ed) == 0:
            continue
        ed = ed.reset_index()
        date_col = "Earnings Date" if "Earnings Date" in ed.columns else ed.columns[0]
        for _, row in ed.iterrows():
            raw_dt = row.get(date_col)
            if raw_dt is None or pd.isna(raw_dt):
                continue
            try:
                ts = pd.Timestamp(raw_dt)
            except (TypeError, ValueError):
                continue
            d = ts.date()
            if d < start or d > end:
                continue
            est = row.get("EPS Estimate")
            act = row.get("Reported EPS")
            est = None if est is None or pd.isna(est) else float(est)
            act = None if act is None or pd.isna(act) else float(act)
            if act is None:
                continue  # not yet reported
            rows.append(
                {
                    "symbol": sym,
                    "earnings_date": d,
                    "eps_estimate": est,
                    "eps_actual": act,
                    "surprise_pct": compute_surprise(act, est),
                }
            )
    return pd.DataFrame(
        rows,
        columns=["symbol", "earnings_date", "eps_estimate", "eps_actual", "surprise_pct"],
    )


def relative_volume(
    prices: pd.DataFrame, earnings_date: date, lookback: int = 20
) -> float:
    """Announcement-day volume / mean trailing volume.

    `prices` is indexed by date with a 'Volume' column.
    """
    if prices is None or len(prices) == 0 or "Volume" not in prices.columns:
        return float("nan")
    idx = pd.to_datetime(prices.index).date
    mask = idx == earnings_date
    if not mask.any():
        # find the first trading day on/after the earnings date
        after = [i for i, d in enumerate(idx) if d >= earnings_date]
        if not after:
            return float("nan")
        pos = after[0]
    else:
        pos = int(pd.Series(mask).to_numpy().argmax())
    if pos < lookback:
        lo = 0
    else:
        lo = pos - lookback
    window = prices["Volume"].iloc[lo:pos]
    if len(window) == 0:
        return float("nan")
    avg = float(window.mean())
    if avg <= 0 or not math.isfinite(avg):
        return float("nan")
    return float(prices["Volume"].iloc[pos]) / avg


def compute_signal(
    surprise_pct: float,
    rel_vol: float,
    settings,
) -> PEADSignal | None:
    """Apply gates and decide direction.

    Long when surprise >= +threshold, short when <= -threshold (if allowed).
    Requires rel_vol >= min_relative_volume.
    """
    if not math.isfinite(surprise_pct) or not math.isfinite(rel_vol):
        return None
    if rel_vol < settings.min_relative_volume:
        return None
    thr = settings.min_surprise_pct
    if surprise_pct >= thr:
        direction = DIR_LONG
    elif surprise_pct <= -thr and settings.allow_short:
        direction = DIR_SHORT
    else:
        return None
    confidence = min(abs(surprise_pct) / (thr * 2.0), 1.0) * min(rel_vol / 3.0, 1.0)
    return PEADSignal(
        symbol="",
        earnings_date=datetime.utcnow().date(),
        surprise_pct=surprise_pct,
        eps_estimate=None,
        eps_actual=None,
        relative_volume=rel_vol,
        direction=direction,
        confidence=round(confidence, 4),
    )
