"""configs/example.yaml -> типизированный Config."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class CryptoConfig(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "1m"
    days: int = Field(default=7, ge=1)


class DataConfig(BaseModel):
    bars_dir: Path = Path("data/bars")


class BacktestConfig(BaseModel):
    fast: int = Field(default=20, ge=1)
    slow: int = Field(default=50, ge=1)
    init_cash: float = Field(default=100_000.0, gt=0)
    fees: float = Field(default=0.001, ge=0.0)


class RiskConfig(BaseModel):
    max_order_notional: float = Field(default=1_000.0, gt=0)
    max_position_notional: float = Field(default=10_000.0, gt=0)
    max_open_positions: int = Field(default=5, ge=1)


class Config(BaseModel):
    crypto: CryptoConfig = CryptoConfig()
    data: DataConfig = DataConfig()
    backtest: BacktestConfig = BacktestConfig()
    risk: RiskConfig = RiskConfig()


def load_config(path: str | Path) -> Config:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return Config(**raw)


__all__ = [
    "BacktestConfig", "Config", "CryptoConfig", "DataConfig",
    "RiskConfig", "load_config",
]
