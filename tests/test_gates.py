from datetime import UTC, datetime, timedelta

from src.strategies.funding_carry.config import FundingCarrySettings
from src.strategies.funding_carry.gates import (
    CooldownGate,
    needs_rebalance,
    passes_entry_filters,
    should_exit,
)
from src.strategies.funding_carry.signal import Signal


def _sig(funding_bps, basis_bps, direction):
    return Signal(
        ts=datetime.now(UTC),
        symbol="BTCUSDT",
        exchange="binance",
        funding_rate=funding_bps / 1e4,
        funding_bps_8h=funding_bps,
        spot_price=100.0,
        perp_price=100.0,
        basis_bps=basis_bps,
        direction=direction,
        confidence=0.9,
    )


def test_cooldown_blocks_then_allows():
    g = CooldownGate(cooldown_sec=60)
    t0 = datetime(2024, 9, 1, 12, 0, 0, tzinfo=UTC)
    assert g.try_consume("BTCUSDT:binance", t0) is True
    assert g.try_consume("BTCUSDT:binance", t0 + timedelta(seconds=30)) is False
    assert g.try_consume("BTCUSDT:binance", t0 + timedelta(seconds=59)) is False
    assert g.try_consume("BTCUSDT:binance", t0 + timedelta(seconds=60)) is True


def test_cooldown_is_per_key():
    g = CooldownGate(cooldown_sec=60)
    t0 = datetime(2024, 9, 1, tzinfo=UTC)
    assert g.try_consume("BTCUSDT:binance", t0)
    assert g.try_consume("ETHUSDT:binance", t0) is True
    assert g.try_consume("BTCUSDT:bybit", t0) is True


def test_cooldown_seconds_left():
    g = CooldownGate(cooldown_sec=60)
    t0 = datetime(2024, 9, 1, tzinfo=UTC)
    g.try_consume("X", t0)
    assert g.seconds_left("X", t0 + timedelta(seconds=20)) == 40.0
    assert g.seconds_left("X", t0 + timedelta(seconds=90)) == 0.0


def test_entry_filters_basis_threshold():
    s = FundingCarrySettings(min_funding_bps=1.0, max_basis_bps=30.0)
    assert passes_entry_filters(_sig(3.0, 10.0, "long_spot_short_perp"), s) is True
    assert passes_entry_filters(_sig(3.0, 45.0, "long_spot_short_perp"), s) is False
    assert passes_entry_filters(_sig(3.0, -45.0, "long_spot_short_perp"), s) is False


def test_entry_filters_funding_threshold():
    s = FundingCarrySettings(min_funding_bps=1.0, max_basis_bps=30.0)
    assert passes_entry_filters(_sig(0.9, 1.0, "flat"), s) is False
    assert passes_entry_filters(_sig(1.5, 1.0, "long_spot_short_perp"), s) is True


def test_should_exit_on_flip_and_on_flat():
    s = FundingCarrySettings(min_funding_bps=1.0, max_basis_bps=30.0)
    assert should_exit(
        _sig(-3.0, 0.0, "short_spot_long_perp"),
        "long_spot_short_perp", s) is True
    assert should_exit(
        _sig(0.2, 0.0, "flat"),
        "long_spot_short_perp", s) is True
    assert should_exit(
        _sig(3.0, 0.0, "long_spot_short_perp"),
        "long_spot_short_perp", s) is False
    assert should_exit(
        _sig(3.0, 99.0, "flat"),
        "long_spot_short_perp", s) is True


def test_needs_rebalance():
    s = FundingCarrySettings(rebalance_threshold_bps=5.0)
    assert needs_rebalance(2.0, s) is False
    assert needs_rebalance(6.0, s) is True
    assert needs_rebalance(-9.0, s) is True
