"""Live runner — заглушка. APP_ENV=live + LIVE_CONFIRM=YES-I-AM-LIVE."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config  # noqa: E402
from src.journal.log_trade import log_event  # noqa: E402
from src.risk.kill_switch import kill_switch  # noqa: E402

CONFIRM_VALUE = "YES-I-AM-LIVE"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/example.yaml")
    a = p.parse_args()

    app_env = os.getenv("APP_ENV", "dev").strip().lower()
    confirm = os.getenv("LIVE_CONFIRM", "").strip()
    if app_env != "live" or confirm != CONFIRM_VALUE:
        logger.error("REFUSING LIVE: APP_ENV={!r} (need 'live'), "
                     "LIVE_CONFIRM={!r} (need {!r})", app_env, confirm, CONFIRM_VALUE)
        return 2

    kill_switch.assert_trading_allowed()
    cfg = load_config(REPO_ROOT / a.config)
    log_event("live_start_attempt", mode="live", symbol=cfg.crypto.symbol)
    raise NotImplementedError("live_runner: not implemented yet")


if __name__ == "__main__":
    raise SystemExit(main())
