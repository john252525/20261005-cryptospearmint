"""Binance testnet WS -> journal/paper-<date>.jsonl. Ордера не отправляются."""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import signal
import sys
from datetime import UTC, datetime
from pathlib import Path

import websockets
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config  # noqa: E402
from src.journal.log_trade import log_event  # noqa: E402

WS_BASE = "wss://stream.testnet.binance.vision/ws"
STOP = asyncio.Event()


def _on_signal(signum: int, _frame) -> None:
    # signal handler: только os.write + флаг, никакого loguru/print
    with contextlib.suppress(Exception):
        os.write(2, f"\n[paper] signal {signum}, stopping\n".encode())
    STOP.set()


async def stream(symbol: str) -> None:
    url = f"{WS_BASE}/{symbol.lower()}@aggTrade"
    logger.info("connecting to {}", url)
    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
        log_event("ws_connected", mode="paper", symbol=symbol, url=url)
        while not STOP.is_set():
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=60.0)
            except TimeoutError:
                logger.debug("no messages in 60s")
                continue
            data = json.loads(raw)
            log_event("trade_tick", mode="paper", symbol=data.get("s", symbol),
                      price=float(data.get("p", 0.0)), qty=float(data.get("q", 0.0)),
                      trade_time_ms=int(data.get("T", 0)))


async def run(cfg) -> int:
    logger.info("paper runner | symbol={}", cfg.crypto.symbol)
    try:
        await stream(cfg.crypto.symbol)
    except Exception as e:
        logger.exception("paper runner failed: {}", e)
        return 1
    log_event("ws_closed", mode="paper", symbol=cfg.crypto.symbol)
    return 0


def main() -> int:
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/example.yaml")
    a = p.parse_args()
    cfg = load_config(REPO_ROOT / a.config)
    log_event("paper_start", mode="paper", symbol=cfg.crypto.symbol,
              started_at=datetime.now(UTC).isoformat(timespec="seconds"))
    try:
        return asyncio.run(run(cfg))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
