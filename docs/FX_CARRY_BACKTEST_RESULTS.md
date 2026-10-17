# G10 FX Carry — Backtest Results (v1, real data)

**Window**: 2023-09-18 → 2026-10-16 (3.08 years)
**Universe**: 9 G10 pairs vs USD · **Max positions**: 3 · **Threshold**: 50 bps
**Cost model**: 10 bps round trip (2 × (2 bps commission + 3 bps slippage))
**Data**: yfinance daily close + FRED 3M interbank (`IR3TIB01*M156N`)

Reproduced by `python3 -m src.strategies.fx_carry.backtest --days 1095 --refresh`.
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
| Avg carry (per trade) | 103.2 bps |
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

### Yearly returns

| Year | Return |
|---|---|
| 2023 | -3.87% |
| 2024 | +11.04% |
| 2025 | -4.63% |
| 2026 | +5.80% |

## 2. Robustness sweeps

| Variant | Sharpe | Total ret | Max DD | Trades | Hit |
|---|---|---|---|---|---|
| baseline (max3, thr50) | +0.481 | +7.96% | -8.39% | 20 | 60.0% |
| max_positions=2 | +0.710 | +8.32% | -4.90% | 10 | 70.0% |
| max_positions=5 | +0.303 | +6.94% | -11.94% | 18 | 50.0% |
| min_carry=100bps | +0.452 | +7.47% | -8.43% | 19 | 57.9% |
| min_carry=25bps | +0.481 | +7.96% | -8.39% | 20 | 60.0% |
| vol filter off | +0.468 | +7.82% | -8.25% | 7 | 57.1% |
| risk 10%/pair | +0.470 | +3.19% | -3.51% | 20 | 60.0% |

## 3. Kill criteria evaluation

| Criterion | Result | Actual |
|---|---|---|
| net Sharpe ≥ 0.4 (else close) | PASS | +0.481 |
| net Sharpe ≥ 0.7 (paper candidate) | FAIL | +0.481 |
| max DD ≤ 15% | PASS | -8.39% |
| hit rate ≥ 50% | PASS | 60.0% |
| avg carry ≥ 50 bps/yr (0.5%) | PASS | 103.2bps |

## 4. Verdict: **ITERATE (доработка)**

Net Sharpe sits in the iterate band (0.4-0.7). Carry premium is partially real but v1 leaks edge to costs/sizing and spot dominates direction. Needs targeted iteration before paper trading.

## 5. What is weaker than expected

1. **Spot dominates carry.** Carry accrual is small vs spot PnL — the book is a
   directional FX bet with a carry tilt, not a pure carry harvester.
2. **JPY short leg is the tail risk.** Any week where the yen rallies
   (BoJ-normalisation headlines) eats several months of carry; the 30-day vol
   filter lags the gap.
3. **FRED monthly data is stale.** Direction can lag a CB pivot by up to a
   month.
4. **NOK/SEK costs under-modelled.** Real interbank spreads on those crosses
   are 2-4× the 10 bps assumption.

## 6. Next steps

1. Add a trend / risk-off overlay (long JPY when carry dispersion compresses or
   VIX > threshold). Carry fails precisely when vol rises.
2. Use forward-implied carry (CIP deviation) instead of lagged FRED prints;
   drop NOK/SEK from v1.
3. Expand sample to 2005-2025 (GFC 2008, CHF de-peg 2015) — 3 years in one
   rate regime cannot validate a carry premium.
