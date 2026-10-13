"""Paper / testnet runner: Binance Testnet spot + USDT-M futures."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import logging
import math
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

import httpx
import yaml

from ..paper.portfolio import DeltaNeutralPortfolio
from ..strategies.funding_carry.config import FundingCarrySettings
from ..strategies.funding_carry.gates import (
    CooldownGate,
    needs_rebalance,
    passes_entry_filters,
    should_exit,
)
from ..strategies.funding_carry.signal import get_signals

log = logging.getLogger(__name__)


class BinanceTestnetClient:
    def __init__(self, api_key, api_secret, spot_base, fut_base):
        self.key = api_key
        self.secret = api_secret.encode()
        self.spot_base = spot_base.rstrip("/")
        self.fut_base = fut_base.rstrip("/")
        self._c = httpx.AsyncClient(timeout=20.0)

    async def aclose(self):
        await self._c.aclose()

    def _signed_qs(self, params):
        p = dict(params); p["timestamp"] = int(time.time() * 1000)
        p.setdefault("recvWindow", 5000)
        qs = urlencode(p)
        sig = hmac.new(self.secret, qs.encode(), hashlib.sha256).hexdigest()
        return f"{qs}&signature={sig}"

    async def _req(self, base, method, path, params=None, signed=False):
        params = dict(params or {}); url = f"{base}{path}"
        headers = {"X-MBX-APIKEY": self.key} if signed else {}
        if signed:
            url = f"{url}?{self._signed_qs(params)}"
            r = await self._c.request(method, url, headers=headers)
        else:
            r = await self._c.request(method, url, params=params, headers=headers)
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {r.status_code} {r.text[:300]}")
        return r.json()

    async def spot_price(self, symbol):
        d = await self._req(self.spot_base, "GET",
                            "/api/v3/ticker/bookTicker", {"symbol": symbol})
        return 0.5 * (float(d["bidPrice"]) + float(d["askPrice"]))

    async def fut_price(self, symbol):
        d = await self._req(self.fut_base, "GET",
                            "/fapi/v1/premiumIndex", {"symbol": symbol})
        return float(d["markPrice"])

    async def spot_filters(self, symbol):
        d = await self._req(self.spot_base, "GET", "/api/v3/exchangeInfo",
                            {"symbol": symbol})
        return _extract_filters(d["symbols"][0]["filters"])

    async def fut_filters(self, symbol):
        d = await self._req(self.fut_base, "GET", "/fapi/v1/exchangeInfo",
                            {"symbol": symbol})
        return _extract_filters(d["symbols"][0]["filters"])

    async def spot_market_order(self, symbol, side, qty):
        return await self._req(self.spot_base, "POST", "/api/v3/order",
                               {"symbol": symbol, "side": side, "type": "MARKET",
                                "quantity": qty}, signed=True)

    async def fut_market_order(self, symbol, side, qty):
        return await self._req(self.fut_base, "POST", "/fapi/v1/order",
                               {"symbol": symbol, "side": side, "type": "MARKET",
                                "quantity": qty}, signed=True)


def _extract_filters(filters):
    out = {"step": 1e-8, "min_qty": 0.0, "min_notional": 0.0, "tick": 1e-8}
    for f in filters:
        t = f.get("filterType")
        if t in ("LOT_SIZE", "MARKET_LOT_SIZE"):
            out["step"] = float(f.get("stepSize", out["step"]) or out["step"])
            out["min_qty"] = float(f.get("minQty", out["min_qty"]) or 0.0)
        elif t in ("MIN_NOTIONAL", "NOTIONAL"):
            v = f.get("notional") or f.get("minNotional")
            if v:
                out["min_notional"] = float(v)
        elif t == "PRICE_FILTER":
            out["tick"] = float(f.get("tickSize", out["tick"]) or out["tick"])
    return out


def round_step(qty, step):
    if step <= 0:
        return qty
    return math.floor(qty / step) * step


def _oid(resp):
    if not resp:
        return None
    return str(resp.get("orderId", ""))


def _avg_fill(resp, fallback):
    if not resp:
        return fallback
    try:
        ex = float(resp.get("executedQty") or 0.0)
        q = float(resp.get("cummulativeQuoteQty") or resp.get("cumQuote") or 0.0)
        if ex > 0 and q > 0:
            return q / ex
        fills = resp.get("fills") or []
        if fills:
            qt = sum(float(f["qty"]) for f in fills)
            ct = sum(float(f["qty"]) * float(f["price"]) for f in fills)
            if qt > 0:
                return ct / qt
    except Exception:
        pass
    return fallback


def load_settings(path):
    if not path:
        return FundingCarrySettings()
    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}
    return FundingCarrySettings(**raw)


class FundingCarryRunner:
    def __init__(self, settings, client=None):
        self.s = settings
        self.pf = DeltaNeutralPortfolio(settings.db_path, settings)
        self.gate = CooldownGate(settings.entry_cooldown_sec)
        self.client = client
        self.halted = False
        self._filters: dict[str, dict] = {}
        Path(settings.journal_path).parent.mkdir(parents=True, exist_ok=True)

    def _journal(self, **rec):
        rec.setdefault("ts", datetime.now(UTC).isoformat())
        with open(self.s.journal_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")

    async def _filter_for(self, venue, symbol):
        key = f"{venue}:{symbol}"
        if key in self._filters:
            return self._filters[key]
        if self.client is None:
            self._filters[key] = {"step": 1e-6, "min_qty": 0.0, "min_notional": 0.0}
            return self._filters[key]
        try:
            f = (await self.client.spot_filters(symbol) if venue == "spot"
                 else await self.client.fut_filters(symbol))
        except Exception as exc:
            log.warning("filter fetch %s %s: %s", venue, symbol, exc)
            f = {"step": 1e-6, "min_qty": 0.0, "min_notional": 0.0}
        self._filters[key] = f
        return f

    async def step(self, signals):
        now = datetime.now(UTC)
        sig_map = {(s.symbol, s.exchange): s for s in signals}
        for pos in self.pf.open_positions():
            sg = sig_map.get((pos["symbol"], pos["exchange"]))
            if sg is None:
                self._journal(symbol=pos["symbol"], action="hold",
                              note="missing_signal")
                continue
            if should_exit(sg, pos["direction"], self.s):
                await self._close(pos, sg, reason="exit_rule")
                continue
            await self._maybe_rebalance(pos, sg, now)
        for sg in signals:
            if sg.exchange != "binance":
                continue
            if self.halted:
                self._journal(symbol=sg.symbol, action="no_op", note="halted")
                continue
            if self.pf.has_open(sg.symbol, sg.exchange):
                continue
            if not passes_entry_filters(sg, self.s):
                self._journal(symbol=sg.symbol, action="no_op", note="filters",
                              funding_rate=sg.funding_rate)
                continue
            key = f"{sg.symbol}:{sg.exchange}"
            if not self.gate.try_consume(key, now):
                self._journal(symbol=sg.symbol, action="no_op", note="cooldown",
                              seconds_left=self.gate.seconds_left(key, now))
                continue
            await self._open(sg)
        await self._snapshot(signals)

    async def _open(self, sig):
        notional = min(self.s.max_pos_per_symbol_usd,
                       self.pf.capital * self.s.target_leverage)
        if notional <= 0:
            return
        spot_side = "BUY" if sig.direction == "long_spot_short_perp" else "SELL"
        perp_side = "SELL" if sig.direction == "long_spot_short_perp" else "BUY"
        sf = await self._filter_for("spot", sig.symbol)
        pf = await self._filter_for("fut", sig.symbol)
        spot_qty = round_step(notional / sig.spot_price, sf["step"])
        perp_qty = round_step(notional / sig.perp_price, pf["step"])
        rec = {"symbol": sig.symbol, "action": "open", "direction": sig.direction,
               "funding_rate": sig.funding_rate, "basis_bps": sig.basis_bps,
               "spot_price": sig.spot_price, "perp_price": sig.perp_price}
        spot_resp = perp_resp = None
        try:
            if self.client is not None:
                spot_resp = await self.client.spot_market_order(
                    sig.symbol, spot_side, spot_qty)
                try:
                    perp_resp = await self.client.fut_market_order(
                        sig.symbol, perp_side, perp_qty)
                except Exception as exc:
                    log.error("perp leg failed, unwinding spot: %s", exc)
                    await self.client.spot_market_order(
                        sig.symbol,
                        "SELL" if spot_side == "BUY" else "BUY", spot_qty)
                    self._journal(symbol=sig.symbol, action="no_op",
                                  note="perp_failed_unwound", error=str(exc))
                    return
            fee_spot = self.s.spot_taker_fee * notional
            fee_perp = self.s.perp_taker_fee * notional
            spot_fill = _avg_fill(spot_resp, sig.spot_price)
            perp_fill = _avg_fill(perp_resp, sig.perp_price)
            pid = self.pf.open_position(
                symbol=sig.symbol, exchange=sig.exchange, direction=sig.direction,
                spot_qty=spot_qty if spot_side == "BUY" else -spot_qty,
                perp_qty=-perp_qty if perp_side == "SELL" else perp_qty,
                spot_entry=spot_fill, perp_entry=perp_fill,
                entry_funding_bps=sig.funding_bps_8h, notional_usd=notional)
            now = datetime.now(UTC)
            self.pf.record_order(now, sig.symbol, "binance_spot", "spot",
                                 spot_side, spot_qty, spot_fill,
                                 _oid(spot_resp), fee_spot, "FILLED")
            self.pf.record_order(now, sig.symbol, "binance_fut", "perp",
                                 perp_side, perp_qty, perp_fill,
                                 _oid(perp_resp), fee_perp, "FILLED")
            slip_spot = abs(spot_fill - sig.spot_price) / sig.spot_price * 1e4
            slip_perp = abs(perp_fill - sig.perp_price) / sig.perp_price * 1e4
            if max(slip_spot, slip_perp) > self.s.kill_if_slippage_bps_gt:
                self.halted = True
                log.error("KILL slippage spot=%.2f perp=%.2f", slip_spot, slip_perp)
            rec.update({"position_id": pid, "spot_order_id": _oid(spot_resp),
                        "perp_order_id": _oid(perp_resp),
                        "spot_fill": spot_fill, "perp_fill": perp_fill,
                        "spot_qty": spot_qty, "perp_qty": perp_qty,
                        "fees_spot": fee_spot, "fees_perp": fee_perp,
                        "slippage_spot_bps": slip_spot,
                        "slippage_perp_bps": slip_perp,
                        "pnl_realized": 0.0})
            self._journal(**rec)
        except Exception as exc:
            log.exception("open failed %s", sig.symbol)
            self._journal(symbol=sig.symbol, action="no_op",
                          note="open_failed", error=str(exc))

    async def _close(self, pos, sig, reason):
        spot_side = "SELL" if pos["spot_qty"] > 0 else "BUY"
        perp_side = "SELL" if pos["perp_qty"] < 0 else "BUY"
        spot_qty = abs(pos["spot_qty"]); perp_qty = abs(pos["perp_qty"])
        notional = pos["notional_usd"]
        rec = {"symbol": pos["symbol"], "action": "close", "reason": reason,
               "position_id": pos["id"], "funding_rate": sig.funding_rate}
        try:
            spot_resp = perp_resp = None
            if self.client is not None:
                spot_resp = await self.client.spot_market_order(
                    pos["symbol"], spot_side, spot_qty)
                try:
                    perp_resp = await self.client.fut_market_order(
                        pos["symbol"], perp_side, perp_qty)
                except Exception as exc:
                    log.error("perp close failed: %s", exc)
                    self.halted = True
            fee_spot = self.s.spot_taker_fee * notional
            fee_perp = self.s.perp_taker_fee * notional
            fees = fee_spot + fee_perp
            spot_fill = _avg_fill(spot_resp, sig.spot_price)
            perp_fill = _avg_fill(perp_resp, sig.perp_price)
            pnl = self.pf.close_position(pos["id"], spot_fill, perp_fill, fees=fees)
            now = datetime.now(UTC)
            self.pf.record_order(now, pos["symbol"], "binance_spot", "spot",
                                 spot_side, spot_qty, spot_fill,
                                 _oid(spot_resp), fee_spot, "FILLED")
            self.pf.record_order(now, pos["symbol"], "binance_fut", "perp",
                                 perp_side, perp_qty, perp_fill,
                                 _oid(perp_resp), fee_perp, "FILLED")
            rec.update({"spot_order_id": _oid(spot_resp),
                        "perp_order_id": _oid(perp_resp),
                        "spot_fill": spot_fill, "perp_fill": perp_fill,
                        "fees_spot": fee_spot, "fees_perp": fee_perp,
                        "pnl_realized": pnl})
            self._journal(**rec)
        except Exception as exc:
            log.exception("close failed %s", pos["symbol"])
            self._journal(symbol=pos["symbol"], action="no_op",
                          note="close_failed", error=str(exc))

    async def _maybe_rebalance(self, pos, sig, now):
        spot_val = abs(pos["spot_qty"]) * sig.spot_price
        perp_val = abs(pos["perp_qty"]) * sig.perp_price
        if perp_val <= 0:
            return
        drift_bps = (spot_val - perp_val) / perp_val * 1e4
        if not needs_rebalance(drift_bps, self.s):
            self._journal(symbol=pos["symbol"], action="hold",
                          position_id=pos["id"], drift_bps=drift_bps,
                          funding_rate=sig.funding_rate)
            return
        target_notional = pos["notional_usd"]
        sf = await self._filter_for("spot", pos["symbol"])
        pf = await self._filter_for("fut", pos["symbol"])
        target_spot = round_step(target_notional / sig.spot_price, sf["step"])
        target_perp = round_step(target_notional / sig.perp_price, pf["step"])
        try:
            if self.client is not None:
                d_spot = target_spot - abs(pos["spot_qty"])
                if abs(d_spot) > sf["step"]:
                    await self.client.spot_market_order(
                        pos["symbol"],
                        "BUY" if (d_spot > 0) == (pos["spot_qty"] > 0) else "SELL",
                        abs(d_spot))
                d_perp = target_perp - abs(pos["perp_qty"])
                if abs(d_perp) > pf["step"]:
                    same_dir = (d_perp > 0) == (pos["perp_qty"] > 0)
                    await self.client.fut_market_order(
                        pos["symbol"],
                        ("BUY" if pos["perp_qty"] < 0 else "SELL") if same_dir
                        else ("SELL" if pos["perp_qty"] < 0 else "BUY"),
                        abs(d_perp))
            with self.pf.tx() as c:
                c.execute("UPDATE positions SET spot_qty=?, perp_qty=? WHERE id=?",
                          (target_spot if pos["spot_qty"] > 0 else -target_spot,
                           -target_perp if pos["perp_qty"] < 0 else target_perp,
                           pos["id"]))
            self._journal(symbol=pos["symbol"], action="rebalance",
                          position_id=pos["id"], drift_bps=drift_bps,
                          funding_rate=sig.funding_rate)
        except Exception as exc:
            log.exception("rebalance failed %s", pos["symbol"])
            self._journal(symbol=pos["symbol"], action="no_op",
                          note="rebalance_failed", error=str(exc))

    async def _snapshot(self, signals):
        marks = {s.symbol: {"spot": s.spot_price, "perp": s.perp_price}
                 for s in signals}
        snap = self.pf.snapshot(marks)
        self._journal(symbol="*", action="hold", note="snapshot", **snap)

    async def run_forever(self):
        log.info("runner start; recovered %d positions", len(self.pf.recover()))
        while True:
            t0 = time.time()
            try:
                sigs = await get_signals(self.s)
                if sigs:
                    await self.step(sigs)
                else:
                    log.warning("no signals this cycle")
            except Exception:
                log.exception("poll cycle failed")
            await asyncio.sleep(max(1.0,
                                    self.s.poll_interval_sec - (time.time() - t0)))


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/funding_carry.yaml")
    p.add_argument("--poll", type=int, default=None)
    p.add_argument("--once", action="store_true")
    a = p.parse_args()
    s = load_settings(a.config)
    if a.poll:
        s.poll_interval_sec = a.poll
    key = os.getenv("BINANCE_TESTNET_API_KEY", "")
    sec = os.getenv("BINANCE_TESTNET_API_SECRET", "")
    client = None
    if key and sec:
        client = BinanceTestnetClient(key, sec,
                                      s.binance_spot_testnet,
                                      s.binance_futures_testnet)
    else:
        log.warning("no testnet keys -> DRY-RUN")
    runner = FundingCarryRunner(s, client=client)

    async def _run():
        try:
            if a.once:
                sigs = await get_signals(s)
                await runner.step(sigs)
            else:
                await runner.run_forever()
        finally:
            if client:
                await client.aclose()
            runner.pf.close()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        log.info("stopped by user")


if __name__ == "__main__":
    main()
