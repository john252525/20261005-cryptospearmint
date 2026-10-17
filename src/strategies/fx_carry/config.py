from __future__ import annotations

from typing import Dict, List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FXCarrySettings(BaseSettings):
    """Configuration for the G10 FX carry strategy."""

    model_config = SettingsConfigDict(env_prefix="FXC_", extra="ignore")

    # USD-quote pairs (EURUSD=X means EUR/USD, base EUR) plus USD-base pairs.
    pairs: List[str] = Field(
        default_factory=lambda: [
            "EURUSD=X",
            "GBPUSD=X",
            "JPY=X",       # USD/JPY (USD base)
            "AUDUSD=X",
            "NZDUSD=X",
            "USDCAD=X",
            "USDCHF=X",
            "USDNOK=X",
            "USDSEK=X",
        ]
    )
    g10_rates_url: str = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
    rate_series: Dict[str, str] = Field(
        default_factory=lambda: {
            "USD": "IR3TIB01USM156N",
            "EUR": "IR3TIB01EZM156N",
            "GBP": "IR3TIB01GBM156N",
            "JPY": "IR3TIB01JPM156N",
            "AUD": "IR3TIB01AUM156N",
            "NZD": "IR3TIB01NZM156N",
            "CAD": "IR3TIB01CAM156N",
            "CHF": "IR3TIB01CHM156N",
            "NOK": "IR3TIB01NOM156N",
            "SEK": "IR3TIB01SEM156N",
        }
    )
    days: int = 1095  # ~3 years
    min_carry_bps: float = 50.0  # min annualised interest differential (bps)
    vol_filter_lookback_days: int = 30
    vol_filter_max_pct: float = 1.5  # skip pair if vol > 1.5x cross-sectional median
    max_positions: int = 3
    risk_per_trade_pct: float = 25.0  # % NAV notional per pair
    commission_bps: float = 2.0
    slippage_bps: float = 3.0
    seed: int = 42
    journal_path: str = "journal/fx_carry.jsonl"
    results_dir: str = "backtest/results"
    cache_path: str = "data/fx_cache.parquet"
    rates_cache_path: str = "data/rates_cache.parquet"

    @property
    def round_trip_cost_bps(self) -> float:
        """Entry + exit cost in bps of notional."""
        return 2.0 * (self.commission_bps + self.slippage_bps)
