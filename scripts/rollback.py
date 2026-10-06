"""Snapshot + rollback for state/pipeline.sqlite, data/state.db, journals.
Usage:
  python scripts/rollback.py snapshot [--tag NAME]
  python scripts/rollback.py --to-date YYYY-MM-DD [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT     = Path(__file__).resolve().parents[1]
BACK     = ROOT / "backups"
QA_DB    = ROOT / "data" / "state.db"
FSM_DB   = ROOT / "state" / "pipeline.sqlite"
JOURNAL  = ROOT / "data" / "journal.jsonl"
JOURNALS = ROOT / "data" / "journals"
KILLLOG  = ROOT / "data" / "kill_events.jsonl"

TS_COLS = ("ts", "created_at", "timestamp", "event_ts")

def _stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")

def snapshot(tag: str | None = None) -> Path:
    dst = BACK / f"snapshot_{tag or _stamp()}"
    dst.mkdir(parents=True, exist_ok=True)
    for src, sub in ((QA_DB, "data"), (FSM_DB, "state"),
                     (JOURNAL, "data"), (KILLLOG, "data")):
        if src.exists():
            (dst / sub).mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / sub / src.name)
    if JOURNALS.exists():
        shutil.copytree(JOURNALS, dst / "data" / "journals", dirs_exist_ok=True)
    (dst / "META.txt").write_text(
        f"snapshot_at={dt.datetime.now(dt.UTC).isoformat()}\n"
        f"tag={tag or '-'}\nroot={ROOT}\n")
    return dst

def _tables(db: Path) -> list[str]:
    if not db.exists():
        return []
    with sqlite3.connect(db) as c:
        return [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

def _cols(db: Path, t: str) -> list[str]:
    try:
        with sqlite3.connect(db) as c:
            return [r[1] for r in c.execute(f"PRAGMA table_info({t})").fetchall()]
    except sqlite3.OperationalError:
        return []

def rollback(to_date: str, dry_run: bool = False) -> Path:
    d = dt.date.fromisoformat(to_date)
    cutoff_iso  = f"{d.isoformat()}T23:59:59"
    cutoff_name = d.strftime("%Y%m%d")
    print(f"[rollback] target={d.isoformat()} dry_run={dry_run}")
    snap = snapshot(tag=f"pre_rollback_{cutoff_name}")
    print(f"[rollback] backup -> {snap}")

    for db, label in ((FSM_DB, "state/pipeline.sqlite"), (QA_DB, "data/state.db")):
        if not db.exists():
            print(f"[rollback] {label}: absent, skip")
            continue
        for tbl in _tables(db):
            cols = _cols(db, tbl)
            col = next((c for c in TS_COLS if c in cols), None)
            if not col:
                continue
            with sqlite3.connect(db) as c:
                n = c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col} > ?",
                              (cutoff_iso,)).fetchone()[0]
            print(f"[rollback] {label}.{tbl}.{col}: {n} rows after cutoff")
            if n and not dry_run:
                with sqlite3.connect(db) as c:
                    c.execute(f"DELETE FROM {tbl} WHERE {col} > ?", (cutoff_iso,))
                    c.commit()

    if JOURNALS.exists():
        stash = snap / "data" / "journals_after"
        stash.mkdir(parents=True, exist_ok=True)
        for f in sorted(JOURNALS.glob("*.jsonl")):
            if f.stem > cutoff_name:
                print(f"[rollback] stash {f.name}")
                if not dry_run:
                    shutil.move(str(f), stash / f.name)
    print(f"[rollback] done. restore point: {snap}")
    return snap

def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "snapshot":
        tag = None
        if "--tag" in sys.argv:
            i = sys.argv.index("--tag")
            tag = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
        print(snapshot(tag))
        return 0
    ap = argparse.ArgumentParser(description="Pipeline rollback")
    ap.add_argument("--to-date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rollback(a.to_date, dry_run=a.dry_run)
    return 0

if __name__ == "__main__":
    sys.exit(main())
