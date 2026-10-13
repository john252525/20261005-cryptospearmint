"""Funding-carry strategy settings (pydantic v2 + pydantic-settings)."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FundingCarrySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FC_", env_file=".env",
                                      env_nested_delimiter="__", extra="ignore")

    symbols: list[str] = Field(default_factory=lambda: ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    exchanges: list[str] = Field(default_factory=lambda: ["binance", "bybit"])

    min_funding_bps: float = 1.0
    max_basis_bps: float = 30.0
    rebalance_threshold_bps: float = 5.0

    max_pos_per_symbol_usd: float = 1000.0
    target_leverage: float = 1.0

    poll_interval_sec: int = 30
    entry_cooldown_sec: int = 60
    kill_if_slippage_bps_gt: float = 20.0

    # Binance VIP0 taker: Spot 0.10%, USDT-M Futures 0.05%; slippage 2 bps/leg/side
    spot_taker_fee: float = 0.0010
    perp_taker_fee: float = 0.0005
    slippage_bps: float = 2.0

    funding_interval_hours: int = 8
    funding_intervals_per_day: int = 3

    days: int = 90
    seed: int = 42

    binance_fapi: str = "https://fapi.binance.com"
    binance_spot: str = "https://api.binance.com"
    bybit_v5: str = "https://api.bybit.com"
    binance_spot_testnet: str = "https://testnet.binance.vision"
    binance_futures_testnet: str = "https://testnet.binancefuture.com"

    journal_path: str = "journal/funding_carry.jsonl"
    db_path: str = "state/funding_carry.db"
    results_dir: str = "backtest/results"

    @property
    def cost_bps_per_leg_change(self) -> float:
        return self.spot_taker_fee * 1e4 + self.perp_taker_fee * 1e4 + 2.0 * self.slippage_bps

    @property
    def round_trip_cost_bps(self) -> float:
        return 2.0 * self.cost_bps_per_leg_change
