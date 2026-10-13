"""Audit data/bars/*.parquet: dup_ts / missing_bars / OHLC / zero_vol_pct.

Writes artifacts/data_audit.json. Exit 1 if any issue.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BARS = ROOT / "data" / "bars"
OUT  = ROOT / "artifacts" / "data_audit.json"


def _ts(series: pd.Series) -> pd.Series:
    raw = pd.to_datetime(series, utc=True, errors="coerce")
    if raw.isna().all():
        try:
            raw = pd.to_datetime(series.astype("int64"), unit="ms", utc=True)
        except Exception:
            pass
    return raw


def _one(path: Path) -> dict:
    df = pd.read_parquet(path)
    empty = {"path": str(path), "rows": 0, "gaps": 0, "dupes": 0,
             "non_monotonic": 0, "zero_vol_pct": 0.0, "ohlc_violations": 0}
    if df.empty:
        return empty

    ts_col = "ts" if "ts" in df.columns else df.columns[0]
    ts = _ts(df[ts_col])
    if ts.isna().all():
        r = dict(empty); r.update(rows=len(df), ts_col=ts_col,
                                  note="ts unparsed")
        return r

    diff = ts.diff().dropna().dt.total_seconds()
    pos = diff[diff > 0]
    med = float(pos.median()) if not pos.empty else 0.0

    ohlc_bad = 0
    if all(c in df.columns for c in ("open", "high", "low", "close")):
        ohlc_bad = int((
            (df["high"] < df["low"])
            | (df["high"] < df["open"])
            | (df["high"] < df["close"])
            | (df["low"] > df["open"])
            | (df["low"] > df["close"])
        ).sum())

    zero_vol_pct = 0.0
    if "volume" in df.columns and len(df) > 0:
        zero_vol_pct = float((df["volume"] <= 0).mean() * 100.0)

    return {"path": str(path), "rows": len(df), "ts_col": ts_col,
            "interval_med_s": med,
            "gaps": int((diff > 2 * med).sum()) if med > 0 else 0,
            "dupes": int(ts.duplicated().sum()),
            "non_monotonic": int((diff < 0).sum()),
            "zero_vol_pct": round(zero_vol_pct, 3),
            "ohlc_violations": ohlc_bad}


def main() -> int:
    files = sorted(BARS.glob("*.parquet"))
    rep: dict[str, Any] = {"ts": datetime.now(UTC).isoformat(), "files": [],
           "gaps": 0, "dupes": 0, "non_monotonic": 0,
           "ohlc_violations": 0, "zero_vol_pct_avg": 0.0}
    if not files:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(rep, indent=2))
        print(f"[data-audit] no parquet in {BARS} — nothing to do")
        return 0

    zv: list[float] = []
    for f in files:
        r = _one(f)
        rep["files"].append(r)
        rep["gaps"]            += r["gaps"]
        rep["dupes"]           += r["dupes"]
        rep["non_monotonic"]   += r["non_monotonic"]
        rep["ohlc_violations"] += r["ohlc_violations"]
        zv.append(r["zero_vol_pct"])
    rep["zero_vol_pct_avg"] = round(sum(zv) / len(zv), 3) if zv else 0.0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=2))

    bad = (rep["gaps"] + rep["dupes"] + rep["non_monotonic"]
           + rep["ohlc_violations"])
    if bad:
        print(f"[data-audit] FAIL gaps={rep['gaps']} dupes={rep['dupes']} "
              f"non_monotonic={rep['non_monotonic']} "
              f"ohlc={rep['ohlc_violations']}", file=sys.stderr)
        return 1
    print("[data-audit] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
