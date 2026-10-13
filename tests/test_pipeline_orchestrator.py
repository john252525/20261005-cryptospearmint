"""Orchestrator CLI + notify formatting + rollback idempotency."""
from __future__ import annotations

import sqlite3

import pytest


def test_orchestrator_help_lists_commands():
    pytest.importorskip("typer")
    from click.testing import CliRunner
    from src.pipeline.orchestrator import app
    r = CliRunner().invoke(app, ["--help"])
    assert r.exit_code == 0
    for cmd in ("fetch", "audit", "backtest", "qa", "report", "snapshot"):
        assert cmd in r.stdout


def test_orchestrator_bad_strategy_exits_nonzero():
    pytest.importorskip("typer")
    from click.testing import CliRunner
    from src.pipeline.orchestrator import app
    r = CliRunner().invoke(app, ["backtest", "--strategy", "nope"])
    assert r.exit_code != 0


def test_notify_no_token_returns_false(monkeypatch, capsys):
    for v in ("TELEGRAM_BOT_TOKEN", "TG_BOT_TOKEN",
              "TELEGRAM_CHAT_ID", "TG_CHAT_ID"):
        monkeypatch.delenv(v, raising=False)
    from src.pipeline.notify import notify
    assert notify("END_OF_DAY", {"net_pnl": 1.0}) is False
    assert "notify:no-creds" in capsys.readouterr().err


def test_notify_format_kill_triggered():
    from src.pipeline.notify import format_event
    s = format_event("KILL_TRIGGERED",
                     {"level": 2, "reason": "dd", "closed": 3,
                      "drawdown_pct": 4.2})
    assert "L2" in s and "de-risk" in s and "dd" in s


def test_notify_format_transition():
    from src.pipeline.notify import format_event
    s = format_event("TRANSITION", {"from_state": "A", "to_state": "B",
                                    "reason": "gate ok"})
    assert "A" in s and "B" in s and "gate ok" in s


def test_rollback_is_idempotent(tmp_path, monkeypatch):
    from src.pipeline import state_machine as sm
    import scripts.rollback as rb

    monkeypatch.setattr(sm, "DB", tmp_path / "state" / "pipeline.sqlite")
    sm.DB.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(rb, "ROOT", tmp_path)
    monkeypatch.setattr(rb, "BACK",     tmp_path / "backups")
    monkeypatch.setattr(rb, "STATE_DB", tmp_path / "state" / "pipeline.sqlite")
    monkeypatch.setattr(rb, "QA_DB",    tmp_path / "data" / "state.db")
    monkeypatch.setattr(rb, "JOURNAL",  tmp_path / "data" / "journal.jsonl")
    monkeypatch.setattr(rb, "JOURNALS", tmp_path / "data" / "journals")
    monkeypatch.setattr(rb, "KILL_LOG", tmp_path / "data" / "kill_events.jsonl")

    sm.transition(sm.Metrics(qa_pass_streak=1))
    sm.transition(sm.Metrics(qa_pass_streak=5))

    def count() -> int:
        with sqlite3.connect(rb.STATE_DB) as c:
            return c.execute(
                "SELECT COUNT(*) FROM pipeline_transitions").fetchone()[0]

    assert count() >= 2
    snap1 = rb.rollback("2000-01-01", dry_run=False)
    after1 = count()
    assert after1 == 0
    snap2 = rb.rollback("2000-01-01", dry_run=False)
    assert count() == after1 == 0
    assert snap1 == snap2 and snap1.exists()
