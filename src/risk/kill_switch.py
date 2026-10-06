"""Kill switch: файл risk/KILL_SWITCH. Наличие файла = торговля запрещена."""
from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

DEFAULT_PATH = Path("risk/KILL_SWITCH")


class KillSwitchArmed(RuntimeError):
    """Торговля запрещена."""


class KillSwitch:
    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            env_path = os.getenv("KILL_SWITCH_FILE")
            resolved: str | Path = env_path if env_path else DEFAULT_PATH
        else:
            resolved = path
        self.path = Path(resolved)

    def is_armed(self) -> bool:
        return self.path.exists()

    def arm(self, reason: str) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        self.path.write_text(f"{ts} {reason}\n", encoding="utf-8")
        logger.error("KILL SWITCH ARMED at {} — {}", self.path, reason)
        return self.path

    def disarm(self) -> None:
        self.path.unlink(missing_ok=True)
        logger.warning("kill switch disarmed: {}", self.path)

    def assert_trading_allowed(self) -> None:
        if self.is_armed():
            raise KillSwitchArmed(f"kill switch armed: {self.path}")


kill_switch = KillSwitch()

__all__ = ["DEFAULT_PATH", "KillSwitch", "KillSwitchArmed", "kill_switch"]
