"""Binance Testnet adapter (skeleton).

Two modes:

  Mode 1 (no API keys)   : public market data only (`market_price`).
  Mode 2 (with API keys) : signed `/api/v3/account` probe to verify keys,
                           plus `account_status()`. Real order submission
                           is not wired yet (see NotImplementedError).

HTTP via `requests` with explicit timeouts. Errors are logged through
loguru and surfaced as False / exceptions where appropriate.

Environment:
    BINANCE_TESTNET_API_KEY
    BINANCE_TESTNET_API_SECRET
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Callable, Optional
from urllib.parse import urlencode

import requests
from loguru import logger


_DEFAULT_SPOT = "https://testnet.binance.vision"
_DEFAULT_FUT = "https://testnet.binancefuture.com"
_TIMEOUT = 10.0
_ORDER_NOT_IMPL_NO_KEYS = (
    "BinanceTestnet: real orders require valid API keys — "
    "not yet implemented in this adapter"
)
_ORDER_NOT_IMPL_KEYS = (
    "Real order submission will be added in next iteration — "
    "currently the adapter verifies connectivity only"
)


class BinanceTestnetAdapter:
    """Adapters Binance Spot/Futures testnet.

    Currently implements market data + auth verification only.
    Order lifecycle methods raise NotImplementedError in both modes.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        spot_base: str = _DEFAULT_SPOT,
        fut_base: str = _DEFAULT_FUT,
    ) -> None:
        self.api_key = api_key or os.environ.get("BINANCE_TESTNET_API_KEY")
        self.api_secret = api_secret or os.environ.get(
            "BINANCE_TESTNET_API_SECRET")
        self.spot_base = spot_base.rstrip("/")
        self.fut_base = fut_base.rstrip("/")
        self._authenticated: Optional[bool] = None
        self._account_cache: Optional[dict] = None

    # ------------------------------------------------------------------
    # auth
    # ------------------------------------------------------------------
    def _has_keys(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def _signed(self, path: str, params: Optional[dict] = None,
                base: Optional[str] = None) -> dict:
        if not self._has_keys():
            raise RuntimeError("no API keys")
        base = (base or self.spot_base).rstrip("/")
        params = dict(params or {})
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000
        query = urlencode(params, doseq=True)
        signature = hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()
        url = f"{base}{path}?{query}&signature={signature}"
        headers = {"X-MBX-APIKEY": self.api_key}
        resp = requests.get(url, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def is_authenticated(self) -> bool:
        if self._authenticated is not None:
            return self._authenticated
        if not self._has_keys():
            self._authenticated = False
            return False
        try:
            acct = self._signed("/api/v3/account")
            self._account_cache = acct
            self._authenticated = True
            logger.info("binance testnet: auth OK (accountType={})",
                        acct.get("accountType", "?"))
            return True
        except Exception as exc:
            logger.warning("binance testnet: auth failed: {!r}", exc)
            self._authenticated = False
            return False

    def account_status(self) -> dict:
        if not self.is_authenticated():
            return {"authenticated": False}
        acct = self._account_cache or self._signed("/api/v3/account")
        masked = {
            k: v for k, v in acct.items()
            if k in ("accountType", "canTrade", "canWithdraw",
                     "canDeposit", "makerCommission", "takerCommission",
                     "updateTime")
        }
        masked["authenticated"] = True
        masked["balance_count"] = len(acct.get("balances", []) or [])
        return masked

    # ------------------------------------------------------------------
    # market data
    # ------------------------------------------------------------------
    def market_price(self, symbol: str) -> float:
        url = f"{self.spot_base}/api/v3/ticker/price"
        try:
            resp = requests.get(url, params={"symbol": symbol.upper()},
                                timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            px = float(data["price"])
            logger.debug("binance price {} = {}", symbol, px)
            return px
        except Exception as exc:
            logger.error("binance market_price {} failed: {!r}",
                         symbol, exc)
            raise

    # ------------------------------------------------------------------
    # Broker protocol — order lifecycle (not implemented)
    # ------------------------------------------------------------------
    def _raise_order_not_impl(self):
        msg = _ORDER_NOT_IMPL_KEYS if self.is_authenticated() \
              else _ORDER_NOT_IMPL_NO_KEYS
        raise NotImplementedError(msg)

    def submit(self, *, client_order_id: str, symbol: str, side: str,
               qty: float, price: float,
               order_type: str = "MARKET") -> str:
        self._raise_order_not_impl()

    def cancel(self, broker_order_id: str) -> bool:
        self._raise_order_not_impl()

    def positions(self) -> dict:
        self._raise_order_not_impl()

    def flatten_all(self, *, dry_run: bool = True) -> list:
        self._raise_order_not_impl()

    def stream_fills(self, callback: Callable[[dict], None]) -> None:
        self._raise_order_not_impl()

    def reconcile(self, portfolio_positions: dict,
                  tolerance_bps: float = 5.0) -> dict:
        self._raise_order_not_impl()


__all__ = ["BinanceTestnetAdapter"]
