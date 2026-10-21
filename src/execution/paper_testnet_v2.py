"""Portfolio-aware paper runner v2.

Does NOT submit orders anywhere. Real market data via ccxt, fake fills locally.
Reads selection from data/robust_strategies.json.

Honest caveat: current robust_strategies.json is SOL-only, and the
portfolio backtest with SL/TP(-2%/+5%) and $10-notional failed the
Sharpe>0.8-in-both-eras gate. This runner STARTS DISARMED by default
(--armed required to write positions). Use it to smoke-test infrastructure
and to observe signals live, not to accrue a paper record until a robust
universe is found.
"""
from __future__ import annotations
import argparse, asyncio, json, sqlite3, sys, time
from datetime import datetime, timezone
from pathlib import Path
import ccxt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from strategies import simple

DB = ROOT / 'state' / 'paper_v2.db'
JOURNAL = ROOT / 'journal' / 'paper_v2.jsonl'
ROBUST_FILE = ROOT / 'data' / 'robust_strategies.json'

NOTIONAL = 10.0
FEE = 0.001
SL = 0.02
TP = 0.05
CAPITAL = 500.0
CYCLE = 300        # 5 min
BARS = 200
TIMEFRAME = '1h'


def _init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS positions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, strategy TEXT, symbol TEXT,
        entry_price REAL, entry_ts TEXT, notional REAL, qty REAL,
        stop REAL, target REAL, fee_entry REAL,
        status TEXT DEFAULT 'open', exit_price REAL, exit_ts TEXT,
        pnl REAL, fees REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS journal(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, event TEXT,
        strategy TEXT, symbol TEXT, notional REAL, pnl_cumulative REAL, note TEXT)""")
    c.commit()
    return c


def _cum_pnl(c):
    return float(c.execute("SELECT COALESCE(SUM(pnl),0) FROM positions WHERE status='closed'").fetchone()[0])


def _log(c, event, strategy='', symbol='', notional=0.0, note=''):
    cum = _cum_pnl(c)
    ts = datetime.now(timezone.utc).isoformat()
    c.execute("INSERT INTO journal(ts,event,strategy,symbol,notional,pnl_cumulative,note) VALUES(?,?,?,?,?,?,?)",
              (ts, event, strategy, symbol, notional, cum, note))
    c.commit()
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open('a') as f:
        f.write(json.dumps({'ts': ts, 'event': event, 'strategy': strategy, 'symbol': symbol,
                            'notional': notional, 'pnl_cumulative': round(cum, 4), 'note': note}) + '\n')
    return cum


def _load_selection():
    p = json.loads(ROBUST_FILE.read_text())
    return p['robust'], p.get('selection_mode', 'unknown')


def _fetch(ex, sym):
    raw = ex.fetch_ohlcv(sym.replace('-', '/'), TIMEFRAME, limit=BARS)
    df = pd.DataFrame(raw, columns=['ts','open','high','low','close','volume'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
    return df.sort_values('ts').reset_index(drop=True).iloc[:-1].reset_index(drop=True)


def one_cycle(armed: bool = False):
    c = _init_db()
    strategies, mode = _load_selection()
    ex = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
    ex.set_sandbox_mode(True)
    note_base = f"selection_mode={mode} armed={armed}"
    cum = _log(c, 'cycle_start', note=note_base)
    print(f"[{datetime.now(timezone.utc).isoformat()}] cycle_start cum=${cum:.4f} {note_base}")

    by_sym = {}
    for s in strategies:
        by_sym.setdefault(s['symbol'], []).append(s)

    for sym, strats in by_sym.items():
        try:
            df = _fetch(ex, sym)
        except Exception as e:
            _log(c, 'fetch_fail', symbol=sym, note=str(e)[:100])
            continue
        px = float(df['close'].iloc[-1]); ts = str(df['ts'].iloc[-1])

        # manage open positions
        for row in c.execute("SELECT id,strategy,entry_price,qty,stop,target,fee_entry FROM positions WHERE symbol=? AND status='open'", (sym,)).fetchall():
            pid, stg, ep, qty, stop, tgt, fee_e = row
            reason = None
            if px <= stop: reason = 'stop_hit'; exit_px = stop
            elif px >= tgt: reason = 'target_hit'; exit_px = tgt
            if reason:
                fee_x = exit_px * qty * FEE
                pnl = (exit_px - ep) * qty - fee_e - fee_x
                c.execute("UPDATE positions SET status='closed',exit_price=?,exit_ts=?,pnl=?,fees=? WHERE id=?",
                          (exit_px, ts, pnl, fee_e+fee_x, pid))
                c.commit()
                new_cum = _log(c, reason, stg, sym, NOTIONAL, f"exit={exit_px:.4f} pnl=${pnl:+.4f}")
                print(f"  CLOSE {stg}/{sym} {reason} px={exit_px:.4f} pnl=${pnl:+.4f} cum=${new_cum:+.4f}")

        # signal check
        for s in strats:
            fn = simple.REGISTRY[s['strategy']]
            e, x = fn(df, **s['params'])
            is_entry = bool(e.iloc[-1])
            is_exit = bool(x.iloc[-1])
            has_pos = c.execute("SELECT COUNT(*) FROM positions WHERE strategy=? AND symbol=? AND status='open'",
                                (s['strategy'], sym)).fetchone()[0] > 0
            tag = f"{s['strategy']}/{sym} e={int(is_entry)} x={int(is_exit)} pos={int(has_pos)}"
            if is_exit and has_pos:
                r = c.execute("SELECT id,entry_price,qty,fee_entry FROM positions WHERE strategy=? AND symbol=? AND status='open'",
                              (s['strategy'], sym)).fetchone()
                pid, ep, qty, fee_e = r
                fee_x = px * qty * FEE
                pnl = (px - ep) * qty - fee_e - fee_x
                c.execute("UPDATE positions SET status='closed',exit_price=?,exit_ts=?,pnl=?,fees=? WHERE id=?",
                          (px, ts, pnl, fee_e+fee_x, pid))
                c.commit()
                new_cum = _log(c, 'exit_signal', s['strategy'], sym, NOTIONAL, f"exit={px:.4f} pnl=${pnl:+.4f}")
                print(f"  EXIT_SIG {tag} pnl=${pnl:+.4f} cum=${new_cum:+.4f}")
            elif is_entry and not has_pos and armed:
                qty = NOTIONAL / px
                fee_e = NOTIONAL * FEE
                c.execute("INSERT INTO positions(strategy,symbol,entry_price,entry_ts,notional,qty,stop,target,fee_entry) "
                          "VALUES(?,?,?,?,?,?,?,?,?)",
                          (s['strategy'], sym, px, ts, NOTIONAL, qty, px*(1-SL), px*(1+TP), fee_e))
                c.commit()
                new_cum = _log(c, 'entry', s['strategy'], sym, NOTIONAL, f"px={px:.4f} stop={px*(1-SL):.4f} target={px*(1+TP):.4f}")
                print(f"  ENTRY {tag} px={px:.4f} cum=${new_cum:+.4f}")
            else:
                _log(c, 'observe', s['strategy'], sym, 0.0, tag)
                print(f"  observe {tag}")
    final = _log(c, 'cycle_end', note=f"cum=${_cum_pnl(c):.4f}")
    c.close()
    print(f"  cycle_end cum=${final:.4f}")


async def run_duration(sec, armed):
    t0 = time.time()
    while True:
        remaining = sec - (time.time() - t0)
        if remaining <= 0:
            break
        try:
            one_cycle(armed)
        except Exception as e:
            print(f"[cycle] ERR {type(e).__name__}: {e}")
        await asyncio.sleep(min(CYCLE, max(1, sec - (time.time() - t0))))


async def run_forever(armed):
    while True:
        try:
            one_cycle(armed)
        except Exception as e:
            print(f"[cycle] ERR {type(e).__name__}: {e}")
        await asyncio.sleep(CYCLE)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--duration', type=int, default=0)
    ap.add_argument('--armed', action='store_true', help='actually write paper positions')
    a = ap.parse_args()
    if a.once:
        one_cycle(a.armed)
    elif a.duration:
        asyncio.run(run_duration(a.duration, a.armed))
    else:
        asyncio.run(run_forever(a.armed))
