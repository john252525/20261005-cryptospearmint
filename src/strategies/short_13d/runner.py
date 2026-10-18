import sqlite3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import yfinance as yf
from .config import Short13DSettings
from .state import init_db, insert_position


def journal_append(path: str, rec: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a') as f:
        f.write(json.dumps(rec, default=str) + '\n')


def run_snapshot() -> dict:
    s = Short13DSettings()
    scraper = sqlite3.connect(s.scraper_db)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=s.lookback_days)).date().isoformat()
    rows = scraper.execute("""
        SELECT ticker, filing_date FROM event_filings
        WHERE filing_type LIKE '%13D%'
          AND ticker IS NOT NULL AND ticker != ''
          AND length(ticker) BETWEEN 1 AND 5
          AND ticker NOT LIKE '%-WT%' AND ticker NOT LIKE '%.%'
          AND filing_date >= ?
        GROUP BY ticker, filing_date
    """, (cutoff,)).fetchall()
    print(f'filings since {cutoff}: {len(rows)}')
    if not rows:
        print('NO FILINGS IN WINDOW')
        return {'opened': 0, 'skipped': 0, 'duplicates': 0, 'reason': 'no_filings'}

    conn = init_db(s.state_db)
    opened = 0
    skipped = 0
    duplicates = 0
    tickers = list(set(r[0] for r in rows))
    if len(tickers) > 100:
        tickers = tickers[:100]

    try:
        bulk = yf.download(tickers, start='2026-09-01', end='2026-11-15',
                           progress=False, auto_adjust=True, group_by='ticker')
    except Exception as e:
        print('bulk error', str(e)[:200])
        return {'opened': 0, 'skipped': 0, 'duplicates': 0, 'reason': f'bulk_error: {e}'}

    for tk, fdate in rows:
        if tk not in tickers:
            skipped += 1
            continue
        try:
            if tk not in bulk.columns.get_level_values(0):
                skipped += 1
                continue
            close = bulk[tk]['Close'].dropna()
            vol = bulk[tk]['Volume'].dropna()
            if len(close) < 21:
                skipped += 1
                continue
            fd_ts = pd.Timestamp(fdate)
            after = close.index[close.index > fd_ts]
            if len(after) < 1:
                skipped += 1
                continue
            entry_date = after[0]
            entry_idx = close.index.get_loc(entry_date)
            entry_price = float(close.iloc[entry_idx])
            if entry_price <= 0 or entry_price > 500:
                skipped += 1
                continue
            vol_win = vol.loc[:entry_date].tail(20)
            px_win = close.loc[:entry_date].tail(20)
            adv_20d = float((vol_win * px_win).mean()) if len(vol_win) > 0 else 0.0
            if adv_20d < s.min_adv_usd:
                skipped += 1
                continue
            shares = int(s.notional_per_trade_usd / entry_price)
            if shares < 1:
                skipped += 1
                continue
            target_exit = (pd.Timestamp(entry_date) + pd.tseries.offsets.BDay(s.holding_days)).date().isoformat()
            for br in s.borrow_rates:
                pid = insert_position(conn, {
                    'ticker': tk, 'filing_date': fdate,
                    'entry_date': str(entry_date.date()),
                    'entry_price': round(entry_price, 2),
                    'shares': shares,
                    'notional_usd': round(shares * entry_price, 2),
                    'target_exit_date': target_exit,
                    'borrow_rate': br,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                })
                if pid is None:
                    duplicates += 1
                    continue
                journal_append(s.journal_path, {
                    'event': 'OPEN', 'pid': pid, 'ticker': tk,
                    'filing_date': fdate,
                    'entry_date': str(entry_date.date()),
                    'entry_price': round(entry_price, 2),
                    'shares': shares, 'borrow_rate': br,
                    'adv_usd': round(adv_20d, 0),
                })
                opened += 1
        except Exception as e:
            print('err', tk, str(e)[:80])
            skipped += 1

    conn.close()
    print(f'DONE opened={opened} duplicates={duplicates} skipped={skipped}')
    return {'opened': opened, 'duplicates': duplicates, 'skipped': skipped, 'filings': len(rows)}


if __name__ == '__main__':
    result = run_snapshot()
    print(json.dumps(result, indent=2))
