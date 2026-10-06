"""FSM: gate-функции + transition, без сети, на tmp_path."""
from __future__ import annotations

import importlib
import json
import os
import time

import pytest


@pytest.fixture()
def sm(tmp_path, monkeypatch):
    """Каждая тест-каприза получает свой state/ и data/qa_state.json."""
    monkeypatch.setenv("QA_ALLOW_UNVERIFIED", "0")
    os.environ.pop("QA_ALLOW_UNVERIFIED", None)
    import src.pipeline.state_machine as mod
    monkeypatch.setattr(mod, "DB",       tmp_path / "state" / "pipeline.sqlite")
    monkeypatch.setattr(mod, "QA_STATE", tmp_path / "data" / "qa_state.json")
    mod.DB.parent.mkdir(parents=True, exist_ok=True)
    mod.QA_STATE.parent.mkdir(parents=True, exist_ok=True)
    importlib.reload(mod)
    # reload сбрасывает monkeypatch-атрибуты → назначим после reload
    mod.DB = tmp_path / "state" / "pipeline.sqlite"
    mod.QA_STATE = tmp_path / "data" / "qa_state.json"
    return mod


def _paper_live_metrics(m):
    return m.Metrics(qa_pass_streak=3, days_paper=30, sharpe=2.0, kill_level=0)


def _write_qa_state(sm, content, age_h: float = 0.0):
    sm.QA_STATE.write_text(json.dumps(content))
    if age_h:
        t = time.time() - age_h * 3600 - 60
        os.utime(sm.QA_STATE, (t, t))


def test_state_absent_fails_closed(sm):
    ok, _ = sm.reason_for(sm.State.PAPER_DRY, _paper_live_metrics(sm))
    assert ok is False


def test_state_streak_counter_blocks(sm):
    _write_qa_state(sm, {"reconcile_with_testnet": 1})
    ok, _ = sm.reason_for(sm.State.PAPER_DRY, _paper_live_metrics(sm))
    assert ok is False


def test_state_alert_reset_blocks(sm):
    # после alert_streak значение пишется как 0 — это НЕ pass
    _write_qa_state(sm, {"reconcile_with_testnet": 0})
    ok, _ = sm.reason_for(sm.State.PAPER_DRY, _paper_live_metrics(sm))
    assert ok is False


def test_state_all_pass_allows(sm):
    # empty dict = reconcile PASSed и был удалён из streak-счётчика
    _write_qa_state(sm, {})
    ok, why = sm.reason_for(sm.State.PAPER_DRY, _paper_live_metrics(sm))
    assert ok is True, why


def test_state_other_keys_only_allows(sm):
    # другие чеки в streak, reconcile отсутствует → PASS
    _write_qa_state(sm, {"fees_match_schedule": 2})
    ok, _ = sm.reason_for(sm.State.PAPER_DRY, _paper_live_metrics(sm))
    assert ok is True


def test_state_stale_blocks(sm):
    _write_qa_state(sm, {}, age_h=48)
    ok, _ = sm.reason_for(sm.State.PAPER_DRY, _paper_live_metrics(sm))
    assert ok is False


def test_state_corrupt_blocks(sm):
    sm.QA_STATE.write_text("{not-json")
    ok, _ = sm.reason_for(sm.State.PAPER_DRY, _paper_live_metrics(sm))
    assert ok is False


def test_bypass_env_allows(sm, monkeypatch):
    _write_qa_state(sm, {"reconcile_with_testnet": 99})
    monkeypatch.setenv("QA_ALLOW_UNVERIFIED", "1")
    ok, _ = sm.reason_for(sm.State.PAPER_DRY, _paper_live_metrics(sm))
    assert ok is True


def test_transition_persists_to_sqlite(sm):
    _write_qa_state(sm, {})
    s0 = sm.current_state()
    assert s0 == sm.State.BOOTSTRAP

    s1, _ = sm.transition(sm.Metrics(qa_pass_streak=1), to=sm.State.PAPER_DRY)
    assert s1 == sm.State.PAPER_DRY

    s2, why = sm.transition(_paper_live_metrics(sm))
    assert s2 == sm.State.PAPER_LIVE, why

    rows = sm.history()
    assert len(rows) == 2
    assert rows[0]["dst"] == "PAPER_LIVE"
    assert rows[1]["dst"] == "PAPER_DRY"
