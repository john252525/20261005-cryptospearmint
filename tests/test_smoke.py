"""Smoke: импорт config, парсинг yaml, границы risk.check_order."""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_config_module_imports() -> None:
    from src.config import BacktestConfig, Config, RiskConfig, load_config  # noqa: F401

    cfg = Config()
    assert cfg.crypto.symbol == "BTCUSDT"
    assert cfg.crypto.interval == "1m"
    assert cfg.backtest.fast < cfg.backtest.slow
    assert cfg.risk.max_order_notional > 0


def test_parse_example_yaml() -> None:
    from src.config import load_config

    cfg = load_config(REPO_ROOT / "configs" / "example.yaml")
    assert cfg.crypto.symbol == "BTCUSDT"
    assert cfg.crypto.days == 7
    assert cfg.backtest.fast == 20
    assert cfg.backtest.slow == 50
    assert cfg.risk.max_open_positions == 5


def test_check_order_boundaries() -> None:
    from src.risk.limits import (
        AccountState,
        LimitBreach,
        Order,
        RiskLimits,
        check_order,
    )

    limits = RiskLimits(
        max_order_notional=1_000.0,
        max_position_notional=5_000.0,
        max_open_positions=5,
    )
    state = AccountState(equity=100_000.0, open_positions=0, position_notional=0.0)

    check_order(Order("BTCUSDT", "buy", 0.01, 100_000.0), state, limits)

    with pytest.raises(LimitBreach, match="max_order_notional"):
        check_order(Order("BTCUSDT", "buy", 0.0101, 100_000.0), state, limits)

    with pytest.raises(LimitBreach, match="max_position_notional"):
        check_order(
            Order("BTCUSDT", "buy", 0.003, 100_000.0),
            AccountState(equity=100_000.0, open_positions=1, position_notional=4_800.0),
            limits,
        )

    with pytest.raises(LimitBreach, match="max_open_positions"):
        check_order(
            Order("BTCUSDT", "buy", 0.001, 100_000.0),
            AccountState(equity=100_000.0, open_positions=5, position_notional=0.0),
            limits,
        )

    with pytest.raises(LimitBreach, match="non-positive qty"):
        check_order(Order("BTCUSDT", "buy", 0.0, 100_000.0), state, limits)
