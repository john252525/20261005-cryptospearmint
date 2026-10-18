from __future__ import annotations
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Short13DSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='S13D_', extra='ignore')

    scraper_db: str = '/root/env-scraper-wt/state/scraper.db'
    state_db: str = '/root/short-13d-paper/state/short_13d.db'
    journal_path: str = '/root/short-13d-paper/journal/short_13d.jsonl'
    lookback_days: int = 7
    min_adv_usd: float = 1_000_000.0
    holding_days: int = 20
    notional_per_trade_usd: float = 100_000.0
    borrow_rates: list[float] = Field(default_factory=lambda: [0.30, 0.50, 0.80])
    bid_ask_bps: float = 15.0
