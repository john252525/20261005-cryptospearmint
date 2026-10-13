"""Snapshot + rollback of state SQLite and journals. Idempotent.

  python -m scripts.rollback snapshot [--tag NAME]
  python -m scripts.rollback --to-date YYYY-MM-DD [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT     = Path(__file__).resolve().parents[1]
BACK     = ROOT / "backups"
STATE_DB = ROOT / "state" / "pipeline.sqlite"
QA_DB    = ROOT / "data" / "state.db"
JOURNAL  = ROOT / "data" / "journal.jsonl"
JOURNALS = ROOT / "data" / "journals"
KILL_LOG = ROOT / "data" / "kill_events.jsonl"

TS_COLUMNS = ("ts", "created_at", "timestamp", "event_ts")


def _stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def snapshot(tag: str | None = None) -> Path:
    dst = BACK / f"snapshot_{tag or _stamp()}"
    dst.mkdir(parents=True, exist_ok=True)
    for src, sub in ((STATE_DB, "state"), (QA_DB, "data"),
                     (JOURNAL, "data"), (KILL_LOG, "data")):
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


def _cols(db: Path, tbl: str) -> list[str]:
    try:
        with sqlite3.connect(db) as c:
            return [r[1] for r in c.execute(f"PRAGMA table_info({tbl})").fetchall()]
    except sqlite3.OperationalError:
        return []


def rollback(to_date: str, dry_run: bool = False) -> Path:
    d = dt.date.fromisoformat(to_date)
    cutoff_iso  = f"{d.isoformat()}T23:59:59.999999"
    cutoff_name = d.strftime("%Y%m%d")

    snap = snapshot(tag=f"pre_rollback_{cutoff_name}")

    for db, _label in ((STATE_DB, "state/pipeline.sqlite"),
                       (QA_DB,    "data/state.db")):
        if not db.exists():
            continue
        for tbl in _tables(db):
            cols = _cols(db, tbl)
            col = next((c for c in TS_COLUMNS if c in cols), None)
            if not col:
                continue
            with sqlite3.connect(db) as c:
                n = c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col} > ?",
                              (cutoff_iso,)).fetchone()[0]
                if n and not dry_run:
                    c.execute(f"DELETE FROM {tbl} WHERE {col} > ?", (cutoff_iso,))
                    c.commit()

    if JOURNALS.exists():
        stash = snap / "data" / "journals_after"
        stash.mkdir(parents=True, exist_ok=True)
        for f in sorted(JOURNALS.glob("*.jsonl")):
            if f.stem > cutoff_name and not dry_run:
                shutil.move(str(f), stash / f.name)

    return snap


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "snapshot":
        tag = None
        if "--tag" in argv:
            i = argv.index("--tag")
            tag = argv[i + 1] if i + 1 < len(argv) else None
        print(snapshot(tag))
        return 0

    ap = argparse.ArgumentParser(prog="rollback")
    ap.add_argument("--to-date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    snap = rollback(a.to_date, dry_run=a.dry_run)
    print(json.dumps({"rollback_date": a.to_date, "dry_run": a.dry_run,
                      "snapshot": str(snap)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
