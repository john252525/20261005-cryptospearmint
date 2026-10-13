#!/usr/bin/env python3
"""Daily QA honesty report -> docs/reports/qa_YYYYMMDD.md"""
from __future__ import annotations
import sqlite3, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qa.honesty_checks import run_checks, _load  # noqa: E402

JOURNAL = ROOT / "journal" / "journal.jsonl"
DB = ROOT / "state" / "state.db"
OUT_DIR = ROOT / "docs" / "reports"


def _avg(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def _ts(s):
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).timestamp()


def compute_metrics(events):
    funding = [e for e in events if e.get("event_type") == "funding_credit"]
    mf = [e for e in events if e.get("event_type") == "fill"
          and e.get("order_type") == "market"]
    basis, legs = [], {}
    for e in events:
        if e.get("event_type") == "fill":
            pid = e.get("position_id")
            if pid:
                legs.setdefault(pid, {})[e.get("leg")] = e
    for l in legs.values():
        if "spot" in l and "perp" in l:
            sp, pp = l["spot"]["price"], l["perp"]["price"]
            if sp:
                basis.append((pp - sp) / sp * 1e4)
    sub = {e["order_id"]: e["ts"] for e in events
           if e.get("event_type") == "order_submit"}
    lat = [(_ts(e["ts"]) - _ts(sub[e["order_id"]])) * 1000
           for e in events
           if e.get("event_type") == "fill" and e.get("order_id") in sub]
    slip = [abs(e["price"] - e["mid"]) / e["mid"] * 1e4
            for e in mf if e.get("mid")]
    ok = 0
    if DB.exists():
        con = sqlite3.connect(DB)
        try:
            rows = con.execute(
                "SELECT ok FROM reconcile_log WHERE ts >= datetime('now','-24 hours')"
            ).fetchall()
            ok = sum(1 for (x,) in rows if x)
        except sqlite3.OperationalError:
            ok = 0
        finally:
            con.close()
    return {
        "funding_events_count": len(funding),
        "avg_basis_at_entry_bps": round(_avg(basis), 4),
        "avg_slippage_bps": round(_avg(slip), 4),
        "order_submit_to_fill_ms": round(_avg(lat), 2),
        "reconciled_ok_hours": f"{ok}/24",
    }


def render(checks, metrics, day):
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


def main():
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not JOURNAL.exists():
        raise SystemExit(f"journal not found: {JOURNAL}")
    checks = run_checks(str(JOURNAL), str(DB), {"emit_alerts": False})
    metrics = compute_metrics(_load(JOURNAL))
    out = OUT_DIR / f"qa_{day}.md"
    out.write_text(render(checks, metrics, day))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
