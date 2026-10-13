"""CLI demo — full order lifecycle on a temp/risk.db."""
from __future__ import annotations
import json

from oms.order_manager import OrderManager
from oms.store import EventStore


def main() -> int:
    store = EventStore("risk.db")
    mgr = OrderManager(store)

    coid = mgr.submit(symbol="AAPL", side="BUY", qty=100, price=180.0,
                      client_order_id="demo_buy_1")
    print(f"[1] submit    {coid} status={mgr.get(coid).status}")

    mgr.ack(coid, "brk_AAPL_42")
    print(f"[2] ack       status={mgr.get(coid).status} "
          f"broker={mgr.get(coid).broker_order_id}")

    mgr.fill(coid, 40, 180.1, "f1")
    s = mgr.get(coid)
    print(f"[3] partial   status={s.status} filled={s.filled_qty} "
          f"avg={s.avg_fill_price:.4f}")

    mgr.fill(coid, 60, 180.4, "f2")
    s = mgr.get(coid)
    print(f"[4] filled    status={s.status} filled={s.filled_qty} "
          f"avg={s.avg_fill_price:.4f}")

    c2 = mgr.submit(symbol="TSLA", side="BUY", qty=10_000, price=250.0,
                    approved=False, reject_reason="position size limit",
                    client_order_id="demo_reject_1")
    print(f"[5] rejected  reason={mgr.get(c2).reject_reason}")

    rp = mgr.replay(coid)
    print(f"[6] replay materialized == replayed: {rp.status == s.status}")

    print("\norders_state:")
    for row in mgr.store.all_states():
        print(" ", json.dumps({k: row[k] for k in
              ("client_order_id", "symbol", "status", "filled_qty",
               "avg_fill_price", "reject_reason")}))

    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
