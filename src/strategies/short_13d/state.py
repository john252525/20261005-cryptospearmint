import logging
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA = '''
CREATE TABLE IF NOT EXISTS paper_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    filing_date TEXT NOT NULL,
    entry_date TEXT NOT NULL,
    entry_price REAL NOT NULL,
    shares INTEGER NOT NULL,
    notional_usd REAL NOT NULL,
    target_exit_date TEXT,
    exit_date TEXT,
    exit_price REAL,
    realized_pnl_usd REAL,
    borrow_rate REAL NOT NULL,
    borrow_cost_usd REAL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    created_at TEXT NOT NULL,
    UNIQUE(ticker, filing_date, borrow_rate)
);
CREATE INDEX IF NOT EXISTS idx_open ON paper_positions(status, ticker);
CREATE UNIQUE INDEX IF NOT EXISTS uq_positions_key
    ON paper_positions(ticker, filing_date, borrow_rate);
'''


def init_db(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    except sqlite3.IntegrityError as e:
        log.warning("unique index migration failed (existing dups?): %s", e)
    return conn


def insert_position(conn: sqlite3.Connection, rec: dict) -> int | None:
    """Insert if new; return new id, or None if (ticker, filing_date, borrow_rate) exists."""
    cur = conn.execute(
        '''INSERT INTO paper_positions
        (ticker, filing_date, entry_date, entry_price, shares, notional_usd,
         target_exit_date, borrow_rate, status, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(ticker, filing_date, borrow_rate) DO NOTHING''',
        (rec['ticker'], rec['filing_date'], rec['entry_date'], rec['entry_price'],
         rec['shares'], rec['notional_usd'], rec['target_exit_date'],
         rec['borrow_rate'], 'OPEN', rec['created_at']))
    conn.commit()
    if cur.rowcount == 0:
        return None
    return cur.lastrowid
