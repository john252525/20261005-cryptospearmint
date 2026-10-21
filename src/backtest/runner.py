"""Long-only event-driven backtester.

Rules:
  - signal on bar i -> fill at OPEN of bar i+1 (next-bar-open, no lookahead)
  - longs only, max one position at a time
  - fee (taker) + slippage charged on BOTH sides
"""
from __future__ import annotations
import numpy as np
import pandas as pd

HOURS_PER_YEAR = 365 * 24


def run(df: pd.DataFrame, entries: pd.Series, exits: pd.Series,
        fee: float = 0.001, slip: float = 0.0005) -> dict:
    o = df['open'].to_numpy(dtype=float)
    ts = pd.to_datetime(df['ts']).to_numpy() if 'ts' in df.columns else df.index.to_numpy()
    e_in = entries.fillna(False).to_numpy(dtype=bool)
    e_out = exits.fillna(False).to_numpy(dtype=bool)
    n = len(df)

    def _fill_price(idx: int) -> float:
        return float(o[idx])

    n_ = n
    entry_idx = e_in.nonzero()[0]
    exit_idx = e_out.nonzero()[0]
    ie, ix = 0, 0
    in_pos = False
    trades: list[dict] = []
    cur_entry_price = cur_entry_ts = None
    cur_entry_i = None

    i = 0
    while i < n_:
        if not in_pos:
            # advance ie to first entry signal >= i
            while ie < len(entry_idx) and entry_idx[ie] < i:
                ie += 1
            if ie < len(entry_idx) and entry_idx[ie] == i:
                fill_i = i + 1
                if fill_i < n_:
                    in_pos = True
                    cur_entry_price = _fill_price(fill_i)
                    cur_entry_ts = ts[fill_i]
                    cur_entry_i = fill_i
                    ie += 1
                    i = fill_i  # jump past the fill bar
                    continue
                else:
                    ie += 1
        else:
            while ix < len(exit_idx) and exit_idx[ix] < i:
                ix += 1
            if ix < len(exit_idx) and exit_idx[ix] == i:
                fill_i = i + 1
                if fill_i < n_:
                    entry_eff = cur_entry_price * (1.0 + slip)
                    exit_eff = _fill_price(fill_i) * (1.0 - slip)
                    gross = exit_eff / entry_eff - 1.0
                    net = (1.0 + gross) * (1.0 - fee) * (1.0 - fee) - 1.0
                    hold_h = (ts[fill_i] - cur_entry_ts) / np.timedelta64(1, 'h')
                    trades.append({
                        'entry_ts': pd.Timestamp(cur_entry_ts),
                        'exit_ts': pd.Timestamp(ts[fill_i]),
                        'entry_price': cur_entry_price,
                        'exit_price': _fill_price(fill_i),
                        'gross_ret': float(gross),
                        'net_ret': float(net),
                        'hold_hours': float(hold_h),
                        'entry_fee': float(fee),
                        'exit_fee': float(fee),
                        'exit_bar': int(fill_i),
                    })
                    in_pos = False
                    cur_entry_price = cur_entry_ts = cur_entry_i = None
                    ix += 1
                    i = fill_i
                    continue
                else:
                    ix += 1
        i += 1

    # Close any open position at last bar close for reporting purposes only
    if in_pos and cur_entry_price is not None:
        last_bar = n_ - 1
        entry_eff = cur_entry_price * (1.0 + slip)
        exit_eff = o[last_bar] * (1.0 - slip)
        gross = exit_eff / entry_eff - 1.0
        net = (1.0 + gross) * (1.0 - fee) * (1.0 - fee) - 1.0
        trades.append({
            'entry_ts': pd.Timestamp(cur_entry_ts),
            'exit_ts': pd.Timestamp(ts[last_bar]),
            'entry_price': cur_entry_price,
            'exit_price': float(o[last_bar]),
            'gross_ret': float(gross),
            'net_ret': float(net),
            'hold_hours': float((ts[last_bar] - cur_entry_ts) / np.timedelta64(1, 'h')),
            'entry_fee': float(fee),
            'exit_fee': float(fee),
            'exit_bar': int(last_bar),
            'forced_close': True,
        })

    tdf = pd.DataFrame(trades)
    # Bar-level realized equity: compound net return at each exit bar
    eq = np.ones(n_, dtype=float)
    if len(tdf):
        for t in tdf.itertuples(index=False):
            exit_pos = min(int(t.exit_bar), n_ - 1)
            eq[exit_pos:] *= (1.0 + t.net_ret)

    # metrics
    total_return = float(eq[-1] / eq[0] - 1.0)
    bar_ret = np.diff(eq) / eq[:-1]
    if bar_ret.std() > 0:
        sharpe = float(bar_ret.mean() / bar_ret.std() * np.sqrt(HOURS_PER_YEAR))
    else:
        sharpe = 0.0
    running_max = np.maximum.accumulate(eq)
    dd = (eq / running_max) - 1.0
    max_dd = float(-dd.min())
    hit_rate = float((tdf['net_ret'] > 0).mean()) if len(tdf) else 0.0
    trades_count = int(len(tdf))
    avg_hold_hours = float(tdf['hold_hours'].mean()) if len(tdf) else 0.0
    fees_paid = float((tdf['entry_fee'] + tdf['exit_fee']).sum()) if len(tdf) else 0.0

    return {
        'total_return': total_return,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'hit_rate': hit_rate,
        'trades_count': trades_count,
        'avg_hold_hours': avg_hold_hours,
        'fees_paid': fees_paid,
        'trades': tdf,
        'equity': eq,
    }
