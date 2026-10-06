"""Демон для live_runner_funding --snap.

Каждые 00/08/16 UTC запускает `live_runner_funding.py --snap` как subprocess.
Немедленно делает initial snap при старте (не ждёт ближайшего).
Корректно выходит по SIGTERM/SIGINT.
"""
from __future__ import annotations

import argparse
import contextlib
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from execution.paper_runner_funding import next_snap_ts  # noqa: E402

STOP = {"flag": False}

def _on_stop(signum, _frame):
    # signal handler: только atomic flag + async-signal-safe os.write.
    # loguru в handler'е вызывает reentrant write в stderr (см. RuntimeError).
    if STOP["flag"]:
        return   # идемпотент: повторный SIGTERM/KILL не печатает второй раз
    STOP["flag"] = True
    with contextlib.suppress(Exception):
        os.write(2, f"\n[daemon] signal {signum} received; will stop after current op\n".encode())

def run_snap(py_file: Path, config: Path) -> None:
    cmd = [sys.executable, str(py_file), "--config", str(config), "--snap"]
    logger.info("running: {}", " ".join(cmd))
    rc = subprocess.call(cmd, cwd=str(REPO_ROOT))
    if rc != 0:
        logger.error("snap subprocess exited rc={}", rc)

def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/funding_portfolio.yaml")
    p.add_argument("--initial", action="store_true",
                   help="сделать snap сразу при старте, не ждать расписания")
    a = p.parse_args()

    signal.signal(signal.SIGTERM, _on_stop)
    signal.signal(signal.SIGINT, _on_stop)

    config = REPO_ROOT / a.config
    runner = REPO_ROOT / "execution" / "live_runner_funding.py"

    if a.initial:
        run_snap(runner, config)

    while not STOP["flag"]:
        now = datetime.now(UTC)
        snap = next_snap_ts(now)
        wait_s = (snap - now).total_seconds()
        logger.info("next snap at {} UTC, sleeping {:.0f}s", snap.isoformat(), wait_s)
        # спим кусками чтобы реагировать на SIGTERM
        deadline = time.monotonic() + wait_s
        while not STOP["flag"] and time.monotonic() < deadline:
            time.sleep(min(30.0, deadline - time.monotonic()))
        if STOP["flag"]:
            break
        # +90s запас на settle funding на бирже
        time.sleep(90)
        run_snap(runner, config)

    logger.info("daemon stopped")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
