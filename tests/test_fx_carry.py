"""Unit tests for the G10 FX carry strategy."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.strategies.fx_carry.config import FXCarrySettings
from src.strategies.fx_carry.signal import (
    PAIR_CCY, compute_carry, compute_vol_filter, generate_signals,
)
from src.strategies.fx_carry.backtest import run_backtest, compute_metrics, Trade


def _rates(**kw) -> pd.DataFrame:
    idx = pd.date_range("2023-01-01", periods=10, freq="ME")
    data = {k.upper(): [v] * len(idx) for k, v in kw.items()}
    return pd.DataFrame(data, index=idx)


def _flat_prices(pairs, n=120, vol=0.0005, seed=7) -> pd.DataFrame:
    rs = np.random.RandomState(seed)
    idx = pd.bdate_range("2023-01-02", periods=n)
    out = {}
    for p in pairs:
        out[p] = np.exp(np.cumsum(rs.randn(n) * vol)) * 1.1
    return pd.DataFrame(out, index=idx)


# 1 -----------------------------------------------------------------------
def test_compute_carry_positive_diff():
    r = _rates(AUD=4.5, USD=5.0, NZD=5.5, JPY=0.1)
    c = compute_carry("AUDUSD=X", r)
    assert pytest.approx(c["carry_bps"], abs=1e-6) == -50.0
    assert c["base_ccy"] == "AUD" and c["quote_ccy"] == "USD"


# 2 -----------------------------------------------------------------------
def test_direction_long_high_yield():
    # 50 bps differential vs 40 bps threshold => clearly long (not a boundary).
    s = FXCarrySettings(pairs=["NZDUSD=X"], min_carry_bps=40.0,
                        vol_filter_max_pct=1.5)
    r = _rates(NZD=5.5, USD=5.0)
    px = _flat_prices(["NZDUSD=X"], n=120, vol=0.0005, seed=3)
    sigs = generate_signals(r, px, settings=s, as_of=px.index[-1])
    sigs = [x for x in sigs if x.pair == "NZDUSD=X"]
    assert len(sigs) == 1
    assert sigs[0].direction == "long"
    assert sigs[0].carry_bps == pytest.approx(50.0, abs=1e-6)


# 3 -----------------------------------------------------------------------
def test_vol_filter_blocks_crash():
    s = FXCarrySettings(pairs=["AUDUSD=X", "NZDUSD=X", "EURUSD=X"],
                        min_carry_bps=50.0, vol_filter_max_pct=1.5)
    r = _rates(AUD=6.0, NZD=0.5, EUR=0.2, USD=0.2)
    # AUD is a crash regime: huge vol relative to the others.
    rs = np.random.RandomState(11)
    idx = pd.bdate_range("2023-01-02", periods=120)
    px = pd.DataFrame({
        "AUDUSD=X": np.exp(np.cumsum(rs.randn(120) * 0.05)),   # ~80% ann vol
        "NZDUSD=X": np.exp(np.cumsum(rs.randn(120) * 0.002)),
        "EURUSD=X": np.exp(np.cumsum(rs.randn(120) * 0.002)),
    }, index=idx)
    sigs = {x.pair: x for x in generate_signals(r, px, settings=s, as_of=idx[-1])}
    assert sigs["AUDUSD=X"].direction is None
    assert sigs["AUDUSD=X"].ann_vol_pct > 30.0


# 4 -----------------------------------------------------------------------
def test_vol_filter_allows_normal():
    s = FXCarrySettings(pairs=["AUDUSD=X", "NZDUSD=X", "EURUSD=X"],
                        min_carry_bps=50.0, vol_filter_max_pct=1.5)
    r = _rates(AUD=6.0, NZD=0.5, EUR=0.2, USD=0.2)
    rs = np.random.RandomState(12)
    idx = pd.bdate_range("2023-01-02", periods=120)
    px = pd.DataFrame({
        p: np.exp(np.cumsum(rs.randn(120) * 0.002))
        for p in ("AUDUSD=X", "NZDUSD=X", "EURUSD=X")
    }, index=idx)
    sigs = {x.pair: x for x in generate_signals(r, px, settings=s, as_of=idx[-1])}
    assert sigs["AUDUSD=X"].direction == "long"


# 5 -----------------------------------------------------------------------
def test_backtest_determinism():
    s = FXCarrySettings(min_carry_bps=50.0, max_positions=3)
    pairs = ["AUDUSD=X", "NZDUSD=X", "EURUSD=X", "JPY=X", "USDCHF=X"]
    r = _rates(AUD=5.0, NZD=5.5, EUR=0.5, JPY=-0.1, CHF=-0.75, USD=1.0)
    px = _flat_prices(pairs, n=300, vol=0.004, seed=21)
    a = run_backtest(px, r, settings=s)
    b = run_backtest(px, r, settings=s)
    assert a.metrics["sharpe"] == b.metrics["sharpe"]
    assert a.metrics["trades_count"] == b.metrics["trades_count"]
    pd.testing.assert_series_equal(
        a.equity.reset_index(drop=True), b.equity.reset_index(drop=True)
    )


# 6 -----------------------------------------------------------------------
def test_fee_application():
    s = FXCarrySettings(commission_bps=2.0, slippage_bps=3.0)
    # round trip = 2*(2+3) = 10 bps
    assert s.round_trip_cost_bps == 10.0
    notional = 250_000.0
    expected_rt = notional * 10.0 / 10_000.0
    entry = 0.5 * (s.round_trip_cost_bps / 10_000.0) * notional
    exit_ = 0.5 * (s.round_trip_cost_bps / 10_000.0) * notional
    assert pytest.approx(entry + exit_, rel=1e-9) == expected_rt
    # And the trade object records the same total on a synthetic round trip.
    t = Trade(pair="AUDUSD=X", direction="long",
              entry_date=pd.Timestamp("2023-01-02"),
              exit_date=pd.Timestamp("2023-01-09"),
              entry_price=1.0, exit_price=1.0, notional_usd=notional,
              gross_pnl=0.0, carry_pnl=0.0, fees=entry + exit_,
              net_pnl=-(entry + exit_), holding_days=7)
    assert pytest.approx(t.fees) == expected_rt
    assert t.net_pnl < 0


# 7 -----------------------------------------------------------------------
def test_max_positions_respected():
    pairs = ["AUDUSD=X", "NZDUSD=X", "EURUSD=X", "GBPUSD=X", "JPY=X"]
    s = FXCarrySettings(pairs=pairs, min_carry_bps=50.0, max_positions=3)
    r = _rates(AUD=6.0, NZD=6.0, EUR=6.0, GBP=6.0, JPY=-2.0, USD=0.0)
    px = _flat_prices(pairs, n=200, vol=0.003, seed=5)
    res = run_backtest(px, r, settings=s)
    open_pairs = set()
    for t in res.trades:
        open_pairs.add(t.pair)
    # At no point should more than 3 distinct pairs be opened per rebalance:
    # check by reconstructing max concurrent from trade overlap.
    events = []
    for t in res.trades:
        events.append((t.entry_date, 1))
        events.append((t.exit_date, -1))
    events.sort()
    cur = peak = 0
    for _, d in events:
        cur += d
        peak = max(peak, cur)
    assert peak <= 3, f"peak concurrent positions {peak} exceeded max_positions=3"


# 8 -----------------------------------------------------------------------
def test_flat_signal_on_low_carry():
    s = FXCarrySettings(pairs=["AUDUSD=X"], min_carry_bps=50.0,
                        vol_filter_max_pct=1.5)
    r = _rates(AUD=5.2, USD=5.0)  # 20 bps < 50 bps threshold
    px = _flat_prices(["AUDUSD=X"], n=120, vol=0.002, seed=8)
    sigs = generate_signals(r, px, settings=s, as_of=px.index[-1])
    aud = [x for x in sigs if x.pair == "AUDUSD=X"][0]
    assert aud.direction is None
    assert aud.carry_bps == pytest.approx(20.0, abs=1e-6)
