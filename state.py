"""SQLite persistence for the risk module: positions, orders, snapshots, kill-events."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from risk.structures import Order, Portfolio, Position, TriggerEvent

DDL = """
CREATE TABLE IF NOT EXISTS positions (
    ts              TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    qty             REAL NOT NULL,
    avg_price       REAL NOT NULL,
    last_price      REAL NOT NULL,
    notional        REAL NOT NULL,
    unrealized_pnl  REAL NOT NULL,
    PRIMARY KEY (ts, symbol)
);
CREATE TABLE IF NOT EXISTS orders (
    order_id    TEXT PRIMARY KEY,
    ts          TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL,
    qty         REAL NOT NULL,
    price       REAL NOT NULL,
    order_type  TEXT,
    status      TEXT NOT NULL,
    reason      TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_ts ON orders(ts);

CREATE TABLE IF NOT EXISTS pnl_snapshots (
    ts              TEXT PRIMARY KEY,
    nav             REAL NOT NULL,
    cash            REAL NOT NULL,
    gross_exposure  REAL NOT NULL,
    net_exposure    REAL NOT NULL,
    realized_pnl    REAL NOT NULL,
    unrealized_pnl  REAL NOT NULL,
    fees            REAL NOT NULL,
    daily_pnl       REAL NOT NULL,
    drawdown_pct    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS kill_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    level         INTEGER NOT NULL,
    reason        TEXT NOT NULL,
    metrics_json  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_kill_events_ts ON kill_events(ts);
"""

_MIGRATIONS = (
    ("pnl_snapshots", "peak_nav",         "REAL NOT NULL DEFAULT 0"),
    ("pnl_snapshots", "nav_start_of_day", "REAL NOT NULL DEFAULT 0"),
)


def _iso(dt=None) -> str:
    return (dt or datetime.now(timezone.utc)).isoformat()


class StateStore:
    def __init__(self, path: str | Path = "risk.db") -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.executescript(DDL)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        for table, col, decl in _MIGRATIONS:
            cols = {r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")}
            if col not in cols:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        self.conn.commit()

    # ---- writes -------------------------------------------------
    def save_positions(self, portfolio: Portfolio, ts=None) -> None:
        t = _iso(ts)
        self.conn.execute("DELETE FROM positions WHERE ts = ?", (t,))
        rows = [(t, p.symbol, p.qty, p.avg_price, p.mark, p.notional, p.unrealized_pnl)
                for p in portfolio.positions.values()]
        if rows:
            self.conn.executemany(
                "INSERT INTO positions VALUES (?,?,?,?,?,?,?)", rows)
        self.conn.commit()

    def save_order(self, order: Order, status: str, reason: str = "") -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?,?,?)",
            (order.order_id, _iso(order.ts), order.symbol, order.side.value,
             order.qty, order.price, order.order_type, status, reason))
        self.conn.commit()

    def save_snapshot(self, portfolio: Portfolio, ts=None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO pnl_snapshots "
            "(ts, nav, cash, gross_exposure, net_exposure, realized_pnl, "
            " unrealized_pnl, fees, daily_pnl, drawdown_pct, "
            " peak_nav, nav_start_of_day) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (_iso(ts), portfolio.nav, portfolio.cash,
             portfolio.gross_exposure, portfolio.net_exposure,
             portfolio.realized_pnl, portfolio.unrealized_pnl,
             portfolio.fees, portfolio.daily_pnl, portfolio.drawdown_pct,
             portfolio.peak_nav, portfolio.nav_start_of_day))
        self.conn.commit()

    def save_kill_event(self, ev: TriggerEvent) -> None:
        self.conn.execute(
            "INSERT INTO kill_events (ts, level, reason, metrics_json) VALUES (?,?,?,?)",
            (_iso(ev.ts), ev.level, ev.reason, json.dumps(ev.metrics, default=str)))
        self.conn.commit()

    # ---- reads --------------------------------------------------
    def load_last_snapshot(self) -> dict | None:
        cur = self.conn.execute(
            "SELECT ts, nav, cash, gross_exposure, net_exposure, realized_pnl, "
            "       unrealized_pnl, fees, daily_pnl, drawdown_pct, "
            "       peak_nav, nav_start_of_day "
            "FROM pnl_snapshots ORDER BY ts DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return None
        keys = ["ts", "nav", "cash", "gross_exposure", "net_exposure",
                "realized_pnl", "unrealized_pnl", "fees", "daily_pnl",
                "drawdown_pct", "peak_nav", "nav_start_of_day"]
        return dict(zip(keys, row))

    def restore_positions(self, ts: str) -> dict:
        out: dict = {}
        cur = self.conn.execute(
            "SELECT symbol, qty, avg_price, last_price FROM positions WHERE ts = ?",
            (ts,))
        for sym, qty, avg, last_px in cur:
            out[str(sym)] = Position(str(sym), float(qty), float(avg), float(last_px))
        return out

    def restore_portfolio(self) -> Portfolio | None:
        last = self.load_last_snapshot()
        if not last:
            return None
        p = Portfolio(cash=float(last["cash"]))
        p.realized_pnl = float(last["realized_pnl"])
        p.fees = float(last["fees"])
        p.positions = self.restore_positions(last["ts"])
        if not p.positions:
            r = self.conn.execute(
                "SELECT ts FROM positions WHERE ts <= ? ORDER BY ts DESC LIMIT 1",
                (last["ts"],)).fetchone()
            if r:
                p.positions = self.restore_positions(r[0])

        nsd = float(last.get("nav_start_of_day") or 0.0)
        pk = float(last.get("peak_nav") or 0.0)
        today_local = datetime.now().astimezone().date().isoformat()
        try:
            last_local = datetime.fromisoformat(
                str(last["ts"])).astimezone().date().isoformat()
        except ValueError:
            last_local = str(last["ts"])[:10]
        if last_local != today_local or nsd <= 0:
            nsd = p.nav
        p.nav_start_of_day = nsd
        p.peak_nav = pk if pk > 0 else p.nav
        if p.nav > p.peak_nav:
            p.peak_nav = p.nav
        return p

    def load_kill_events_since(self, since_iso: str) -> list:
        cur = self.conn.execute(
            "SELECT ts, level, reason, metrics_json FROM kill_events "
            "WHERE ts >= ? ORDER BY ts", (since_iso,))
        return [{"ts": ts, "level": int(lvl), "reason": rsn,
                 "metrics": json.loads(mj)} for ts, lvl, rsn, mj in cur]

    def close(self) -> None:
        self.conn.close()
