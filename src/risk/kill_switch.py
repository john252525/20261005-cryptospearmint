"""Minimal kill-switch façade — file-based, no POSIX magic."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_PATH = Path("risk/KILL_SWITCH")


class KillSwitch:
    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            env = os.getenv("KILL_SWITCH_FILE")
            path = env if env else DEFAULT_PATH
        self.path = Path(path)

    def check(self) -> int:
        """Return current kill level (0 or 3). Never raises."""
        try:
            return 3 if self.path.exists() else 0
        except OSError:
            return 0

    @property
    def armed(self) -> bool:
        return self.check() > 0

    def arm(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch()

    def disarm(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
