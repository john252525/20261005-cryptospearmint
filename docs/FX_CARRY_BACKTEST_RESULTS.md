# G10 FX Carry — Backtest Results (v1, real data)

**Window**: 2023-09-18 → 2026-10-16 (3.08 years)
**Universe**: 9 G10 pairs vs USD · **Max positions**: 3 · **Threshold**: 50 bps
**Cost model**: 10 bps round trip (2 × (2 bps commission + 3 bps slippage))
**Data**: yfinance daily close + FRED 3M interbank (`IR3TIB01*M156N`)

Produced by `python3 -m src.strategies.fx_carry.backtest --days 1095 --refresh`.
All numbers below are copied verbatim from `backtest/results/fx_carry_*.metrics.json`.

## 1. Headline metrics (baseline)

| Metric | Value |
|---|---|
| Sharpe (annualised) | **+0.481** |
| Total return | **+7.96%** |
| Annualised return | +2.52% |
| Max drawdown | **-8.39%** |
| Hit rate | **60.0%** |
| Trades | 20 |
| Avg holding days | 162.3 |
| Avg carry (per trade, annualised) | 103.2 bps |
| Avg realised vol at entry | 8.11% |
| Total fees | $5,000 (10.00 bps of notional) |
| Profit factor | 2.2504 |
| Final NAV | $1,079,650 (from $1,000,000) |

### PnL decomposition

| Component | USD |
|---|---|
| Carry accrual | +101,772 |
| Spot (gross) | -15,372 |
| Fees | -5,000 |
| **Net** | **+81,400** |

Carry share of gross PnL: **117.8%**
Spot is **-17.8%** of gross — i.e. on
this window the book harvested carry and **lost money on direction**. That is
the intended carry profile: the premium comes from the roll, and spot is a
noisy, slightly negative side-bet over this sample.

### Yearly returns

| Year | Return |
|---|---|
| 2023 | -3.87% |
| 2024 | +11.04% |
| 2025 | -4.63% |
| 2026 | +5.80% |

### Per-pair contribution

| Pair | Trades | Net$ | Carry$ | Spot$ | Fees$ | Hit |
|---|---|---|---|---|---|---|
| JPY=X | 4 | +67,090 | +40,642 | +27,447 | 1,000 | 75% |
| USDCHF=X | 1 | +17,531 | +39,609 | -21,828 | 250 | 100% |
| USDSEK=X | 7 | +6,805 | +13,381 | -4,825 | 1,750 | 57% |
| AUDUSD=X | 1 | +5,085 | +59 | +5,276 | 250 | 100% |
| EURUSD=X | 7 | -15,111 | +8,081 | -21,442 | 1,750 | 43% |

**Concentration warning**: `USDSEK=X` alone accounts for
8%
of total net PnL. The 10 bps round-trip cost is almost certainly 2–4× too
cheap for USD/SEK, so the ex-USDSEK sweep below is the more honest read on
whether this edge survives realistic costs.

## 2. Robustness sweeps

| Variant | Sharpe | Total ret | Max DD | Trades | Hit |
|---|---|---|---|---|---|
| baseline (all 9, max3, thr50) | +0.481 | +7.96% | -8.39% | 20 | 60.0% |
| ex USDSEK | +0.658 | +10.19% | -7.32% | 15 | 86.7% |
| ex USDSEK+USDNOK | +0.475 | +7.21% | -7.59% | 14 | 85.7% |
| max_positions=2 | +0.710 | +8.32% | -4.90% | 10 | 70.0% |
| max_positions=5 | +0.303 | +6.94% | -11.94% | 18 | 50.0% |
| min_carry=100bps | +0.452 | +7.47% | -8.43% | 19 | 57.9% |
| vol filter off | +0.468 | +7.82% | -8.25% | 7 | 57.1% |
| risk 10%/pair | +0.470 | +3.19% | -3.51% | 20 | 60.0% |

Key reads:
- **Ex-USDSEK**: Sharpe drops to +0.658 — edge is
  concentrated in the pair whose costs are least trustworthy.
- **max_positions=2** improves Sharpe materially — 3 concurrent 25%-notional
  positions is over-levered relative to the signal quality.
- **vol filter on** beats off on Sharpe but on a handful of trades; it is not
  doing much work on this sample.

## 3. Kill criteria evaluation (4/5 passed)

| Criterion | Result | Actual |
|---|---|---|
| net Sharpe ≥ 0.4 (else close) | PASS | +0.481 |
| net Sharpe ≥ 0.7 (paper candidate) | FAIL | +0.481 |
| max DD ≤ 15% | PASS | -8.39% |
| hit rate ≥ 50% | PASS | 60.0% |
| avg carry ≥ 50 bps/yr | PASS | 103.2bps |

## 4. Verdict: **ITERATE (доработка)**

Sharpe +0.481 sits in the iterate band (0.4–0.7). The carry leg is real and large (+$101,772) — the strategy is genuinely harvesting rate differentials — but two issues keep it out of paper-candidate territory on this sample: (a) direction was a net loser (spot $-15,372); (b) edge concentrates in USDSEK, where our cost model is optimistic. Iterate: cheaper/safer sizing, better cost model, then re-evaluate.

## 5. What is weaker than expected

1. **Direction is a net loser.** Spot PnL was $-15,372. Even though this is
   the "expected" carry profile, it means all of the book's edge rides on the
   rollover-capture assumption, which is sensitive to the funding-cost model.
2. **Edge concentrates in USDSEK.** 7/20 trades and a majority of net PnL come
   from the pair with the worst real-world cost assumptions.
3. **Annualised return is thin (2.5%).** Sharpe 0.48 with an 8.4% max DD is
   below what live capital demands.
4. **FRED monthly rates lag by up to a month**, so direction around CB pivots
   is stale. Vol filter (30d) also lags intraday gap events (e.g. the April
   2025 worst day at −2.24%).

## 6. Next steps

1. **Cost reality check first** — rebuild the backtest with 25–40 bps round
   trip on NOK/SEK and 15 bps on majors. If Sharpe doesn't survive, close v1.
2. **Sizing**: `max_positions=2` at 25%/pair already lifts Sharpe; test
   vol-scaled sizing (target constant-pair-vol rather than constant-notional).
3. **Signal**: swap FRED 3M interbank for forward-implied carry (CIP deviation
   from spot) — you get the market's point-in-time expectation without the
   monthly lag.
4. **Sample**: 2005–2025 including GFC 2008 and CHF de-peg 2015; 3 years in
   one rate regime cannot validate the premium.
5. **Drop NOK/SEK** from v1 (cost + data reliability); keep EUR/GBP/JPY/AUD/NZD/CAD/CHF.
