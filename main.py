"""End-to-end demo: risk limits + kill-switch + OMS + PaperBroker."""
from __future__ import annotations
import json

from config import load_config
from risk.limits import Limits
from risk.kill_switch import KillSwitch
from risk.portfolio import PortfolioManager
from risk.structures import Portfolio
from oms.store import EventStore
from brokers.paper import PaperBroker
from brokers.paper_adapter import PaperOmsRunner


def main() -> int:
    cfg = load_config("config.yaml")
    broker_cfg = cfg.get("broker", {})

    limits = Limits.from_dict(cfg["limits"])
    ks = KillSwitch(cfg["kill_switch"])

    portfolio = Portfolio(
        cash=float(broker_cfg.get("initial_cash", 100_000.0)))
    PortfolioManager(portfolio)

    store = EventStore("risk.db")
    broker = PaperBroker(
        db_path="risk.db",
        config=broker_cfg,
        fill_latency_ms=float(broker_cfg.get("latency_ms", 50.0)),
        auto_tick=False,
    )
    broker.set_mark("AAPL", 180.0)

    runner = PaperOmsRunner(
        store=store, broker=broker,
        portfolio=portfolio, limits=limits, kill_switch=ks,
    )

    # 1. in-limits buy, fills after latency
    r1 = runner.submit(symbol="AAPL", side="BUY", qty=100, price=180.0,
                       client_order_id="demo_1")
    print("[1] submit   ", r1)
    runner.advance(0.1)
    print("[1] broker    positions=", broker.positions(),
          " cash={:.2f}".format(broker.cash()))
    st = runner.mgr.get("demo_1")
    print(f"[1] oms       {st.status} filled={st.filled_qty} "
          f"avg={st.avg_fill_price:.4f}")

    # 2. oversize buy -> pre-trade reject, never reaches broker
    r2 = runner.submit(symbol="AAPL", side="BUY", qty=10_000, price=180.0,
                       client_order_id="demo_2")
    print("[2] submit   ", r2)

    # 3. force drawdown, fire kill-switch
    portfolio.cash -= 8_000
    portfolio.peak_nav = 100_000.0
    fired = ks.auto_check(portfolio)
    print("[3] kill     ", ks.status()["name"],
          " fired=", [e.level for e in fired])

    # 4. flatten plan when L3
    if ks.requires_flatten():
        plan = runner.flatten_all(dry_run=True)
        print("[4] flatten  ", json.dumps(plan, default=str))

    # 5. reconcile broker book vs portfolio
    rec = runner.reconcile(tolerance_bps=5.0)
    print("[5] reconcile", json.dumps(
        {"ok": rec["ok"],
         "worst_bps": round(rec.get("worst_drift_bps", 0.0), 4),
         "tolerance": rec.get("tolerance_bps")}, default=str))

    store.close()
    broker.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
