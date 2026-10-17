"""In-process paper broker.

Deterministic clock via advance(seconds); optional asyncio ticker for
real-time. Idempotent submit keyed on client_order_id. Fees + slippage
from config (fraction <0.5, or bps >=0.5, auto-detected). Persistence:
broker_orders / broker_fills in the same SQLite file the OMS uses;
book state reloaded from DB on init.
"""
from __future__ import annotations

import asyncio
import heapq
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


DDL = """
CREATE TABLE IF NOT EXISTS broker_orders (
    broker_order_id TEXT PRIMARY KEY,
    client_order_id TEXT NOT NULL UNIQUE,
    ts              REAL NOT NULL,
    symbol          TEXT NOT NULL,
    side            TEXT NOT NULL,
    qty             REAL NOT NULL,
    price           REAL NOT NULL,
    order_type      TEXT NOT NULL,
    status          TEXT NOT NULL,
    filled_qty      REAL NOT NULL DEFAULT 0,
    avg_fill_price  REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_broker_orders_coid ON broker_orders(client_order_id);

CREATE TABLE IF NOT EXISTS broker_fills (
    fill_id           TEXT PRIMARY KEY,
    broker_order_id   TEXT NOT NULL,
    client_order_id   TEXT NOT NULL,
    ts                REAL NOT NULL,
    qty               REAL NOT NULL,
    price             REAL NOT NULL,
    fee               REAL NOT NULL,
    slippage          REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_broker_fills_bo ON broker_fills(broker_order_id);
"""


@dataclass
class _Order:
    broker_order_id: str
    client_order_id: str
    symbol: str
    side: str
    qty: float
    price: float
    order_type: str
    submitted_at: float
    due_at: float
    status: str = "PENDING"
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0


class PaperBroker:
    def __init__(
        self,
        db_path: str | Path = "risk.db",
        config: Optional[dict] = None,
        fill_latency_ms: float = 50.0,
        auto_tick: bool = False,
        tick_interval_ms: float = 20.0,
    ) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(DDL)
        self._conn.commit()

        cfg = dict(config or {})
        self._latency_s = max(0.0, float(fill_latency_ms) / 1000.0)
        self._slippage = self._norm_bps(cfg.get("slippage_bps", 0.0))
        self._fee_spot = self._norm_bps(cfg.get("spot_taker_fee", 0.0))
        self._fee_perp = self._norm_bps(cfg.get("perp_taker_fee", 0.0))
        self._fee_eq = self._norm_bps(cfg.get("equity_commission_bps", 0.0))
        self._asset_class = str(cfg.get("asset_class", "spot")).lower()
        self._initial_cash = float(cfg.get("initial_cash", 100_000.0))

        self._lock = threading.RLock()
        self._now: float = 0.0
        self._pending: list = []
        self._orders: dict = {}
        self._marks: dict = {}
        self._callbacks: list = []

        self._book_cash: float = self._initial_cash
        self._book_positions: dict = {}
        self._reload_book()

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._stopped = False

        if auto_tick:
            self._start_loop()
            self._schedule_ticker(tick_interval_ms)

    @staticmethod
    def _norm_bps(value) -> float:
        try:
            x = float(value)
        except (TypeError, ValueError):
            return 0.0
        if x <= 0:
            return 0.0
        return x if x < 0.5 else x / 10_000.0

    def _fee_rate(self) -> float:
        ac = self._asset_class
        if ac in ("spot", "crypto_spot", "crypto"):
            return self._fee_spot
        if ac in ("perp", "crypto_perp", "future"):
            return self._fee_perp
        if ac in ("equity", "stock", "us_equity"):
            return self._fee_eq
        return 0.0

    def _reload_book(self) -> None:
        book: dict = {}
        cash = self._initial_cash
        for sym, side, qty, avg in self._conn.execute(
                "SELECT symbol, side, filled_qty, avg_fill_price "
                "FROM broker_orders WHERE status = 'FILLED'"):
            signed = float(qty) if side == "BUY" else -float(qty)
            book[str(sym)] = book.get(str(sym), 0.0) + signed
            cash -= signed * float(avg)
        fee_sum = self._conn.execute(
            "SELECT COALESCE(SUM(fee), 0) FROM broker_fills").fetchone()[0]
        cash -= float(fee_sum or 0.0)
        self._book_positions = {k: v for k, v in book.items() if abs(v) > 1e-12}
        self._book_cash = cash

    def _start_loop(self) -> None:
        if self._loop is not None:
            return
        loop = asyncio.new_event_loop()

        def runner():
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self._loop = loop
        self._loop_thread = threading.Thread(target=runner, daemon=True)
        self._loop_thread.start()

    def _schedule_ticker(self, tick_interval_ms: float) -> None:
        if self._loop is None:
            return
        interval = max(0.005, tick_interval_ms / 1000.0)

        async def ticker():
            while not self._stopped:
                await asyncio.sleep(interval)
                self.advance(interval)

        asyncio.run_coroutine_threadsafe(ticker(), self._loop)

    def close(self) -> None:
        self._stopped = True
        if self._loop is not None:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
        try:
            self._conn.close()
        except Exception:
            pass

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("seconds must be >= 0")
        with self._lock:
            self._now += float(seconds)
            self._drain_locked()

    def now(self) -> float:
        with self._lock:
            return self._now

    def _drain_locked(self) -> None:
        while self._pending and self._pending[0][0] <= self._now:
            _, bid = heapq.heappop(self._pending)
            self._try_fill_locked(bid)
        for bid, o in list(self._orders.items()):
            if o.status != "PENDING":
                continue
            if o.order_type == "LIMIT" and \
                    o.submitted_at + self._latency_s <= self._now:
                self._try_fill_locked(bid)

    def set_mark(self, symbol: str, price: float) -> None:
        with self._lock:
            self._marks[symbol] = float(price)

    def marks(self) -> dict:
        with self._lock:
            return dict(self._marks)

    def submit(self, *, client_order_id: str, symbol: str, side: str,
               qty: float, price: float,
               order_type: str = "MARKET") -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT broker_order_id FROM broker_orders "
                "WHERE client_order_id = ?", (client_order_id,)).fetchone()
            if row:
                return row[0]

            bid = f"paper_{client_order_id}"
            o = _Order(
                broker_order_id=bid, client_order_id=client_order_id,
                symbol=symbol, side=side.upper(),
                qty=float(qty), price=float(price),
                order_type=order_type.upper(),
                submitted_at=self._now,
                due_at=self._now + self._latency_s,
            )
            self._orders[bid] = o
            self._persist_order(o)
            heapq.heappush(self._pending, (o.due_at, bid))
            if self._latency_s == 0.0:
                self._drain_locked()
            return bid

    def cancel(self, broker_order_id: str) -> bool:
        with self._lock:
            o = self._orders.get(broker_order_id)
            if o is None:
                o = self._load_order(broker_order_id)
            if o is None or o.status != "PENDING":
                return False
            o.status = "CANCELED"
            self._persist_order(o)
            self._emit({"kind": "cancel",
                        "broker_order_id": broker_order_id,
                        "client_order_id": o.client_order_id})
            return True

    def positions(self) -> dict:
        with self._lock:
            return dict(self._book_positions)

    def cash(self) -> float:
        with self._lock:
            return self._book_cash

    def order_count(self) -> int:
        with self._lock:
            return self._conn.execute(
                "SELECT COUNT(*) FROM broker_orders").fetchone()[0]

    def stream_fills(self, callback: Callable[[dict], None]) -> None:
        self._callbacks.append(callback)

    def flatten_all(self, *, dry_run: bool = True) -> list:
        with self._lock:
            plan = []
            for sym, qty in self._book_positions.items():
                if abs(qty) < 1e-12:
                    continue
                plan.append({
                    "symbol": sym,
                    "side": "SELL" if qty > 0 else "BUY",
                    "qty": abs(qty),
                    "type": "MARKET",
                    "mark": self._marks.get(sym),
                })
            if dry_run:
                return plan
            submitted = []
            for p in plan:
                coid = f"flat_{uuid.uuid4().hex[:12]}"
                bid = self.submit(
                    client_order_id=coid, symbol=p["symbol"],
                    side=p["side"], qty=p["qty"], price=0.0,
                    order_type="MARKET")
                submitted.append({"client_order_id": coid,
                                  "broker_order_id": bid})
            return submitted

    def reconcile(self, portfolio_positions: dict,
                  tolerance_bps: float = 5.0) -> dict:
        with self._lock:
            broker = {k: v for k, v in self._book_positions.items()
                      if abs(v) > 1e-12}
            portf = {k: float(v) for k, v in (portfolio_positions or {}).items()
                     if abs(float(v)) > 1e-12}
            symbols = set(broker) | set(portf)
            detail = []
            worst = 0.0
            for s in sorted(symbols):
                bq = broker.get(s, 0.0)
                pq = portf.get(s, 0.0)
                denom = max(abs(bq), abs(pq), 1.0)
                drift_bps = abs(bq - pq) / denom * 10_000.0
                worst = max(worst, drift_bps)
                detail.append({
                    "symbol": s, "broker_qty": bq, "portfolio_qty": pq,
                    "drift_bps": drift_bps,
                    "status": "ok" if drift_bps <= tolerance_bps else "alert",
                })
            return {"ok": all(d["status"] == "ok" for d in detail),
                    "worst_drift_bps": worst,
                    "tolerance_bps": tolerance_bps,
                    "detail": detail}

    def _load_order(self, broker_order_id: str) -> Optional[_Order]:
        row = self._conn.execute(
            "SELECT broker_order_id, client_order_id, symbol, side, qty, "
            "       price, order_type, status, filled_qty, avg_fill_price "
            "FROM broker_orders WHERE broker_order_id = ?",
            (broker_order_id,)).fetchone()
        if not row:
            return None
        o = _Order(
            broker_order_id=row[0], client_order_id=row[1], symbol=row[2],
            side=row[3], qty=row[4], price=row[5], order_type=row[6],
            submitted_at=0.0, due_at=0.0,
            status=row[7], filled_qty=row[8], avg_fill_price=row[9])
        self._orders[broker_order_id] = o
        return o

    def _persist_order(self, o: _Order) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO broker_orders "
            "(broker_order_id, client_order_id, ts, symbol, side, qty, price, "
            " order_type, status, filled_qty, avg_fill_price) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (o.broker_order_id, o.client_order_id, o.submitted_at,
             o.symbol, o.side, o.qty, o.price, o.order_type,
             o.status, o.filled_qty, o.avg_fill_price))
        self._conn.commit()

    def _try_fill_locked(self, broker_order_id: str) -> None:
        o = self._orders.get(broker_order_id) or self._load_order(broker_order_id)
        if o is None or o.status != "PENDING":
            return

        mark = self._marks.get(o.symbol)

        if o.order_type == "LIMIT":
            if mark is None:
                return
            if o.side == "BUY" and mark > o.price:
                return
            if o.side == "SELL" and mark < o.price:
                return
            base = o.price
        else:
            base = mark if mark is not None and mark > 0 else o.price
            if base <= 0:
                return

        slip = base * self._slippage
        fill_px = base + slip if o.side == "BUY" else base - slip

        notional = abs(o.qty) * fill_px
        fee = notional * self._fee_rate()

        signed = o.qty if o.side == "BUY" else -o.qty
        self._book_positions[o.symbol] = \
            self._book_positions.get(o.symbol, 0.0) + signed
        if abs(self._book_positions[o.symbol]) < 1e-12:
            self._book_positions.pop(o.symbol, None)
        self._book_cash -= signed * fill_px + fee

        o.status = "FILLED"
        o.filled_qty = o.qty
        o.avg_fill_price = fill_px
        self._persist_order(o)

        fill_id = f"fill_{uuid.uuid4().hex[:12]}"
        self._conn.execute(
            "INSERT INTO broker_fills "
            "(fill_id, broker_order_id, client_order_id, ts, qty, price, "
            " fee, slippage) VALUES (?,?,?,?,?,?,?,?)",
            (fill_id, o.broker_order_id, o.client_order_id, self._now,
             o.qty, fill_px, fee, abs(slip)))
        self._conn.commit()

        self._emit({
            "kind": "fill",
            "fill_id": fill_id,
            "broker_order_id": o.broker_order_id,
            "client_order_id": o.client_order_id,
            "symbol": o.symbol,
            "side": o.side,
            "qty": o.qty,
            "price": fill_px,
            "fee": fee,
            "slippage": abs(slip),
        })

    def _emit(self, event: dict) -> None:
        for cb in list(self._callbacks):
            try:
                cb(event)
            except Exception:
                pass
