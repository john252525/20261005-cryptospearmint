"""Telegram notifier — stdlib only (urllib).

Env: TELEGRAM_BOT_TOKEN / TG_BOT_TOKEN, TELEGRAM_CHAT_ID / TG_CHAT_ID.
If creds are absent, message is written to stderr; send returns False.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.request
from typing import Any

API = "https://api.telegram.org/bot{token}/sendMessage"

PRIORITY = {"KILL_TRIGGERED": "!!", "HONESTY_FAIL": "!!",
            "PIPELINE_FAIL": "!!", "TRANSITION": "->", "END_OF_DAY": "ok"}

KILL_LEVELS = {
    1: "L1 warn - nothing blocked",
    2: "L2 de-risk - block new entries",
    3: "L3 flatten - close book",
    4: "L4 kill - trading disabled, manual re-arm required",
}


def _token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TG_BOT_TOKEN") or ""


def _chat() -> str:
    return os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TG_CHAT_ID") or ""


def _now() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC")


def format_event(event: str, data: dict[str, Any]) -> str:
    head = f"[{PRIORITY.get(event, '?')}] {event}  {_now()}"
    if event == "END_OF_DAY":
        body = (f"net PnL: {data.get('net_pnl', 0):,.2f} USDT\n"
                f"funding: {data.get('funding', 0):,.2f}  fees: {data.get('fees', 0):,.2f}\n"
                f"drawdown: {data.get('drawdown_pct', 0):.2f}%  state: {data.get('state', '?')}\n"
                f"QA: {data.get('qa', '?')}\n"
                f"report: {data.get('report_path', '-')}")
    elif event == "KILL_TRIGGERED":
        lvl = int(data.get("level", 0))
        body = (f"level L{lvl} - {KILL_LEVELS.get(lvl, '?')}\n"
                f"reason: {data.get('reason', '-')}\n"
                f"closed: {data.get('closed', 0)}  dd: {data.get('drawdown_pct', 0):.2f}%")
    elif event == "HONESTY_FAIL":
        checks = data.get("checks") or []
        body = ("failed: " + ", ".join(str(c) for c in checks)
                + f"\nreport: {data.get('report_path', '-')}")
    elif event == "PIPELINE_FAIL":
        body = (f"stage: {data.get('stage', '?')}  code: {data.get('code', 1)}")
    elif event == "TRANSITION":
        body = (f"{data.get('from_state', '?')} -> {data.get('to_state', '?')}\n"
                f"gate: {data.get('reason', '-')}")
    else:
        body = json.dumps(data, default=str)[:1200]
    return f"{head}\n{body}"


def send(text: str) -> bool:
    token, chat = _token(), _chat()
    if not (token and chat):
        sys.stderr.write(f"[notify:no-creds]\n{text}\n")
        return False
    payload = json.dumps({"chat_id": chat, "text": text,
                          "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(
        API.format(token=token), data=payload,
        headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5).read()
        return True
    except Exception as e:
        sys.stderr.write(f"[notify:error] {e}\n")
        return False


def notify(event: str, data: dict[str, Any] | None = None) -> bool:
    return send(format_event(event, data or {}))


def end_of_day(*, net_pnl: float, funding: float, fees: float,
               drawdown_pct: float, state: str, qa: str,
               report_path: str) -> bool:
    return notify("END_OF_DAY", {"net_pnl": net_pnl, "funding": funding,
                                 "fees": fees, "drawdown_pct": drawdown_pct,
                                 "state": state, "qa": qa,
                                 "report_path": report_path})


def kill_triggered(level: int, reason: str,
                   closed: int = 0, drawdown_pct: float = 0.0) -> bool:
    return notify("KILL_TRIGGERED", {"level": level, "reason": reason,
                                     "closed": closed,
                                     "drawdown_pct": drawdown_pct})


def honesty_fail(checks: list[str], report_path: str) -> bool:
    return notify("HONESTY_FAIL", {"checks": checks, "report_path": report_path})


def pipeline_fail(stage: str, code: int = 1) -> bool:
    return notify("PIPELINE_FAIL", {"stage": stage, "code": code})


def transition(from_state: str, to_state: str, reason: str) -> bool:
    return notify("TRANSITION", {"from_state": from_state,
                                 "to_state": to_state, "reason": reason})


if __name__ == "__main__":
    evt = sys.argv[1] if len(sys.argv) > 1 else "END_OF_DAY"
    notify(evt, {})
