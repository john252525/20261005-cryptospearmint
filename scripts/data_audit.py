"""Audit data/bars/*.parquet: gaps, dupes, ts monotonicity.
Writes artifacts/data_audit.json. Exit 1 if any issue.
"""
from __future__ import annotations

import contextlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BARS = ROOT / "data" / "bars"
OUT  = ROOT / "artifacts" / "data_audit.json"

def _ts(series):
    raw = pd.to_datetime(series, utc=True, errors="coerce")
    if raw.isna().all():
        with contextlib.suppress(Exception):
            raw = pd.to_datetime(series.astype("int64"), unit="ms", utc=True)
    return raw

def _one(path: Path) -> dict:
    df = pd.read_parquet(path)
    if df.empty:
        return {"path": str(path), "rows": 0, "gaps": 0, "dupes": 0, "non_monotonic": 0}
    ts_col = "ts" if "ts" in df.columns else df.columns[0]
    raw = _ts(df[ts_col])
    if raw.isna().all():
        return {"path": str(path), "rows": len(df), "ts_col": ts_col,
                "gaps": 0, "dupes": 0, "non_monotonic": 0, "note": "ts unparsed"}
    diff = raw.diff().dropna().dt.total_seconds()
    pos = diff[diff > 0]
    med = float(pos.median()) if not pos.empty else 0.0
    return {"path": str(path), "rows": len(df), "ts_col": ts_col,
            "interval_med_s": med,
            "gaps": int((diff > 2 * med).sum()) if med > 0 else 0,
            "dupes": int(df[ts_col].duplicated().sum()),
            "non_monotonic": int((diff < 0).sum())}

def main() -> int:
    files = sorted(BARS.glob("*.parquet"))
    rep = {"ts": datetime.now(UTC).isoformat(), "files": [],
           "gaps": 0, "dupes": 0, "non_monotonic": 0}
    if not files:
        print(f"[data-audit] no parquet in {BARS}; nothing to do")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(rep, indent=2))
        return 0
    for f in files:
        r = _one(f)
        rep["files"].append(r)
        rep["gaps"] += r["gaps"]
        rep["dupes"] += r["dupes"]
        rep["non_monotonic"] += r["non_monotonic"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=2))
    bad = rep["gaps"] + rep["dupes"] + rep["non_monotonic"]
    if bad:
        print(f"[data-audit] FAIL gaps={rep['gaps']} dupes={rep['dupes']} "
              f"non_monotonic={rep['non_monotonic']}", file=sys.stderr)
        return 1
    print("[data-audit] OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
