# Paper Broker

In-process broker simulator used on the `risk-engine` branch.
No network, no API keys. Deterministic time under test.

## Broker contract

    submit(client_order_id, symbol, side, qty, price, order_type)
        -> broker_order_id
        Idempotent on client_order_id.
    cancel(broker_order_id) -> bool
        False if unknown or already terminal.
    positions() -> dict[str, float]
        signed quantity per symbol.
    flatten_all(dry_run=True) -> list[dict]
        dry_run=True  : return plan, no orders sent.
        dry_run=False : submit MARKET orders closing every position.
    stream_fills(callback) -> None
        callback receives dicts with kind 'fill' or 'cancel'.
    reconcile(portfolio_positions, tolerance_bps=5.0) -> dict
        compare broker book vs portfolio; drift > tolerance -> 'alert'.

## Deterministic time

Paper broker does not sleep. The caller drives the clock:

    broker.submit(...)
    broker.advance(0.05)   # one latency window
    broker.advance(1.0)    # e.g. to cross a limit

An optional real-time mode (auto_tick=True) runs an asyncio event loop
in a background thread that calls advance(tick_interval) every
tick_interval_ms. In that mode all callbacks fire on the asyncio
thread, so any SQLite connection the callback touches must be opened
with check_same_thread=False. Reference stack uses auto_tick=False
and drives advance() from the caller thread.

## Fees & slippage

Config fields (auto-detected as fraction <0.5, or bps >=0.5):

    slippage_bps           applied to base price; BUY up, SELL down
    spot_taker_fee         crypto spot taker
    perp_taker_fee         crypto perp taker
    equity_commission_bps  US equity commission
    asset_class            'spot' | 'perp' | 'equity'

Fee is charged once on the fill notional.

## Persistence

Same SQLite file as the OMS:

    broker_orders(broker_order_id, client_order_id, ts, symbol, side,
                  qty, price, order_type, status, filled_qty,
                  avg_fill_price)   UNIQUE(client_order_id)
    broker_fills(fill_id, broker_order_id, client_order_id, ts,
                 qty, price, fee, slippage)

The in-memory book is reconstructed from broker_orders + broker_fills
on every PaperBroker instantiation, so positions survive process restart.

## What paper does NOT model

Honest gaps - do not treat paper PnL as indicative:

- Order queue priority / FIFO / partial fills.
- Market impact and depth (fills never move the mid).
- Cross-venue routing and refuse-to-fill on gapped books.
- Exchange halts, circuit breakers, symbol rollover.
- Latency jitter / colocated asymmetry (only a fixed fill_latency_ms).
- Margin, cross-margin, portfolio margin netting.
- Funding schedule for perps (no periodic funding debits/credits).
- Borrow / short-locate for equities.
- Corporate actions (splits, dividends, symbol changes).
- IOC / FOK time-in-force semantics; all orders are good-till-fill.

Real adapters (IBKR / Alpaca / Binance) will plug into the same
Broker Protocol; the OMS + risk stack above assumes that contract.
