"""Binance testnet WS -> journal/paper-<date>.jsonl. Ключи не нужны, ордера не отправляются."""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import websockets
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config  # noqa: E402
from src.journal.log_trade import log_event  # noqa: E402

WS_BASE = "wss://stream.testnet.binance.vision/ws"
RECV_TIMEOUT_S = 5.0

_stop = asyncio.Event()
_stopped_printed = False


def _on_signal(signum: int, _frame) -> None:
    """Async-signal-safe: только os.write + флаг, идемпотентно."""
    global _stopped_printed
    with contextlib.suppress(Exception):
        if not _stopped_printed:
            os.write(2, f"\n[paper] signal {signum}, stopping\n".encode())
            _stopped_printed = True
    _stop.set()


async def stream(symbol: str, *, seconds: float = 0.0) -> None:
    url = f"{WS_BASE}/{symbol.lower()}@aggTrade"
    logger.info("connecting to {}", url)
    started = time.monotonic()
    ticks = 0

    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
        log_event("ws_connected", mode="paper", symbol=symbol, url=url)
        logger.info("connected to {}", url)

        async def _auto_stop() -> None:
            if seconds > 0:
                await asyncio.sleep(seconds)
                _stop.set()

        stopper = asyncio.create_task(_auto_stop()) if seconds > 0 else None

        try:
            while not _stop.is_set():
                if seconds > 0 and (time.monotonic() - started) >= seconds:
                    break
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=RECV_TIMEOUT_S)
                except TimeoutError:
                    continue
                data = json.loads(raw)
                ticks += 1
                log_event("trade_tick", mode="paper", symbol=data.get("s", symbol),
                          price=float(data.get("p", 0.0)), qty=float(data.get("q", 0.0)),
                          trade_time_ms=int(data.get("T", 0)))
        finally:
            if stopper is not None:
                stopper.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await stopper

    logger.info("disconnected | ticks={} elapsed={:.1f}s", ticks, time.monotonic() - started)


async def run(cfg, *, seconds: float) -> int:
    logger.info("paper runner | symbol={} seconds={} (0=inf)",
                cfg.crypto.symbol, seconds)
    try:
        await stream(cfg.crypto.symbol, seconds=seconds)
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
    p.add_argument("--seconds", type=float, default=0.0,
                   help="остановиться после N секунд (0 = бесконечно)")
    a = p.parse_args()

    cfg = load_config(REPO_ROOT / a.config)
    log_event("paper_start", mode="paper", symbol=cfg.crypto.symbol,
              started_at=datetime.now(UTC).isoformat(timespec="seconds"),
              seconds=a.seconds or None)

    try:
        return asyncio.run(run(cfg, seconds=a.seconds))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
