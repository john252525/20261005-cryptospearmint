import importlib.util
import pandas as pd
import pytest

from src.strategies.funding_carry.config import FundingCarrySettings
from src.strategies.funding_carry.backtest import sensitivity_grid, synthetic_data


def test_alt_symbols_in_grid():
    syms = ["BTCUSDT", "DOGEUSDT", "WIFUSDT"]
    data = synthetic_data(syms, 20, 11)
    g = sensitivity_grid([1.0, 2.0], ["vip0"], days=20, symbols=syms, data=data, seed=11)
    assert len(g) == 2
    assert (g["trades_count"] >= 0).all()


def test_vip4_tier_costs():
    v0 = FundingCarrySettings(fee_tier="vip0")
    v1 = FundingCarrySettings(fee_tier="vip1_bnb")
    v4 = FundingCarrySettings(fee_tier="vip4")
    assert v0.cost_bps_per_leg_change == pytest.approx(19.0)
    assert v1.cost_bps_per_leg_change == pytest.approx(13.0)
    assert v4.cost_bps_per_leg_change == pytest.approx(10.0)


def test_distribution_stats():
    spec = importlib.util.spec_from_file_location("bva", "scripts/baseline_vs_alt.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    ts = pd.date_range("2026-07-01", periods=5, freq="8h", tz="UTC")
    df = pd.DataFrame({"ts": ts, "funding_rate": [0.0001, 0.0002, -0.0001, 0.0010, 0.0]})
    r = m.stats_row("X", df)
    assert r["n_events"] == 5
    assert r["median_bps"] == pytest.approx(1.0)
    assert r["pct_gt_5bps"] == pytest.approx(1 / 5)
    assert r["pct_gt_10bps"] == pytest.approx(0.0)


def test_grid_shape_3x2():
    data = synthetic_data(["BTCUSDT"], 20, 7)
    g = sensitivity_grid([0.5, 1.0, 2.0], ["vip0", "vip4"],
                         days=20, symbols=["BTCUSDT"], data=data, seed=7)
    assert len(g) == 6


def test_grid_empty_data_does_not_crash():
    g = sensitivity_grid([1.0, 2.0], ["vip0", "vip4"],
                         days=10, symbols=["BTCUSDT"], data={}, seed=1)
    assert len(g) == 4
    assert (g["trades_count"] == 0).all()
