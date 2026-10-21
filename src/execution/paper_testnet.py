"""Paper trading runner for top-3 strategies.

Paper-only: real market data, fake fills simulated locally. NO API KEYS needed.
State persists in SQLite (state/paper.db). Journal appends to journal/paper_journal.jsonl.

Usage:
  python3 -m src.execution.paper_testnet --once       # single cycle (for testing)
  python3 -m src.execution.paper_testnet              # hourly loop

Fill model: entry/exit at CLOSE of signal bar (paper simplification),
fee 10 bps per side, $10 notional per position.
"""
from __future__ import annotations
import argparse, asyncio, json, sqlite3, sys
from datetime import datetime, timezone
from pathlib import Path

import ccxt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from strategies import simple

STATE_DB = ROOT / 'state' / 'paper.db'
JOURNAL = ROOT / 'journal' / 'paper_journal.jsonl'
TOP3 = ROOT / 'data' / 'top3.json'

NOTIONAL_USD = 10.0
FEE = 0.001  # 10 bps per side
CYCLE_SECONDS = 60
BARS_NEEDED = 200
TIMEFRAME = '1h'


def _symbol_ccxt(sym: str) -> str:
    # 'SOL-USDT' -> 'SOL/USDT'
    return sym.replace('-', '/')


def _init_db() -> sqlite3.Connection:
    STATE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(STATE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy TEXT, symbol TEXT, entry_ts TEXT, entry_price REAL,
            qty REAL, fee_entry REAL, status TEXT DEFAULT 'open'
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy TEXT, symbol TEXT, entry_ts TEXT, exit_ts TEXT,
            entry_price REAL, exit_price REAL, qty REAL,
            fee_entry REAL, fee_exit REAL, gross_ret REAL, net_ret REAL, pnl_usd REAL
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS last_bar (
            symbol TEXT PRIMARY KEY, last_ts TEXT
        )""")
    conn.commit()
    return conn


def _load_top3() -> list[dict]:
    if not TOP3.exists():
        raise SystemExit(f"missing {TOP3} — run src/backtest/grid.py + top3 selection first")
    data = json.loads(TOP3.read_text())
    return data['top3']


def _journal(rec: dict) -> None:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open('a') as f:
        f.write(json.dumps(rec, default=str) + '\n')


def _get_open_position(conn, strategy: str, symbol: str):
    return conn.execute(
        "SELECT id, entry_ts, entry_price, qty, fee_entry FROM positions "
        "WHERE strategy=? AND symbol=? AND status='open'",
        (strategy, symbol)).fetchone()


def _fetch_closed_bars(exchange, ccxt_symbol: str) -> pd.DataFrame:
    raw = exchange.fetch_ohlcv(ccxt_symbol, TIMEFRAME, limit=BARS_NEEDED)
    df = pd.DataFrame(raw, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
    df = df.sort_values('ts').reset_index(drop=True)
    # drop the still-forming last bar
    return df.iloc[:-1].reset_index(drop=True)


def one_cycle() -> None:
    conn = _init_db()
    top3 = _load_top3()
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
    exchange.set_sandbox_mode(True)  # testnet endpoints (for future real test orders)

    now = datetime.now(timezone.utc).isoformat()
    print(f"[cycle] {now}")
    summary = []

    # Group top-3 by symbol to reuse the fetch per symbol
    by_symbol: dict[str, list[dict]] = {}
    for t in top3:
        by_symbol.setdefault(t['symbol'], []).append(t)

    for sym, strats in by_symbol.items():
        ccxt_sym = _symbol_ccxt(sym)
        try:
            df = _fetch_closed_bars(exchange, ccxt_sym)
        except Exception as e:
            print(f"  {sym} fetch FAIL: {type(e).__name__}: {str(e)[:120]}")
            continue
        last_ts = str(df['ts'].iloc[-1])
        row = conn.execute("SELECT last_ts FROM last_bar WHERE symbol=?", (sym,)).fetchone()
        is_new_bar = (row is None) or (row[0] != last_ts)
        print(f"  {sym}: {len(df)} closed bars, last_ts={last_ts} new_bar={is_new_bar}")

        for s in strats:
            name, params = s['strategy'], s['params']
            fn = simple.REGISTRY[name]
            entries, exits = fn(df, **params)
            e_now = bool(entries.iloc[-1])
            x_now = bool(exits.iloc[-1])
            close_now = float(df['close'].iloc[-1])

            pos = _get_open_position(conn, name, sym)
            if pos and x_now:
                pos_id, entry_ts, entry_price, qty, fee_entry = pos
                gross = close_now / entry_price - 1.0
                net = (1.0 + gross) * (1.0 - FEE) * (1.0 - FEE) - 1.0
                fee_exit = close_now * qty * FEE
                pnl_usd = (close_now - entry_price) * qty - (fee_entry + fee_exit)
                conn.execute("INSERT INTO trades(strategy,symbol,entry_ts,exit_ts,entry_price,"
                             "exit_price,qty,fee_entry,fee_exit,gross_ret,net_ret,pnl_usd) "
                             "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                             (name, sym, entry_ts, last_ts, entry_price, close_now, qty,
                              fee_entry, fee_exit, gross, net, pnl_usd))
                conn.execute("UPDATE positions SET status='closed' WHERE id=?", (pos_id,))
                _journal({'event': 'exit', 'ts': last_ts, 'strategy': name, 'symbol': sym,
                          'side': 'long', 'exit_price': close_now, 'qty': qty,
                          'gross_ret': gross, 'net_ret': net, 'pnl_usd': pnl_usd,
                          'fee_exit': fee_exit, 'notional': NOTIONAL_USD})
                summary.append(f"EXIT  {name}/{sym} @ {close_now:.4f} net={net:+.4%} pnl=${pnl_usd:+.4f}")
            elif (not pos) and e_now:
                qty = NOTIONAL_USD / close_now
                fee_entry = NOTIONAL_USD * FEE
                conn.execute("INSERT INTO positions(strategy,symbol,entry_ts,entry_price,qty,fee_entry,status) "
                             "VALUES(?,?,?,?,?,?,'open')",
                             (name, sym, last_ts, close_now, qty, fee_entry))
                _journal({'event': 'entry', 'ts': last_ts, 'strategy': name, 'symbol': sym,
                          'side': 'long', 'entry_price': close_now, 'qty': qty,
                          'fee': fee_entry, 'notional': NOTIONAL_USD, 'status': 'open'})
                summary.append(f"ENTRY {name}/{sym} @ {close_now:.4f} qty={qty:.6f} notional=${NOTIONAL_USD}")
            else:
                summary.append(f"hold  {name}/{sym} pos={'yes' if pos else 'no'} "
                               f"e={int(e_now)} x={int(x_now)}")

        conn.execute("INSERT INTO last_bar(symbol,last_ts) VALUES(?,?) "
                     "ON CONFLICT(symbol) DO UPDATE SET last_ts=excluded.last_ts",
                     (sym, last_ts))
    conn.commit()
    conn.close()
    print("\n".join("  " + s for s in summary))


async def loop_forever():
    print(f"[paper] loop start, cycle={CYCLE_SECONDS}s, notional=${NOTIONAL_USD}, fee={FEE:.4%}/side")
    while True:
        try:
            one_cycle()
        except Exception as e:
            print(f"[cycle] ERROR {type(e).__name__}: {e}")
        await asyncio.sleep(CYCLE_SECONDS)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', action='store_true')
    args = ap.parse_args()
    if args.once:
        one_cycle()
    else:
        asyncio.run(loop_forever())
