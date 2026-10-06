"""Synthetic journal tests: honest paper must pass, fake paper must be caught."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qa.honesty_checks import run_checks  # noqa: E402


def _w(tmp_path, events):
    p = tmp_path / "journal.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in events))
    return p


def _fill(order_id, ts, side, price, mid, fee, leg="perp", otype="market", pos="p1"):
    return {
        "event_type": "fill", "order_id": order_id, "position_id": pos,
        "ts": ts, "symbol": "BTCUSDT", "leg": leg, "side": side,
        "order_type": otype, "liquidity": "taker", "qty": 0.01,
        "price": price, "mid": mid, "fee": fee, "market_touch": mid,
    }


def _honest():
    """Append-only stream, ordered by ts (must be). fee = taker 5bps on notional 420.1 -> 0.210."""
    return [
        {"event_type": "order_submit", "order_id": "o1",
         "ts": "2025-01-15T08:00:00.000Z", "symbol": "BTCUSDT", "market": "spot"},
        _fill("o1", "2025-01-15T08:00:00.120Z", "buy", 42010.0, 42000.0, 0.210, leg="spot"),
        {"event_type": "order_submit", "order_id": "o2",
         "ts": "2025-01-15T08:00:00.200Z", "symbol": "BTCUSDT", "market": "perp"},
        _fill("o2", "2025-01-15T08:00:00.320Z", "sell", 41990.0, 42000.0, 0.210, leg="perp"),
        {"event_type": "position_open", "position_id": "p1",
         "ts": "2025-01-15T08:00:00.500Z", "symbol": "BTCUSDT"},
        {"event_type": "funding_credit", "ts": "2025-01-15T08:00:03.000Z",
         "symbol": "BTCUSDT", "amount_usd": 0.5, "funding_rate": 0.0001, "nav_usd": 1000.0},
        {"event_type": "delta_snapshot", "ts": "2025-01-15T09:00:00.000Z",
         "nav_usd": 1000.0, "delta_usd": 5.0},
    ]


def test_fake_no_fees_caught(tmp_path):
    ev = _honest()
    for e in ev:
        if e.get("event_type") == "fill":
            e["fee"] = 0.0
    r = run_checks(str(_w(tmp_path, ev)), str(tmp_path / "x.db"), {"emit_alerts": False})
    assert r["fees_match_schedule"]["passed"] is False


def test_fake_zero_latency_caught(tmp_path):
    ev = _honest()
    for e in ev:
        if e.get("event_type") == "fill" and e["order_id"] == "o1":
            e["ts"] = "2025-01-15T08:00:00.000Z"
    r = run_checks(str(_w(tmp_path, ev)), str(tmp_path / "x.db"), {"emit_alerts": False})
    assert r["latency_recorded"]["passed"] is False


def test_fake_backdated_caught(tmp_path):
    ev = _honest()
    ev.append({"event_type": "delta_snapshot", "ts": "2025-01-15T00:00:00.000Z",
               "nav_usd": 1000.0, "delta_usd": 1.0})
    r = run_checks(str(_w(tmp_path, ev)), str(tmp_path / "x.db"), {"emit_alerts": False})
    assert r["ts_monotonic"]["passed"] is False


def test_honest_passes_core_checks(tmp_path):
    r = run_checks(str(_w(tmp_path, _honest())), str(tmp_path / "x.db"),
                   {"emit_alerts": False})
    for k in ("fees_match_schedule", "slippage_simulated", "latency_recorded",
              "ts_monotonic", "both_legs_executed", "delta_within_target",
              "funding_cadence", "no_conflicting_orders"):
        assert r[k]["passed"], (k, r[k])


def test_fake_perfect_slippage_caught(tmp_path):
    ev = _honest()
    for e in ev:
        if e.get("event_type") == "fill" and e.get("order_type") == "market":
            e["price"] = e["mid"]
    r = run_checks(str(_w(tmp_path, ev)), str(tmp_path / "x.db"), {"emit_alerts": False})
    assert r["slippage_simulated"]["passed"] is False


def test_fake_missing_leg_caught(tmp_path):
    ev = [e for e in _honest()
          if not (e.get("event_type") == "fill" and e.get("leg") == "spot")]
    r = run_checks(str(_w(tmp_path, ev)), str(tmp_path / "x.db"), {"emit_alerts": False})
    assert r["both_legs_executed"]["passed"] is False
