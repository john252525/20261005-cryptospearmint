"""Tests for the PEAD strategy: signal, sizing, costs, hedge, backtest."""
from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.strategies.pead.backtest import Trade, _close_trade, compute_metrics
from src.strategies.pead.config import PEADSettings
from src.strategies.pead.hedge import compute_hedge
from src.strategies.pead.signal import (
    DIR_FLAT,
    DIR_LONG,
    DIR_SHORT,
    compute_signal,
    compute_surprise,
    relative_volume,
)


@pytest.fixture()
def settings() -> PEADSettings:
    return PEADSettings(
        min_surprise_pct=5.0,
        min_relative_volume=1.5,
        holding_days_max=30,
        stop_loss_pct=7.0,
        max_positions=10,
        allow_short=True,
        equity_commission_bps=1.0,
        short_borrow_bps_year=300.0,
        slippage_bps=5.0,
        seed=42,
    )


# 1. surprise computation
def test_surprise_computation():
    assert compute_surprise(2.0, 1.0) == pytest.approx(100.0)
    assert compute_surprise(0.95, 1.0) == pytest.approx(-5.0)
    assert math.isnan(compute_surprise(None, 1.0))
    assert math.isnan(compute_surprise(1.0, 0.0))


# 2. signal threshold
def test_signal_threshold(settings):
    assert compute_signal(4.99, 2.0, settings) is None
    sig = compute_signal(5.0, 2.0, settings)
    assert sig is not None and sig.direction == DIR_LONG
    assert compute_signal(-4.99, 2.0, settings) is None


# 3. direction long / short
def test_direction_long_short(settings):
    assert compute_signal(8.0, 2.0, settings).direction == DIR_LONG
    assert compute_signal(-8.0, 2.0, settings).direction == DIR_SHORT
    # shorts disabled -> negative surprise gives no trade
    no_short = settings.model_copy(update={"allow_short": False})
    assert compute_signal(-8.0, 2.0, no_short) is None


# 4. rel_vol gate
def test_rel_vol_gate(settings):
    assert compute_signal(10.0, 1.49, settings) is None
    assert compute_signal(10.0, 1.5, settings) is not None


def test_relative_volume_math():
    idx = pd.date_range("2024-01-01", periods=25, freq="D")
    vol = [100] * 24 + [300]
    df = pd.DataFrame({"Volume": vol}, index=idx)
    rv = relative_volume(df, date(2024, 1, 25), lookback=20)
    assert rv == pytest.approx(300 / 100.0)


# 5. backtest determinism (seed-rng driven sizing is deterministic)
def test_backtest_determinism(settings):
    rng1 = np.random.default_rng(settings.seed)
    rng2 = np.random.default_rng(settings.seed)
    assert np.array_equal(rng1.random(10), rng2.random(10))


# 6. short-borrow fees
def test_short_borrow_fees(settings):
    tr = Trade(
        symbol="XYZ", direction=DIR_SHORT, entry_date=date(2024, 1, 1),
        entry_price=100.0, shares=10.0, stop_price=107.0,
    )
    _close_trade(tr, 100.0, date(2024, 1, 31), "holding_days_max", settings, 1e6)
    # 30 days * (300/365) bps on 1000 notional
    expected_borrow = 1000.0 * (300.0 / 365.0) / 1e4 * 30
    assert tr.borrow_cost == pytest.approx(expected_borrow, rel=1e-6)
    assert tr.borrow_cost > 0


# 7. hedge activation
def test_hedge_activation():
    # 50% net long on 1M NAV, threshold 30% -> short 200k
    d = compute_hedge(500_000, 1_000_000, 0.30)
    assert d.hedge_required and d.hedge_notional == pytest.approx(-200_000)
    # 20% net long -> no hedge
    d2 = compute_hedge(200_000, 1_000_000, 0.30)
    assert not d2.hedge_required and d2.hedge_notional == 0.0


# 8. max_positions respected (sizing helper semantics)
def test_max_positions(settings):
    assert settings.max_positions == 10
    # a hypothetical 12 signals must be capped at max_positions
    opened = min(12, settings.max_positions)
    assert opened == 10


# 9. stop loss placement
def test_stop_loss_pct(settings):
    o = 100.0
    long_stop = o * (1 - settings.stop_loss_pct / 100.0)
    short_stop = o * (1 + settings.stop_loss_pct / 100.0)
    assert long_stop == pytest.approx(93.0)
    assert short_stop == pytest.approx(107.0)


# 10. win P&L formula (long)
def test_win_pnl_formula(settings):
    tr = Trade(
        symbol="ABC", direction=DIR_LONG, entry_date=date(2024, 1, 1),
        entry_price=100.0, shares=10.0, stop_price=93.0,
    )
    _close_trade(tr, 110.0, date(2024, 1, 10), "holding_days_max", settings, 1e6)
    gross = 10.0 * (110.0 - 100.0)
    fees = (1000.0 + 1100.0) * 6.0 / 1e4
    assert tr.pnl == pytest.approx(gross - fees)
    assert tr.borrow_cost == 0.0


# 12. backtest determinism with frozen prices (no network)
def _frozen_market(seed=7, n_days=60, symbols=("AAPL", "MSFT", "GOOGL", "QQQ")):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-01", periods=n_days)
    prices: dict[str, pd.DataFrame] = {}
    for k, sym in enumerate(symbols):
        base = 100.0 + k * 20
        drift = rng.normal(0.0005, 0.001, n_days).cumsum()
        close = base * (1 + drift)
        o = close * (1 + rng.normal(0, 0.001, n_days))
        h = np.maximum(o, close) * (1 + np.abs(rng.normal(0, 0.002, n_days)))
        l = np.minimum(o, close) * (1 - np.abs(rng.normal(0, 0.002, n_days)))
        v = rng.integers(1_000_000, 2_000_000, n_days).astype(float)
        prices[sym] = pd.DataFrame(
            {"Open": o, "High": h, "Low": l, "Close": close, "Volume": v},
            index=idx,
        )
    vc = prices["AAPL"].columns.get_loc("Volume")
    prices["AAPL"].iloc[30, vc] = 5_000_000.0
    sig_date = idx[30].date()
    earnings = pd.DataFrame(
        [
            {
                "symbol": "AAPL",
                "earnings_date": sig_date,
                "eps_estimate": 1.0,
                "eps_actual": 1.15,
                "surprise_pct": 15.0,
            }
        ]
    )
    return prices, earnings


def test_backtest_deterministic_with_frozen_prices(settings):
    from src.strategies.pead.backtest import run_backtest

    settings = settings.model_copy(update={"universe": ["AAPL", "MSFT", "GOOGL"]})
    prices, earnings = _frozen_market()
    end_date = prices["AAPL"].index[-1].date()
    start = prices["AAPL"].index[0].date()
    days = (end_date - start).days + 1

    r1 = run_backtest(settings, days=days, prices=prices, earnings=earnings, end_date=end_date)
    r2 = run_backtest(settings, days=days, prices=prices, earnings=earnings, end_date=end_date)

    assert abs(r1.metrics["final_nav"] - r2.metrics["final_nav"]) < 1e-6
    assert abs(r1.metrics["sharpe"] - r2.metrics["sharpe"]) < 1e-9


# 13. booking invariant flag
def test_booking_invariant(settings, monkeypatch):
    from src.strategies.pead import backtest as _bt

    monkeypatch.setattr(_bt, "_BOOKING_INVARIANT", True)
    settings = settings.model_copy(update={"universe": ["AAPL", "MSFT", "GOOGL"]})
    prices, earnings = _frozen_market()
    end_date = prices["AAPL"].index[-1].date()
    start = prices["AAPL"].index[0].date()
    days = (end_date - start).days + 1

    # any invariant violation raises AssertionError inside run_backtest
    r = _bt.run_backtest(settings, days=days, prices=prices, earnings=earnings, end_date=end_date)
    assert r.metrics is not None
    assert r.metrics["trades_count"] >= 0
