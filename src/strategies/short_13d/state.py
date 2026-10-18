import sqlite3
from pathlib import Path

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
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_open ON paper_positions(status, ticker);
'''


def init_db(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def insert_position(conn: sqlite3.Connection, rec: dict) -> int:
    conn.execute(
        '''INSERT INTO paper_positions
        (ticker, filing_date, entry_date, entry_price, shares, notional_usd,
         target_exit_date, borrow_rate, status, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (rec['ticker'], rec['filing_date'], rec['entry_date'], rec['entry_price'],
         rec['shares'], rec['notional_usd'], rec['target_exit_date'],
         rec['borrow_rate'], 'OPEN', rec['created_at']))
    conn.commit()
    return conn.execute('SELECT last_insert_rowid()').fetchone()[0]
