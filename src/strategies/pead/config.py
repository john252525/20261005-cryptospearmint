"""PEAD strategy settings (pydantic v2 + pydantic-settings).

Post-Earnings Announcement Drift: after a large earnings surprise the
price tends to keep drifting in the direction of the surprise for weeks.
We trade the drift, long on positive surprise, short on negative.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_UNIVERSE: list[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM", "V", "JNJ",
    "WMT", "PG", "XOM", "MA", "HD", "CVX", "ABBV", "PFE", "KO", "PEP",
]


class PEADSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PEAD_", env_file=".env", env_nested_delimiter="__", extra="ignore"
    )

    universe: list[str] = Field(default_factory=lambda: list(DEFAULT_UNIVERSE))

    # signal gates
    min_surprise_pct: float = 5.0
    min_relative_volume: float = 1.5

    # holding / risk
    holding_days_min: int = 5
    holding_days_max: int = 30
    stop_loss_pct: float = 7.0
    max_positions: int = 10
    risk_per_trade_pct: float = 0.25

    # costs (all in bps)
    allow_short: bool = True
    equity_commission_bps: float = 1.0
    short_borrow_bps_year: float = 300.0  # estimate
    slippage_bps: float = 5.0

    # hedge
    hedge_threshold_frac: float = 0.30  # net long > 30% NAV -> short QQQ
    hedge_symbol: str = "QQQ"

    # backtest
    days: int = 1095
    seed: int = 42

    # io
    journal_path: str = "journal/pead.jsonl"
    db_path: str = "state/pead.db"
    results_dir: str = "backtest/results"

    @property
    def commission_per_side_bps(self) -> float:
        return self.equity_commission_bps + self.slippage_bps

    @property
    def borrow_per_day_bps(self) -> float:
        return self.short_borrow_bps_year / 365.0
