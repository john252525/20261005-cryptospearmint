"""Delta-neutral portfolio accounting with SQLite persistence."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from ..strategies.funding_carry.config import FundingCarrySettings

SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL, exchange TEXT NOT NULL, direction TEXT NOT NULL,
    spot_qty REAL NOT NULL, perp_qty REAL NOT NULL,
    spot_entry REAL NOT NULL, perp_entry REAL NOT NULL,
    entry_basis_bps REAL NOT NULL, entry_funding_bps REAL NOT NULL DEFAULT 0.0,
    notional_usd REAL NOT NULL, opened_ts TEXT NOT NULL, closed_ts TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    realized_pnl REAL NOT NULL DEFAULT 0.0,
    funding_pnl REAL NOT NULL DEFAULT 0.0,
    fees_paid REAL NOT NULL DEFAULT 0.0);
CREATE INDEX IF NOT EXISTS idx_positions_open ON positions(status, symbol, exchange);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL, symbol TEXT NOT NULL, venue TEXT NOT NULL,
    leg TEXT NOT NULL, side TEXT NOT NULL, qty REAL NOT NULL, price REAL,
    order_id TEXT, fee REAL NOT NULL DEFAULT 0.0, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS funding_events (
    ts TEXT NOT NULL, symbol TEXT NOT NULL, position_id INTEGER,
    funding_rate REAL NOT NULL, notional_usd REAL NOT NULL, income_usd REAL NOT NULL);
CREATE TABLE IF NOT EXISTS pnl_snapshots (
    ts TEXT NOT NULL, nav REAL NOT NULL, realized REAL NOT NULL,
    unrealized REAL NOT NULL, funding_accrued REAL NOT NULL,
    delta_usd REAL NOT NULL, delta_bps_nav REAL NOT NULL,
    basis_usd REAL NOT NULL, basis_bps REAL NOT NULL);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def _iso(ts=None):
    return (ts or datetime.now(timezone.utc)).isoformat()


class DeltaNeutralPortfolio:
    def __init__(self, db_path: str, settings: FundingCarrySettings) -> None:
        self.s = settings; self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._init_meta(settings.max_pos_per_symbol_usd * max(1, len(settings.symbols)))

    @contextmanager
    def tx(self):
        try:
            yield self._conn; self._conn.commit()
        except Exception:
            self._conn.rollback(); raise

    def close(self):
        self._conn.close()

    def _init_meta(self, capital):
        with self.tx() as c:
            c.execute("INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)",
                      ("capital_usd", repr(float(capital))))
            c.execute("INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)",
                      ("realized_pnl", "0.0"))
            c.execute("INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)",
                      ("funding_accrued", "0.0"))

    def _meta(self, key):
        r = self._conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return float(r["value"]) if r else 0.0

    def _set_meta(self, key, value):
        with self.tx() as c:
            c.execute("INSERT INTO meta(key, value) VALUES (?, ?) "
                      "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                      (key, repr(float(value))))

    @property
    def capital(self):
        return self._meta("capital_usd")

    @property
    def realized_pnl(self):
        return self._meta("realized_pnl")

    @property
    def funding_accrued(self):
        return self._meta("funding_accrued")

    def open_positions(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM positions WHERE status='open' ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def has_open(self, symbol, exchange) -> bool:
        r = self._conn.execute(
            "SELECT 1 FROM positions WHERE status='open' AND symbol=? AND exchange=? LIMIT 1",
            (symbol, exchange)).fetchone()
        return r is not None

    def open_position(self, symbol, exchange, direction, spot_qty, perp_qty,
                      spot_entry, perp_entry, entry_funding_bps, notional_usd,
                      ts=None) -> int:
        basis_bps = (perp_entry - spot_entry) / spot_entry * 1e4
        with self.tx() as c:
            cur = c.execute(
                """INSERT INTO positions
                   (symbol, exchange, direction, spot_qty, perp_qty, spot_entry,
                    perp_entry, entry_basis_bps, entry_funding_bps, notional_usd,
                    opened_ts, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,'open')""",
                (symbol, exchange, direction, spot_qty, perp_qty, spot_entry,
                 perp_entry, basis_bps, entry_funding_bps, notional_usd, _iso(ts)))
            return int(cur.lastrowid)

    def close_position(self, position_id, spot_exit, perp_exit, fees=0.0, ts=None) -> float:
        r = self._conn.execute("SELECT * FROM positions WHERE id=?",
                               (position_id,)).fetchone()
        if r is None or r["status"] != "open":
            return 0.0
        pnl = (r["spot_qty"] * (spot_exit - r["spot_entry"])
               + r["perp_qty"] * (perp_exit - r["perp_entry"]) - fees)
        with self.tx() as c:
            c.execute("""UPDATE positions SET status='closed', closed_ts=?,
                        realized_pnl=?, fees_paid=fees_paid+? WHERE id=?""",
                      (_iso(ts), pnl, fees, position_id))
        self._set_meta("realized_pnl", self.realized_pnl + pnl)
        return pnl

    def record_order(self, ts, symbol, venue, leg, side, qty, price,
                     order_id, fee, status) -> None:
        with self.tx() as c:
            c.execute("""INSERT INTO orders (ts, symbol, venue, leg, side, qty,
                        price, order_id, fee, status) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (_iso(ts), symbol, venue, leg, side, qty, price,
                       str(order_id) if order_id is not None else None, fee, status))

    @staticmethod
    def funding_income(direction, funding_rate, notional_usd) -> float:
        if direction == "long_spot_short_perp":
            return notional_usd * funding_rate
        if direction == "short_spot_long_perp":
            return -notional_usd * funding_rate
        return 0.0

    def accrue_funding(self, symbol, funding_rate, notional_usd,
                       position_id=None, ts=None) -> float:
        direction = "flat"
        if position_id is not None:
            r = self._conn.execute(
                "SELECT direction FROM positions WHERE id=?",
                (position_id,)).fetchone()
            if r:
                direction = r["direction"]
        else:
            r = self._conn.execute(
                "SELECT id, direction FROM positions WHERE status='open' AND symbol=? LIMIT 1",
                (symbol,)).fetchone()
            if r:
                position_id, direction = r["id"], r["direction"]
        income = self.funding_income(direction, funding_rate, notional_usd)
        with self.tx() as c:
            c.execute("""INSERT INTO funding_events (ts, symbol, position_id,
                        funding_rate, notional_usd, income_usd) VALUES (?,?,?,?,?,?)""",
                      (_iso(ts), symbol, position_id, funding_rate, notional_usd, income))
        self._set_meta("funding_accrued", self.funding_accrued + income)
        return income

    def mark_to_market(self, marks: dict[str, dict[str, float]]) -> dict:
        unrealized = delta_usd = basis_usd = notional_sum = 0.0
        for p in self.open_positions():
            mk = marks.get(p["symbol"])
            if not mk:
                continue
            sp = float(mk.get("spot", p["spot_entry"]))
            pp = float(mk.get("perp", p["perp_entry"]))
            unrealized += (p["spot_qty"] * (sp - p["spot_entry"])
                           + p["perp_qty"] * (pp - p["perp_entry"]))
            delta_usd += p["spot_qty"] * sp + p["perp_qty"] * pp
            bb = (pp - sp) / sp * 1e4
            basis_usd += p["notional_usd"] * bb / 1e4
            notional_sum += p["notional_usd"]
        nav = self.capital + self.realized_pnl + self.funding_accrued + unrealized
        return {"nav": nav, "realized": self.realized_pnl,
                "unrealized": unrealized, "funding_accrued": self.funding_accrued,
                "delta_usd": delta_usd,
                "delta_bps_nav": (delta_usd / nav * 1e4) if nav else 0.0,
                "basis_usd": basis_usd,
                "basis_bps": (basis_usd / notional_sum * 1e4) if notional_sum else 0.0,
                "open_positions": len(self.open_positions())}

    def snapshot(self, marks, ts=None) -> dict:
        m = self.mark_to_market(marks)
        with self.tx() as c:
            c.execute("""INSERT INTO pnl_snapshots (ts, nav, realized, unrealized,
                        funding_accrued, delta_usd, delta_bps_nav, basis_usd, basis_bps)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                      (_iso(ts), m["nav"], m["realized"], m["unrealized"],
                       m["funding_accrued"], m["delta_usd"], m["delta_bps_nav"],
                       m["basis_usd"], m["basis_bps"]))
        return m

    def recover(self) -> list[dict]:
        return self.open_positions()
