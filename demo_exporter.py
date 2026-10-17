"""Minimal demo exporter for the E2E demo_runner.

Reads /root/risk_v0/state/demo.db and exposes metrics on :9101.
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import time
from pathlib import Path

from prometheus_client import Gauge, Counter, start_http_server

DB = os.environ.get("DEMO_DB", "/root/risk_v0/state/demo.db")
MARK_PX = float(os.environ.get("DEMO_MARK_PX", "60000.0"))

orders_g = Counter("demo_orders_total", "Orders by status", ["status"])
fills_g = Counter("demo_fills_total", "Fills recorded")
fees_g = Gauge("demo_fees_total", "Cumulative fees")
cash_g = Gauge("demo_cash_usd", "Broker cash")
pos_qty_g = Gauge("demo_position_qty", "Position qty", ["symbol"])
pos_usd_g = Gauge("demo_position_notional_usd", "Position notional", ["symbol"])
nav_g = Gauge("demo_nav_usd", "NAV (cash + positions at mark)")

_last_orders: dict = {}
_last_fills = 0


def _connect():
    uri = f"file:{DB}?mode=ro"
    c = sqlite3.connect(uri, uri=True, timeout=1.0)
    c.row_factory = sqlite3.Row
    return c


def _poll():
    global _last_fills
    if not Path(DB).exists():
        return
    with _connect() as c:
        rows = c.execute(
            "SELECT status, COUNT(*) AS n FROM broker_orders GROUP BY status"
        ).fetchall()
        cur = {r["status"]: int(r["n"]) for r in rows}
        for status in ("PENDING", "FILLED", "CANCELED"):
            delta = cur.get(status, 0) - _last_orders.get(status, 0)
            if delta > 0:
                orders_g.labels(status=status).inc(delta)
            _last_orders[status] = cur.get(status, 0)

        row = c.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(fee),0) AS f FROM broker_fills"
        ).fetchone()
        n_fills = int(row["n"]); fee_sum = float(row["f"])
        delta_fills = n_fills - _last_fills
        if delta_fills > 0:
            fills_g.inc(delta_fills)
        _last_fills = n_fills
        fees_g.set(fee_sum)

        pos = {}
        for r in c.execute(
            "SELECT symbol, side, filled_qty FROM broker_orders WHERE status='FILLED'"
        ):
            signed = float(r["filled_qty"]) if r["side"] == "BUY" else -float(r["filled_qty"])
            pos[r["symbol"]] = pos.get(r["symbol"], 0.0) + signed

        cash = 10000.0
        for r in c.execute(
            "SELECT side, filled_qty, avg_fill_price FROM broker_orders "
            "WHERE status='FILLED'"
        ):
            signed = float(r["filled_qty"]) if r["side"] == "BUY" else -float(r["filled_qty"])
            cash -= signed * float(r["avg_fill_price"])
        cash -= fee_sum
        cash_g.set(cash)

        nav = cash
        for sym, qty in pos.items():
            pos_qty_g.labels(symbol=sym).set(qty)
            notional = qty * MARK_PX
            pos_usd_g.labels(symbol=sym).set(notional)
            nav += notional
        nav_g.set(nav)


def main() -> int:
    global DB
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9101)
    ap.add_argument("--db", default=DB)
    ap.add_argument("--interval", type=float, default=2.0)
    args = ap.parse_args()
    DB = args.db
    start_http_server(args.port)
    print(f"demo_exporter listening on :{args.port} db={DB}", flush=True)
    while True:
        try:
            _poll()
        except Exception as exc:  # noqa: BLE001
            print(f"[demo_exporter] poll error: {exc!r}", flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
