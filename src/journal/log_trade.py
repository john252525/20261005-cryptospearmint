"""Append-only JSONL: journal/<prefix>-<date>.jsonl."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

JOURNAL_DIR = Path("journal")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _target(prefix: str, day: date | None) -> Path:
    day = day or datetime.now(timezone.utc).date()
    return JOURNAL_DIR / f"{prefix}-{day.isoformat()}.jsonl"


def log_record(record: dict[str, Any], *, prefix: str = "events",
               day: date | None = None) -> Path:
    target = _target(prefix, day)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": _now_iso(), "id": uuid.uuid4().hex, **record}
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    return target


def log_trade(*, symbol: str, side: str, qty: float, price: float,
              mode: str = "paper", strategy: str = "unknown",
              order_id: str | None = None, **extra: Any) -> Path:
    return log_record({
        "kind": "trade", "mode": mode, "strategy": strategy, "symbol": symbol,
        "side": side, "qty": float(qty), "price": float(price),
        "notional": abs(float(qty)) * float(price), "order_id": order_id, **extra,
    }, prefix="trades")


def log_event(event: str, *, mode: str = "dev", **extra: Any) -> Path:
    prefix = "paper" if mode == "paper" else "events"
    return log_record({"kind": "event", "mode": mode, "event": event, **extra},
                      prefix=prefix)


__all__ = ["JOURNAL_DIR", "log_event", "log_record", "log_trade"]
