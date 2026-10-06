"""Exchange adapters: real ccxt (Binance testnet) или детерминированный mock.

Имитируют ccxt API: fetch_ticker, amount_to_precision, create_order,
fetch_balance, fetch_positions, set_sandbox_mode.

Mock — для CI и для проверки всей ордерной цепочки без ключей. Не для продакшна:
модель мгновенного исполнения, отсутствие funding, отсутствие liquidation.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime

# ---------------------------------------------------------------- mocks

class _MockBase:
    def __init__(self, prices: dict[str, float], balances: dict[str, float],
                 *, fee_bps: float = 10.0):
        self.prices = dict(prices)
        self.balances = dict(balances)
        self.orders: list[dict] = []
        self.fee_bps = fee_bps
        self._next_id = 1

    def _mk_id(self) -> str:
        prefix = "spot" if "Spot" in type(self).__name__ else "fut"
        oid = f"{prefix}-mock-{self._next_id}"
        self._next_id += 1
        return oid

    def _fill(self, symbol: str, side: str, amount: float) -> dict:
        price = self.prices[symbol]
        fee = price * amount * (self.fee_bps / 10000.0)
        return {
            "id": self._mk_id(),
            "symbol": symbol, "side": side,
            "amount": float(amount), "filled": float(amount),
            "average": price, "price": price,
            "status": "closed", "type": "market",
            "fee": {"cost": round(fee, 8)},
            "timestamp": int(datetime.now(UTC).timestamp() * 1000),
        }

    def fetch_ticker(self, symbol: str) -> dict:
        return {"last": self.prices[symbol], "symbol": symbol}

    def fetch_balance(self, params: dict | None = None) -> dict:
        return {"total": dict(self.balances), "free": dict(self.balances)}

    def set_sandbox_mode(self, val: bool) -> None:
        pass


class MockSpotExchange(_MockBase):
    """ccxt-like spot. Символ '<BASE>/<QUOTE>'."""

    def amount_to_precision(self, symbol: str, amount: float) -> str:
        return f"{amount:.6f}"

    def create_order(self, symbol, type, side, amount, price=None, params=None):
        if "/" not in symbol:
            raise ValueError(f"bad spot symbol {symbol!r}")
        base, quote = symbol.split("/")
        cost = self.prices[symbol] * amount
        if side == "buy":
            if self.balances.get(quote, 0.0) < cost:
                raise RuntimeError(
                    f"mock spot: insufficient {quote} "
                    f"(have {self.balances.get(quote, 0.0):.2f}, need {cost:.2f})")
            self.balances[quote] = self.balances.get(quote, 0.0) - cost
            self.balances[base] = self.balances.get(base, 0.0) + amount
        elif side == "sell":
            if self.balances.get(base, 0.0) < amount:
                raise RuntimeError(
                    f"mock spot: insufficient {base} "
                    f"(have {self.balances.get(base, 0.0):.8f}, need {amount:.8f})")
            self.balances[base] -= amount
            self.balances[quote] = self.balances.get(quote, 0.0) + cost
        else:
            raise ValueError(f"bad side {side!r}")
        o = self._fill(symbol, side, amount)
        self.orders.append(o)
        return o


class MockFuturesExchange(_MockBase):
    """ccxt-like USDⓈ-M futures. Символ '<BASE>/<QUOTE>:<QUOTE>'."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.positions: dict[str, float] = {}  # signed contracts

    def create_order(self, symbol, type, side, amount, price=None, params=None):
        delta = amount if side == "buy" else -amount
        self.positions[symbol] = self.positions.get(symbol, 0.0) + delta
        o = self._fill(symbol, side, amount)
        self.orders.append(o)
        return o

    def fetch_positions(self, symbols=None) -> list[dict]:
        out = []
        for sym, contracts in self.positions.items():
            if abs(contracts) > 1e-12:
                out.append({
                    "symbol": sym, "contracts": abs(contracts),
                    "side": "long" if contracts > 0 else "short",
                })
        return out


# ---------------------------------------------------------------- real (ccxt)

def _require_env(key: str) -> str:
    v = os.getenv(key, "").strip()
    if not v:
        raise SystemExit(f"env {key} is required for live mode (testnet keys)")
    return v


def real_spot_exchange():
    import ccxt
    ex = ccxt.binance({
        "apiKey": _require_env("BINANCE_TESTNET_SPOT_KEY"),
        "secret": _require_env("BINANCE_TESTNET_SPOT_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "spot", "adjustForTimeDifference": True},
    })
    ex.urls["api"]["public"] = "https://testnet.binance.vision/api/v3"
    ex.urls["api"]["private"] = "https://testnet.binance.vision/api/v3"
    return ex


def real_futures_exchange():
    import ccxt
    ex = ccxt.binanceusdm({
        "apiKey": _require_env("BINANCE_TESTNET_FUTURES_KEY"),
        "secret": _require_env("BINANCE_TESTNET_FUTURES_SECRET"),
        "enableRateLimit": True,
        "options": {"adjustForTimeDifference": True},
    })
    ex.set_sandbox_mode(True)
    return ex


# ---------------------------------------------------------------- helpers

_MOCK_SPOT_PRICES = {
    "BTCUSDT": 60000.0, "ETHUSDT": 2500.0, "LINKUSDT": 15.0,
    "LTCUSDT": 70.0, "DOGEUSDT": 0.10,
}


def to_spot_symbol(sym: str) -> str:
    s = sym.upper()
    for q in ("USDT", "USDC", "BUSD"):
        if s.endswith(q):
            return f"{s[:-len(q)]}/{q}"
    return s


def to_perp_symbol(sym: str) -> str:
    spot = to_spot_symbol(sym)
    b, q = spot.split("/")
    return f"{b}/{q}:{q}"


def build_exchanges(cfg: dict, *, use_mock: bool):
    """Возвращает (spot_ex, fut_ex). use_mock=True — без ключей, для CI."""
    symbols = cfg["data"]["symbols"]
    if use_mock:
        spot_prices = {to_spot_symbol(s): _MOCK_SPOT_PRICES.get(s.upper(), 100.0) for s in symbols}
        # перп = спот * 1.0003 (реалистичный базис 3 bps)
        fut_prices = {to_perp_symbol(s): _MOCK_SPOT_PRICES.get(s.upper(), 100.0) * 1.0003
                      for s in symbols}
        spot = MockSpotExchange(spot_prices, {"USDT": 100_000.0})
        fut = MockFuturesExchange(fut_prices, {"USDT": 10_000.0})
        return spot, fut
    return real_spot_exchange(), real_futures_exchange()


__all__ = [
    "MockFuturesExchange",
    "MockSpotExchange",
    "build_exchanges",
    "real_futures_exchange",
    "real_spot_exchange",
    "to_perp_symbol",
    "to_spot_symbol",
]
