"""Telegram wrapper. Env: TELEGRAM_BOT_TOKEN|TG_BOT_TOKEN, TELEGRAM_CHAT_ID|TG_CHAT_ID."""
from __future__ import annotations

import datetime as dt
import os
from typing import Any

import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TG_BOT_TOKEN")
CHAT  = os.getenv("TELEGRAM_CHAT_ID")   or os.getenv("TG_CHAT_ID")
API   = "https://api.telegram.org/bot{token}/sendMessage"

PRIO = {"KILL_TRIGGERED": "🔴", "HONESTY_FAIL": "🟠",
        "PIPELINE_FAIL": "🟠", "TRANSITION": "🔵", "END_OF_DAY": "🟢"}
KILL_DESC = {1: "L1 warn", 2: "L2 de-risk — block new entries",
             3: "L3 flatten — close book", 4: "L4 kill — manual re-arm"}

def _fmt(event: str, d: dict[str, Any]) -> str:
    ts = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC")
    head = f"{PRIO.get(event, '⚪')} *{event}*  `{ts}`"
    if event == "END_OF_DAY":
        body = (f"net PnL: `{d.get('net_pnl', 0):,.2f}` USDT\n"
                f"funding: `{d.get('funding', 0):,.2f}` · fees: `{d.get('fees', 0):,.2f}`\n"
                f"drawdown: `{d.get('dd_pct', 0):.2f}%` · state: `{d.get('state', '?')}`\n"
                f"QA: `{d.get('qa', '?')}`\nreport: `{d.get('report_path', '-')}`")
    elif event == "KILL_TRIGGERED":
        lvl = int(d.get("level", 0))
        body = (f"level `L{lvl}` — {KILL_DESC.get(lvl, '?')}\n"
                f"reason: {d.get('reason', '-')}\n"
                f"closed: `{d.get('closed', 0)}` · dd: `{d.get('dd_pct', 0):.2f}%`")
    elif event == "HONESTY_FAIL":
        body = ("failed: " + ", ".join(f"`{c}`" for c in (d.get("checks") or [])) +
                f"\nreport: `{d.get('report_path', '-')}`")
    elif event == "PIPELINE_FAIL":
        body = (f"stage: `{d.get('stage', '?')}` · code: `{d.get('code', 1)}`\n"
                f"run: `{d.get('run', '-')}`")
    elif event == "TRANSITION":
        body = f"`{d.get('src', '?')}` → `{d.get('dst', '?')}`\ngate: {d.get('reason', '-')}"
    else:
        body = "```\n" + str(d)[:1200] + "\n```"
    return f"{head}\n{body}"

def notify(event: str, data: dict[str, Any] | None = None) -> bool:
    data = data or {}
    text = _fmt(event, data)
    if not (TOKEN and CHAT):
        print(f"[notify:{event}] (no creds)\n{text}\n")
        return False
    try:
        r = requests.post(API.format(token=TOKEN),
                          json={"chat_id": CHAT, "text": text,
                                "parse_mode": "Markdown",
                                "disable_web_page_preview": True}, timeout=5)
        return bool(r.ok)
    except Exception as e:
        print(f"[notify] error: {e}")
        return False

def eod(net_pnl, funding, fees, dd_pct, state, qa, report_path) -> bool:
    return notify("END_OF_DAY", {"net_pnl": net_pnl, "funding": funding, "fees": fees,
                                 "dd_pct": dd_pct, "state": state, "qa": qa,
                                 "report_path": str(report_path)})

def kill(level: int, reason: str, closed: int = 0, dd_pct: float = 0.0) -> bool:
    return notify("KILL_TRIGGERED", {"level": level, "reason": reason,
                                     "closed": closed, "dd_pct": dd_pct})

def transition(src: str, dst: str, reason: str) -> bool:
    return notify("TRANSITION", {"src": src, "dst": dst, "reason": reason})

def honesty_fail(checks: list[str], report_path: str) -> bool:
    return notify("HONESTY_FAIL", {"checks": checks, "report_path": str(report_path)})

def pipeline_fail(stage: str, code: int = 1, run: str = "-") -> bool:
    return notify("PIPELINE_FAIL", {"stage": stage, "code": code, "run": run})
