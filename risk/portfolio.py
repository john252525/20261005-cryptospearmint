"""Thin wrapper around Portfolio: ingest positions / fills / marks."""
from __future__ import annotations
from typing import Any

from risk.structures import Order, Portfolio, Position


class PortfolioManager:
    def __init__(self, portfolio: Portfolio) -> None:
        self.p = portfolio

    def update_prices(self, prices) -> None:
        if not isinstance(prices, dict):
            prices = dict(prices)
        self.p.mark(prices)

    def apply_fill(self, order: Order, fill_price=None, fee: float = 0.0) -> float:
        return self.p.apply_fill(order, fill_price, fee)

    def update_from_dict(self, snapshot: dict[str, Any]) -> None:
        """Snapshot::

            {"cash": 100_000,
             "peak_nav": 100_000,
             "positions": {"AAPL": {"qty": 10, "avg_price": 180.0,
                                     "last_price": 160.0}}}
        """
        if "cash" in snapshot:
            self.p.cash = float(snapshot["cash"])
        if "realized_pnl" in snapshot:
            self.p.realized_pnl = float(snapshot["realized_pnl"])
        if "nav_start_of_day" in snapshot:
            self.p.nav_start_of_day = float(snapshot["nav_start_of_day"])
        if "peak_nav" in snapshot:
            self.p.peak_nav = float(snapshot["peak_nav"])

        raw = snapshot.get("positions")
        if raw is None:
            return
        items = raw.items() if isinstance(raw, dict) \
                else ((r["symbol"], r) for r in raw)
        for sym, row in items:
            self.p.positions[sym] = Position(
                sym,
                float(row.get("qty", 0.0)),
                float(row.get("avg_price", 0.0)),
                float(row.get("last_price", 0.0))
                or float(row.get("avg_price", 0.0)),
            )
        if self.p.nav > self.p.peak_nav:
            self.p.peak_nav = self.p.nav

    def update_from_dataframe(self, df) -> None:
        required = {"symbol", "qty", "avg_price"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame missing columns: {sorted(missing)}")
        has_last = "last_price" in df.columns
        for row in df.itertuples(index=False):
            avg = float(row.avg_price)
            last = float(getattr(row, "last_price")) if has_last else avg
            self.p.positions[str(row.symbol)] = Position(
                str(row.symbol), float(row.qty), avg, last or avg)
        if self.p.nav > self.p.peak_nav:
            self.p.peak_nav = self.p.nav
