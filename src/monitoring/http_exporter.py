"""HTTP exporter: publish trading metrics on :9100 every N seconds."""

from __future__ import annotations

import argparse
import json
import signal
import sqlite3
import sys
import threading
from pathlib import Path
from typing import Any

from loguru import logger
from prometheus_client import start_http_server

from src.monitoring.metrics import publish

ROOT     = Path(__file__).resolve().parents[2]
STATE_DB = ROOT / "state" / "funding_carry.db"
KILLS    = ROOT / "data" / "kill_events.jsonl"

_stop = threading.Event()


def _on_signal(signum: int, _frame) -> None:
    logger.info("signal {} received; shutting down", signum)
    _stop.set()


def _read_funding_carry_db() -> dict[str, Any]:
    if not STATE_DB.exists():
        return {}
    snap: dict[str, Any] = {}
    try:
        with sqlite3.connect(STATE_DB) as c:
            tables = [r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for t in tables:
                cols = [r[1] for r in c.execute(
                    f"PRAGMA table_info({t})").fetchall()]
                if not cols:
                    continue
                for cand, key in (("nav", "nav"),
                                  ("equity", "nav"),
                                  ("drawdown_pct", "drawdown_pct"),
                                  ("daily_loss_pct", "daily_loss_pct"),
                                  ("funding_accrued_usd", "funding_accrued_usd"),
                                  ("delta_exposure_bps", "delta_exposure_bps")):
                    if cand in cols and key not in snap:
                        try:
                            row = c.execute(
                                f"SELECT {cand} FROM {t} "
                                "ORDER BY rowid DESC LIMIT 1").fetchone()
                            if row and row[0] is not None:
                                snap[key] = float(row[0])
                        except sqlite3.OperationalError:
                            pass
                if "symbol" in cols:
                    notional_col = next(
                        (cc for cc in ("notional_usd", "notional", "size_usd")
                         if cc in cols), None)
                    if notional_col:
                        try:
                            rows = c.execute(
                                f"SELECT symbol, {notional_col} FROM {t} "
                                "WHERE rowid IN (SELECT MAX(rowid) FROM "
                                f"{t} GROUP BY symbol)").fetchall()
                            pos = {str(r[0]): float(r[1] or 0.0) for r in rows}
                            if pos:
                                snap["position_size_usd"] = pos
                        except sqlite3.OperationalError:
                            pass
    except sqlite3.DatabaseError as e:
        logger.warning("funding_carry.db read failed: {}", e)
    return snap


def _read_kill_events() -> dict[str, Any]:
    if not KILLS.exists():
        return {}
    try:
        lines = [ln for ln in KILLS.read_text().splitlines() if ln.strip()]
        if not lines:
            return {}
        last = json.loads(lines[-1])
        lvl = last.get("level")
        if isinstance(lvl, str) and lvl.startswith("L"):
            lvl = int(lvl[1:])
        if lvl is not None:
            return {"kill_level": int(lvl)}
    except Exception as e:  # noqa: BLE001
        logger.warning("kill_events read failed: {}", e)
    return {}


def collect() -> dict[str, Any]:
    state: dict[str, Any] = {}
    state.update(_read_funding_carry_db())
    state.update(_read_kill_events())
    return state


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="http_exporter")
    ap.add_argument("--port", type=int, default=9100)
    ap.add_argument("--interval", type=float, default=5.0)
    a = ap.parse_args(argv)

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    start_http_server(a.port)
    logger.info("exporter listening on :{} (interval {}s)", a.port, a.interval)

    ticks = 0
    while not _stop.is_set():
        try:
            snap = collect()
            if snap:
                publish(snap)
            ticks += 1
            if ticks % 12 == 0:
                logger.info("tick {} keys={}", ticks, list(snap.keys()))
        except Exception as e:  # noqa: BLE001
            logger.warning("tick failed: {}", e)
        _stop.wait(a.interval)

    logger.info("exporter stopped after {} ticks", ticks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
