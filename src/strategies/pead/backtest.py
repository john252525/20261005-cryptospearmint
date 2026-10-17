"""Event-driven PEAD backtest.

Trade lifecycle:
  signal  : earnings announced on day T (after close), surprise gate passes
  entry   : open of T+2 (T+1 for the reaction, T+2 gives a clean fill)
  sizing  : risk_per_trade_pct of NAV risked to the stop -> shares
  exit    : stop-loss / holding_days_max / end of sample

Costs: commission+slippage per side, short borrow per day on short legs.
Hedge: if net long exposure > hedge_threshold_frac of NAV, short QQQ.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .config import PEADSettings
from .hedge import compute_hedge
from .signal import (
    DIR_LONG,
    DIR_SHORT,
    compute_signal,
    compute_surprise,
    fetch_earnings_calendar,
    relative_volume,
)


@dataclass
class Trade:
    symbol: str
    direction: str
    entry_date: date
    entry_price: float
    shares: float
    stop_price: float
    exit_date: date | None = None
    exit_price: float | None = None
    exit_reason: str = ""
    surprise_pct: float = float("nan")
    borrow_cost: float = 0.0
    fees: float = 0.0
    pnl: float = 0.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_date": self.entry_date.isoformat(),
            "entry_price": self.entry_price,
            "shares": self.shares,
            "stop_price": self.stop_price,
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "surprise_pct": self.surprise_pct,
            "borrow_cost": self.borrow_cost,
            "fees": self.fees,
            "pnl": self.pnl,
        }


@dataclass
class BacktestResult:
    equity: pd.DataFrame
    trades: list[Trade] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def _download_prices(symbols: list[str], start: date, end: date) -> dict[str, pd.DataFrame]:
    import yfinance as yf

    out: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            df = yf.download(
                sym,
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
                interval="1d",
                progress=False,
                auto_adjust=False,
                threads=False,
            )
        except Exception:  # noqa: BLE001
            continue
        if df is None or len(df) == 0:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df = df.rename(columns=str.title)
        df.index = pd.to_datetime(df.index).normalize()
        out[sym] = df
    return out


def _nav_from_positions(cash: float, positions: dict[str, Trade], prices: dict[str, pd.DataFrame], d: date) -> float:
    nav = cash
    for tr in positions.values():
        df = prices.get(tr.symbol)
        px = tr.entry_price
        if df is not None:
            sub = df[df.index.date <= d]
            if len(sub) and not pd.isna(sub["Close"].iloc[-1]):
                px = float(sub["Close"].iloc[-1])
        sign = 1.0 if tr.direction == DIR_LONG else -1.0
        nav += sign * tr.shares * px
    return nav


def run_backtest(settings: PEADSettings, days: int | None = None) -> BacktestResult:
    rng = np.random.default_rng(settings.seed)
    days = days or settings.days
    end = date.today()
    start = end - timedelta(days=days)

    universe = list(settings.universe)
    prices = _download_prices(universe + [settings.hedge_symbol], start, end)
    if not prices:
        raise RuntimeError("DATA_UNAVAILABLE: no price data downloaded")

    cal = fetch_earnings_calendar(universe, start - timedelta(days=5), end)
    if cal.empty:
        raise RuntimeError("DATA_UNAVAILABLE: no earnings calendar returned")

    # build trading calendar from union of price dates
    all_dates = sorted({d for df in prices.values() for d in df.index.date})
    all_dates = [d for d in all_dates if start <= d <= end]
    if not all_dates:
        raise RuntimeError("DATA_UNAVAILABLE: empty trading calendar")

    cash = 1_000_000.0
    initial_nav = cash
    open_pos: dict[str, Trade] = {}
    pending: list[dict] = []
    trades: list[Trade] = []
    equity_rows: list[dict] = []
    hedge_pos: Trade | None = None

    cal_by_date: dict[date, list[dict]] = {}
    for _, row in cal.iterrows():
        cal_by_date.setdefault(row["earnings_date"], []).append(row.to_dict())

    for di, d in enumerate(all_dates):
        # ---- exits ----
        for sym in list(open_pos.keys()):
            tr = open_pos[sym]
            df = prices.get(sym)
            if df is None:
                continue
            sub = df[df.index.date == d]
            if len(sub) == 0:
                continue
            low = float(sub["Low"].iloc[0])
            high = float(sub["High"].iloc[0])
            close = float(sub["Close"].iloc[0])
            days_held = (d - tr.entry_date).days
            exit_px = None
            reason = ""
            if tr.direction == DIR_LONG:
                if low <= tr.stop_price:
                    exit_px, reason = tr.stop_price, "stop_loss"
            else:
                if high >= tr.stop_price:
                    exit_px, reason = tr.stop_price, "stop_loss"
            if exit_px is None and days_held >= settings.holding_days_max:
                exit_px, reason = close, "holding_days_max"
            if exit_px is None and di == len(all_dates) - 1:
                exit_px, reason = close, "end_of_sample"
            if exit_px is not None:
                _close_trade(tr, exit_px, d, reason, settings, cash)
                cash += tr.pnl
                trades.append(tr)
                del open_pos[sym]

        # ---- hedge rebalance ----
        nav_now = _nav_from_positions(cash, open_pos, prices, d)
        net_long = 0.0
        for tr in open_pos.values():
            df = prices.get(tr.symbol)
            px = tr.entry_price
            if df is not None:
                sub = df[df.index.date == d]
                if len(sub):
                    px = float(sub["Close"].iloc[0])
            sign = 1.0 if tr.direction == DIR_LONG else -1.0
            net_long += sign * tr.shares * px
        hedge_df = prices.get(settings.hedge_symbol)
        if hedge_df is not None:
            hsub = hedge_df[hedge_df.index.date == d]
            if len(hsub) and nav_now > 0:
                hpx = float(hsub["Close"].iloc[0])
                decision = compute_hedge(net_long, nav_now, settings.hedge_threshold_frac)
                target_hedge_val = decision.hedge_notional  # negative = short QQQ
                # current hedge value (positive number = size of the short)
                cur = 0.0
                if hedge_pos is not None:
                    cur = -hedge_pos.shares * hpx
                if abs(target_hedge_val - cur) > 0.02 * nav_now:
                    if hedge_pos is not None:
                        # unwind existing hedge
                        exit_px = hpx
                        _close_trade(hedge_pos, exit_px, d, "hedge_rebalance", settings, cash)
                        cash += hedge_pos.pnl
                        trades.append(hedge_pos)
                        hedge_pos = None
                    if target_hedge_val < 0:
                        shares = abs(target_hedge_val) / hpx
                        stop = hpx * (1.0 + settings.stop_loss_pct / 100.0)
                        hedge_pos = Trade(
                            symbol=settings.hedge_symbol,
                            direction=DIR_SHORT,
                            entry_date=d,
                            entry_price=hpx,
                            shares=shares,
                            stop_price=stop,
                        )

        # ---- signals announced today -> schedule entry at T+2 ----
        if d in cal_by_date:
            for ev in cal_by_date[d]:
                sym = ev["symbol"]
                if sym in open_pos or sym in [p["symbol"] for p in pending]:
                    continue
                if len(open_pos) >= settings.max_positions:
                    continue
                df = prices.get(sym)
                if df is None:
                    continue
                rv = relative_volume(df, d)
                sig = compute_signal(ev["surprise_pct"], rv, settings)
                if sig is None:
                    continue
                pend = {"symbol": sym, "direction": sig.direction,
                        "confidence": sig.confidence, "signal_date": d,
                        "surprise_pct": float(ev["surprise_pct"])}
                pending.append(pend)

        # ---- entries due today (T+2 after signal) ----
        still_pending = []
        for p in pending:
            due = p["signal_date"] + timedelta(days=2)
            if d < due:
                still_pending.append(p)
                continue
            if len(open_pos) >= settings.max_positions:
                continue
            sym = p["symbol"]
            df = prices.get(sym)
            if df is None:
                continue
            sub = df[df.index.date == d]
            if len(sub) == 0:
                still_pending.append(p)
                continue
            o = float(sub["Open"].iloc[0])
            if not math.isfinite(o) or o <= 0:
                continue
            nav = _nav_from_positions(cash, open_pos, prices, d)
            risk_amt = nav * settings.risk_per_trade_pct / 100.0
            stop_dist = o * settings.stop_loss_pct / 100.0
            shares = risk_amt / stop_dist if stop_dist > 0 else 0.0
            if shares <= 0:
                continue
            if p["direction"] == DIR_LONG:
                stop = o * (1.0 - settings.stop_loss_pct / 100.0)
            else:
                if not settings.allow_short:
                    continue
                stop = o * (1.0 + settings.stop_loss_pct / 100.0)
            open_pos[sym] = Trade(
                symbol=sym, direction=p["direction"], entry_date=d,
                entry_price=o, shares=shares, stop_price=stop,
                surprise_pct=float(p.get("surprise_pct", float("nan"))),
            )
        pending = still_pending

        # ---- mark equity ----
        nav = _nav_from_positions(cash, open_pos, prices, d)
        equity_rows.append({"date": d, "nav": nav, "cash": cash,
                            "n_positions": len(open_pos)})

    # force-close any survivors at last close
    last_d = all_dates[-1]
    for sym in list(open_pos.keys()):
        tr = open_pos[sym]
        df = prices.get(sym)
        px = tr.entry_price
        if df is not None and len(df):
            px = float(df["Close"].iloc[-1])
        _close_trade(tr, px, last_d, "end_of_sample", settings, cash)
        cash += tr.pnl
        trades.append(tr)
    if hedge_pos is not None:
        hdf = prices.get(settings.hedge_symbol)
        px = hedge_pos.entry_price
        if hdf is not None and len(hdf):
            px = float(hdf["Close"].iloc[-1])
        _close_trade(hedge_pos, px, last_d, "end_of_sample", settings, cash)
        cash += hedge_pos.pnl
        trades.append(hedge_pos)

    eq = pd.DataFrame(equity_rows)
    eq["date"] = pd.to_datetime(eq["date"])
    eq = eq.set_index("date")
    metrics = compute_metrics(eq, trades, initial_nav, settings)
    return BacktestResult(equity=eq, trades=trades, metrics=metrics)


def _close_trade(tr: Trade, exit_px: float, d: date, reason: str, settings: PEADSettings, cash: float) -> None:
    tr.exit_date = d
    tr.exit_price = exit_px
    tr.exit_reason = reason
    sign = 1.0 if tr.direction == DIR_LONG else -1.0
    gross = sign * tr.shares * (exit_px - tr.entry_price)
    entry_notional = tr.shares * tr.entry_price
    exit_notional = tr.shares * exit_px
    fees = (entry_notional + exit_notional) * settings.commission_per_side_bps / 1e4
    borrow = 0.0
    if tr.direction == DIR_SHORT:
        hold_days = max((d - tr.entry_date).days, 1)
        borrow = entry_notional * settings.borrow_per_day_bps / 1e4 * hold_days
    tr.fees = round(fees, 6)
    tr.borrow_cost = round(borrow, 6)
    tr.pnl = round(gross - fees - borrow, 6)


def compute_metrics(eq: pd.DataFrame, trades: list[Trade], initial_nav: float, settings: PEADSettings) -> dict:
    if eq.empty:
        return {}
    nav = eq["nav"].to_numpy(dtype=float)
    rets = np.diff(nav) / np.where(nav[:-1] == 0, 1.0, nav[:-1])
    if len(rets) > 1 and np.std(rets) > 0:
        sharpe = float(np.mean(rets) / np.std(rets) * math.sqrt(252))
    else:
        sharpe = float("nan")
    peak = np.maximum.accumulate(nav)
    dd = (nav - peak) / peak
    max_dd = float(-dd.min()) if len(dd) else float("nan")
    total_return = float(nav[-1] / initial_nav - 1.0) if initial_nav else float("nan")
    n = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    hit_rate = len(wins) / n if n else float("nan")
    fees = sum(t.fees for t in trades)
    borrow = sum(t.borrow_cost for t in trades)
    gross_pnl = sum(t.pnl for t in trades)
    return {
        "sharpe": round(sharpe, 4) if math.isfinite(sharpe) else None,
        "total_return_pct": round(total_return * 100, 4),
        "max_dd_pct": round(max_dd * 100, 4),
        "trades_count": n,
        "hit_rate": round(hit_rate, 4) if math.isfinite(hit_rate) else None,
        "fees_total": round(fees, 2),
        "borrow_total": round(borrow, 2),
        "net_pnl": round(gross_pnl, 2),
        "final_nav": round(float(nav[-1]), 2),
        "initial_nav": round(initial_nav, 2),
        "universe_size": len(settings.universe),
        "seed": settings.seed,
        "generated_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def save_results(res: BacktestResult, settings: PEADSettings) -> dict[str, str]:
    out = Path(settings.results_dir)
    out.mkdir(parents=True, exist_ok=True)
    tag = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    eq_path = out / f"pead_{tag}.parquet"
    m_path = out / f"pead_{tag}.metrics.json"
    tr_path = out / f"pead_{tag}.trades.parquet"
    res.equity.to_parquet(eq_path)
    m_path.write_text(json.dumps(res.metrics, indent=2))
    pd.DataFrame([t.to_dict() for t in res.trades]).to_parquet(tr_path)
    return {"equity": str(eq_path), "metrics": str(m_path), "trades": str(tr_path)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pead.backtest")
    ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--synthetic", action="store_true", help="unused placeholder")
    args = ap.parse_args(argv)
    settings = PEADSettings()
    res = run_backtest(settings, days=args.days)
    paths = save_results(res, settings)
    print(json.dumps(res.metrics, indent=2))
    print("saved:", json.dumps(paths, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
