from __future__ import annotations

import pandas as pd
import pytest

from src.research.backtest_funding import simulate


@pytest.fixture()
def bars():
    idx = pd.date_range("2025-01-01", periods=48 * 60, freq="1min", tz="UTC")
    return pd.Series(100.0, index=idx)


def _funding(idx):
    f_ts = idx[(idx.minute == 0) & (idx.hour % 8 == 0)]
    return pd.Series(0.0001, index=f_ts)


def _sig(idx):
    e = pd.Series(False, index=idx)
    x = pd.Series(False, index=idx)
    e.iloc[0] = True
    x.iloc[-1] = True
    return e, x


def test_positive_funding_yields_income(bars):
    f = _funding(bars.index)
    e, x = _sig(f.index)
    res = simulate(bars, f, e, x, init_cash=100_000.0,
                   spot_fee=0.0, perp_fee=0.0, deploy_ratio=1.0)
    s = res["stats"]
    assert s["Trades"] == 1
    assert s["Funding Events"] >= 5
    assert s["Funding Income [USDT]"] > 0
    assert s["final_equity"] > 100_000.0


def test_fees_eat_small_funding(bars):
    f = _funding(bars.index)
    e, x = _sig(f.index)
    res = simulate(bars, f, e, x, init_cash=100_000.0,
                   spot_fee=0.0100, perp_fee=0.0100, deploy_ratio=1.0)
    assert res["stats"]["final_equity"] < 100_000.0


def test_no_signal_no_trades(bars):
    f = _funding(bars.index)
    e = pd.Series(False, index=f.index)
    x = pd.Series(False, index=f.index)
    res = simulate(bars, f, e, x, init_cash=10_000.0,
                   spot_fee=0.001, perp_fee=0.0005, deploy_ratio=0.9)
    assert res["stats"]["Trades"] == 0
    assert res["stats"]["final_equity"] == 10_000.0
