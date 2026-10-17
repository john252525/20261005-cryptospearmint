"""Bridge PaperBroker to OrderManager / Portfolio.

Owns client_order_id <-> broker_order_id mapping. Wires paper broker
callbacks into OMS ack/fill events and applies fills to the Portfolio
so risk engine and broker book stay in lockstep.
"""
from __future__ import annotations
from typing import Optional

from risk.limits import Limits
from risk.kill_switch import KillSwitch
from risk.portfolio import PortfolioManager
from risk.structures import Order, Portfolio, Side

from oms.order_manager import OrderManager
from oms.store import EventStore
from brokers.paper import PaperBroker


class PaperOmsRunner:
    def __init__(
        self,
        *,
        store: EventStore,
        broker: PaperBroker,
        portfolio: Optional[Portfolio] = None,
        limits: Optional[Limits] = None,
        kill_switch: Optional[KillSwitch] = None,
    ) -> None:
        self.store = store
        self.broker = broker
        self.mgr = OrderManager(store)
        self.portfolio = portfolio
        self.limits = limits
        self.kill_switch = kill_switch
        self._applied_fills: set = set()
        broker.stream_fills(self._on_broker_event)

    # ------------------------------------------------------------------
    def submit(self, *, symbol: str, side: str, qty: float, price: float,
               order_type: str = "MARKET",
               client_order_id: Optional[str] = None,
               skip_limits: bool = False) -> dict:
        # 1. kill-switch gate
        if self.kill_switch is not None and self.kill_switch.blocks_new_orders():
            coid = self.mgr.submit(
                symbol=symbol, side=side, qty=qty, price=price,
                order_type=order_type, client_order_id=client_order_id,
                approved=False,
                reject_reason=f"kill-switch L{self.kill_switch.level}")
            return {"client_order_id": coid, "approved": False,
                    "reason": f"kill-switch L{self.kill_switch.level}"}

        # 2. pre-trade limits
        if (self.limits is not None and self.portfolio is not None
                and not skip_limits):
            o = Order(order_id=client_order_id or "pre",
                      symbol=symbol, side=Side(side), qty=qty,
                      price=price, order_type=order_type)
            r = self.limits.check_order(o, self.portfolio)
            if not r.approved:
                coid = self.mgr.submit(
                    symbol=symbol, side=side, qty=qty, price=price,
                    order_type=order_type, client_order_id=client_order_id,
                    approved=False, reject_reason=r.reason)
                return {"client_order_id": coid, "approved": False,
                        "reason": r.reason}

        # 3. OMS
        coid = self.mgr.submit(
            symbol=symbol, side=side, qty=qty, price=price,
            order_type=order_type, client_order_id=client_order_id,
            approved=True)

        # 4. broker
        bid = self.broker.submit(
            client_order_id=coid, symbol=symbol, side=side,
            qty=qty, price=price, order_type=order_type)
        return {"client_order_id": coid, "approved": True,
                "broker_order_id": bid}

    def advance(self, seconds: float) -> None:
        self.broker.advance(seconds)

    def flatten_all(self, *, dry_run: bool = True) -> list:
        plan = self.broker.flatten_all(dry_run=True)
        if dry_run:
            return plan
        submitted = []
        for p in plan:
            submitted.append(self.submit(
                symbol=p["symbol"], side=p["side"], qty=p["qty"],
                price=0.0, order_type="MARKET", skip_limits=True))
        return submitted

    def reconcile(self, tolerance_bps: float = 5.0) -> dict:
        if self.portfolio is None:
            return {"ok": True, "note": "no portfolio attached"}
        pp = {s: p.qty for s, p in self.portfolio.positions.items()}
        return self.broker.reconcile(pp, tolerance_bps=tolerance_bps)

    def replay(self) -> int:
        return self.mgr.rebuild_all()

    # ------------------------------------------------------------------
    def _on_broker_event(self, ev: dict) -> None:
        if ev.get("kind") != "fill":
            return
        coid = ev["client_order_id"]
        bid = ev.get("broker_order_id")

        try:
            self.mgr.ack(coid, bid)
        except Exception:
            pass

        try:
            self.mgr.fill(coid, ev["qty"], ev["price"],
                          ev.get("fill_id", ""))
        except Exception:
            pass

        if self.portfolio is None:
            return
        fid = ev.get("fill_id", "")
        if fid and fid in self._applied_fills:
            return
        if fid:
            self._applied_fills.add(fid)
        fill_order = Order(
            order_id=ev.get("fill_id", "f"),
            symbol=ev["symbol"], side=Side(ev["side"]),
            qty=ev["qty"], price=ev["price"])
        try:
            self.portfolio.apply_fill(
                fill_order, fee=float(ev.get("fee", 0.0)))
        except Exception:
            pass
