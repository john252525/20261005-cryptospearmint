"""Portfolio construction with SL/TP + fixed-notional accounting.

Model:
  capital = $500 (default)
  per-trade notional = $10 (hardcoded)
  stop-loss = -2% of entry, take-profit = +5% of entry
  per-strategy cap = 30% capital (with $10/trade and 1 symbol = never binding)
  max concurrent positions = 10 (with 3 SOL strategies = max 3)

Metrics use fixed-notional accounting: portfolio equity moves only when trades close,
PnL = notional * net_ret. This is the *real* paper-trading model, not all-in compounding.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from strategies import simple

FEE = 0.001
SLIP = 0.0005
NOTIONAL = 10.0
SL = 0.02
TP = 0.05


def simulate_trades(df: pd.DataFrame, entries: pd.Series, exits: pd.Series,
                    fee: float = FEE, slip: float = SLIP,
                    sl: float = SL, tp: float = TP,
                    notional: float = NOTIONAL) -> list[dict]:
    o = df['open'].to_numpy(float); h = df['high'].to_numpy(float)
    lo = df['low'].to_numpy(float); c = df['close'].to_numpy(float)
    ts = pd.to_datetime(df['ts']).to_numpy()
    e_in = entries.fillna(False).to_numpy(bool)
    e_out = exits.fillna(False).to_numpy(bool)
    n = len(df)
    trades = []
    in_pos = False
    entry_fill = stop = target = entry_ts = None
    i = 0
    while i < n:
        if not in_pos:
            if e_in[i] and i + 1 < n:
                eb = i + 1
                entry_fill = o[eb] * (1 + slip)
                stop = entry_fill * (1 - sl)
                target = entry_fill * (1 + tp)
                entry_ts = ts[eb]
                in_pos = True
                if lo[eb] <= stop:
                    _close_trade(trades, entry_ts, ts[eb], entry_fill, stop, fee, notional)
                    in_pos = False
                elif h[eb] >= target:
                    _close_trade(trades, entry_ts, ts[eb], entry_fill, target, fee, notional)
                    in_pos = False
                i = eb + 1
            else:
                i += 1
        else:
            exit_px = None
            if lo[i] <= stop:
                exit_px = stop
            elif h[i] >= target:
                exit_px = target
            if exit_px is not None:
                _close_trade(trades, entry_ts, ts[i], entry_fill, exit_px, fee, notional)
                in_pos = False
                i += 1
            elif e_out[i] and i + 1 < n:
                _close_trade(trades, entry_ts, ts[i+1], entry_fill, o[i+1]*(1-slip), fee, notional)
                in_pos = False
                i += 2
            else:
                i += 1
    if in_pos:
        _close_trade(trades, entry_ts, ts[-1], entry_fill, c[-1], fee, notional)
    return trades


def _close_trade(trades, entry_ts, exit_ts, entry_px, exit_px, fee, notional):
    gross = exit_px / entry_px - 1.0
    net = (1 + gross) * (1 - fee) * (1 - fee) - 1.0
    trades.append({'entry_ts': pd.Timestamp(entry_ts), 'exit_ts': pd.Timestamp(exit_ts),
                   'entry_px': float(entry_px), 'exit_px': float(exit_px),
                   'gross_ret': float(gross), 'net_ret': float(net),
                   'pnl_usd': float(notional * net),
                   'hold_h': float((pd.Timestamp(exit_ts) - pd.Timestamp(entry_ts)) / np.timedelta64(1, 'h'))})


def portfolio_metrics(trades: list[dict], capital: float = 500.0) -> dict:
    if not trades:
        return {'sharpe': 0.0, 'dd': 0.0, 'return': 0.0, 'n_trades': 0, 'total_pnl': 0.0, 'win_rate': 0.0}
    tdf = pd.DataFrame(trades)
    tdf['day'] = pd.to_datetime(tdf['exit_ts']).dt.date
    daily_pnl = tdf.groupby('day')['pnl_usd'].sum().sort_index()
    full = pd.date_range(min(daily_pnl.index), max(daily_pnl.index), freq='D').date
    daily_pnl = daily_pnl.reindex(full, fill_value=0.0)
    equity = capital + daily_pnl.cumsum().values
    daily_ret = daily_pnl.values / capital
    running = np.maximum.accumulate(equity)
    dd = float(-((equity / running) - 1.0).min())
    sharpe = float(daily_ret.mean() / daily_ret.std() * np.sqrt(365)) if daily_ret.std() > 0 else 0.0
    return {'sharpe': round(sharpe, 3), 'dd': round(dd, 4),
            'return': round(float(equity[-1] / capital - 1.0), 4),
            'n_trades': len(tdf), 'total_pnl': round(float(daily_pnl.sum()), 2),
            'win_rate': round(float((tdf['net_ret'] > 0).mean()), 3)}


def build_portfolio(strategies: list[dict], data_bull: dict, data_bear: dict,
                    capital: float = 500.0) -> dict:
    out = {'capital': capital, 'notional': NOTIONAL, 'sl': SL, 'tp': TP}
    for era, data in [('bull', data_bull), ('bear', data_bear)]:
        trades = []
        per_strat = {}
        for s in strategies:
            df = data.get(s['symbol'])
            if df is None or len(df) < 200:
                continue
            e, x = simple.REGISTRY[s['strategy']](df, **s['params'])
            t = simulate_trades(df, e, x)
            for tr in t:
                tr['strategy'] = s['strategy']
                tr['symbol'] = s['symbol']
            per_strat[s['strategy']] = portfolio_metrics(t, capital)
            trades += t
        m = portfolio_metrics(trades, capital)
        out[f'portfolio_{era}'] = m
        out[f'per_strategy_{era}'] = per_strat
    return out
