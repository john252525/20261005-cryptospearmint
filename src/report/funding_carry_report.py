"""Daily journal report."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def load_journal(path, day):
    p = Path(path)
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(rec.get("ts", "")).startswith(day):
                out.append(rec)
    return out


def summarize(records):
    actions = Counter(r.get("action", "?") for r in records)
    realized = sum(float(r.get("pnl_realized", 0.0) or 0.0)
                   for r in records if r.get("action") == "close")
    fees = sum(float(r.get("fees_spot", 0.0) or 0.0)
               + float(r.get("fees_perp", 0.0) or 0.0)
               for r in records if r.get("action") in ("open", "close"))
    snaps = [r for r in records if r.get("note") == "snapshot"]
    per_symbol = defaultdict(lambda: {"opens": 0, "closes": 0, "pnl": 0.0})
    for r in records:
        s = r.get("symbol")
        if r.get("action") == "open":
            per_symbol[s]["opens"] += 1
        elif r.get("action") == "close":
            per_symbol[s]["closes"] += 1
            per_symbol[s]["pnl"] += float(r.get("pnl_realized", 0.0) or 0.0)
    prev_nav = snaps[0]["nav"] if snaps else None
    nav_delta = (snaps[-1]["nav"] - snaps[0]["nav"]) if len(snaps) > 1 else 0.0
    return {"events": len(records), "actions": dict(actions),
            "realized_pnl_usd": realized, "fees_usd": fees,
            "nav_start": prev_nav,
            "nav_end": snaps[-1]["nav"] if snaps else None,
            "nav_delta_usd": nav_delta,
            "funding_accrued_usd": snaps[-1].get("funding_accrued") if snaps else None,
            "delta_usd": snaps[-1].get("delta_usd") if snaps else None,
            "delta_bps_nav": snaps[-1].get("delta_bps_nav") if snaps else None,
            "per_symbol": {k: dict(v) for k, v in per_symbol.items()}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--journal", default="journal/funding_carry.jsonl")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    s = summarize(load_journal(a.journal, a.date))
    if a.json:
        print(json.dumps(s, indent=2, default=str)); return
    print(f"\n=== funding carry report :: {a.date} ===")
    for k, v in s.items():
        if k == "per_symbol":
            continue
        print(f"{k:>22}: {v}")
    print(f"{'per_symbol':>22}:")
    for sym, d in s["per_symbol"].items():
        print(f"    {sym}: opens={d['opens']} closes={d['closes']} pnl={d['pnl']:.4f}")
    print()


if __name__ == "__main__":
    main()
