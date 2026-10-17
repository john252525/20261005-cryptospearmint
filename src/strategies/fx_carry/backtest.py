"""Event-driven daily-bar backtest for the G10 FX carry strategy."""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .config import FXCarrySettings
from .signal import FXCarrySignal, fetch_fx_prices, fetch_rates, generate_signals


@dataclass
class Position:
    pair: str
    direction: str          # 'long' | 'short'
    notional_usd: float     # absolute notional at entry
    entry_date: pd.Timestamp
    entry_price: float
    carry_bps: float
    ann_vol_pct: float


@dataclass
class Trade:
    pair: str
    direction: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    notional_usd: float
    gross_pnl: float
    carry_pnl: float
    fees: float
    net_pnl: float
    holding_days: int

    @property
    def is_win(self) -> bool:
        return self.net_pnl > 0


@dataclass
class BacktestResult:
    equity: pd.Series
    trades: List[Trade] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


def _pair_pnl_fraction(direction: str, entry_price: float, exit_price: float) -> float:
    if entry_price <= 0 or exit_price <= 0:
        return 0.0
    ret = (exit_price / entry_price) - 1.0
    return ret if direction == "long" else -ret


def run_backtest(prices: pd.DataFrame,
                 rates: pd.DataFrame,
                 settings: Optional[FXCarrySettings] = None,
                 start: Optional[pd.Timestamp] = None,
                 end: Optional[pd.Timestamp] = None) -> BacktestResult:
    """Weekly-rebalanced carry backtest on daily bars.

    * Rebalance every Monday using signals computed as-of that date.
    * Target notional = risk_per_trade_pct/100 * NAV per position.
    * Round-trip cost = 2*(commission+slippage) bps on notional, charged at
      entry (half) and exit (half) so partial runs stay consistent.
    * Carry accrues daily as (carry_bps/10000)/252 * notional * sign.
    """
    s = settings or FXCarrySettings()
    if prices is None or prices.empty:
        raise ValueError("prices frame is empty")

    px = prices.copy().sort_index().ffill()
    if start is not None:
        px = px.loc[pd.Timestamp(start):]
    if end is not None:
        px = px.loc[:pd.Timestamp(end)]
    px = px.dropna(how="all")
    if px.empty:
        raise ValueError("prices empty after date filter")

    dates = px.index
    nav = 1_000_000.0          # starting NAV in USD
    initial_nav = nav
    equity_vals: List[float] = []
    equity_idx: List[pd.Timestamp] = []

    positions: Dict[str, Position] = {}
    trades: List[Trade] = []
    entry_costs: Dict[str, float] = {}
    pending_exit_fee: Dict[str, float] = {}

    cost_frac = s.round_trip_cost_bps / 10_000.0
    notional_target = (s.risk_per_trade_pct / 100.0) * initial_nav

    def _close_position(pair: str, date: pd.Timestamp, price: float) -> None:
        nonlocal nav
        pos = positions.pop(pair)
        gross = _pair_pnl_fraction(pos.direction, pos.entry_price, price) * pos.notional_usd
        # Carry accrued while holding: signed carry_bps annualised
        days_held = max((date - pos.entry_date).days, 0)
        carry_sign = 1.0 if pos.direction == "long" else -1.0
        carry_pnl = (pos.carry_bps / 10_000.0) * (days_held / 252.0) * pos.notional_usd * carry_sign
        # Fees: entry half already deducted at entry; exit half now.
        exit_fee = 0.5 * cost_frac * pos.notional_usd
        total_fees = entry_costs.pop(pair, 0.0) + exit_fee
        net = gross + carry_pnl - total_fees
        nav += net
        trades.append(Trade(
            pair=pair, direction=pos.direction,
            entry_date=pos.entry_date, exit_date=date,
            entry_price=pos.entry_price, exit_price=price,
            notional_usd=pos.notional_usd,
            gross_pnl=gross, carry_pnl=carry_pnl,
            fees=total_fees, net_pnl=net,
            holding_days=days_held,
        ))

    rebalance_days = [d for d in dates if d.dayofweek == 0]  # Monday
    rebalance_set = set(rebalance_days)

    for i, date in enumerate(dates):
        price_row = px.loc[date]

        # Mark-to-market for today's equity (before any rebalance).
        mtm = 0.0
        for pair, pos in positions.items():
            p_now = price_row.get(pair, np.nan)
            if not np.isfinite(p_now):
                p_now = pos.entry_price
            mtm += _pair_pnl_fraction(pos.direction, pos.entry_price, p_now) * pos.notional_usd
            days_held = max((date - pos.entry_date).days, 0)
            carry_sign = 1.0 if pos.direction == "long" else -1.0
            mtm += (pos.carry_bps / 10_000.0) * (days_held / 252.0) * pos.notional_usd * carry_sign
        equity_vals.append(nav + mtm)
        equity_idx.append(date)

        if date not in rebalance_set:
            continue

        # Only use data up to `date` to avoid look-ahead.
        sigs: List[FXCarrySignal] = generate_signals(
            rates.loc[:date], px.loc[:date], settings=s, as_of=date
        )
        active = [sg for sg in sigs if sg.direction is not None]
        # Rank by |carry| desc, then conf; keep max_positions.
        active.sort(key=lambda x: (abs(x.carry_bps), x.confidence), reverse=True)
        active = active[: s.max_positions]
        target: Dict[str, FXCarrySignal] = {sg.pair: sg for sg in active}

        # Close positions that are no longer targeted or flipped.
        for pair in list(positions.keys()):
            pos = positions[pair]
            sig = target.get(pair)
            need_close = sig is None or sig.direction != pos.direction
            if need_close:
                p_now = price_row.get(pair, np.nan)
                if not np.isfinite(p_now) or p_now <= 0:
                    continue
                _close_position(pair, date, float(p_now))

        # Open new / resize existing.
        for pair, sig in target.items():
            if pair in positions:
                continue
            p_now = price_row.get(pair, np.nan)
            if not np.isfinite(p_now) or p_now <= 0:
                continue
            entry_fee = 0.5 * cost_frac * notional_target
            nav -= entry_fee
            entry_costs[pair] = entry_fee
            positions[pair] = Position(
                pair=pair, direction=sig.direction, notional_usd=notional_target,
                entry_date=date, entry_price=float(p_now),
                carry_bps=float(sig.carry_bps) if np.isfinite(sig.carry_bps) else 0.0,
                ann_vol_pct=float(sig.ann_vol_pct) if np.isfinite(sig.ann_vol_pct) else 0.0,
            )

    # Force-close at the end.
    last_date = dates[-1]
    last_row = px.loc[last_date]
    for pair in list(positions.keys()):
        p_now = last_row.get(pair, np.nan)
        if np.isfinite(p_now) and p_now > 0:
            _close_position(pair, last_date, float(p_now))
    if positions:
        for pair, pos in list(positions.items()):
            _close_position(pair, last_date, pos.entry_price)

    equity = pd.Series(equity_vals, index=pd.DatetimeIndex(equity_idx), name="equity")
    metrics = compute_metrics(equity, trades, initial_nav, s)
    return BacktestResult(equity=equity, trades=trades, metrics=metrics)


def compute_metrics(equity: pd.Series, trades: List[Trade],
                    initial_nav: float, settings: FXCarrySettings) -> Dict[str, float]:
    if equity.empty:
        return {}
    ret = equity.pct_change().dropna()
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9)
    total_return = float(equity.iloc[-1] / initial_nav - 1.0)
    ann_ret = float((1.0 + total_return) ** (1.0 / years) - 1.0) if total_return > -1 else -1.0
    if len(ret) > 1 and ret.std(ddof=1) > 0:
        sharpe = float(ret.mean() / ret.std(ddof=1) * np.sqrt(252))
    else:
        sharpe = 0.0
    roll_max = equity.cummax()
    dd = equity / roll_max - 1.0
    max_dd = float(dd.min())
    n_trades = len(trades)
    wins = sum(1 for t in trades if t.is_win)
    hit_rate = float(wins / n_trades) if n_trades else 0.0
    total_fees = float(sum(t.fees for t in trades))
    avg_hold = float(np.mean([t.holding_days for t in trades])) if n_trades else 0.0
    avg_carry = float(np.mean([t.carry_bps for t in trades])) if n_trades else 0.0
    total_notional = float(sum(t.notional_usd for t in trades)) or 1.0
    fee_bps = float(total_fees / total_notional * 10_000.0)
    gross_win = sum(t.net_pnl for t in trades if t.is_win)
    gross_loss = -sum(t.net_pnl for t in trades if not t.is_win)
    profit_factor = float(gross_win / gross_loss) if gross_loss > 0 else float("inf")
    avg_vol = float(np.mean([t.holding_days for t in trades])) if n_trades else 0.0
    return {
        "sharpe": round(sharpe, 4),
        "max_dd": round(max_dd, 4),
        "win_rate": round(hit_rate, 4),
        "hit_rate": round(hit_rate, 4),
        "trades_count": int(n_trades),
        "total_fees": round(total_fees, 2),
        "total_return": round(total_return, 6),
        "ann_return": round(ann_ret, 6),
        "fee_bps": round(fee_bps, 2),
        "years": round(years, 4),
        "avg_holding_days": round(avg_hold, 2),
        "avg_carry_bps": round(avg_carry, 2),
        "avg_vol_pct": round(avg_vol, 2),
        "profit_factor": round(profit_factor, 4) if np.isfinite(profit_factor) else None,
        "asset_class": "fx",
        "adjusted": True,
        "delisted_count": 0,
        "final_nav": round(float(equity.iloc[-1]), 2),
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="G10 FX carry backtest")
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--refresh", action="store_true", help="bypass caches")
    args = ap.parse_args(argv)

    s = FXCarrySettings(days=args.days)
    os.makedirs(s.results_dir, exist_ok=True)

    print(f"[fx-carry] fetching {len(s.pairs)} pairs, days={args.days}")
    prices = fetch_fx_prices(s.pairs, days=args.days, settings=s, use_cache=not args.refresh)
    print(f"[fx-carry] prices shape={prices.shape} range={prices.index[0].date()}..{prices.index[-1].date()}")
    rates = fetch_rates(settings=s, use_cache=not args.refresh)
    print(f"[fx-carry] rates shape={rates.shape} range={rates.index[0].date()}..{rates.index[-1].date()}")

    res = run_backtest(prices, rates, settings=s)
    m = res.metrics
    print("[fx-carry] metrics:")
    for k, v in m.items():
        print(f"  {k}: {v}")

    stamp = pd.Timestamp.utcnow().strftime("%Y%m%dT%H%M%SZ")
    mpath = os.path.join(s.results_dir, f"fx_carry_{stamp}.metrics.json")
    epath = os.path.join(s.results_dir, f"fx_carry_{stamp}.parquet")
    equity = res.equity
    if isinstance(equity.index, pd.DatetimeIndex) and equity.index.tz is not None:
        equity = equity.copy()
        equity.index = equity.index.tz_localize(None)
    try:
        equity.to_parquet(epath)
    except Exception as exc:  # pragma: no cover
        print(f"[fx-carry] parquet write failed ({exc}); writing csv instead")
        equity.to_csv(epath.replace(".parquet", ".csv"))
    with open(mpath, "w") as fh:
        json.dump(m, fh, indent=2)
    print(f"[fx-carry] wrote {mpath}")
    print(f"[fx-carry] wrote {epath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
