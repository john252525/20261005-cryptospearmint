from datetime import datetime, timezone

import pytest

from src.strategies.funding_carry.signal import (
    Signal,
    classify,
    compute_basis_bps,
    mid_price,
)


def test_classify_long_spot_short_perp():
    d, c = classify(2.5, 5.0, 1.0, 30.0)
    assert d == "long_spot_short_perp"
    assert 0.0 < c <= 1.0


def test_classify_short_spot_long_perp():
    d, c = classify(-3.0, -4.0, 1.0, 30.0)
    assert d == "short_spot_long_perp"
    assert 0.0 < c <= 1.0


def test_classify_flat_below_min_funding():
    assert classify(0.4, 3.0, 1.0, 30.0)[0] == "flat"


def test_classify_flat_on_basis_breach():
    assert classify(5.0, 55.0, 1.0, 30.0)[0] == "flat"


def test_classify_nan_is_flat():
    nan = float("nan")
    assert classify(nan, 1.0, 1.0, 30.0)[0] == "flat"
    assert classify(5.0, nan, 1.0, 30.0)[0] == "flat"


def test_confidence_monotonic_in_funding():
    _, c1 = classify(1.0, 0.0, 1.0, 30.0)
    _, c2 = classify(4.0, 0.0, 1.0, 30.0)
    assert c2 > c1


def test_basis_sign_and_magnitude():
    assert compute_basis_bps(100.0, 100.3) == pytest.approx(30.0)
    assert compute_basis_bps(100.0, 99.7) == pytest.approx(-30.0)


def test_mid_price_missing_data_is_none():
    assert mid_price(None, 100.0) is None
    assert mid_price(0.0, 100.0) is None
    assert mid_price(101.0, 100.0) is None
    assert mid_price(float("nan"), 100.0) is None
    assert mid_price(99.0, 101.0) == pytest.approx(100.0)


def test_signal_to_dict_roundtrip():
    s = Signal(
        ts=datetime(2024, 9, 1, tzinfo=timezone.utc),
        symbol="BTCUSDT",
        exchange="binance",
        funding_rate=0.0002,
        funding_bps_8h=2.0,
        spot_price=60000.0,
        perp_price=60060.0,
        basis_bps=10.0,
        direction="long_spot_short_perp",
        confidence=0.5,
    )
    d = s.to_dict()
    assert d["symbol"] == "BTCUSDT"
    assert d["ts"].startswith("2024-09-01")
    assert d["direction"] == "long_spot_short_perp"
