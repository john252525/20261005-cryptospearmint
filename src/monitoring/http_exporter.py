"""Prometheus HTTP exporter on :9100.

Reads state from SQLite (`risk.db`) and publishes gauges every `interval`
seconds. Tolerates a missing or empty DB (publishes zeros) and deduplicates
`risk_orders_total` by `order_id` across polls.
"""
from __future__ import annotations
import argparse
import signal
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loguru import logger
from prometheus_client import start_http_server

from src.monitoring.metrics import (
    RiskState, publish, record_order, reset,
)


class Exporter:
    def __init__(self, db_path: str, interval: float = 5.0) -> None:
        self.db_path = db_path
        self.interval = interval
        self._stop = threading.Event()
        self._seen_orders: set[str] = set()
        self._warned_missing = False

    # ---- lifecycle ------------------------------------------------
    def _handle_signal(self, signum, _frame) -> None:
        logger.info("signal {} received - shutting down", signum)
        self._stop.set()

    def run(self, port: int = 9100, addr: str = "0.0.0.0") -> None:
        reset()
        start_http_server(port=port, addr=addr)
        logger.info("exporter on {}:{}  db={}  poll={}s",
                    addr, port, self.db_path, self.interval)

        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        try:
            self._preload_seen_orders()
        except Exception:
            logger.exception("preload failed - starting with empty dedupe set")

        while not self._stop.is_set():
            try:
                state = self._read_state()
                publish(state)
                logger.debug("nav={:.2f} dd={:.2f}% kill=L{} opm={} seen={}",
                             state.nav, state.drawdown_pct,
                             state.kill_level, state.orders_per_min,
                             len(self._seen_orders))
            except Exception:
                logger.exception("poll failed")
            self._stop.wait(self.interval)

        logger.info("clean exit")

    # ---- db helpers -----------------------------------------------
    def _db_ok(self) -> bool:
        return Path(self.db_path).exists()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro",
                               uri=True, timeout=2.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _preload_seen_orders(self) -> None:
        if not self._db_ok():
            return
        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0).isoformat()
        n = 0
        with self._connect() as conn:
            for r in conn.execute(
                    "SELECT order_id, symbol, side, status "
                    "FROM orders WHERE ts >= ?", (today,)):
                self._seen_orders.add(r["order_id"])
                record_order(r["symbol"], r["side"], r["status"])
                n += 1
        logger.info("preloaded {} order ids for dedupe", n)

    def _read_state(self) -> RiskState:
        if not self._db_ok():
            if not self._warned_missing:
                logger.warning("db {} not found - publishing zeros",
                               self.db_path)
                self._warned_missing = True
            return RiskState()

        self._warned_missing = False
        with self._connect() as conn:
            snap = conn.execute(
                "SELECT ts, nav, daily_pnl, drawdown_pct, nav_start_of_day "
                "FROM pnl_snapshots ORDER BY ts DESC LIMIT 1").fetchone()
            if snap is None:
                return RiskState()

            pos_ts = conn.execute(
                "SELECT MAX(ts) AS ts FROM positions").fetchone()["ts"]
            pos_rows = []
            if pos_ts:
                pos_rows = conn.execute(
                    "SELECT symbol, notional FROM positions WHERE ts = ?",
                    (pos_ts,)).fetchall()
                if not pos_rows:
                    earlier = conn.execute(
                        "SELECT ts FROM positions WHERE ts <= ? "
                        "ORDER BY ts DESC LIMIT 1", (pos_ts,)).fetchone()
                    if earlier:
                        pos_rows = conn.execute(
                            "SELECT symbol, notional FROM positions WHERE ts = ?",
                            (earlier["ts"],)).fetchall()

            lvl = conn.execute(
                "SELECT level FROM kill_events ORDER BY ts DESC LIMIT 1"
            ).fetchone()
            kill_level = int(lvl["level"]) if lvl else 0

            cutoff = (datetime.now(timezone.utc)
                      - timedelta(seconds=60)).isoformat()
            opm = conn.execute(
                "SELECT COUNT(*) AS n FROM orders WHERE ts >= ?", (cutoff,)
            ).fetchone()["n"]

            today = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0).isoformat()
            for r in conn.execute(
                    "SELECT order_id, symbol, side, status "
                    "FROM orders WHERE ts >= ?", (today,)):
                if r["order_id"] in self._seen_orders:
                    continue
                self._seen_orders.add(r["order_id"])
                record_order(r["symbol"], r["side"], r["status"])

        nav_start = float(snap["nav_start_of_day"] or 0.0)
        daily_pnl = float(snap["daily_pnl"] or 0.0)
        dl_pct = ((-daily_pnl) / nav_start * 100.0) \
            if nav_start > 0 and daily_pnl < 0 else 0.0

        return RiskState(
            nav=float(snap["nav"]),
            drawdown_pct=float(snap["drawdown_pct"]),
            kill_level=kill_level,
            orders_per_min=float(opm),
            daily_loss_pct=dl_pct,
            positions={r["symbol"]: float(r["notional"]) for r in pos_rows},
        )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Risk metrics HTTP exporter")
    ap.add_argument("--db", default="risk.db")
    ap.add_argument("--port", type=int, default=9100)
    ap.add_argument("--addr", default="0.0.0.0")
    ap.add_argument("--interval", type=float, default=5.0)
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args(argv)

    logger.remove()
    logger.add(sys.stderr, level=args.log_level.upper(),
               format="<green>{time:HH:mm:ss}</green> | "
                      "<level>{level: <7}</level> | {message}")

    if not Path(args.db).exists():
        logger.warning("db {} does not exist yet - starting with zero gauges",
                       args.db)

    Exporter(args.db, interval=args.interval).run(port=args.port, addr=args.addr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
