import numpy as np
import pandas as pd
import pytest

from src.strategies.funding_carry.backtest import (
    run_backtest,
    simulate_symbol,
    synthetic_data,
    target_pos,
)
from src.strategies.funding_carry.config import FundingCarrySettings


def _flat_frames(funding_bps, basis_bps, n=40):
    ts = pd.date_range("2024-07-01", periods=n, freq="8h", tz="UTC")
    funding = pd.DataFrame({"ts": ts, "funding_rate": funding_bps / 1e4})
    spot = pd.DataFrame({"ts": ts, "close": 100.0})
    perp = pd.DataFrame({"ts": ts, "close": 100.0 * (1 + basis_bps / 1e4)})
    return funding, spot, perp


def test_target_pos_mapping():
    s = FundingCarrySettings(min_funding_bps=1.0, max_basis_bps=30.0)
    assert target_pos(3.0, 5.0, s) == 1
    assert target_pos(-3.0, -5.0, s) == -1
    assert target_pos(0.2, 5.0, s) == 0
    assert target_pos(3.0, 100.0, s) == 0


def test_funding_pnl_matches_analytic():
    s = FundingCarrySettings(
        min_funding_bps=1.0, max_basis_bps=30.0,
        max_pos_per_symbol_usd=1000.0, target_leverage=1.0,
        spot_taker_fee=0.0, perp_taker_fee=0.0, slippage_bps=0.0,
    )
    n = 40
    funding, spot, perp = _flat_frames(5.0, 0.0, n)
    frame, trades = simulate_symbol("BTCUSDT", funding, spot, perp, s)
    expected = 1000.0 * (5.0 / 1e4) * (n - 1)
    assert trades, "expected at least one trade"
    assert trades[0]["funding_usd"] == pytest.approx(expected, rel=1e-9)
    assert trades[0]["basis_usd"] == pytest.approx(0.0, abs=1e-9)
    assert trades[0]["fees_usd"] == pytest.approx(0.0, abs=1e-9)
    assert trades[0]["pnl_usd"] == pytest.approx(expected, rel=1e-9)


def test_negative_funding_pays_when_long_perp():
    s = FundingCarrySettings(
        min_funding_bps=1.0, max_basis_bps=30.0,
        max_pos_per_symbol_usd=1000.0,
        spot_taker_fee=0.0, perp_taker_fee=0.0, slippage_bps=0.0,
    )
    funding, spot, perp = _flat_frames(-4.0, 0.0, 30)
    _, trades = simulate_symbol("BTCUSDT", funding, spot, perp, s)
    assert trades[0]["direction"] == "short_spot_long_perp"
    assert trades[0]["funding_usd"] > 0


def test_round_trip_fees_exact():
    s = FundingCarrySettings(
        min_funding_bps=1.0, max_basis_bps=30.0,
        max_pos_per_symbol_usd=1000.0,
        spot_taker_fee=0.0010, perp_taker_fee=0.0005, slippage_bps=2.0,
    )
    n = 20
    ts = pd.date_range("2024-07-01", periods=n, freq="8h", tz="UTC")
    rates = [2.0 / 1e4] * 10 + [0.0] * (n - 10)
    funding = pd.DataFrame({"ts": ts, "funding_rate": rates})
    spot = pd.DataFrame({"ts": ts, "close": 100.0})
    perp = pd.DataFrame({"ts": ts, "close": 100.0})
    _, trades = simulate_symbol("BTCUSDT", funding, spot, perp, s)
    assert len(trades) == 1
    expected_fees = 2 * s.cost_bps_per_leg_change / 1e4 * 1000.0
    assert trades[0]["fees_usd"] == pytest.approx(expected_fees, rel=1e-9)
    assert trades[0]["funding_usd"] == pytest.approx(
        1000.0 * 2.0 / 1e4 * 9, rel=1e-9)


def test_basis_convergence_pnl_sign():
    s = FundingCarrySettings(
        min_funding_bps=1.0, max_basis_bps=30.0,
        max_pos_per_symbol_usd=1000.0,
        spot_taker_fee=0.0, perp_taker_fee=0.0, slippage_bps=0.0,
    )
    n = 12
    ts = pd.date_range("2024-07-01", periods=n, freq="8h", tz="UTC")
    funding = pd.DataFrame({"ts": ts, "funding_rate": [3.0 / 1e4] * n})
    spot = pd.DataFrame({"ts": ts, "close": [100.0] * n})
    basis = np.linspace(20.0, 0.0, n)
    perp = pd.DataFrame({"ts": ts, "close": 100.0 * (1 + basis / 1e4)})
    _, trades = simulate_symbol("BTCUSDT", funding, spot, perp, s)
    assert trades[0]["basis_usd"] == pytest.approx(
        1000.0 * 20.0 / 1e4, rel=0.05)


def test_backtest_determinism_same_seed_same_result():
    s = FundingCarrySettings(symbols=["BTCUSDT", "ETHUSDT"], days=30, seed=7)
    d1 = synthetic_data(s.symbols, s.days, s.seed)
    d2 = synthetic_data(s.symbols, s.days, s.seed)
    _, m1, _ = run_backtest(s, data=d1)
    _, m2, _ = run_backtest(s, data=d2)
    assert m1["total_return"] == pytest.approx(m2["total_return"], rel=1e-12)
    assert m1["sharpe"] == pytest.approx(m2["sharpe"], rel=1e-12)
    assert m1["trades_count"] == m2["trades_count"]


def test_backtest_different_seed_differs():
    s = FundingCarrySettings(symbols=["BTCUSDT"], days=30, seed=1)
    _, m1, _ = run_backtest(s, data=synthetic_data(s.symbols, s.days, 1))
    _, m2, _ = run_backtest(s, data=synthetic_data(s.symbols, s.days, 2))
    assert m1["total_return"] != pytest.approx(m2["total_return"], rel=1e-12)


def test_backtest_metrics_keys_present():
    s = FundingCarrySettings(
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"], days=20, seed=3)
    _, m, _ = run_backtest(s, data=synthetic_data(s.symbols, s.days, s.seed))
    for key in ("total_return", "sharpe", "max_dd", "avg_basis_at_entry_bps",
                "hit_rate", "trades_count"):
        assert key in m
    assert m["max_dd"] <= 0.0


def test_missing_symbol_data_is_tolerated():
    s = FundingCarrySettings(symbols=["BTCUSDT", "ETHUSDT"], days=20, seed=5)
    data = synthetic_data(["BTCUSDT"], s.days, s.seed)
    daily, m, _ = run_backtest(s, data=data)
    assert len(daily) > 0
    assert isinstance(m["trades_count"], int)


def test_total_return_matches_trade_pnl():
    s = FundingCarrySettings(symbols=["BTCUSDT", "ETHUSDT"], days=30, seed=99)
    _, m, trades = run_backtest(s, data=synthetic_data(s.symbols, s.days, s.seed))
    assert trades, "need at least one trade"
    cap = m["total_capital_usd"]
    trades_net = sum(t["pnl_usd"] for t in trades)
    assert m["total_return"] * cap == pytest.approx(trades_net, abs=1e-6)
