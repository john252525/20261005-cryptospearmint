"""SQLite storage for the SEC event pipeline.

Schema follows the brief (event_filings / scrape_runs) and keeps the
idempotency guarantee via PRIMARY KEY (accession_no, primary_document).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS event_filings (
    accession_no     TEXT NOT NULL,
    primary_document TEXT NOT NULL,
    filing_type      TEXT NOT NULL,
    cik              TEXT NOT NULL,
    ticker           TEXT,
    company_name     TEXT,
    filing_date      TEXT NOT NULL,
    event_type       TEXT,
    summary_text     TEXT,
    url_primary      TEXT,
    scanned_at       TEXT NOT NULL,
    PRIMARY KEY (accession_no, primary_document)
);
CREATE INDEX IF NOT EXISTS idx_filing_type_date
    ON event_filings(filing_type, filing_date);
CREATE INDEX IF NOT EXISTS idx_event_type ON event_filings(event_type);
CREATE INDEX IF NOT EXISTS idx_cik ON event_filings(cik);

CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id     TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    query      TEXT,
    forms      TEXT,
    start_date TEXT,
    end_date   TEXT,
    fetched    INTEGER DEFAULT 0,
    inserted   INTEGER DEFAULT 0,
    duplicates INTEGER DEFAULT 0,
    errors     INTEGER DEFAULT 0
);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Storage:
    """Thin wrapper around a SQLite file."""

    def __init__(self, db_path: str = "data/event_filings.db") -> None:
        self.db_path = db_path
        parent = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(parent, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -- writes ------------------------------------------------------------

    def insert_filing(self, rec: Dict[str, Any]) -> bool:
        """Insert one filing; return True if new, False if duplicate."""
        row = {
            "accession_no": rec["accession_no"],
            "primary_document": rec["primary_document"],
            "filing_type": rec.get("filing_type") or "",
            "cik": rec.get("cik") or "",
            "ticker": rec.get("ticker"),
            "company_name": rec.get("company_name"),
            "filing_date": rec.get("filing_date") or "",
            "event_type": rec.get("event_type"),
            "summary_text": rec.get("summary_text"),
            "url_primary": rec.get("url_primary"),
            "scanned_at": rec.get("scanned_at") or _utcnow(),
        }
        sql = (
            "INSERT OR IGNORE INTO event_filings "
            "(accession_no, primary_document, filing_type, cik, ticker, "
            " company_name, filing_date, event_type, summary_text, url_primary,"
            " scanned_at) VALUES "
            "(:accession_no, :primary_document, :filing_type, :cik, :ticker,"
            " :company_name, :filing_date, :event_type, :summary_text,"
            " :url_primary, :scanned_at)"
        )
        cur = self._conn.execute(sql, row)
        self._conn.commit()
        return cur.rowcount > 0

    def start_run(
        self,
        query: str,
        forms: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        run_id = uuid.uuid4().hex
        self._conn.execute(
            "INSERT INTO scrape_runs "
            "(run_id, started_at, query, forms, start_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                run_id,
                _utcnow(),
                query,
                ",".join(forms or []),
                start_date,
                end_date,
            ),
        )
        self._conn.commit()
        return run_id

    def finish_run(
        self,
        run_id: str,
        fetched: int,
        inserted: int,
        duplicates: int,
        errors: int,
    ) -> None:
        self._conn.execute(
            "UPDATE scrape_runs SET finished_at=?, fetched=?, inserted=?, "
            "duplicates=?, errors=? WHERE run_id=?",
            (_utcnow(), fetched, inserted, duplicates, errors, run_id),
        )
        self._conn.commit()

    # -- reads -------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        by_type = self._conn.execute(
            "SELECT filing_type, COUNT(*) n FROM event_filings "
            "GROUP BY filing_type ORDER BY n DESC"
        ).fetchall()
        by_event = self._conn.execute(
            "SELECT COALESCE(event_type,'NULL') event_type, COUNT(*) n "
            "FROM event_filings GROUP BY event_type ORDER BY n DESC"
        ).fetchall()
        total = self._conn.execute(
            "SELECT COUNT(*) FROM event_filings"
        ).fetchone()[0]
        unique_cik = self._conn.execute(
            "SELECT COUNT(DISTINCT cik) FROM event_filings"
        ).fetchone()[0]
        runs = self._conn.execute(
            "SELECT COUNT(*) FROM scrape_runs"
        ).fetchone()[0]
        return {
            "db_path": self.db_path,
            "total_filings": total,
            "unique_ciks": unique_cik,
            "scrape_runs": runs,
            "by_filing_type": {r["filing_type"]: r["n"] for r in by_type},
            "by_event_type": {r["event_type"]: r["n"] for r in by_event},
        }

    def last_scanned_at(self, filing_type: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT MAX(scanned_at) FROM event_filings WHERE filing_type=?",
            (filing_type,),
        ).fetchone()
        return row[0] if row and row[0] else None

    def dump_stats_json(self) -> str:
        return json.dumps(self.stats(), indent=2, sort_keys=True)
