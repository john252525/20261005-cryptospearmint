"""Funding + basis signal ingestion: Binance & Bybit public REST."""
from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from .config import FundingCarrySettings

log = logging.getLogger(__name__)
DIR_LONG_SPOT_SHORT_PERP = "long_spot_short_perp"
DIR_SHORT_SPOT_LONG_PERP = "short_spot_long_perp"
DIR_FLAT = "flat"


@dataclass(slots=True)
class Signal:
    ts: datetime
    symbol: str
    exchange: str
    funding_rate: float
    funding_bps_8h: float
    spot_price: float
    perp_price: float
    basis_bps: float
    direction: str
    confidence: float

    def to_dict(self) -> dict:
        return {"ts": self.ts.isoformat(), "symbol": self.symbol,
                "exchange": self.exchange, "funding_rate": self.funding_rate,
                "funding_bps_8h": self.funding_bps_8h,
                "spot_price": self.spot_price, "perp_price": self.perp_price,
                "basis_bps": self.basis_bps, "direction": self.direction,
                "confidence": self.confidence}


def mid_price(bid, ask) -> float | None:
    if bid is None or ask is None:
        return None
    try:
        bid = float(bid); ask = float(ask)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(bid) or not math.isfinite(ask):
        return None
    if bid <= 0 or ask <= 0 or ask < bid:
        return None
    return 0.5 * (bid + ask)


def compute_basis_bps(spot: float, perp: float) -> float:
    if not spot or not math.isfinite(spot) or not math.isfinite(perp):
        return float("nan")
    return (perp - spot) / spot * 1e4


def classify(funding_bps_8h, basis_bps, min_funding_bps, max_basis_bps):
    if funding_bps_8h != funding_bps_8h or basis_bps != basis_bps:
        return DIR_FLAT, 0.0
    if abs(basis_bps) > max_basis_bps:
        return DIR_FLAT, 0.0
    if funding_bps_8h >= min_funding_bps:
        direction = DIR_LONG_SPOT_SHORT_PERP
    elif funding_bps_8h <= -min_funding_bps:
        direction = DIR_SHORT_SPOT_LONG_PERP
    else:
        return DIR_FLAT, 0.0
    f = abs(funding_bps_8h) / max(3.0 * min_funding_bps, 1e-9)
    b = 1.0 - min(1.0, abs(basis_bps) / max(max_basis_bps, 1e-9))
    return direction, max(0.0, min(1.0, f * b))


async def fetch_binance(client: httpx.AsyncClient, symbol: str, s: FundingCarrySettings):
    try:
        prem_r, book_r = await asyncio.gather(
            client.get(f"{s.binance_fapi}/fapi/v1/premiumIndex",
                       params={"symbol": symbol}),
            client.get(f"{s.binance_spot}/api/v3/ticker/bookTicker",
                       params={"symbol": symbol}))
        prem_r.raise_for_status(); book_r.raise_for_status()
        prem = prem_r.json(); book = book_r.json()
    except Exception as exc:
        log.warning("binance fetch failed %s: %s", symbol, exc); return None
    spot = mid_price(book.get("bidPrice"), book.get("askPrice"))
    if spot is None:
        return None
    try:
        funding_rate = float(prem["lastFundingRate"])
        perp = float(prem["markPrice"])
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("binance malformed %s: %s", symbol, exc); return None
    bb = compute_basis_bps(spot, perp)
    fb = funding_rate * 1e4
    d, c = classify(fb, bb, s.min_funding_bps, s.max_basis_bps)
    return Signal(datetime.now(timezone.utc), symbol, "binance",
                  funding_rate, fb, spot, perp, bb, d, c)


async def fetch_bybit(client: httpx.AsyncClient, symbol: str, s: FundingCarrySettings):
    try:
        lin_r, spot_r = await asyncio.gather(
            client.get(f"{s.bybit_v5}/v5/market/tickers",
                       params={"category": "linear", "symbol": symbol}),
            client.get(f"{s.bybit_v5}/v5/market/tickers",
                       params={"category": "spot", "symbol": symbol}))
        lin_r.raise_for_status(); spot_r.raise_for_status()
        lin = (lin_r.json().get("result") or {}).get("list") or []
        spo = (spot_r.json().get("result") or {}).get("list") or []
        if not lin or not spo:
            return None
        lin, spo = lin[0], spo[0]
    except Exception as exc:
        log.warning("bybit fetch failed %s: %s", symbol, exc); return None
    spot = mid_price(spo.get("bid1Price"), spo.get("ask1Price"))
    if spot is None:
        return None
    try:
        funding_rate = float(lin["fundingRate"])
        perp = float(lin["markPrice"])
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("bybit malformed %s: %s", symbol, exc); return None
    bb = compute_basis_bps(spot, perp)
    fb = funding_rate * 1e4
    d, c = classify(fb, bb, s.min_funding_bps, s.max_basis_bps)
    return Signal(datetime.now(timezone.utc), symbol, "bybit",
                  funding_rate, fb, spot, perp, bb, d, c)


_FETCHERS = {"binance": fetch_binance, "bybit": fetch_bybit}


async def get_signals(settings: FundingCarrySettings,
                      client: httpx.AsyncClient | None = None) -> list[Signal]:
    own = client is None
    if own:
        client = httpx.AsyncClient(timeout=10.0)
    tasks, keys = [], []
    for exch in settings.exchanges:
        f = _FETCHERS.get(exch)
        if f is None:
            continue
        for sym in settings.symbols:
            tasks.append(f(client, sym, settings)); keys.append((exch, sym))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    if own:
        await client.aclose()
    out: list[Signal] = []
    for key, res in zip(keys, results):
        if isinstance(res, Exception):
            log.warning("signal task %s raised: %s", key, res); continue
        if res is not None:
            out.append(res)
    return out
