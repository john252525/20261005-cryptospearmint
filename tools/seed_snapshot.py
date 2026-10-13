"""Seed a snapshot into risk.db so the exporter has something to serve.

Creates the schema via StateStore, writes one Portfolio with a single open
position (marked-to-market), and commits snapshot+positions under one ts.
Idempotent: re-running overwrites by primary key.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone

from state import StateStore
from risk.structures import Order, Portfolio, Side


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="risk.db")
    ap.add_argument("--cash", type=float, default=100_000.0)
    ap.add_argument("--symbol", default="AAPL")
    ap.add_argument("--qty", type=float, default=100.0)
    ap.add_argument("--entry", type=float, default=180.0)
    ap.add_argument("--mark", type=float, default=160.0)
    args = ap.parse_args()

    store = StateStore(args.db)
    p = Portfolio(cash=args.cash)

    fill = Order("seed-1", args.symbol, Side.BUY, args.qty, args.entry)
    p.apply_fill(fill)
    p.mark({args.symbol: args.mark})

    ts = datetime.now(timezone.utc)
    store.save_snapshot(p, ts=ts)
    store.save_positions(p, ts=ts)
    store.save_order(fill, "approved", "seed")
    store.close()

    print(f"[seed] db={args.db} nav={p.nav:.2f} dd={p.drawdown_pct:.2f}% "
          f"positions={list(p.positions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
