"""docs/reports/daily_YYYYMMDD.md — daily trading summary."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT      = Path(__file__).resolve().parents[2]
JOURNAL   = ROOT / "data" / "journal.jsonl"
JOURNALS  = ROOT / "data" / "journals"
KILL_LOG  = ROOT / "data" / "kill_events.jsonl"
REPORTS   = ROOT / "docs" / "reports"
QA_LATEST = REPORTS / "qa_latest.md"


def _iter_rows(day: str) -> list[dict]:
    rows: list[dict] = []
    for f in (JOURNAL, JOURNALS / f"{day}.jsonl"):
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def _drawdown_pct(rows: list[dict]) -> float:
    eq = peak = dd = 0.0
    for r in rows:
        eq += (float(r.get("pnl", 0.0)) + float(r.get("funding", 0.0))
               - float(r.get("fee", 0.0)))
        peak = max(peak, eq)
        if peak > 0:
            dd = max(dd, (peak - eq) / peak * 100.0)
    return dd


def _kill_level() -> int:
    try:
        from src.risk.kill_switch import DEFAULT_PATH, KillSwitch
        return 3 if KillSwitch(DEFAULT_PATH).path.exists() else 0
    except Exception:
        return 0


def _state() -> str:
    try:
        from src.pipeline.state_machine import current_state
        return current_state().value
    except Exception:
        return "UNKNOWN"


def _qa_status() -> str:
    files = list(REPORTS.glob("qa_*.md"))
    if not files:
        return "MISSING"
    latest = max(files, key=lambda p: p.stat().st_mtime)
    txt = latest.read_text(errors="ignore").lower()
    if any(s in txt for s in ("only dry_run", "no vendor credentials",
                              "unverified (accepted)")):
        return "WARN_NO_CREDS"
    if "fail-closed" in txt:
        return "FAIL_CLOSED"
    if ": fail" in txt or " fail " in txt:
        return "FAIL"
    return "PASS"


def build_daily(out: str | None = None) -> Path:
    day = dt.datetime.now(dt.UTC).strftime("%Y%m%d")
    iso = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    rows = _iter_rows(day)

    pnl     = sum(float(r.get("pnl", 0.0))     for r in rows)
    funding = sum(float(r.get("funding", 0.0)) for r in rows)
    fees    = sum(float(r.get("fee", 0.0))     for r in rows)
    net     = pnl + funding - fees
    dd      = _drawdown_pct(rows)
    kill    = _kill_level()
    qa      = _qa_status()
    state   = _state()

    bucket: dict[str, dict] = {}
    for r in rows:
        s = r.get("symbol", "?")
        b = bucket.setdefault(s, {"symbol": s, "side": r.get("side", "-"),
                                  "pnl": 0.0, "funding": 0.0})
        b["pnl"]     += float(r.get("pnl", 0.0))
        b["funding"] += float(r.get("funding", 0.0))
    top3 = sorted(bucket.values(),
                  key=lambda x: x["pnl"] + x["funding"], reverse=True)[:3]

    incidents: list[dict] = []
    if KILL_LOG.exists():
        for line in KILL_LOG.read_text().splitlines():
            if line.strip():
                try:
                    incidents.append(json.loads(line))
                except Exception:
                    continue

    top_md = "\n".join(
        f"| {p['symbol']} | {p['side']} | {p['pnl']:,.2f} | {p['funding']:,.2f} |"
        for p in top3) or "| - | - | - | - |"

    inc_md = "\n".join(
        f"- `{i.get('ts', '')}` L{i.get('level', '?')} - "
        f"{i.get('msg', i.get('reason', ''))}"
        for i in incidents) or "- none"

    para = (f"Net PnL {iso}: {net:,.2f} USDT "
            f"(gross {pnl:,.2f}, funding {funding:,.2f}, fees {fees:,.2f}); "
            f"drawdown {dd:.2f}%, kill L{kill}, QA {qa}, state {state}. "
            + ("no incidents." if not incidents
               else f"incidents: {len(incidents)}."))

    md = f"""# Daily report — {iso}

| metric | value |
|---|---|
| net PnL (USDT) | {net:,.2f} |
| gross PnL | {pnl:,.2f} |
| funding income | {funding:,.2f} |
| fees | {fees:,.2f} |
| drawdown | {dd:.2f}% |
| kill level | L{kill} |
| QA status | {qa} |
| pipeline state | {state} |
| events | {len(rows)} |

## Top-3 positions
| symbol | side | pnl | funding |
|---|---|---|---|
{top_md}

## Incidents
{inc_md}

_{para}_
"""
    target = Path(out) if out else (REPORTS / f"daily_{day}.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(md)
    try:
        from src.pipeline.notify import end_of_day
        end_of_day(net_pnl=net, funding=funding, fees=fees, drawdown_pct=dd,
                   state=state, qa=qa, report_path=str(target))
    except Exception:
        pass
    return target


def build_qa(out: str | None = None) -> Path:
    dst = Path(out) if out else QA_LATEST
    dst.parent.mkdir(parents=True, exist_ok=True)
    if QA_LATEST.exists() and QA_LATEST.resolve() != dst.resolve():
        dst.write_text(QA_LATEST.read_text())
    return dst


if __name__ == "__main__":
    print(build_daily())
