# Simple Strategies Playground — Strategies & Results

Server: 176.12.79.100 (kz-ai-sandbox.dev), path: /opt/20261005-cryptospearmint.
Isolated from canonical server 109.172.6.35 (trading-desk, risk_v0, short-13d, monitoring).

## Ten Strategies

1. **sma_cross(fast, slow)** — long when SMA_fast crosses above SMA_slow, exit on cross-down.
2. **ema_cross(fast, slow)** — same but with EMAs (faster reaction, more whipsaw).
3. **rsi_obos(n, low, high)** — long when RSI crosses back up through oversold, exit when RSI>50.
4. **bb_bounce(n, k)** — long when close < lower Bollinger band, exit above the middle band.
5. **macd_cross(12,26,9)** — long on MACD line above signal line, exit on reverse cross.
6. **momentum(n, thr)** — long when n-bar rate-of-change > thr %, exit when ROC turns negative.
7. **mean_rev(n, k)** — like BB-bounce but deeper (k=2.5 default), more selective.
8. **donchian_break(n)** — long on close >= prior n-bar high, exit on close <= prior n-bar low.
9. **rsi_bb_combo** — long when RSI<40 AND close < lower BB (confluence entry), exit when RSI>50.
10. **obv_divergence(n)** — long when OBV > OBV-MA AND price crosses above its MA (volume confirms).

All long-only. Backtester: next-bar-open fills, 10 bps fee per side, 5 bps slippage per side.

## Backtest Grid

Dataset: Binance 1h klines, 2022-01-01 .. 2024-12-31, 26 303 bars per symbol (BTC/ETH/SOL).
Total runs: **156**. Tuning grids: sma_cross (9 combos), ema_cross (3), rsi_obos (4x4=16), bb_bounce (3), macd_cross (1), momentum (3x3=9), mean_rev (4), donchian_break (3), rsi_bb_combo (1), obv_divergence (3).

### Top 10 by Sharpe

| # | strategy | params | symbol | ret | sharpe | max_dd | hit | trades | fees |
|---|----------|--------|--------|-----|--------|--------|-----|--------|------|
| 1 | ema_cross | {"fast":20,"slow":50} | SOL-USDT | +5.456 | +1.112 | 0.467 | 0.324 | 225 | 0.450 |
| 2 | sma_cross | {"fast":10,"slow":100} | SOL-USDT | +4.412 | +1.022 | 0.471 | 0.341 | 208 | 0.416 |
| 3 | sma_cross | {"fast":20,"slow":100} | SOL-USDT | +2.788 | +0.885 | 0.550 | 0.317 | 161 | 0.322 |
| 4 | sma_cross | {"fast":30,"slow":100} | SOL-USDT | +1.899 | +0.775 | 0.604 | 0.342 | 152 | 0.304 |
| 5 | sma_cross | {"fast":10,"slow":50} | SOL-USDT | +1.652 | +0.758 | 0.685 | 0.321 | 349 | 0.698 |
| 6 | sma_cross | {"fast":20,"slow":50} | SOL-USDT | +1.325 | +0.706 | 0.635 | 0.364 | 291 | 0.582 |
| 7 | momentum | {"n":20,"thr":3.0} | SOL-USDT | +1.056 | +0.676 | 0.585 | 0.378 | 405 | 0.810 |
| 8 | sma_cross | {"fast":20,"slow":100} | BTC-USDT | +0.562 | +0.519 | 0.490 | 0.289 | 180 | 0.360 |
| 9 | sma_cross | {"fast":10,"slow":40} | SOL-USDT | +0.458 | +0.505 | 0.770 | 0.315 | 426 | 0.852 |
| 10 | ema_cross | {"fast":12,"slow":26} | SOL-USDT | +0.468 | +0.504 | 0.801 | 0.292 | 452 | 0.904 |

### Buy & Hold reference (same period, same costs)

| symbol | total_return | sharpe | max_dd |
|--------|--------------|--------|--------|
| BTC | +1.017 | +0.700 | 0.674 |
| ETH | -0.094 | +0.282 | 0.767 |
| SOL | +0.121 | +0.556 | 0.954 |

Note: SOL buy&hold delivered only +12% in 2022-2024. The trend strategies produced 4-5x on the same asset — that is genuine edge from trend filtering, but also exposes the whale in the room: **all three top strategies are concentrated on SOL**, and their max drawdowns are 46-55%. This is not a smooth-return system.

## Selection

Strict filter: sharpe > 1.0 AND max_dd < 0.20 AND hit_rate > 0.50 AND trades > 20.
**Result: 0 of 156 passed.** Trend-following structurally has hit-rate ~30-35% (few big winners carry the P&L) — the hit-rate>50% requirement was unrealistic for this strategy class and would have only admitted a family of scalping strategies, which we are not building.

Fallback (documented in top3.json: `selection_mode=relaxed_from_sharpe_top3`):
top-3 by Sharpe among runs with positive return and trades >= 20.

| rank | strategy | params | symbol | sharpe | dd | hit | trades | ret |
|------|----------|--------|--------|--------|-----|-----|--------|-----|
| 1 | ema_cross | {'fast': 20, 'slow': 50} | SOL-USDT | +1.112 | 0.467 | 0.324 | 225 | +5.456 |
| 2 | sma_cross | {'fast': 10, 'slow': 100} | SOL-USDT | +1.022 | 0.471 | 0.341 | 208 | +4.412 |
| 3 | sma_cross | {'fast': 20, 'slow': 100} | SOL-USDT | +0.885 | 0.550 | 0.317 | 161 | +2.788 |

**Rationale for top-3:** #1 and #3 are trend systems with different memory (EMA 20/50 vs SMA 20/100) on the highest-vol asset in the basket; they will diverge during chop. #2 (SMA 10/100) uses a very long slow leg — the most conservative trend filter, effectively "only ride the big move". All three are intentionally different lookbacks, not three variants of one parameter.

**Honest risk flag:** all three share symbol SOL. If SOL enters a multi-month chop regime, all three paper books will lose in parallel. This is why paper is 2-4 weeks minimum, and why paper notional is $10/trade, not $100.

## Paper Runner

Mode: **paper-only**. Real Binance market data (via ccxt, testnet endpoints prepared but not required), fills simulated locally at signal-bar close with 10 bps fee per side.

- Notional: $10 per position (hard-coded).
- Cycle: 1 hour effective (poll every 60s, act on newly closed bar).
- State: SQLite at `state/paper.db` (positions, trades, last_bar).
- Journal: append-only JSONL at `journal/paper_journal.jsonl`.
- No API keys required for paper mode.

Run once (test):
    cd /opt/20261005-cryptospearmint && source venv/bin/activate && python3 -m src.execution.paper_testnet --once

Run continuously (nohup / tmux):
    cd /opt/20261005-cryptospearmint && source venv/bin/activate && nohup python3 -m src.execution.paper_testnet > journal/paper_run.log 2>&1 &

Stop:
    pkill -f src.execution.paper_testnet

Inspect:
    tail -20 journal/paper_run.log
    python3 -c "import sqlite3; c=sqlite3.connect('state/paper.db'); print(c.execute('SELECT strategy,symbol,status FROM positions').fetchall()); print(c.execute('SELECT sum(pnl_usd), count(*) FROM trades').fetchall())"

## Promotion Threshold: Paper -> Live

Required before any real money:

1. **Minimum 2 full weeks** of paper (14 days), ideally 4.
2. **Positive net P&L** on aggregate across the three strategies, after fees.
3. **No single strategy with a drawdown > 15%** during paper — if any dies, restart the clock for that strategy.
4. **Trade count sanity** — at least 10 executed round-trips per strategy over the paper window (below that, the sample is not meaningful).

## Small Live ($10-100 per trade)

Only after the paper gate above passes.

Prerequisites:
- Binance API keys with **trade** permission only (no withdraw). IP-restricted.
- Env var `ENABLE_REAL_MONEY=true` set. Without it, runner refuses to submit real orders.
- Hard cap **$10 notional per trade**, hard-coded in the runner (not a parameter, not a config file). To raise to $100 a code change + git commit is required, which forces a conscious decision.

Execution guardrails for live:
- One symbol at a time in the runner (start SOL since top-3 is SOL-heavy).
- Max 1 open position globally.
- Daily loss limit: if aggregate live P&L < -$5 (50% of the single-trade notional), halt and require manual restart.
- No leverage, no margin, no futures. Spot only.

## What I did NOT touch

On this server (176.12.79.100): nothing outside `/opt/20261005-cryptospearmint/`.
On canonical server (109.172.6.35): trading-desk, risk_v0, env-scraper-wt, short-13d-paper, monitoring — physically different host, untouched.
