import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import yfinance as yf
from .config import Short13DSettings


def journal_append(path, rec):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a') as f:
        f.write(json.dumps(rec, default=str) + '\n')


def run_exit_snapshot():
    s = Short13DSettings()
    today = datetime.now(timezone.utc).date().isoformat()
    conn = sqlite3.connect(s.state_db)
    rows = conn.execute("""
        SELECT id, ticker, entry_date, entry_price, shares, borrow_rate,
               target_exit_date, filing_date
        FROM paper_positions
        WHERE status = 'OPEN' AND target_exit_date <= ?
    """, (today,)).fetchall()
    print(f'ready_to_exit: {len(rows)} (target <= {today})')
    if not rows:
        print('NOTHING TO EXIT')
        conn.close()
        return {'exited': 0, 'pending': 0}

    tickers = list(set(r[1] for r in rows))
    try:
        bulk = yf.download(tickers[:50], start='2026-09-01', end='2026-12-15',
                           progress=False, auto_adjust=True, group_by='ticker')
    except Exception as e:
        print('bulk error', str(e)[:200])
        conn.close()
        return {'exited': 0, 'pending': len(rows), 'error': str(e)}

    exited = 0
    for pid, tk, entry_date, entry_price, shares, br, target_exit, filing_date in rows:
        try:
            if tk not in bulk.columns.get_level_values(0):
                continue
            close = bulk[tk]['Close'].dropna()
            if len(close) == 0:
                continue
            target_ts = pd.Timestamp(target_exit)
            on_or_after = close.index[close.index >= target_ts]
            if len(on_or_after) == 0:
                continue
            exit_date = on_or_after[0]
            exit_price = float(close.loc[exit_date])
            if exit_price <= 0:
                continue
            short_pnl = shares * (entry_price - exit_price)
            days_held = (exit_date - pd.Timestamp(entry_date)).days
            borrow_cost = shares * entry_price * br * (days_held / 365.0)
            bid_ask_cost = shares * entry_price * (s.bid_ask_bps / 10000.0)
            net_pnl = short_pnl - borrow_cost - bid_ask_cost
            conn.execute(
                """UPDATE paper_positions SET
                    status='CLOSED', exit_date=?, exit_price=?,
                    realized_pnl_usd=?, borrow_cost_usd=?
                    WHERE id=?""",
                (str(exit_date.date()), round(exit_price, 2),
                 round(net_pnl, 2), round(borrow_cost, 2), pid))
            journal_append(s.journal_path, {
                'event': 'CLOSE', 'pid': pid, 'ticker': tk,
                'entry_date': entry_date, 'entry_price': entry_price,
                'exit_date': str(exit_date.date()), 'exit_price': round(exit_price, 2),
                'shares': shares, 'days_held': days_held,
                'short_pnl': round(short_pnl, 2),
                'borrow_cost': round(borrow_cost, 2),
                'bid_ask_cost': round(bid_ask_cost, 2),
                'net_pnl': round(net_pnl, 2),
                'borrow_rate': br,
            })
            exited += 1
        except Exception as e:
            continue
    conn.commit()
    conn.close()
    print(f'DONE exited={exited} of {len(rows)}')
    return {'exited': exited, 'pending': len(rows) - exited}


if __name__ == '__main__':
    result = run_exit_snapshot()
    print(json.dumps(result, indent=2))
