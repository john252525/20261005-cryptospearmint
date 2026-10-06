"""FSM BOOTSTRAP → PAPER_DRY → PAPER_LIVE → SMALL_LIVE → SCALE.
CLI: python -m src.pipeline.state_machine {status|history|advance [json]|can [json]}
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB   = ROOT / "state" / "pipeline.sqlite"
QA_STATE = ROOT / "data" / "qa_state.json"

class State(StrEnum):
    BOOTSTRAP  = "BOOTSTRAP"
    PAPER_DRY  = "PAPER_DRY"
    PAPER_LIVE = "PAPER_LIVE"
    SMALL_LIVE = "SMALL_LIVE"
    SCALE      = "SCALE"

ORDER = [State.BOOTSTRAP, State.PAPER_DRY, State.PAPER_LIVE,
         State.SMALL_LIVE, State.SCALE]

@dataclass
class Metrics:
    days_paper: int = 0
    days_live: int = 0
    qa_pass_streak: int = 0
    qa_fail_streak: int = 0
    max_dd_pct: float = 0.0
    sharpe: float = 0.0
    kill_level: int = 0
    incident_count_24h: int = 0
    extra: dict = field(default_factory=dict)

def _testnet_reconciled(max_age_h: float = 24.0) -> bool:
    """Строгая проверка testnet-reconcile.

    Возвращает True ТОЛЬКО если:
      * env QA_ALLOW_UNVERIFIED=1 (явный локальный bypass), ИЛИ
      * data/qa_state.json свежий (< max_age_h часов) И содержит
        reconcile_with_testnet.passed is True (строгое identity, без truthy).
    Всё остальное — False. Fail-closed: файл отсутствует, устарел,
    повреждён, или проверка отдала FAIL — перехода нет.
    """
    if os.getenv("QA_ALLOW_UNVERIFIED") == "1":
        return True
    if not QA_STATE.exists():
        return False
    age_h = (time.time() - QA_STATE.stat().st_mtime) / 3600.0
    if age_h > max_age_h:
        return False
    try:
        obj = json.loads(QA_STATE.read_text())
    except Exception:
        return False

    def _find(node):
        if isinstance(node, dict):
            if "reconcile_with_testnet" in node:
                v = node["reconcile_with_testnet"]
                if isinstance(v, dict):
                    return v.get("passed") is True
                return v is True
            for val in node.values():
                r = _find(val)
                if r is not None:
                    return r
        elif isinstance(node, list):
            for val in node:
                r = _find(val)
                if r is not None:
                    return r
        return None

    return _find(obj) is True

GATES = {
    (State.BOOTSTRAP, State.PAPER_DRY):
        (lambda m: m.qa_pass_streak >= 1, "qa_pass_streak >= 1"),
    (State.PAPER_DRY, State.PAPER_LIVE):
        (lambda m: m.qa_pass_streak >= 3 and m.days_paper >= 7
                   and m.kill_level == 0 and _testnet_reconciled(),
         "qa_pass_streak>=3 · days_paper>=7 · kill_level==0 · testnet reconciled"),
    (State.PAPER_LIVE, State.SMALL_LIVE):
        (lambda m: m.days_paper >= 30 and m.max_dd_pct <= 10.0
                   and m.sharpe >= 1.0 and m.kill_level == 0,
         "days_paper>=30 · dd<=10% · sharpe>=1.0 · kill_level==0"),
    (State.SMALL_LIVE, State.SCALE):
        (lambda m: m.days_live >= 30 and m.max_dd_pct <= 15.0
                   and m.incident_count_24h == 0 and m.kill_level == 0,
         "days_live>=30 · dd<=15% · incidents_24h==0 · kill_level==0"),
}

def _conn() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS pipeline_transitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL, src TEXT NOT NULL, dst TEXT NOT NULL,
        ok INTEGER NOT NULL, reason TEXT NOT NULL, metrics TEXT NOT NULL)""")
    return c

def next_state(s: State) -> State | None:
    i = ORDER.index(s)
    return ORDER[i + 1] if i + 1 < len(ORDER) else None

def reason_for(s: State, m: Metrics) -> tuple[bool, str]:
    nxt = next_state(s)
    if nxt is None:
        return False, f"terminal: {s.value}"
    cond, why = GATES[(s, nxt)]
    try:
        return bool(cond(m)), why
    except Exception as e:
        return False, f"gate error: {e}"

def can_transition(s: State, m: Metrics) -> bool:
    return reason_for(s, m)[0]

def current_state() -> State:
    with _conn() as c:
        row = c.execute("SELECT dst FROM pipeline_transitions WHERE ok=1 "
                        "ORDER BY id DESC LIMIT 1").fetchone()
    return State(row[0]) if row else State.BOOTSTRAP

def _log(src: State, dst: State, ok: bool, reason: str, m: Metrics) -> None:
    with _conn() as c:
        c.execute("INSERT INTO pipeline_transitions(ts,src,dst,ok,reason,metrics) "
                  "VALUES (?,?,?,?,?,?)",
                  (dt.datetime.now(dt.UTC).isoformat(),
                   src.value, dst.value, int(ok), reason,
                   json.dumps(m.__dict__, default=str)))
        c.commit()

def transition(m: Metrics, to: State | None = None) -> tuple[State, str]:
    src = current_state()
    dst = to or next_state(src)
    if dst is None:
        _log(src, src, False, "terminal state", m)
        return src, "terminal state"
    ok, why = (True, f"forced -> {dst.value}") if to else reason_for(src, m)
    _log(src, dst, ok, why, m)
    if not ok:
        return src, why
    try:
        from src.pipeline.notify import transition as nt
        nt(src.value, dst.value, why)
    except Exception:
        pass
    return dst, why

def history(limit: int = 50) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT ts,src,dst,ok,reason FROM pipeline_transitions "
                         "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(zip(("ts", "src", "dst", "ok", "reason"), r, strict=False)) for r in rows]

def _cli() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(current_state().value)
    elif cmd == "history":
        for r in history():
            print(r)
    elif cmd == "advance":
        m = Metrics(**(json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}))
        s, why = transition(m)
        print(f"{s.value} :: {why}")
    elif cmd == "can":
        m = Metrics(**(json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}))
        ok, why = reason_for(current_state(), m)
        print(json.dumps({"ok": ok, "reason": why}))
    else:
        print(__doc__)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(_cli())
