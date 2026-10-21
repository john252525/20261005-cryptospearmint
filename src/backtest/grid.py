"""Grid search over strategy params x symbols. Saves CSV at data/backtest_grid.csv."""
from __future__ import annotations
import itertools, json, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from strategies import simple
from backtest.runner import run

DATA = ROOT / 'data'
OUT = DATA / 'backtest_grid.csv'
START = pd.Timestamp('2022-01-01', tz='UTC')
END = pd.Timestamp('2024-12-31 23:00:00', tz='UTC')

SYMBOLS = ['BTC-USDT_1h.parquet', 'ETH-USDT_1h.parquet', 'SOL-USDT_1h.parquet']

# Parameter grids (empty dict => default params, 1 run)
GRIDS = {
    'sma_cross':      [{'fast': f, 'slow': s} for f, s in [(10,40),(10,50),(10,100),(20,40),(20,50),(20,100),(30,40),(30,50),(30,100)]],
    'ema_cross':      [{'fast': f, 'slow': s} for f, s in [(12,26),(9,21),(20,50)]],
    'rsi_obos':       [{'n': 14, 'low': l, 'high': h} for l in [20,25,30,35] for h in [65,70,75,80]],
    'bb_bounce':      [{'n': 20, 'k': k} for k in [1.5, 2.0, 2.5]],
    'macd_cross':     [{}],
    'momentum':       [{'n': n, 'thr': t} for n in [5,10,20] for t in [1.0,2.0,3.0]],
    'mean_rev':       [{'n': 20, 'k': k} for k in [1.5, 2.0, 2.5, 3.0]],
    'donchian_break': [{'n': n} for n in [10,20,40]],
    'rsi_bb_combo':   [{}],
    'obv_divergence': [{'n': n} for n in [10,20,40]],
}

dfs = {f: pd.read_parquet(DATA / f) for f in SYMBOLS}
for f in dfs:
    dfs[f] = dfs[f][(dfs[f]['ts'] >= START) & (dfs[f]['ts'] <= END)].reset_index(drop=True)
    assert len(dfs[f]) > 20000, f"{f} short: {len(dfs[f])}"

rows = []
total_runs = 0
for strat_name, param_list in GRIDS.items():
    fn = simple.REGISTRY[strat_name]
    for params in param_list:
        for sym_file in SYMBOLS:
            df = dfs[sym_file]
            try:
                entries, exits = fn(df, **params)
            except TypeError as e:
                print(f"SKIP {strat_name} {params}: {e}"); continue
            res = run(df, entries, exits)
            rows.append({
                'strategy': strat_name,
                'params': json.dumps(params, separators=(',', ':')),
                'symbol': sym_file.replace('_1h.parquet', ''),
                'total_return': round(res['total_return'], 6),
                'sharpe': round(res['sharpe'], 4),
                'max_dd': round(res['max_dd'], 6),
                'hit_rate': round(res['hit_rate'], 4),
                'trades': res['trades_count'],
                'fees_paid': round(res['fees_paid'], 6),
            })
            total_runs += 1

out = pd.DataFrame(rows).sort_values('sharpe', ascending=False).reset_index(drop=True)
out.to_csv(OUT, index=False)
print(f"\n=== {total_runs} runs, saved -> {OUT} ===")
print("\n=== TOP 15 by Sharpe ===")
with pd.option_context('display.max_rows', 20, 'display.width', 220, 'display.max_colwidth', 55):
    print(out.head(15).to_string(index=False))
