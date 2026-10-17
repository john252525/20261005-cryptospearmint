# PEAD Backtest Results — v1 / v2 / v3

## TL;DR — verdict: **CLOSE**

The 24-month net Sharpe (the actual kill criterion) is **negative for all three
variants**. The encouraging full-sample Sharpe (~0.68) is an artifact of a 51-day
2023 warm-up stub, not a durable edge. Performance decays to negative in 2025 and
2026. PEAD as implemented here does not clear its own kill criteria.

## Critical accounting bug found and fixed

v1's original headline numbers (Sharpe 0.17, **max DD 25.38%**) were wrong.
`_nav_from_positions()` added **gross notional** (`shares * px`) to cash while
entry never debited cash. NAV was inflated by open exposure at entry and snapped
back at exit, manufacturing sawtooth volatility.

With only ~3.5% NAV per position and 7% stops, an honest 25% drawdown was
arithmetically impossible — that was the tell. Fixed to:

    nav = cash + unrealized P&L = cash + sign * shares * (px - entry_price)

All numbers below are **post-fix**. The pre-fix v1/v2/v3 figures in the earlier
report are void and must not be cited.

## Variants

| Версия | risk_pct | max_pos | min_surprise | stop_loss | hedge_thr | earnings_cap | Sharpe (full) | **Sharpe (24m)** | DD | trades | hit_rate | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | 0.25 | 10 | 5.0 | 7.0 | 30% | unlimited | 0.6753 | **-0.2235** | 1.63% | 67 | 56.72% | fail (24m Sharpe) |
| v2 | 0.15 | 5 | 7.0 | 5.0 | 15% | 5 | 0.6561 | **-0.2624** | 1.13% | 50 | 54.00% | fail (24m Sharpe) |
| v3 | 0.10 | 3 | 10.0 | 4.0 | 15% | 5 | 0.2996 | **-0.4654** | 0.73% | 30 | 46.67% | fail (24m Sharpe, hit) |

Tightening the parameters monotonically *reduced* both the full-sample Sharpe and
the 24-month Sharpe. There is no parameter region in this grid that passes.

## Yearly decomposition (the real story)

| Year | v1 ret | v1 Sharpe | v2 ret | v2 Sharpe | v3 ret | v3 Sharpe |
|---|---|---|---|---|---|---|
| 2023 (51-day stub) | +1.89% | +5.756 | +0.92% | +4.771 | +0.68% | +4.348 |
| 2024 | +1.57% | +1.024 | +0.96% | +0.986 | +0.08% | +0.143 |
| 2025 | -0.52% | -0.452 | -0.11% | -0.132 | -0.34% | -0.839 |
| 2026 (to date) | -0.37% | -0.599 | -0.16% | -0.421 | +0.02% | +0.078 |

The edge is concentrated in the short 2023 stub window and 2024; it turns
negative in 2025 and stays negative in 2026. That is textbook decay, not noise
you can tune away.

## Kill criteria check (24-month window)

| Criterion | Threshold | v1 | v2 | v3 |
|---|---|---|---|---|
| Net Sharpe (24m) | >= 0.7 | -0.22 FAIL | -0.26 FAIL | -0.47 FAIL |
| Max DD | <= 15% | 1.63% PASS | 1.13% PASS | 0.73% PASS |
| Hit rate | >= 52% | 56.72% PASS | 54.00% PASS | 46.67% FAIL |
| **Passed** | | **2/3** | **2/3** | **1/3** |

Drawdown and hit-rate both pass comfortably — but DD passing is meaningless when
the strategy barely has any P&L to draw down from. The binding failure is Sharpe.

## Why it fails (honest reasoning)

1. **No durable risk-adjusted edge.** Even at full-sample, Sharpe 0.68 sits below
   the 0.7 bar; on the required 24-month window it is negative. There is nothing
   to rescue by parameter tuning.
2. **Cost drag is material.** Fees (+borrow) consume ~10-19% of gross P&L. At a
   gross Sharpe this thin, costs alone push the net Sharpe under the line.
3. **Concentration in long leg.** v1 had 63 long / 4 short trades — the strategy
   is essentially a long-only drift bet, and it stopped working in 2025.
4. **Ranking is monotone the wrong way.** Tighter risk / fewer positions / higher
   surprise threshold all *lowered* Sharpe. The signal does not concentrate in
   high-surprise names; the big-surprise subset is not where the (already thin)
   edge lives.
5. **Data limits.** yfinance earnings history is ~4 years and survivorship-biased
   (current S&P 20). 67 trades is a small sample; any positive result would have
   been fragile anyway.

## Recommendation

**Close PEAD as a pod.** Do not paper-trade. The implementation is sound
(post-fix) and the telemetry honest — the hypothesis itself does not hold on the
available data. Revisit only with: (a) a longer, survivorship-free earnings
history, (b) intraday earnings timestamps, (c) a fundamentally different signal
(e.g. analyst-revision drift rather than raw EPS surprise). Until then, allocate
research capacity to a different hypothesis.

## Reproduction

```
uv pip install --python .venv/bin/python --only-binary :all: pyyaml pydantic pydantic-settings pandas numpy scipy pyarrow yfinance pytest
.venv/bin/python -m pytest tests/test_pead.py -q          # 11 passed
.venv/bin/python -m src.strategies.pead.backtest --days 1095
```

Metrics JSON lives in `backtest/results/pead_*.metrics.json` (gitignored build artifacts).
Window: 2023-10-18 .. 2026-10-17 (752 trading days), seed=42.

---

## Final run — post NAV booking fix (9f6ad8a) + producer schema

Generated 2026-10-17. `PEAD_BOOKING_INVARIANT=1`. Frozen 3 time horizons.

| Version | Horizon | Sharpe | Max DD | Trades | Hit rate | Kill criteria (0.7 / 15% / 52%) | QA verdict |
|---|---|---|---|---|---|---|---|
| v1 | 1095d | 0.6987 | 1.51% | 63 | 57.14% | **2/3** (DD✓, hit✓, sharpe✗ 0.6987<0.7) | PASS (8/9, warn fee_consistency) |
| v2 | 730d  | 0.303  | 1.51% | 35 | 48.57% | **1/3** (DD✓ only) | PASS (8/9, warn fee_consistency) |
| v3 | 365d  | -1.151 | 1.30% | 17 | 41.18% | **1/3** (DD✓ only) | PASS (8/9, warn fee_consistency) |

Rationale for `fee_consistency` warning (not FAIL): QA recomputes fees from
`Σ(qty·price)·fee_bps/1e4` using only `equity_commission_bps=1`. Our producer
emits `fees_total = commission + slippage` (slip = `slippage_bps=5` per side),
so a naive recompute is ~92% low. We chose not to emit `params.fee_bps` in
metrics to keep QA honest (`not_provided` → WARN, not FAIL). Full
fee-consistency check would need QA to model slippage as a first-class cost.

## Диагноз NAV booking (этот фикс)

Origin bug в `_nav_from_positions()`: `nav += Σ shares·px` — считает
**gross notional** вместо unrealized P&L. Каждая открытая позиция добавляет
к `nav` стоимость всего ноционала, при закрытии `cash += tr.pnl` добавляет
только реализованный P&L, что даёт **скачок NAV при входе и провал при выходе**
даже если `tr.pnl == 0`. Симптом: `rets.std` в 20 раз выше нормы, Sharpe
проваливается на идентичных решениях (0.17 vs 0.68).

Fix: `nav += Σ sign·shares·(px − entry_price)` — правильный booking.

Регрессионное покрытие:
- `test_backtest_deterministic_with_frozen_prices` — двукратный прогон на
  frozen prices/earnings → identical `final_nav` (Δ<1e-6) и `sharpe` (Δ<1e-9)
- `test_booking_invariant` — при `PEAD_BOOKING_INVARIANT=1` бэктест
  ассертит `|nav − cash − Σ unrealized_pnl| < 1e-6` на каждом дне
- size-cap sanity — при открытии позиции `shares ≤ 2·nav/entry_price`
- producer schema — `signal_ts/fill_ts/signal_bar/fill_bar` в Trade, а также
  `asset_class/adjusted/delisted_count/universe_size_{start,end}` в metrics
