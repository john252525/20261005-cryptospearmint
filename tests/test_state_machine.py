"""FSM: gates, transitions, terminal state, idempotency."""
from __future__ import annotations

import pytest


@pytest.fixture()
def sm(tmp_path, monkeypatch):
    import src.pipeline.state_machine as mod
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
    monkeypatch.setattr(mod, "DB", tmp_path / "state" / "pipeline.sqlite")
    mod.DB.parent.mkdir(parents=True, exist_ok=True)
    return mod


def test_initial_state_is_bootstrap(sm):
    assert sm.current_state() == sm.State.BOOTSTRAP


def test_can_transition_denies_without_qa_streak(sm):
    ok, why = sm.can_transition(sm.State.BOOTSTRAP, sm.Metrics(qa_pass_streak=0))
    assert ok is False and "qa_pass_streak" in why


def test_can_transition_allows_with_qa_streak(sm):
    ok, _ = sm.can_transition(sm.State.BOOTSTRAP, sm.Metrics(qa_pass_streak=1))
    assert ok is True


def test_paper_live_gate_requires_testnet(sm):
    m = sm.Metrics(qa_pass_streak=3, days_in_phase=7, kill_level=0,
                   testnet_reconciled=False)
    assert sm.can_transition(sm.State.PAPER_DRY, m)[0] is False
    m.testnet_reconciled = True
    assert sm.can_transition(sm.State.PAPER_DRY, m)[0] is True


def test_terminal_state_denies(sm):
    ok, why = sm.can_transition(sm.State.SCALE, sm.Metrics())
    assert ok is False and "terminal" in why


def test_transition_advances_and_logs(sm):
    s, _ = sm.transition(sm.Metrics(qa_pass_streak=1))
    assert s == sm.State.PAPER_DRY
    rows = sm.history()
    assert len(rows) == 1
    assert rows[0]["from_state"] == "BOOTSTRAP"
    assert rows[0]["to_state"] == "PAPER_DRY"


def test_transition_denied_stays_and_logs(sm):
    s, _ = sm.transition(sm.Metrics(qa_pass_streak=0))
    assert s == sm.State.BOOTSTRAP
    rows = sm.history()
    assert len(rows) == 1 and "denied" in rows[0]["reason"]


def test_multi_transitions(sm):
    sm.transition(sm.Metrics(qa_pass_streak=5))
    sm.transition(sm.Metrics(qa_pass_streak=3, days_in_phase=10,
                             kill_level=0, testnet_reconciled=True))
    assert sm.current_state() == sm.State.PAPER_LIVE
    assert sm.history()[0]["to_state"] == "PAPER_LIVE"
