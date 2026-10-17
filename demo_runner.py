"""Demo runner: DCA buy BTCUSDT $100 every N seconds via PaperBroker.

E2E infrastructure smoke test — proves OMS + PaperBroker + SQLite state
work together on a live stream. The strategy is intentionally naive.

Environment:
    DEMO_DURATION_SEC  (default 300)
    DEMO_DB_PATH       (default /root/risk_v0/state/demo.db)
    DEMO_INTERVAL_SEC  (default 60)
    DEMO_SYMBOL        (default BTCUSDT)
    DEMO_PRICE         (default 60000.0)
    DEMO_NOTIONAL_USD  (default 100.0)
"""
from __future__ import annotations
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from oms.store import EventStore
from risk.structures import Portfolio
from risk.limits import Limits
from risk.kill_switch import KillSwitch
from brokers.paper import PaperBroker
from brokers.paper_adapter import PaperOmsRunner

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("demo_runner")

DURATION_SEC = int(os.environ.get("DEMO_DURATION_SEC", "300"))
INTERVAL_SEC = float(os.environ.get("DEMO_INTERVAL_SEC", "60"))
DB_PATH = os.environ.get("DEMO_DB_PATH", "/root/risk_v0/state/demo.db")
SYMBOL = os.environ.get("DEMO_SYMBOL", "BTCUSDT")
PRICE = float(os.environ.get("DEMO_PRICE", "60000.0"))
NOTIONAL = float(os.environ.get("DEMO_NOTIONAL_USD", "100.0"))

QTY = NOTIONAL / PRICE

_stop = asyncio.Event()


def _on_sig(sig, _frame):
    log.info("stopping on signal %s", sig)
    _stop.set()


async def main() -> int:
    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, _on_sig, s, None)
        except NotImplementedError:
            signal.signal(s, _on_sig)

    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    # clean slate for a deterministic demo
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(DB_PATH + suffix).unlink()
        except FileNotFoundError:
            pass

    store = EventStore(DB_PATH)
    portfolio = Portfolio(cash=10_000.0)
    broker = PaperBroker(
        db_path=DB_PATH,
        config={
            "initial_cash": 10_000.0,
            "slippage_bps": 2.0,
            "spot_taker_fee": 0.001,
            "asset_class": "spot",
        },
        fill_latency_ms=50.0,
        auto_tick=False,
    )
    broker.set_mark(SYMBOL, PRICE)

    limits = Limits(
        max_position_size=200_000.0,
        max_gross_exposure=500_000.0,
        max_net_exposure=500_000.0,
        max_daily_loss=50_000.0,
        max_drawdown_pct=100.0,
        max_single_symbol_pct=100.0,
        max_orders_per_minute=300,
    )
    ks = KillSwitch()

    runner = PaperOmsRunner(
        store=store, broker=broker,
        portfolio=portfolio, limits=limits, kill_switch=ks,
    )

    log.info("demo_runner starting: symbol=%s qty=%.8f price=%.2f "
             "interval=%ss duration=%ss db=%s",
             SYMBOL, QTY, PRICE, INTERVAL_SEC, DURATION_SEC, DB_PATH)

    started = loop.time()
    tick = 0
    errors = 0
    while not _stop.is_set():
        if loop.time() - started >= DURATION_SEC:
            log.info("duration reached (%.1fs), stopping",
                     loop.time() - started)
            break
        tick += 1
        try:
            res = runner.submit(symbol=SYMBOL, side="BUY",
                                qty=QTY, price=PRICE,
                                order_type="MARKET")
            log.info("tick=%d submit %s", tick, res)
            # advance paper clock to trigger fill (latency 50ms)
            runner.advance(0.1)
            st = runner.mgr.get(res["client_order_id"])
            log.info("tick=%d oms status=%s filled=%s avg_px=%s",
                     tick, st.status, st.filled_qty, st.avg_fill_price)
        except Exception as exc:  # noqa: BLE001
            errors += 1
            log.warning("tick=%d error: %r", tick, exc)

        try:
            await asyncio.wait_for(_stop.wait(), timeout=INTERVAL_SEC)
        except asyncio.TimeoutError:
            pass

    # snapshot final state
    positions = broker.positions()
    log.info("demo_runner finished: ticks=%d errors=%d "
             "final_positions=%s cash=%.2f",
             tick, errors, positions, broker.cash())
    try:
        store.close()
        broker.close()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
