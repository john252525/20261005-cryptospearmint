"""SQLite registry of backtest QA runs."""
from __future__ import annotations
import json, logging, sqlite3
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("qa.registry")

DEFAULT_DB = "state/backtest_qa.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS backtest_qa (
    backtest_id     TEXT PRIMARY KEY,
    ts              TEXT NOT NULL,
    checks_passed   INTEGER NOT NULL,
    checks_failed   INTEGER NOT NULL,
    verdict         TEXT NOT NULL,
    details         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_backtest_qa_ts ON backtest_qa(ts);
CREATE INDEX IF NOT EXISTS idx_backtest_qa_verdict ON backtest_qa(verdict);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(_SCHEMA)
    return con


def record(backtest_id: str, results: dict, db_path: str = DEFAULT_DB,
           fail_threshold: int = 1, verdict: str | None = None) -> dict:
    passed = sum(1 for r in results.values() if r["passed"])
    failed = sum(1 for r in results.values() if not r["passed"])
    if verdict is None:
        verdict = "PASS" if failed < fail_threshold else "FAIL"
    ts = _now()
    con = _connect(db_path)
    try:
        con.execute(
            "INSERT INTO backtest_qa(backtest_id, ts, checks_passed, checks_failed, "
            "verdict, details) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(backtest_id) DO UPDATE SET "
            "ts=excluded.ts, checks_passed=excluded.checks_passed, "
            "checks_failed=excluded.checks_failed, verdict=excluded.verdict, "
            "details=excluded.details",
            (backtest_id, ts, passed, failed, verdict, json.dumps(results)),
        )
        con.commit()
    finally:
        con.close()
    return {"backtest_id": backtest_id, "ts": ts, "verdict": verdict,
            "checks_passed": passed, "checks_failed": failed}


def get(backtest_id: str, db_path: str = DEFAULT_DB) -> dict | None:
    if not Path(db_path).exists():
        return None
    con = _connect(db_path)
    try:
        row = con.execute(
            "SELECT backtest_id, ts, checks_passed, checks_failed, verdict, details "
            "FROM backtest_qa WHERE backtest_id=?", (backtest_id,)).fetchone()
    finally:
        con.close()
    if not row:
        return None
    bid, ts, p, f, v, det = row
    try:
        details = json.loads(det)
    except json.JSONDecodeError:
        details = {}
    return {"backtest_id": bid, "ts": ts, "checks_passed": p,
            "checks_failed": f, "verdict": v, "details": details}


def list_recent(db_path: str = DEFAULT_DB, since_ts: str | None = None,
                limit: int | None = None) -> list[dict]:
    if not Path(db_path).exists():
        return []
    q = ("SELECT backtest_id, ts, checks_passed, checks_failed, verdict "
         "FROM backtest_qa")
    args: list = []
    if since_ts:
        q += " WHERE ts >= ?"
        args.append(since_ts)
    q += " ORDER BY ts DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    con = _connect(db_path)
    try:
        rows = con.execute(q, args).fetchall()
    finally:
        con.close()
    return [{"backtest_id": r[0], "ts": r[1], "checks_passed": r[2],
             "checks_failed": r[3], "verdict": r[4]} for r in rows]
