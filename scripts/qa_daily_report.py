#!/usr/bin/env python3
"""Daily QA honesty report -> docs/reports/qa_YYYYMMDD.md"""
from __future__ import annotations

import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qa.honesty_checks import _load_journal, run_checks  # noqa: E402

JOURNAL = ROOT / "data" / "journal.jsonl"
DB = ROOT / "data" / "state.db"
OUT_DIR = ROOT / "docs" / "reports"


def _avg(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def _parse(s: str) -> float:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).timestamp()


def compute_metrics(events: list[dict]) -> dict:
    funding = [e for e in events if e.get("event_type") == "funding_credit"]
    market_fills = [e for e in events if e.get("event_type") == "fill"
                    and e.get("order_type") == "market"]
    basis = []
    legs: dict[str, dict] = {}
    for e in events:
        if e.get("event_type") == "fill":
            pid = e.get("position_id")
            if pid:
                legs.setdefault(pid, {})[e.get("leg")] = e
    for pid, l in legs.items():
        if "spot" in l and "perp" in l:
            sp, pp = l["spot"]["price"], l["perp"]["price"]
            if sp:
                basis.append((pp - sp) / sp * 1e4)

    submit = {e["order_id"]: e["ts"] for e in events if e.get("event_type") == "order_submit"}
    lat = []
    for e in events:
        if e.get("event_type") == "fill" and e.get("order_id") in submit:
            lat.append((_parse(e["ts"]) - _parse(submit[e["order_id"]])) * 1000.0)

    slip = [abs(e["price"] - e["mid"]) / e["mid"] * 1e4
            for e in market_fills if e.get("mid")]

    ok_hours = 0
    if DB.exists():
        con = sqlite3.connect(DB)
        try:
            rows = con.execute(
                "SELECT ts, ok FROM reconcile_log WHERE ts >= datetime('now','-24 hours')"
            ).fetchall()
            ok_hours = sum(1 for _, ok in rows if ok)
        except sqlite3.OperationalError:
            ok_hours = 0
        finally:
            con.close()

    return {
        "funding_events_count": len(funding),
        "avg_basis_at_entry_bps": round(_avg(basis), 4),
        "avg_slippage_bps": round(_avg(slip), 4),
        "order_submit_to_fill_ms": round(_avg(lat), 2),
        "reconciled_ok_hours": f"{ok_hours}/24",
    }


def render(checks: dict, metrics: dict, day: str) -> str:
    lines = [f"# QA Honesty Report — {day}", ""]
    passed = sum(1 for r in checks.values() if r["passed"])
    lines += [f"**Passed: {passed}/{len(checks)}**", "",
              "## Checks", "",
              "| # | check | pass | value | threshold | message |",
              "|---|---|---|---|---|---|"]
    for i, (name, r) in enumerate(checks.items(), 1):
        mark = "✅" if r["passed"] else "❌"
        lines.append(f"| {i} | `{name}` | {mark} | {r['value']} | "
                     f"{r['threshold']} | {r['message']} |")
    lines += ["", "## Metrics", "", "| metric | value |", "|---|---|"]
    for k, v in metrics.items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    day = datetime.now(UTC).strftime("%Y%m%d")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not JOURNAL.exists():
        raise SystemExit(f"journal not found: {JOURNAL}")
    checks = run_checks(str(JOURNAL), str(DB), {"emit_alerts": False})
    metrics = compute_metrics(_load_journal(JOURNAL))
    out = OUT_DIR / f"qa_{day}.md"
    out.write_text(render(checks, metrics, day))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
