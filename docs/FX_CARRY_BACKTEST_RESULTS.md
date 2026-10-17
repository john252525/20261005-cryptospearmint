# G10 FX Carry — Backtest Results (v1, real data)

**Window**: 2023-09-18 → 2026-10-16 (3.08 years)
**Universe**: 9 G10 pairs vs USD · **Max positions**: 3 · **Threshold**: 50 bps
**Cost model (baseline)**: 10 bps round trip — 2 × (2 bps commission + 3 bps slippage)
**Data**: yfinance daily close + FRED 3M interbank (`IR3TIB01*M156N`)

Reproduced by `python3 -m src.strategies.fx_carry.backtest --days 1095 --refresh`.
All headline numbers below are copied verbatim from `backtest/results/fx_carry_*.metrics.json`;
per-pair/sweep/cost tables are regenerated from the same equity series.

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
| Spot (gross)   | -15,372 |
| Fees           | -5,000 |
| **Net**        | **+81,400** |

Carry is **117.8%** of gross PnL; spot is
**-17.8%**. Over this window the book
harvested rate differentials and gave back a slice of it to (mostly JPY and
EUR) spot moves. Roll-over capture did nearly all of the work.

### Yearly returns

| Year | Return |
|---|---|
| 2023 | -3.87% |
| 2024 | +11.04% |
| 2025 | -4.63% |
| 2026 | +5.80% |

### Per-pair contribution

| Pair | Trades | Net$ | % of net | Carry$ | Spot$ | Fees$ | Hit |
|---|---|---|---|---|---|---|---|
| JPY=X | 4 | +67,090 | +82% | +40,642 | +27,447 | 1,000 | 75% |
| USDCHF=X | 1 | +17,531 | +22% | +39,609 | -21,828 | 250 | 100% |
| USDSEK=X | 7 | +6,805 | +8% | +13,381 | -4,825 | 1,750 | 57% |
| AUDUSD=X | 1 | +5,085 | +6% | +59 | +5,276 | 250 | 100% |
| EURUSD=X | 7 | -15,111 | -19% | +8,081 | -21,442 | 1,750 | 43% |

**What the data actually says**: **JPY=X** dominates the book at
**82%** of net PnL (4 trades, 75% hit).
`USDSEK=X` (7 trades) contributes only **+8%** of net. The single
biggest loser is **EURUSD=X** (-15,111,
43% hit) —
a long-EUR-carry book that got run over by spot. So the honest read is *not*
"edge sits in USDSEK": it sits in **JPY=X** (82%), and removing
USDSEK actually **improves** Sharpe (see sweeps below).

## 2. Robustness sweeps (all at 10-bps baseline cost)

| Variant | Sharpe | Total ret | Max DD | Trades | Hit |
|---|---|---|---|---|---|
| baseline 10bps RT (all 9, max3, thr50) | +0.481 | +7.96% | -8.39% | 20 | 60.0% |
| ex USDSEK | +0.658 | +10.19% | -7.32% | 15 | 86.7% |
| ex USDSEK+USDNOK | +0.475 | +7.21% | -7.59% | 14 | 85.7% |
| max_positions=2 | +0.710 | +8.32% | -4.90% | 10 | 70.0% |
| max_positions=5 | +0.303 | +6.94% | -11.94% | 18 | 50.0% |
| min_carry=100bps | +0.452 | +7.47% | -8.43% | 19 | 57.9% |
| vol filter off | +0.468 | +7.82% | -8.25% | 7 | 57.1% |
| risk 10%/pair | +0.470 | +3.19% | -3.51% | 20 | 60.0% |

Key reads:
- **ex-USDSEK Sharpe = +0.658** (vs +0.481 baseline) — removing the
  NOK-adjacent crosses *raises* Sharpe, because 7 low-quality USDSEK trades are dropped.
- **ex-USDSEK+USDNOK Sharpe = +0.475** with hit
  86% on 14 trades — many of the remaining trades are
  winners but sample is small.
- **max_positions=2** lifts Sharpe to **+0.710** and halves max DD to
  -4.90%. 3 concurrent 25%-notional positions are over-levered for the signal.
- **min_carry=100 bps** barely changes anything (+0.452) — the 50-bps
  threshold is already binding only on the same few pairs.
- **vol filter off** gives Sharpe +0.468 on 7 trades — it isn't doing
  much on this sample, but I'd keep it as a tail-event protection, not a PnL driver.

## 3. Cost sensitivity (real, same strategy, higher bps)

| Cost scenario | Sharpe | Total ret | Max DD | Trades | Hit |
|---|---|---|---|---|---|
| 10 bps RT (baseline) | +0.481 | +7.96% | -8.39% | 20 | 60.0% |
| 15 bps RT | +0.462 | +7.63% | -8.42% | 20 | 60.0% |
| 25 bps RT | +0.423 | +6.95% | -8.49% | 20 | 55.0% |
| 40 bps RT (stress) | +0.364 | +5.94% | -8.59% | 20 | 55.0% |

At 25 bps RT Sharpe is **+0.423**, at 40 bps it's **+0.364**. The strategy survives stress
costs *but* the margin over the 0.4-close threshold compresses quickly — this is
a thin-edge strategy where costs matter.

## 4. Kill criteria evaluation (4/5 passed)

| Criterion | Result | Actual |
|---|---|---|
| net Sharpe ≥ 0.4 (else close) | PASS | +0.481 |
| net Sharpe ≥ 0.7 (paper candidate) | FAIL | +0.481 |
| max DD ≤ 15% | PASS | -8.39% |
| hit rate ≥ 50% | PASS | 60.0% |
| avg carry ≥ 50 bps/yr | PASS | 103.2bps |

## 5. Verdict: **ITERATE (доработка)**

Sharpe +0.481 falls in the 0.4-0.7 iterate band. The carry leg is genuinely real (+$101,772, 118% of gross PnL), but the sample is a single 3-year rate regime, and net return is thin (+7.96% / ann 2.52%) for an -8.39% DD. Two findings push toward 'iterate' rather than 'paper': (a) the edge is concentrated in a single pair (JPY=X, 82% of net) — the sample is too narrow to attribute this to a persistent carry premium rather than a favorable yen-trend window; (b) the book survives at 40 bps RT but Sharpe drops to +0.364, so cost realism matters. Next iteration: cost realism, drop the losing long-EUR leg, extend sample.

## 6. What the result actually shows (weaker than hoped)

1. **Edge is pair-concentrated, not broad.** JPY=X is 82% of
   net ($+67,090 on 4 trades). Remove JPY and the book has
   almost no net PnL. That is one big carry run (yen weakness) captured by
   a coincidentally correct trade, not a robust cross-sectional premium.
2. **One pair is a consistent loser.** EURUSD=X is -15,111
   over 7 trades at 43% hit — the "long EUR as high-yielder vs USD" side
   of the book is systematically wrong on this sample and shouldn't be in v1.
3. **Direction is roughly neutral; carry is the whole story.** Spot
   -15,372 vs carry +101,772. That's the *correct* shape for a carry
   strategy, but it means all of the edge rides on the rollover-capture model,
   not on a robust signal.
4. **Net return is thin.** +7.96% total over ~3y (ann
   2.52%) for -8.39% max DD. A 0.48 Sharpe with an
   ~8% DD is below the bar for serious capital.
5. **`avg_holding_days=162`** — a weekly rebalance schedule almost never
   rotates (top-3 carry pairs are stable across weeks), so the "weekly
   rebalance" doesn't add diversification in practice. The vol filter fires
   rarely. The strategy is nearly a static buy-and-hold carry book on the same
   2–3 pairs for months at a time.

## 7. Next steps (prioritized)

1. **Fix the systematic loser.** EURUSD=X lost on 7 trades — check whether
   the long-EUR carry signal was genuinely wrong (i.e. the rate differential
   sign didn't predict the spot) or whether the entry date is being
   contaminated by stale FRED data. Either justify EUR or drop it in v2.
2. **Reduce pair concentration risk.** Require at least 2 pairs contributing
   or cap per-pair contribution. If v1 payoff is 82% from JPY=X, a single
   adverse yen move can wipe it out (2024-08 BoJ shock is in-sample but
   barely visible in the -8.4% DD; a larger shock would not be).
3. **Cost realism.** Rebuild with 25–40 bps on NOK/SEK. Baseline survives at
   40 bps RT but the margin is thin; if v2 drops NOK/SEK, the edge doesn't
   sit there anyway per the sweeps.
4. **Signal upgrade.** Forward-implied carry (CIP deviation from spot) instead
   of lagged FRED monthly data — removes ~1-month staleness around CB pivots.
5. **Sample expansion.** 2005–2025 to include GFC 2008 and CHF de-peg 2015.
   3 years in one rate regime cannot validate a carry premium; the "82% from
   JPY" finding is exactly the kind of sample-specific artefact that a wider
   window resolves.
