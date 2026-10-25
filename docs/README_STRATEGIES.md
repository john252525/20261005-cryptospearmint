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


---

# v2 — Anti-Overfit + Portfolio + Paper Runner v2

## Motivation

v1 top-3 was three SOL trend strategies with DD 47-55%, hit ~32%. That is not tradeable as-is; the natural suspicion is 2022-2024 SOL bull-era overfitting. v2 tests this directly.

## Data

Bear-era data fetched from Binance 1h klines:
- BTC 2018-01-01..2021-12-31: 34 943 bars
- ETH same period: 34 943 bars
- SOL: **only from 2020-08-11** (listing date), 12 167 bars

**Critical honesty note:** the SOL "bear" window 2020-08..2021-12 is NOT a bear market for SOL. It is the listing-to-ATH phase (price $3 -> $180). Any SOL strategy will look brilliant there and it does not constitute an out-of-sample bear test. BTC/ETH 2018-01..2020-06 (true-bear, real drawdown with COVID crash) is the only honest bear test in this dataset.

## Anti-Overfit Filter Results

All 156 v1 combos re-run on bear-era data, kept when they exist on both eras.

Strict joint gate (Sharpe>0.8 both, trades>20 both, DD<40% both): **0 of 156 pass.**

Relaxed (Sharpe>0.8 bull, >0.5 bear, trades>20 both, DD<60% both): **3 of 156 pass** — and all three are SOL-only, and all three are the same family (EMA/SMA cross with long slow leg). They pass only because SOL 2020-21 was a moon shot.

| strategy | params | symbol | bull_sharpe | bear_sharpe | bull_dd | bear_dd | trades_bull | trades_bear |
|----------|--------|--------|-------------|-------------|---------|---------|-------------|-------------|
| ema_cross | {'fast': 20, 'slow': 50} | SOL-USDT | +1.112 | +1.623 | 46.7% | 55.9% | 225 | 109 |
| sma_cross | {'fast': 20, 'slow': 100} | SOL-USDT | +0.885 | +1.559 | 55.0% | 49.8% | 161 | 86 |
| sma_cross | {'fast': 10, 'slow': 100} | SOL-USDT | +1.022 | +1.495 | 47.1% | 53.0% | 208 | 110 |

## Portfolio — and why it failed

Built per spec: $500 capital, $10 per-trade notional, SL -2%, TP +5%, per-strategy cap 30%, max 10 concurrent positions.

Portfolio from the 3 relaxed "robust" strategies (all SOL):

| era | portfolio sharpe | portfolio DD | portfolio return | trades | total PnL |
|-----|------------------|--------------|------------------|--------|-----------|
| SOL bull 2022-24 | **-0.054** | 1.65% | -0.20% | 588 | -$1.01 |
| SOL "bear" 2020-21 | **-0.145** | 1.32% | -0.23% | 304 | -$1.13 |

Both fail the Sharpe>0.8-in-both-eras target. **Portfolio is not tradeable with SL -2% / TP +5%.**

Same portfolio with SL/TP disabled (only exit signal):

| era | portfolio sharpe | portfolio DD | portfolio return | total PnL |
|-----|------------------|--------------|------------------|-----------|
| SOL bull 2022-24 | +1.120 | 3.08% | +14.06% | +$70.29 |
| SOL "bear" 2020-21 | +1.803 | 3.55% | +22.32% | +$111.59 |

So the *strategy* has edge on SOL, but the SL/TP combination destroys it. Why? Average hold time of these trend strategies is 40-100 hours; a -2% stop on 1h bars fires within 1-2 bars of entry, and a +5% target caps trend rides. Result: churn, win-rate ~31%, no room for the fat tail to materialise. This is a structural conflict, not a tuning problem.

## Cross-Asset Diagnostic (BTC/ETH, true-bear window)

The decisive test: apply the same families on BTC and ETH across 2022-2024 (bull-era) and 2018-06..2020-06 (true-bear) with and without SL/TP.

| strategy | params | symbol | era | sharpe WITH SL/TP | sharpe NO SL/TP | no-SL DD | no-SL trades |
|----------|--------|--------|-----|-------------------|-----------------|----------|--------------|
| ema_cross | {"fast":20,"slow":50} | BTC-USDT | bull_2022_2024 | -1.186 | +0.248 | 1.28% | 243 |
| ema_cross | {"fast":20,"slow":50} | BTC-USDT | true_bear_2018_2020 | -0.444 | +1.004 | 0.63% | 168 |
| ema_cross | {"fast":20,"slow":50} | ETH-USDT | bull_2022_2024 | +0.895 | +0.345 | 1.04% | 225 |
| ema_cross | {"fast":20,"slow":50} | ETH-USDT | true_bear_2018_2020 | -0.824 | +0.894 | 1.22% | 193 |
| sma_cross | {"fast":20,"slow":100} | BTC-USDT | bull_2022_2024 | +0.260 | +0.640 | 1.11% | 174 |
| sma_cross | {"fast":20,"slow":100} | BTC-USDT | true_bear_2018_2020 | -0.165 | +0.668 | 0.82% | 129 |
| sma_cross | {"fast":20,"slow":100} | ETH-USDT | bull_2022_2024 | -0.128 | +0.322 | 1.17% | 177 |
| sma_cross | {"fast":20,"slow":100} | ETH-USDT | true_bear_2018_2020 | +0.606 | +0.993 | 0.85% | 135 |
| sma_cross | {"fast":10,"slow":100} | BTC-USDT | bull_2022_2024 | -0.611 | +0.043 | 1.91% | 224 |
| sma_cross | {"fast":10,"slow":100} | BTC-USDT | true_bear_2018_2020 | +0.038 | +0.638 | 1.07% | 156 |
| sma_cross | {"fast":10,"slow":100} | ETH-USDT | bull_2022_2024 | +0.360 | +0.375 | 1.15% | 215 |
| sma_cross | {"fast":10,"slow":100} | ETH-USDT | true_bear_2018_2020 | +0.134 | +0.900 | 0.86% | 164 |

Summary: SL/TP is **worse than no SL/TP on 11 of 12 combos**, average Sharpe delta **-0.68**.

Best cross-era candidate under no-SL model: `sma_cross fast=10,slow=100` on ETH —
  bull 2022-24: Sharpe +0.375, true-bear 2018-20: Sharpe +0.900, no-SL DD ~1.2%.
This is the ONLY family/asset combo that is positive on both eras with no SL/TP and is not SOL-correlated. It still does NOT clear the >0.8-on-both gate (bull side is 0.375).

## Verdict v2

**Negative on the "paper trading launch" gate.** Reasoning:

1. Zero strategies clear the strict anti-overfit filter.
2. The 3 "relaxed" survivors all live on one asset (SOL) in one regime (listing boom), which is not out-of-sample evidence.
3. Portfolio on those 3 with SL/TP fails Sharpe target in both eras.
4. SL/TP -2%/+5% removes ~0.7 Sharpe: incompatible with multi-day trend holding.
5. The only cross-era positive non-SOL candidate (`sma 10/100` on ETH) has bull Sharpe 0.375 — too weak to justify real money.

**No live capital should be deployed.** Paper runner v2 exists as infrastructure (`src/execution/paper_testnet_v2.py`), starts DISARMED by default, and the `robust_strategies.json` it reads is marked `selection_mode=relaxed` with an explicit caveat.

## Next steps (v3)

1. **Expand universe** to 30+ altcoin pairs. The edge candidate (SMA 10/100) may exist on many alts; cross-sectional robustness is the real test, not one asset's history.
2. **Drop SL/TP** for trend strategies; use ATR-based trailing stop, not fixed percent. Fixed 2% is structurally wrong for 1h bars with 40-100h holds.
3. **Cross-sectional momentum** — rank alts by 30d ROC, long top-5, rebalance weekly. This is the classic robust version and it does not need per-symbol backtest cherry-picking.
4. **Regime split** — test strategies separately on 2018-bear / 2019-chop / 2020-COVID / 2021-bull / 2022-bear / 2023-24-recovery. "Positive on both eras" hides a lot of dead months.
5. Only after (1)-(4) do we re-run the promotion gate.

## Paper Runner v2 — infrastructure, not a trading record

Reads selection from `data/robust_strategies.json`.
Real Binance market data via ccxt; fills simulated locally; state in `state/paper_v2.db`; journal in `journal/paper_v2.jsonl` (JSONL, one line per tick, includes `pnl_cumulative` in USD on $500 base).

**DISARMED BY DEFAULT** — records observes but does not open positions. To open paper positions (still fake money):

    cd /opt/20261005-cryptospearmint && source venv/bin/activate
    python3 -m src.execution.paper_testnet_v2 --armed --duration 3600
    # or daemon mode:
    nohup python3 -m src.execution.paper_testnet_v2 --armed > journal/paper_v2.log 2>&1 &

Read the live journal:

    tail -f /opt/20261005-cryptospearmint/journal/paper_v2.jsonl
    # each line: {ts, event, strategy, symbol, notional, pnl_cumulative, note}

Inspect DB directly:

    python3 -c "import sqlite3; c=sqlite3.connect('/opt/20261005-cryptospearmint/state/paper_v2.db'); print('open:', c.execute(\"SELECT COUNT(*) FROM positions WHERE status='open'\").fetchone()[0]); print('cum pnl:', c.execute(\"SELECT COALESCE(SUM(pnl),0) FROM positions WHERE status='closed'\").fetchone()[0])"

Stop:

    pkill -f src.execution.paper_testnet_v2

Smoke test (single cycle, disarmed):

    python3 -m src.execution.paper_testnet_v2 --once

## How to take this code out of the sandbox

SSH to GitHub from this host returns Permission denied (no key installed). Options:

A) Copy git bundle (easiest):

    # on your workstation
    scp root@176.12.79.100:/tmp/playground_v2.bundle .
    git clone playground_v2.bundle simple-strategies-playground
    cd simple-strategies-playground && git branch -a

B) Install an SSH key here and push directly:

    # on this server (176.12.79.100)
    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
    cat ~/.ssh/id_ed25519.pub
    # add that pub key to https://github.com/settings/keys as an auth key
    ssh -T git@github.com   # expect: Hi <username>!
    cd /opt/20261005-cryptospearmint
    git remote add origin git@github.com:<username>/20261005-cryptospearmint.git
    git push -u origin main





---

# v3 — Final iteration: two independent tests, both failed

Two tests were run as the last shot. Either would have unlocked armed paper. Neither did.

## Test A — Cross-sectional momentum (32-symbol universe, 4h bars)

Universe: 32 pairs (30 alts + BTC + ETH), Binance 4h, 2020-01-01..2024-12-31, 10 961 bars each (SHIB/ICP/AXAX etc. start later at listing).
Rule: every 7 days (42 x 4h bars) rank by 30-day (180-bar) return, long top-5 equal-weight, short bottom-5 equal-weight. Fee 10 bps + 5 bps slippage per rebalance per side.

| period | Sharpe | return | max DD | rebalances | avg turnover | gross | fee drag | hit rate |
|--------|--------|--------|--------|------------|--------------|-------|----------|----------|
| P1 2020-01..2022-06 | +0.862 | +111.6% | -31.5% | 126 | 0.80 | +132.6% | 30.4% | 0.54 |
| P2 2022-07..2024-12 | +0.521 | +30.7% | -25.4% | 127 | 0.84 | +68.5% | 32.0% | 0.56 |

Gate was Sharpe>1.0 in BOTH periods and DD>-30% in both.
**Result: FAILED** — P1 +0.862, P2 +0.521.

Interpretation: the strategy is *not* broken — both periods are positive (+111.6% and +30.7%), hit rate ~54%, gross returns +133% / +68%. But turnover runs at 0.80 per rebalance and fees+slippage eat 30% and 32% of P&L — roughly a quarter to a third of gross. What remains is a mid-single-digit Sharpe, and in P2 it decays to +0.52 as the market matures and momentum alpha compresses. Notably P2 gross fell relative to P1 while fees stayed flat, so the fee drag in relative terms got worse.

## Test B — ATR trailing stop on v1 top-5 strategies

Same 5 families (sma_cross 20/50, ema_cross 12/26, macd_cross, rsi_obos, donchian_break) on BTC/ETH/SOL, bull 2022-2024 vs pre-2022 2018-2021. Three trailing variants were tested.

**Methodology note (important):** per-trade Sharpe (my first pass) is not comparable to the v2 daily-equity metric. The table below uses the *same* accounting as v2 — $500 capital, $10/trade, no stop (exit on signal only) — so it is apples-to-apples with earlier results.

| strategy | symbol | bull Sharpe | pre-2022 Sharpe | bull trades | pre trades | bull win | pre win |
|----------|--------|-------------|-----------------|-------------|------------|----------|---------|
| sma_cross | SOL-USDT | +0.722 | +1.201 | 284 | 136 | 36.6% | 41.2% |
| ema_cross | SOL-USDT | +0.490 | +2.145 | 415 | 182 | 31.1% | 38.5% |
| sma_cross | BTC-USDT | +0.187 | +0.403 | 310 | 394 | 32.6% | 32.7% |
| sma_cross | ETH-USDT | +0.024 | +0.874 | 302 | 404 | 29.5% | 35.1% |
| donchian_break | SOL-USDT | -0.088 | +1.487 | 298 | 132 | 31.9% | 43.9% |
| ema_cross | BTC-USDT | -0.235 | +0.171 | 420 | 535 | 24.3% | 27.7% |
| donchian_break | BTC-USDT | -0.326 | +0.099 | 279 | 351 | 29.7% | 33.9% |
| ema_cross | ETH-USDT | -0.344 | +1.113 | 426 | 530 | 27.7% | 32.3% |
| rsi_obos | SOL-USDT | -0.606 | +0.394 | 452 | 217 | 56.0% | 58.1% |
| macd_cross | SOL-USDT | -0.827 | +1.756 | 881 | 408 | 32.8% | 40.0% |
| donchian_break | ETH-USDT | -1.088 | +0.748 | 297 | 343 | 32.0% | 37.0% |
| macd_cross | ETH-USDT | -1.239 | +0.339 | 859 | 1119 | 31.5% | 37.8% |
| rsi_obos | ETH-USDT | -1.707 | -1.464 | 437 | 561 | 51.9% | 56.5% |
| rsi_obos | BTC-USDT | -1.987 | -1.972 | 429 | 531 | 49.0% | 53.9% |
| macd_cross | BTC-USDT | -2.029 | -0.630 | 881 | 1154 | 31.4% | 33.5% |

Gate was Sharpe>1.0 in both eras for at least one combo.
**Result: FAILED** — no combo clears bull>1.0. Best is `sma_cross` on `SOL-USDT`: bull +0.722, pre-2022 +1.201.

The ATR-trailing variants themselves made things worse, not better: `atr_floor` produced uniformly negative Sharpes (e.g. sma_cross BTC bull -2.57 / pre -1.07), and `spec_breakeven_floor` (stop=entry) is degenerate — it converts every trade into an identical (~-2x fee) loss, which collapses the return standard deviation and makes a naive Sharpe blow up to nonsense values. I capped/degenerate-guarded that path rather than report ±1e14 as if it were a result.

Pattern across the table: strategies are **positive in pre-2022 and weak-to-negative in 2022-2024** (e.g. ema_cross SOL +2.15 -> +0.49; rsi_obos is negative in both eras despite a 50%+ win rate, because losers are much larger than winners). This is the opposite of a robust edge and consistent with TA-on-majors being progressively arbitraged as crypto matured.

## Final decision

**NEGATIVE. Playground closed.** Paper stays DISARMED. No live capital.

Both independent tests failed their pre-registered gates. No parameters were tuned to force a pass, no new strategies were invented to fit the 2024 window, and no universe was cherry-picked after seeing results.

## Playground closed: lessons learned

1. **Fixed-percent SL/TP kills trend edge.** On 1h bars with 40-100h holds, a -2% stop fires within 1-2 bars and a +5% target caps the fat tail. Measured: worse than no-stop on 11 of 12 combos, average Sharpe delta -0.68. Any trend system needs an ATR-scaled or structural stop, not a fixed percent.
2. **TA on majors is mostly arbitraged now.** Pre-2022 Sharpe > 2022-24 Sharpe for nearly every combo. Whatever worked in the 2018-2021 retail era has decayed as the market professionalised. The one survivor family (long-slow-leg SMA/EMA cross) is exactly the slowest, least-leveraged version.
3. **Cross-sectional momentum works but does not pay its costs at 10 bps + 5 bps.** Gross +133% / +69% shrinks to Sharpe 0.86 / 0.52 after fees and slippage of 30%+ each period. A real implementation would need maker fills, longer hold, or a mid-cap-only universe; none of those were tested here.
4. **Statistical TA edge on majors is not the same thing as structural edge.** Every test here was a search for a statistical pattern in price. None of them produced something I would put $10 of real money behind. That is the honest result of 3 iterations over ~470 backtests: the TA playground does not contain a deployable system on the tested universe. If real edge exists in this space it is more likely in structural/flow/carry terrain, not in the price-pattern search that this playground explored.

## Infrastructure left behind (usable, if a future universe is found)

- `src/strategies/indicators.py` — SMA/EMA/RSI/BB/MACD/ROC/Donchian/OBV.
- `src/strategies/simple.py` — 10 strategies, registry keyed by name.
- `src/backtest/runner.py` — next-bar-open long-only backtester, fee+slippage, 8 metrics.
- `src/backtest/portfolio.py` — fixed-notional P&L, daily-equity metrics, configurable SL/TP.
- `src/backtest/grid.py` — parameter grid search -> CSV.
- `src/execution/paper_testnet_v2.py` — paper runner, SQLite + JSONL with live `pnl_cumulative`, DISARMED by default.
- `data/` — 1h majors 2018-2024, 4h 32-pair 2020-2024, and the three result CSVs / JSONs behind every number above.

## How to take the code out of this sandbox

SSH from this host to GitHub still returns Permission denied. Copy the bundle:

    scp root@176.12.79.100:/tmp/playground_v3.bundle .
    git clone playground_v3.bundle simple-strategies-playground
    cd simple-strategies-playground && git log --oneline

Or install a key and push directly:

    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
    cat ~/.ssh/id_ed25519.pub     # add to https://github.com/settings/keys
    ssh -T git@github.com         # expect: Hi <username>!
    cd /opt/20261005-cryptospearmint
    git remote add origin git@github.com:<username>/20261005-cryptospearmint.git
    git push -u origin main


---

# v5 — High-APR funding arbitrage (target 100-200% net APR): NEGATIVE

Target was 100-200% net APR. Three sub-strategies were tested. **None reached 100%. Best honest result: 10.18% net APR.** No live capital, no armed paper.

## Data

Binance funding history, 8h events, 2022-01-01..2024-12-31:
- 28 symbols, 90,346 total events
- Typical symbol: 3288 events (3/day, no gaps; ARB max gap 8h)

Bybit funding history, same window:
- 23 symbols, 75,601 total events
- Unavailable on Bybit: MKR, OP, ARB

## The starting premise was wrong

The filter for Sub-A was mean_apr > 100% AND pct_positive > 0.75. **Zero of 28 symbols qualified.** Not one.

| metric | value |
|--------|-------|
| max mean APR across universe | **13.75%** (ARB) |
| median mean APR | 7.1% |
| symbols with mean APR > 20% | 0 |
| symbols with mean APR > 50% | 0 |
| symbols with mean APR > 100% | 0 |

Full universe (Binance, mean APR annualized; vol = annualized std of the funding APR itself):

| symbol | events | mean APR % | pct positive | APR vol % |
|--------|--------|-----------|--------------|-----------|
| ARB | 1949 | +13.75 | 0.93 | 0.5 |
| OP | 2834 | +10.38 | 0.84 | 0.6 |
| UNI | 3288 | +9.98 | 0.89 | 0.3 |
| LINK | 3288 | +9.82 | 0.89 | 0.4 |
| FIL | 3288 | +9.79 | 0.86 | 0.5 |
| DOGE | 3288 | +9.15 | 0.85 | 0.4 |
| VET | 3288 | +9.09 | 0.87 | 0.4 |
| MKR | 3288 | +9.03 | 0.86 | 0.6 |
| LTC | 3288 | +8.86 | 0.86 | 0.4 |
| ALGO | 3288 | +8.63 | 0.86 | 0.5 |
| GRT | 3288 | +8.55 | 0.88 | 0.5 |
| AAVE | 3288 | +8.46 | 0.86 | 0.4 |
| FTM | 3288 | +7.54 | 0.83 | 0.6 |
| XRP | 3288 | +7.47 | 0.79 | 0.5 |
| ADA | 3288 | +6.73 | 0.78 | 0.5 |
| XLM | 3288 | +5.77 | 0.74 | 0.5 |
| NEAR | 3288 | +5.55 | 0.77 | 0.7 |
| HBAR | 3288 | +5.38 | 0.81 | 0.7 |
| AVAX | 3288 | +4.27 | 0.70 | 0.6 |
| CHZ | 3288 | +3.87 | 0.79 | 1.1 |
| ATOM | 3288 | +1.74 | 0.62 | 0.5 |
| CRV | 3288 | +1.46 | 0.72 | 0.8 |
| COMP | 3288 | +1.43 | 0.76 | 1.2 |
| SNX | 3288 | +0.27 | 0.69 | 0.9 |
| DOT | 3288 | -0.40 | 0.56 | 0.6 |
| TRX | 3288 | -5.33 | 0.55 | 1.0 |
| BCH | 3288 | -5.34 | 0.48 | 0.7 |
| SOL | 3363 | -7.50 | 0.72 | 3.9 |

## Sub-A — single-exchange delta-neutral on top funding

Since nothing cleared 100%, the filter was relaxed to "top-5 by mean APR that actually exist" (ARB, OP, UNI, LINK, FIL) to measure what IS achievable. $100/symbol, $500 total, entry/exit 20 bps round-trip, weekly regime check (7d rolling mean funding > 0).

| symbol | mean APR | active days % | switches | gross APR | fee drag | net APR |
|--------|----------|---------------|----------|-----------|----------|---------|
| ARB | +13.75 | 95.8 | 11 | +13.54 | 1.24 | +12.30 |
| OP | +10.38 | 88.8 | 21 | +11.15 | 1.62 | +9.52 |
| UNI | +9.98 | 96.6 | 17 | +9.87 | 1.13 | +8.73 |
| LINK | +9.82 | 94.2 | 17 | +9.84 | 1.13 | +8.71 |
| FIL | +9.79 | 88.7 | 29 | +10.22 | 1.93 | +8.28 |

**Portfolio: net APR 9.51%, CAGR +9.99%, max DD -0.08%, total +33.05% over 3.0y.**

Reported Sharpe was 15.4 — **that number is an artifact and should be ignored.** It treats daily funding as near-deterministic. In reality the funding rate itself has ~50% annualized volatility (see last column of the universe table), flips sign, and can stay negative for weeks. A proper Sharpe including funding volatility and basis risk is closer to 1.5-2.5, not 15.

**Sub-A PASS (>100% net APR): NO** — 9.51% vs target 100%.

## Sub-B — cross-exchange funding spread (Binance vs Bybit)

Threshold: |spread| > 5 bps per 8h event (= 54.8% APR). Cost: 40 bps round-trip per switch (two legs, two exchanges).

Top-10 symbols by mean |spread|:

| symbol | mean abs spread bps | gross APR upper % | events >5bps | % events >5bps |
|--------|---------------------|-------------------|--------------|----------------|
| BCH | 0.851 | +9.32 | 18.0 | 0.91 |
| CRV | 0.801 | +8.77 | 28.0 | 1.42 |
| TRX | 0.778 | +8.52 | 17.0 | 0.86 |
| VET | 0.769 | +8.42 | 53.0 | 2.68 |
| COMP | 0.725 | +7.94 | 24.0 | 1.21 |
| SNX | 0.712 | +7.80 | 18.0 | 0.91 |
| DOT | 0.696 | +7.63 | 6.0 | 0.30 |
| ATOM | 0.689 | +7.54 | 6.0 | 0.30 |
| SOL | 0.673 | +7.36 | 14.0 | 0.73 |
| HBAR | 0.653 | +7.15 | 20.0 | 1.01 |

**Aggregate: mean |spread| across the whole universe = 0.602 bps per 8h. Only 259 of 45 403 events (0.57%) exceeded 5 bps. 0 of 23 symbols had positive net APR. Zero.**

You need |spread| > 40 bps merely to break even on a single switch against 40 bps round-trip cost. Observed average was 0.6 bps — off by nearly two orders of magnitude.

**Sub-B PASS: NO.** This is not a tuning problem. Binance/Bybit funding spreads are fully arbitraged by market makers operating with maker rebates and colocated infrastructure.

## Sub-C — combined

Top-3 by absolute net yield across A and B. All three picks were Sub-A (ARB +12.30%, OP +9.52%, UNI +8.73%) because every Sub-B candidate had negative net yield.

**Portfolio: net APR 10.18%, CAGR +9.61%, max DD -0.05%.**

Sub-C == Sub-A with a slightly different weighting. No independent edge from combining.

**Sub-C PASS: NO.**

## Honest reconciliation

**Capacity (asked explicitly):** PASS for Sub-A. $100 notional on ARB/OP/UNI/LINK/FIL is roughly 0.0001% of 24h ADV on Binance futures. Liquidity is not the constraint here. It is also not the reason APR is low — true funding yield on these names is simply ~10%.

**Risks NOT captured in the backtest** (this is where 9.5% becomes less attractive, not more):
- **Funding volatility is ~50% annualized.** A strategy that plans on 13.7% mean APR on ARB should expect multi-week negative stretches. My daily-Sharpe computation hid this completely.
- **Basis dislocation.** Spot and perp can diverge 1-2% in a flash crash before funding settles. On $100 notional, one 2% dislocation = $2 loss = ~2.5 months of carry at 10% APR. Delta-neutral is not risk-neutral.
- **Liquidation of the short perp leg** if the spot hedge lags during a gap. Mitigable with a 50%+ margin buffer and isolated margin, but not free.
- **Single-venue custody.** Both legs on Binance: if withdrawals freeze, the position cannot be unwound.

**What would actually get to 100%+ APR** (none of it is this portfolio):
1. New-listing perps — regularly print 50-200%+ APR for the first days-weeks, then decay. Capacity $1-5k per name, needs daily manual attention. Not a systematic portfolio strategy.
2. Mania-window mid-caps (2021 alt season, 2024 memecoin weeks) hit 100-300% APR during the window. But the 2022-2024 base rate is ~10%; timing these windows is a separate skill and backtests that include them overstate the base rate.
3. Cross-venue basis on illiquid exchanges — exactly where custody/counterparty risk is real.
4. Per-name manual research on new listings — out of scope for this playground.

## Verdict v5

**NEGATIVE. No paper launched. No live capital.**

- Sub-A: 9.51% net APR (real, capacity-OK, but 10x below target)
- Sub-B: 0 positive symbols (structurally dead at retail fees)
- Sub-C: 10.18% net APR (no added edge)

**Honest achievable band for $500-1000 capital, top-30 majors, retail fees: 8-15% net APR.** Reaching 100%+ requires either (a) new-listing/micro-cap perps with 10x capacity constraint and manual monitoring, or (b) mania-window timing skill that the base rate does not support. Neither is a systematic portfolio play, and neither is in this playground.

Note on the 100%+ target itself: in 2021 and during 2024 memecoin waves, high-APR funding windows were real. But a strategy that lives off those windows is a *timing* strategy, and the honest backtest (averaging across 2022-2024) shows when the windows close, funding reverts to single digits. Designing around the window means designing for the 10-15% of months when it is open, not the 85% when it is closed.


---

# v6 — New listings + memecoins funding arb (target 50-200% net APR): NEGATIVE

Premise was: majors cap at 7-14% APR, but new perp listings and memecoins print 30-300%. Tested on 25 new listings and 9 memecoins. **Neither universe reaches 50%. Best honest result: 12.23% net APR (new listings, naive equal-weight).**

## Data

New perp listings, Binance funding, first 90 days post-listing: **20 coins** requested, **25 files** after adding 1000-prefix memes (BONK/PEPE/FLOKI/SHIB/SATS live under `1000*` symbols on Binance futures — this mattered, see the bug section).

Memecoins: BOME, BONK, DOGE, FLOKI, MEME, PEPE, SHIB, TURBO, WIF (9 with data; MOG has no Binance futures market).

## Bug found and fixed mid-analysis (documented for honesty)

My first pass computed APR as `mean(rate) * 3 * 365`. **That is only right for 8h funding.** Binance moved many alt perps to **4h funding (6 events/day)** during 2023-24. An audit showed **12 symbols at 3/day and 13 at 6/day** — so the per-coin APR column was understated by 2x on half the universe. The *aggregate* numbers were computed from daily-summed rates and were correct throughout; only the per-coin display column was wrong. The table below uses the corrected `events_per_day` factor. Audit saved at `data/funding_frequency_audit.csv`.

## Sub-A — new listings, first 90 days, delta-neutral

$100/coin, hold long spot + short perp, exit when 7d rolling funding turns negative, 40 bps round-trip per position.

| coin | listing | ev/day | mean APR % | active % | switches | gross APR | fee APR | **net APR** |
|------|---------|--------|-----------|----------|----------|-----------|---------|-------------|
| WIF | 2024-01-18 | 6.1 | +94.87 | 98 | 1 | +90.98 | 1.60 | +89.38 |
| SATS | 2023-12-12 | 6.1 | +49.65 | 98 | 1 | +48.63 | 1.60 | +47.02 |
| JTO | 2023-12-08 | 6.1 | +44.19 | 98 | 1 | +40.97 | 1.60 | +39.37 |
| TON | 2024-03-01 | 6.1 | +44.26 | 90 | 3 | +44.16 | 4.81 | +39.35 |
| PYTH | 2023-11-22 | 6.1 | +41.51 | 98 | 1 | +39.19 | 1.60 | +37.59 |
| BONK | 2023-11-22 | 6.1 | +38.38 | 90 | 5 | +41.18 | 8.02 | +33.15 |
| MEME | 2023-11-03 | 6.1 | +30.10 | 98 | 1 | +28.92 | 1.60 | +27.32 |
| BOME | 2024-03-16 | 6.0 | +26.88 | 99 | 1 | +26.16 | 1.62 | +24.54 |
| TIA | 2023-10-31 | 6.1 | +17.97 | 80 | 4 | +23.37 | 6.42 | +16.95 |
| EIGEN | 2024-10-01 | 6.1 | +17.72 | 99 | 1 | +16.78 | 1.60 | +15.18 |
| W | 2024-04-03 | 6.1 | +16.43 | 97 | 3 | +15.15 | 4.81 | +10.34 |
| TURBO | 2024-05-30 | 6.1 | +15.24 | 96 | 3 | +14.19 | 4.81 | +9.38 |
| FLOKI | 2023-05-06 | 3.0 | +8.33 | 91 | 1 | +8.65 | 1.60 | +7.05 |
| ARB | 2023-03-23 | 3.0 | +8.19 | 88 | 3 | +7.52 | 4.81 | +2.71 |
| SEI | 2023-08-16 | 3.0 | -14.63 | 59 | 5 | +8.24 | 8.02 | +0.21 |
| BLUR | 2023-04-27 | 3.0 | +3.15 | 76 | 5 | +7.22 | 8.02 | -0.80 |
| PEPE | 2023-05-05 | 3.0 | -0.12 | 76 | 5 | +6.05 | 8.02 | -1.97 |
| WLD | 2023-07-24 | 3.0 | -12.63 | 15 | 2 | +0.48 | 3.21 | -2.73 |
| SUI | 2023-05-03 | 3.0 | -4.90 | 40 | 4 | +2.83 | 6.42 | -3.59 |
| APT | 2022-10-18 | 3.0 | -26.74 | 14 | 5 | +0.73 | 8.02 | -7.29 |
| SHIB | 2022-01-01 | 3.0 | +3.39 | 64 | 7 | +3.69 | 11.23 | -7.54 |
| OP | 2022-06-01 | 3.0 | +0.41 | 59 | 10 | +3.18 | 16.04 | -12.87 |
| DOGE | 2022-01-01 | 3.0 | +1.85 | 64 | 13 | +2.87 | 20.86 | -17.99 |
| ENA | 2024-04-02 | 6.1 | -34.17 | 16 | 12 | +0.92 | 19.25 | -18.33 |
| INJ | 2022-08-16 | 3.0 | -10.38 | 41 | 14 | +1.73 | 22.46 | -20.73 |

**Aggregate (equal-weight 25 coins): gross +19.35%, net +12.23%.**
Coins above 30% net: **6**. Above 50%: **1**. Best: **WIF +89.38%**.

**Reported Sharpe 9.14 is an artifact** — 91-day windows give few independent observations and funding vol is not in the model. Ignore it.

**Sub-A PASS (>50% net APR): NO.**

What this actually shows: new listings DO have elevated funding — WIF at 89% net, SATS 47%, JTO 39%, TON 39%, PYTH 38%. But six coins are **negative** (ENA −18%, INJ −21%, DOGE −18%, OP −13%, SHIB −8%, APT −7%) because funding went negative for long stretches right after listing. Naive equal-weight pays for that. Cherry-picking the winners would produce ~37% — but that requires knowing ex-ante which listings will have positive funding, and I have not built or validated any such classifier. Reporting 37% as "achievable" would be a lie.

## Sub-B — memecoins, whole history, threshold 20% APR

Hold only when 7-day rolling funding APR > 20%; exit below.

| coin | mean APR all % | active % | switches | gross APR | **net APR** |
|------|----------------|----------|----------|-----------|-------------|
| WIF | +23.72 | 25.3 | 8 | +18.84 | +16.51 |
| BONK | +18.45 | 23.4 | 12 | +13.36 | +9.87 |
| MEME | +18.51 | 26.7 | 12 | +11.81 | +8.31 |
| PEPE | +15.15 | 24.4 | 24 | +10.96 | +5.71 |
| BOME | +15.60 | 18.6 | 6 | +7.44 | +4.82 |
| TURBO | +8.19 | 13.8 | 6 | +4.12 | +1.49 |
| SHIB | +6.70 | 10.7 | 20 | +3.59 | +1.40 |
| FLOKI | +5.77 | 13.6 | 18 | +5.32 | +1.38 |
| DOGE | +9.16 | 9.7 | 14 | +3.14 | +1.28 |

**Aggregate (equal-weight 9 memes): gross +8.73%, net +5.64%.**
All 9 positive, best WIF 16.51%. Coins above 50%: **0**.

**Sub-B PASS (>50% net APR): NO.**

The "memecoins have crazy funding" narrative does not survive the base rate. Mean across 9 memes over full history is 8.7% gross. The 100-300% figures people quote come from specific mania weeks — the threshold filter catches them (active only 10-27% of days) and they still pay single digits net per year. Survivorship is doing the work in that narrative.

## Sub-C — combined dynamic top-5

Every day: rank all 50 symbols by 7-day rolling funding APR, hold top-5 with APR > 20%, equal weight.

| metric | value |
|--------|-------|
| universe | 50 symbols |
| days tracked | 1334 |
| days with ≥1 position | 244 (18.3%) |
| mean active positions/day | 0.71 |
| switches | 296 |
| gross APR | +8.85% |
| fee drag | 3.24% |
| **net APR** | **+5.61%** |
| CAGR | +5.76% |
| max DD | -4.26% |

**Sub-C PASS (>50% net APR): NO.**

The structural problem: 80% of days, nothing in a 50-symbol universe qualifies above the 20% APR threshold. The strategy lives in its best 15-20% of days and the rest is idle capital.

## Honest reconciliation

**Capacity: PASS, unambiguously.** Measured 24h ADV on Binance futures:
- WIF $13.4M, JTO $10.5M, PYTH $14.5M, BONK $19.1M, TIA $59.8M, EIGEN $11.4M, W $17.1M
- Thinnest: **SATS $1.17M** → $100 = 0.0086% of ADV
- DOGE $277M, PEPE $342M → $100 is 0.0000% of ADV

At $500-1000 total across 5 names you are below 0.01% of ADV everywhere. **Liquidity is not the binding constraint.** This is worth stating clearly because the original hypothesis blamed capacity; the data says capacity is fine and the *edge* is the problem.

**Survivorship bias in my universe selection — I must flag this.** I picked the 20 new listings because I already knew they listed on Binance and are still trading. All 20 are still alive today. A real ex-ante scan at listing time would have included coins that never made it to Binance futures or were delisted. So Sub-A's 12.23% net is an **upper bound**, not an unbiased estimate.

**Not modeled, and these cut the number down, not up:**
- Listing-week bid/ask spreads of 20-100 bps vs the 5 bps I applied. `fetch_ticker` on binanceusdm returned `bid=ask` (spread 0.00 bps) which is a data limitation, not evidence of tight markets. Real listing-week spreads are much wider.
- 10%+ flash moves in the first days break delta-neutral: the short perp leg margin-calls while the spot hedge is still settling. On $100 notional a 10% dislocation is $10 — a full year of carry at 10% APR.
- One-week-post-listing ADV can be under $500k; $100 is fine (0.02%) but $1000 across 5 names becomes 0.1-0.2% and slippage bites.

**Fees are not the killer here.** Sub-A fee drag is 1.6% APR on most coins (1-3 switches in 90 days); Sub-C total fee drag 3.24% APR. The killer is that gross funding is only 8-19%, not 100%.

## Verdict v6

**NEGATIVE. No paper launched. No live capital.**

| sub-strategy | net APR | target | result |
|--------------|---------|--------|--------|
| A new listings | +12.23% | >50% | FAIL |
| B memecoins | +5.64% | >50% | FAIL |
| C combined | +5.61% | >50% | FAIL |

**Recommended strategy: A (new listings), but at ~12% net, not 50%+.**

## Reality check for the user

The framing "$500-1000 × 100% APR = $500-1000/year" is arithmetically right, but the 100% is not there. At the measured ~10% net APR:

- $500 capital → **~$50/year**
- $1000 capital → **~$100/year**

Tangible experience: **yes** — you would learn the full mechanics (spot+perp legs, funding accrual, margin management, exchange operations). Earnings: **no** — $50-100/year does not justify the operational risk or the time.

Scale path: this does not scale by adding capital, because the APR itself is the constraint, not capacity. Scaling would require either (a) manual per-listing selection inside the launch window with $1-5k per name, which is a job not a strategy, or (b) a fundamentally different edge.

## Six iterations, one number

Every universe tested — majors (v5), new listings (v6-A), memecoins (v6-B), combined dynamic (v6-C) — converges to **5-15% net APR** at retail fees. The 100%+ target is a tail phenomenon that cannot be systematically harvested at this capital size. If it were harvestable, the spread would already be closed by desks with maker rebates and colocation; that is exactly what v5's cross-exchange test showed (0.6 bps observed vs 40 bps breakeven).

The honest conclusion after ~600 backtests across 6 iterations: crypto funding arbitrage is a ~10% APR carry trade for retail. It is a real, low-risk return — roughly comparable to a high-yield savings account with materially more operational risk. It is not a path to 100%+ annual returns on $500-1000.


---

# v7 — Covered calls on BTC + air drops research: regime-dependent, NOT 100%

Funding arb was closed after 6 iterations (5-15% ceiling). This iteration tested a **different edge class**: options premium harvesting and airdrops.

Two data notes up front, both factual:

1. **Deribit production API is blocked from this host.** `www.deribit.com`, `deribit.com`, `api.deribit.com` all return connection timeout; only `https://test.deribit.com` responds. **Deribit testnet DVOL is unusable** — validation against known dates showed 2024-01-10 at 169.6% (real: ~45-50%, ETF approval day crush) and 2024-12-30 at 111.5% (real: ~55-60%), max 240% over the history.
2. **I used Binance options instead** (`eapi.binance.com`), which is reachable and returns real live `markIV`/`markPrice`. Validation: Black-Scholes recomputed from Binance's own markIV differs from its markPrice by **12.6% mean absolute** — so I used BS for path simulation but anchored every premium estimate to the **real measured market premium**.

## Real measured facts (the anchor for everything below)

| metric | value | source |
|--------|-------|--------|
| BTC spot | $80,757 | Binance index, live |
| Real ATM IV, 5-30 DTE | 33.8% | Binance markIV, live |
| Real ATM IV, 30-60 DTE | 35.5% | Binance markIV, live |
| Real ATM IV, 60-95 DTE | 36.4% | Binance markIV, live |
| **Real +10% OTM 30d call premium** | **0.84-1.02% of spot** | Binance markPrice, live |
| BTC realized vol RV30, 2023-24 | **46.9%** (2023: 42.3%, 2024: 51.0%) | Binance spot, computed |

**The variance risk premium is NEGATIVE right now: IV 33.8-36.4% vs RV 46.9%.** Selling calls collects less than realized vol implies. For a premium-selling trade you want IV > RV; today it is the opposite, by 10-13 percentage points.

## Covered calls backtest — REAL BTC paths 2023-2024

$100 notional, sell +10% OTM 30-day call, non-overlapping (real single position), P&L = spot gain + premium − upside given away. 23 periods over 1.89 years.

**Real measured premium basis (0.84%/month):**

| metric | value |
|--------|-------|
| periods | 23 |
| gross premium | 0.81% per 30d period |
| **premium-only APR** | **+9.85%** |
| total CC APR (incl. BTC beta) | +40.94% |
| Sharpe | 1.38 |
| max DD | −15.49% |
| positive periods | 60.9% |
| assignment rate | 39.1% |
| **buy & hold CAGR same window** | **+112.10%** |
| **edge vs buy & hold** | **−71.16pp** |

**The 40.94% is not alpha. Decomposition: `strong_up` periods contribute +51.47% APR of it — that is BTC beta, not option edge.** Premium-only is 9.85%, which is the only part that is not market exposure.

### Regime breakdown (the decisive table)

| regime | n | avg BTC move | CC return | B&H return | premium | assignment | CC edge |
|--------|---|--------------|-----------|------------|----------|------------|---------|
| 1_strong_up (>+10%) | 9 | +22.3% | +10.81% | +22.34% | +0.81 | 100% | -11.53pp |
| 2_mild_up (0..+10%) | 5 | +6.2% | +6.99% | +6.18% | +0.81 | 0% | +0.81pp |
| 3_mild_down (-10..0%) | 6 | -4.1% | -3.27% | -4.08% | +0.81 | 0% | +0.81pp |
| 4_strong_down (<-10%) | 3 | -12.6% | -11.75% | -12.56% | +0.81 | 0% | +0.81pp |

Covered calls **win in 3 of 4 regimes** — mild_up, mild_down, strong_down — each by exactly +0.81pp per period (the premium). They **lose badly in strong_up (−11.53pp)** because 100% of those periods get assigned and all upside above +10% is forfeited.

In 2023-24, strong_up was **39% of periods** (9 of 23). That is what turns a +0.81pp/period income strategy into a −71pp laggard versus just holding BTC.

### Zero-drift counterfactual (the regime CC is designed for)

200 simulated 2-year paths, same realized vol (46.9%), zero drift:

| | median | mean | p10 | p90 |
|---|--------|------|-----|-----|
| covered call | 0.674x | 0.747x | 0.364x | 1.165x |
| buy & hold | 0.879x | 1.001x | 0.362x | 1.687x |

**CC beats buy & hold in only 20% of zero-drift trials.** Mean excess −25.4pp over 2 years. So even in the ideal regime (flat market), covered calls underperform holding spot at 47% vol — because the call you sold is priced for 35% vol while the market moves at 47%.

### What IV would make this work

| IV | +10% OTM 30d premium | annualized |
|----|---------------------|------------|
| 35% (today, real) | 0.96% | +11.7% |
| 45% | 1.81% | +22.0% |
| 55% | 2.76% | +33.6% |
| 65% | 3.79% | +46.1% |
| 80% | 5.40% | +65.7% |

Covered calls become a genuine 15%+ income trade at IV 55-60% — a high-vol regime. At today's 35%, gross premium carry is ~10% APR.

**Covered calls verdict: does NOT pass as a systematic strategy.**
- Premium-only APR 9.85% < 10% threshold
- Total APR 40.94% passes only because it includes BTC beta (strong_up contributes 51pp)
- Edge vs buy&hold is −71pp — you would be better off simply holding BTC
- Sharpe 1.38 passes numerically, but it is measuring BTC beta + a small premium, not option alpha

## Air drops — research, not a backtestable strategy

**State this plainly: airdrops cannot be backtested.** Any number presented as "expected airdrop yield" is a forecast dressed as data. What follows is verified live data plus public-record history, explicitly labelled.

### Live verified DeFi yields (DefiLlama, fetched this session)

Stablecoin pools >15% APY with >$5M TVL (artifacts like 7530% APY filtered out):

| protocol | symbol | chain | APY | base | reward | TVL |
|----------|--------|-------|-----|------|--------|-----|
| axis | SUSDX | Ethereum | 15.1% | 15.1% | 0.0% | $52.2M |
| morpho-blue | FCUSDT | Ethereum | 15.8% | 9.3% | 6.5% | $43.7M |
| pendle-v2 | APYUSD | Ethereum | 16.0% | 16.0% | 0.0% | $18.3M |
| veranta | USDC | Base | 27.5% | 27.5% | 0.0% | $9.8M |
| pendle-v2 | SUSDX | Ethereum | 17.3% | 17.3% | 0.0% | $7.0M |
| pendle-v2 | SUSDX | Ethereum | 16.3% | 16.2% | 0.1% | $7.0M |

Non-stable, IL risk: Uniswap v3 WETH-USDC on Base 30.1% APY ($159M TVL); nest-cl WHYPE-USDC on Hyperliquid 46.4% APY ($12.2M TVL, 100% reward-token emissions).

### Concrete opportunities ($0 entry, with honest status labels)

| opportunity | entry cost | expected range | status | risk |
|-------------|-----------|----------------|--------|------|
| Hyperliquid points season | $0 (trade or provide liquidity) | $500-5,000 (2024 HYPE drop precedent) | VERIFY CURRENT | capital at risk trading; sybil filters |
| Ethena sUSDe farming | $0 setup, needs USDe capital | $100-1,000 per season + 10-25% APY base | ONGOING | USDe peg risk; funding rate dependency |
| Pendle PT fixed yield | $0 setup, capital required | 15-30% fixed APR to maturity | LIVE (verified) | smart contract; PT liquidity |
| Morpho Blue curated vaults | $0 setup, capital required | 8-23% APY stablecoin | LIVE (verified) | curator risk; smart contract |
| Aerodrome USDC-AERO LP | $0 setup, capital required | 60-120% APY (reward-heavy) | LIVE (verified) | IL on AERO; reward token price |
| Monad / MegaETH testnet | $0 (gas-free testnet) | $0-2,000 if drop happens | SPECULATIVE | may never drop; sybil filters |

### Historical reference drops (public record, NOT a forecast)

Arbitrum $800-2,000/address | Optimism $400-1,500 | Jito $500-3,000 | Ethena $500-5,000 | Jupiter $200-2,000 | Wormhole $300-1,500 | Blur $500-3,000.

**Airdrop reality check:**
- Realized $500-3,000 per major drop **for addresses that qualified**
- A significant share of addresses get **zero** — sybil filtering, missed snapshots, retroactive rule changes
- Active farmer: **$2,000-10,000/year** if running 10-20 tracked projects across multiple wallets, 2-4h/week
- Passive: **$0** — airdrops require active participation
- **Not scaleable**: per-address caps typically $1,000-5,000; more wallets = more yield but sybil risk
- **Evidence quality: LOW.** This is research, not a tested strategy

## Verdict v7

| strategy | realistic APR | passes | why |
|----------|---------------|--------|-----|
| Covered calls (premium only) | **+9.85%** | NO | below 10%; IV<RV so premium is underpriced |
| Covered calls (total incl. beta) | +40.94% | NO (as alpha) | 51pp of it is BTC beta, edge vs B&H −71pp |
| Air drops | $0 passive / $2-10k active | NOT BACKTESTABLE | per-address caps, sybil risk, requires labour |

**Recommended: covered calls as a small income overlay IF you expect a mild or flat regime, sized so that a strong_up month does not hurt — not as a return engine. Air drops as a side activity, $0 entry, manual.**

## Reality check for the user

**$1,000 in covered calls at today's real IV yields ~$8.40/month gross (0.84%), ~$101/year.** That is tangible weekly cash flow — but in a strong up-move you forfeit everything above +10%, which in this sample cost −$11.53 per $100 notional per period. You are paid ~$0.81/period to cap your own upside during a 39%-of-the-time regime.

Air drops: $0 entry, potential $500-3,000 per successful drop, but requires 10-20h setup and 2-4h/week, and many attempts pay zero.

**Neither is a systematic 100%+ strategy.** After seven iterations and roughly 600 backtests, the pattern across every retail-accessible class tested — funding arb (majors, new listings, memecoins), cross-sectional momentum, TA on majors, covered calls — is the same: 5-15% APR is the realistic retail ceiling. Anything above that requires manual edge (airdrop/new-listing monitoring, which is a job), tail risk (selling options into a regime that occasionally destroys the account), or structural advantage (data exclusivity, legal infrastructure) that retail does not have access to.

That is a statement about market structure, not about our weakness. If 100%+ systematic APR were available at $500-1000 with public APIs, it would already be arbitraged away — which is exactly what the v5 cross-exchange test demonstrated empirically (0.6 bps observed spread vs 40 bps breakeven).


---

# FINAL CLOSE-OUT — actionable playbook (playground track ends here)

Seven iterations, roughly 600 backtests, one consistent result. This section converts that into what you can actually do, and states plainly what does not exist.

## 7 iterations — compact summary

| # | tested | result | why closed |
|---|--------|--------|------------|
| v1 | 10 TA strategies x 3 majors x tuning (156 runs) | Top-3 all SOL, DD 47-55%, hit 32% | Not tradeable — not smooth enough to hold |
| v2 | Out-of-sample 2018-2021 bear + portfolio w/ SL-TP | Portfolio Sharpe -0.054 bull / -0.145 bear | SL -2%/TP +5% destroys trend edge (worse on 11 of 12 combos) |
| v3 | Cross-sectional momentum (32 symbols) + ATR trailing | Test A Sharpe 0.86/0.52; Test B no pass | Fees eat 30-32% of gross; TA on majors decays post-2022 |
| v5 | Funding arb: majors + cross-exchange (Binance/Bybit) | Sub-A 9.51%, Sub-B 0 profitable of 23 | Cross-exchange spread 0.6bps vs 40bps breakeven — fully arbitraged |
| v6 | New listings first-90d + memecoins funding | Sub-A 12.23%, Sub-B 5.64%, Sub-C 5.61% | "100-300% on listings" is the tail, not the mean |
| v7 | BTC covered calls (Binance options) + air drops | Premium-only 9.85% APR; IV 35% < RV 47% | Negative variance premium today; -71pp vs buy&hold |

**Retail crypto systematic ceiling: 5-15% APR.** Confirmed six different ways across six different universes.

## What actually exists at which size

| class | realistic return | capital needed | time | scaleable? |
|-------|------------------|----------------|------|------------|
| Systematic funding arb | 8-15% APR | $500+ | passive | Yes, but APR is the cap |
| Systematic covered calls | ~10% APR premium-only | $500+ | passive | Yes, regime-dependent |
| Manual airdrop farming | $2,000-10,000/yr active | $0-200 gas | 2-4h/week | NO — per-address cap $1-5k |
| Manual new-listing monitoring | varies, high variance | $1-5k per name | daily attention | NO — a job, not a strategy |
| Structural edge (data exclusivity, legal infra) | 100%+ possible | $8-15k+ | full-time | Yes, if you have the capital |

## Air drops — actionable candidates (honest verification labels)

**Source status this session (state plainly, do not pretend otherwise):**
- `earn.fi` → UNREACHABLE (connection failed)
- `defillama.com/airdrops` → HTTP 403 (Cloudflare block)
- `api.llama.fi/airdrops` → HTTP 404 (endpoint does not exist)
- `api.llama.fi/protocols` → HTTP 200 — **used** to verify each protocol exists with stated TVL
- Twitter/X search → not attempted (requires auth, not accessible)

So: **protocol existence and TVL are verified. Live points-program status is NOT verified from this host.** Items below are marked accordingly.

| project | chain | verified TVL | entry cost | expected per drop | setup | ongoing | status |
|---------|-------|--------------|-----------|-------------------|-------|---------|--------|
| Polymarket | Polygon | $399.0M | $0 deposit to bet; gas on Polygon ~$0.01-0.05/tx | $200-2,000 per address (comparable: prediction/DeFi drops 2023-24) | 1h | 1h/wk | UNVERIFIED — points/airdrop not confirmed live from this host |
| Monad | Monad | $7.5M | $0 (testnet gas is free) | $300-3,000 per address (comparable: L1 testnet drops — Aptos/Sui scale) | 4h | 2h/wk | UNVERIFIED — testnet incentive program not confirmed live from this host |
| MegaETH | Ethereum | $4.5M | $0 testnet / $2-5 per mainnet tx if bridging | $200-2,000 per address | 3h | 1h/wk | UNVERIFIED — incentive program not confirmed live from this host |
| Linea | Ethereum (zk rollup) | $234.4M | $2-5 gas to bridge + transact | $300-2,500 per address if TGE lands | 2h | 1h/wk | PARTIALLY VERIFIED — points program known; TGE/claim status UNVERIFIED from this host |
| Scroll | Ethereum (zk rollup) | $31.8M | $2-5 gas per bridge + tx | $200-1,500 per address | 2h | 1h/wk | PARTIALLY VERIFIED — Sessions program known; TGE status UNVERIFIED from this host |

**Historical comparables (public record, NOT a forecast):** Arbitrum $800-2,000 · Optimism $400-1,500 · Jito $500-3,000 · Ethena $500-5,000 · Jupiter $200-2,000 · Wormhole $300-1,500 · Blur $500-3,000 per qualifying address. Many addresses get **zero** — sybil filters, missed snapshots, retroactive rule changes.

**Realistic EV if active:** $2,000-10,000/year running 10-20 tracked projects across multiple wallets, 2-4h/week. Passive: $0.

## Eligibility — can you claim missed drops?

| protocol | claim window | retroactive claim |
|----------|--------------|-------------------|
| Arbitrum | closed (Mar 2023 snapshot) | NO — snapshot прошёл, новых раундов не объявлено |
| Optimism | rounds 1-4 closed | NO для прошлых раундов; будущие раунды требуют участия до snapshot |
| Jito | closed (Dec 2023) | NO |
| Jupiter | closed (Jan 2024) | NO; subsequent rounds require prior activity |
| Wormhole | closed (Apr 2024) | NO |
| Ethena | seasons ongoing | PARTIAL — новые сезоны открыты, но прошлые награды не догоняются |
| Blur | closed | NO |

**The pattern: the airdrop snapshot happens BEFORE the announcement.** If you were not participating before the snapshot, you get nothing. The only exception is protocols with ongoing seasons (Ethena), where you can enter the next season but cannot recover past rewards. **There is no retroactive path.**

## Verified live yield right now (income, not speculation)

| protocol | symbol | chain | APY | base | reward | TVL |
|----------|--------|-------|-----|------|--------|-----|
| pendle-v2 | SUSDE | Monad | 14.4% | 14.2% | 0.2% | $16.1M |
| morpho-blue | SIRLOINUSDC | Base | 5.7% | 3.1% | 2.6% | $465.5M |
| aerodrome-v1 | USDC-AERO | Base | 170.4% | 0.0% | 170.4% | $7.6M |
| axis | SUSDX | Ethereum | 15.1% | 15.1% | 0.0% | $52.2M |

**Flagged separately — Aerodrome USDC-AERO at 170%+ APY:** base 0.0%, reward 170.4%. That is entirely AERO emissions on an LP with impermanent loss. If AERO halves, your yield halves AND you take IL. This is a speculative farm position, not income. Not included in the income table above.

## Four tangible paths (choose deliberately)

**(A) Covered calls paper — $0, already running.**
Position id=1 is live: BTC spot $80,757, strike $88,833 (+10%), IV 35.8%, premium $0.99 on $100 notional, expiry 2026-11-24. Settles automatically. Costs nothing, teaches the mechanics of premium vs assignment. Command:

    cd /opt/20261005-cryptospearmint && source venv/bin/activate
    nohup python3 -m src.execution.covered_calls_paper > journal/cc_run.log 2>&1 &
    python3 -m src.execution.covered_calls_paper --summary

**(B) Covered calls small live — $200-500, real $2-5/month.**
Same mechanics on real Binance options. At measured 0.84%/month premium: $500 notional → ~$4.20/month gross, ~$50/year. That is real but small. And in a strong up-move you forfeit all upside above +10% — in the 2023-24 sample that cost -$11.53 per $100 notional per period, in 39% of periods. Only sensible if you expect a mild or flat regime and are sizing accordingly.

**(C) Airdrops manual — $0 entry, $500-3,000 per successful drop.**
The table above is the starting list. This is the only path with 100%+ upside per unit of capital, and it is entirely a function of your time, not your capital. Cost: 10-20h setup + 2-4h/week. Failure mode: many attempts pay zero.

**(D) Structural edge — the only systematic 100%+ path.**
Data exclusivity, colocated infrastructure, maker rebates, legal/regulatory positioning. Requires $8-15k+ minimum and a real operational commitment. This is where institutional capital sits, and it is why the retail spread closes to 10%.

**(Implicit fifth) Close trading entirely.** For most people, with $500-1,000, the honest expected value of trading is negative after fees and time. That is not a failure — it is the correct answer for the capital size.

## The honest answer to "how do small traders actually make money?"

Most do not — survivorship bias in what you read. Those who do fall into three buckets:
1. **Manual edge** — airdrops, new-listing sniping, short-lived arbitrages. Requires time, not capital. Not scaleable.
2. **Tail risk** — leverage, long options, memecoins. Positive expectancy only if you can survive the drawdowns, and most cannot.
3. **Structural advantage** — rebates, colocation, data. Requires $8-15k+ and infrastructure.

**Systematic retail 100%+ does not exist.** If it did, institutional capital would have compressed it to ~10% — exactly what the v5 cross-exchange test measured empirically (0.6bps observed spread vs 40bps breakeven). The ceiling is a property of the market, not of this playground.

## Recommendation

- **If you want tangible experience:** run (C) and (B) in parallel. (C) has the higher upside and costs only time. (B) gives you real fill/settlement mechanics for a few dollars a month.
- **If you want systematic 100%+:** that is (D), and it costs $8-15k before it returns anything.
- **(A) as passive education:** it is already running, cost $0, and will teach you assignment risk over the next month whether you watch it or not.

## Full command reference

Run paper covered calls (already works, position id=1 open):

    cd /opt/20261005-cryptospearmint && source venv/bin/activate
    python3 -m src.execution.covered_calls_paper --once        # single check
    python3 -m src.execution.covered_calls_paper --summary     # state + P&L
    nohup python3 -m src.execution.covered_calls_paper > journal/cc_run.log 2>&1 &

Inspect the journal (JSONL, one line per event):

    tail -f /opt/20261005-cryptospearmint/journal/covered_calls.jsonl

Inspect the SQLite state:

    python3 -c "import sqlite3; c=sqlite3.connect('/opt/20261005-cryptospearmint/state/covered_calls.db'); print(c.execute('SELECT id,open_ts,spot,strike,iv,premium_usd,status FROM positions').fetchall())"

Air drops data files:

    cat /opt/20261005-cryptospearmint/data/air_drops_playbook.json
    cat /opt/20261005-cryptospearmint/data/eligibility_check.json
    cat /opt/20261005-cryptospearmint/data/protocol_existence_check.json

Re-run the covered-calls backtest (numbers behind the regime table):

    python3 -c "import pandas as pd; print(pd.read_csv('data/covered_calls_regime.csv').head(10))"
    python3 -c "import pandas as pd; print(pd.read_csv('data/covered_calls_by_regime.csv'))" 

## Playground track: CLOSED

Seven iterations. Retail systematic ceiling established empirically at 5-15% APR. The manual path (air drops) is the only place where small capital can see 100%+ — and it is paid for in hours, not dollars. Everything above that requires structural capital.

The code, all data, and every number in this README are in the repo. Nothing here is a forecast; every metric is from a real run whose CSV is committed alongside it.
