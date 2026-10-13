"""FSM for pipeline lifecycle. Transitions logged to SQLite.

BOOTSTRAP -> PAPER_DRY -> PAPER_LIVE -> SMALL_LIVE -> SCALE.

CLI:
  python -m src.pipeline.state_machine status|history|can JSON|advance JSON
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB   = ROOT / "state" / "pipeline.sqlite"


class State(str, Enum):
    BOOTSTRAP  = "BOOTSTRAP"
    PAPER_DRY  = "PAPER_DRY"
    PAPER_LIVE = "PAPER_LIVE"
    SMALL_LIVE = "SMALL_LIVE"
    SCALE      = "SCALE"


ORDER: list[State] = [State.BOOTSTRAP, State.PAPER_DRY, State.PAPER_LIVE,
                      State.SMALL_LIVE, State.SCALE]


@dataclass
class Metrics:
    days_in_phase: int = 0
    qa_pass_streak: int = 0
    kill_level: int = 0
    max_drawdown_pct: float = 0.0
    sharpe: float = 0.0
    incidents_24h: int = 0
    testnet_reconciled: bool = False
    extra: dict = field(default_factory=dict)


def next_state(state: State) -> State | None:
    i = ORDER.index(state)
    return ORDER[i + 1] if i + 1 < len(ORDER) else None


GATES: dict[State, tuple] = {
    State.BOOTSTRAP: (
        lambda m: m.qa_pass_streak >= 1,
        "qa_pass_streak >= 1",
    ),
    State.PAPER_DRY: (
        lambda m: (m.qa_pass_streak >= 3 and m.days_in_phase >= 7
                   and m.kill_level == 0 and m.testnet_reconciled),
        "qa_pass_streak>=3 / days_in_phase>=7 / kill_level==0 / testnet_reconciled",
    ),
    State.PAPER_LIVE: (
        lambda m: (m.days_in_phase >= 30 and m.max_drawdown_pct <= 10.0
                   and m.sharpe >= 1.0 and m.kill_level == 0),
        "days_in_phase>=30 / max_drawdown<=10 / sharpe>=1.0 / kill_level==0",
    ),
    State.SMALL_LIVE: (
        lambda m: (m.days_in_phase >= 30 and m.max_drawdown_pct <= 15.0
                   and m.incidents_24h == 0 and m.kill_level == 0),
        "days_in_phase>=30 / max_drawdown<=15 / incidents_24h==0 / kill_level==0",
    ),
}


def can_transition(state: State, metrics: Metrics) -> tuple[bool, str]:
    nxt = next_state(state)
    if nxt is None:
        return False, f"terminal state {state.value}, no further transitions"
    cond, why = GATES[state]
    try:
        ok = bool(cond(metrics))
    except Exception as e:
        return False, f"gate error: {e}"
    return ok, why


def _conn() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS pipeline_transitions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        ts           TEXT NOT NULL,
        from_state   TEXT NOT NULL,
        to_state     TEXT NOT NULL,
        reason       TEXT NOT NULL,
        metrics_json TEXT NOT NULL)""")
    return c


def _log(frm: State, to: State, reason: str, metrics: Metrics) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO pipeline_transitions"
            "(ts, from_state, to_state, reason, metrics_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (dt.datetime.now(dt.UTC).isoformat(),
             frm.value, to.value, reason,
             json.dumps(asdict(metrics), default=str)))
        c.commit()


def current_state() -> State:
    with _conn() as c:
        row = c.execute(
            "SELECT to_state FROM pipeline_transitions ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return State(row[0]) if row else State.BOOTSTRAP


def history(limit: int = 50) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, from_state, to_state, reason FROM pipeline_transitions "
            "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(zip(("ts", "from_state", "to_state", "reason"), r)) for r in rows]


def transition(metrics: Metrics, *,
               force_to: State | None = None) -> tuple[State, str]:
    frm = current_state()
    to  = force_to or next_state(frm)

    if to is None:
        reason = f"terminal state {frm.value}"
        _log(frm, frm, reason, metrics)
        return frm, reason

    allowed, why = can_transition(frm, metrics)
    if not allowed and force_to is None:
        _log(frm, frm, f"denied: {why}", metrics)
        return frm, why

    reason = why if force_to is None else f"forced -> {to.value}"
    _log(frm, to, reason, metrics)
    try:
        from src.pipeline.notify import transition as ntf
        ntf(frm.value, to.value, reason)
    except Exception:
        pass
    return to, reason


def _cli(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else "status"

    if cmd == "status":
        print(current_state().value)
        return 0
    if cmd == "history":
        for r in history():
            print(r)
        return 0
    if cmd in ("can", "advance"):
        raw = argv[1] if len(argv) > 1 else "{}"
        m = Metrics(**json.loads(raw))
        if cmd == "can":
            ok, why = can_transition(current_state(), m)
            print(json.dumps({"ok": ok, "reason": why}))
        else:
            s, why = transition(m)
            print(f"{s.value} :: {why}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_cli())
