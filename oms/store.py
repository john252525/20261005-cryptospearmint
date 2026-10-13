"""SQLite event store + materialized order-state cache."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from oms.events import Event, deserialize, serialize


DDL = """
CREATE TABLE IF NOT EXISTS order_events (
    seq             INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        TEXT    NOT NULL UNIQUE,
    client_order_id TEXT    NOT NULL,
    event_type      TEXT    NOT NULL,
    ts              TEXT    NOT NULL,
    payload_json    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_order_events_coid
    ON order_events(client_order_id, seq);

CREATE TABLE IF NOT EXISTS orders_state (
    client_order_id TEXT PRIMARY KEY,
    symbol          TEXT,
    side            TEXT,
    qty             REAL,
    filled_qty      REAL NOT NULL DEFAULT 0,
    avg_fill_price  REAL NOT NULL DEFAULT 0,
    broker_order_id TEXT,
    status          TEXT NOT NULL,
    last_event_ts   TEXT NOT NULL,
    reject_reason   TEXT
);
CREATE INDEX IF NOT EXISTS ix_orders_state_status ON orders_state(status);
"""

_COLS = ("client_order_id", "symbol", "side", "qty",
         "filled_qty", "avg_fill_price", "broker_order_id",
         "status", "last_event_ts", "reject_reason")


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or datetime.now(timezone.utc)).isoformat()


class EventStore:
    def __init__(self, path: str | Path = "risk.db") -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(DDL)
        self._conn.commit()

    # ---- events -----------------------------------------------------
    def append(self, event: Event) -> bool:
        """Append event. Returns False if event_id already present."""
        try:
            self._conn.execute(
                "INSERT INTO order_events "
                "(event_id, client_order_id, event_type, ts, payload_json) "
                "VALUES (?,?,?,?,?)",
                (event.event_id, event.client_order_id,
                 event.event_type, _iso(event.ts), serialize(event)))
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def load_events(self, client_order_id: str) -> list[Event]:
        return [deserialize(r[0]) for r in self._conn.execute(
            "SELECT payload_json FROM order_events "
            "WHERE client_order_id = ? ORDER BY seq", (client_order_id,))]

    def all_events(self) -> Iterator[Event]:
        for r in self._conn.execute(
                "SELECT payload_json FROM order_events ORDER BY seq"):
            yield deserialize(r[0])

    def has_event(self, event_id: str) -> bool:
        return self._conn.execute(
            "SELECT 1 FROM order_events WHERE event_id = ?",
            (event_id,)).fetchone() is not None

    # ---- materialized state -----------------------------------------
    def upsert_state(self, state: dict) -> None:
        vals = [state.get(c) for c in _COLS]
        assignments = ", ".join(f"{c}=excluded.{c}" for c in _COLS[1:])
        self._conn.execute(
            f"INSERT INTO orders_state ({','.join(_COLS)}) "
            f"VALUES ({','.join('?' * len(_COLS))}) "
            f"ON CONFLICT(client_order_id) DO UPDATE SET {assignments}",
            vals)
        self._conn.commit()

    def load_state(self, client_order_id: str) -> Optional[dict]:
        self._conn.row_factory = sqlite3.Row
        try:
            r = self._conn.execute(
                "SELECT * FROM orders_state WHERE client_order_id = ?",
                (client_order_id,)).fetchone()
            return dict(r) if r else None
        finally:
            self._conn.row_factory = None

    def all_states(self) -> list[dict]:
        self._conn.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in self._conn.execute(
                "SELECT * FROM orders_state ORDER BY last_event_ts")]
        finally:
            self._conn.row_factory = None

    def close(self) -> None:
        self._conn.close()
