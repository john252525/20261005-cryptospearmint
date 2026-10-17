"""Binance testnet adapter: 4 network-free tests."""
from __future__ import annotations
import pytest

from brokers.binance_testnet import BinanceTestnetAdapter


class _FakeResp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    monkeypatch.delenv("BINANCE_TESTNET_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_TESTNET_API_SECRET", raising=False)


def test_adapter_init_no_keys():
    a = BinanceTestnetAdapter()
    assert a.is_authenticated() is False
    assert a.account_status() == {"authenticated": False}


def test_adapter_init_with_keys_but_no_verify(monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("testnet unreachable (test)")

    monkeypatch.setattr("brokers.binance_testnet.requests.get", boom)
    a = BinanceTestnetAdapter(api_key="fake_key", api_secret="fake_secret")
    assert a.is_authenticated() is False


def test_market_price_returns_float(monkeypatch):
    def ok_get(url, params=None, timeout=None, headers=None):
        return _FakeResp({"symbol": (params or {}).get("symbol"),
                          "price": "100.50"})

    monkeypatch.setattr("brokers.binance_testnet.requests.get", ok_get)
    a = BinanceTestnetAdapter()
    px = a.market_price("BTCUSDT")
    assert isinstance(px, float)
    assert px == pytest.approx(100.50)


def test_submit_raises_without_auth():
    a = BinanceTestnetAdapter()
    with pytest.raises(NotImplementedError) as ei:
        a.submit(client_order_id="x", symbol="BTCUSDT",
                 side="BUY", qty=1.0, price=100.0)
    assert "real orders require valid API keys" in str(ei.value)
