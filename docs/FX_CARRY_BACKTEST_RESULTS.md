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


---

# v2 — publication-lag fix, 20-летняя выборка, per-pair cap. **Гипотеза закрыта.**

**Окно**: 2006-09-22 → 2026-10-16 (20.07 лет; ограничено историей yfinance по FX,
запрос 7300 дней ≈ 20 лет). Числа — из `backtest/results/fx_carry_*.{metrics,trades}.parquet`
(прогон `--days 7300 --refresh`) и из sweep-прогонов ниже.

## v2.1 Что исправлено

| # | Изменение | Зачем |
|---|---|---|
| 1 | `rate_publication_lag_days = 45` | **look-ahead bias**: FRED `IR3TIB01*M156N` индексирован началом месяца M, а публикуется к середине M+1; v1 читал месяц M на датах внутри M |
| 2 | `max_pair_concentration_pct = 40` от текущего NAV | per-pair cap: `min(notional_target, cap)` в открытии позиции |
| 3 | окно 1095 → 7300 дней | GFC 2008, Euro crisis 2011-12, yen unwind 2024 |
| 4 | экспорт `*.trades.parquet` | аудит сделок (per-pair, carry vs spot, hit) |

## v2.2 «EURUSD anomaly» — что было на самом деле

Маппинг **корректен**: `EURUSD=X → (EUR, USD)`, `carry = rate(EUR) − rate(USD)`, знак
положительный → long. Инверсии нет; все 7 v1-сделок — логичные **short EURUSD**
(carry −144…−207 bps), USD действительно доходнее EUR весь период.

**Убыток EURUSD — это реальный убыток сигнала, а не артефакт данных.** Прямой
прогон на точном v1-окне с одинаковыми прочими настройками:

| Настройки | EURUSD net | EURUSD carry | EURUSD spot |
|---|---|---|---|
| lag=0 (v1)   | **−15,111** | +8,081 | −21,442 |
| lag=45 (v2)  | **−12,486** | +8,241 | −18,977 |

Устранение look-ahead улучшает EURUSD лишь на **+2,625** (17% убытка) и **не меняет
вывод**: даже с корректным лагом 5 из 7 сделок — short EURUSD, и на четырёх из них
спот пошёл против шорта (EUR ралли 2025: −8,225, −8,161, −10,500). Carry-компонента
положительна (+8,241), но спот съедает её втрое.

То есть «аномалия» — не ошибка маппинга и не look-ahead, а **честная отрицательная
альфа инструмента**: сигнал правильно определяет, что USD доходнее EUR, но
европейская валюта в этом окне укреплялась, и шорт systematically терял на споте.
На 20-летней выборке EURUSD выходит в +4.4% net (+9,998) — то есть 3-летнее окно
попало в специфический эпизод, а не выявило баг.

**Стоимость look-ahead (весь портфель, не только EURUSD)**: **−0.021 Sharpe** на
точном v1-окне (0.4811 → 0.4598), **−0.092** на 20-летней выборке (0.258 → 0.165).
На смещённом на месяц sweep-окне лаг, наоборот, слегка повышает Sharpe (+0.024) —
эффект лага сам по себе порядка ±0.02 и не объясняет перехода от 0.48 к 0.17.
См. таблицу разложения в §v2.3.

## v2.3 3 года vs 20 лет (10 bps RT)

| Вариант | Sharpe | Total ret | Max DD | Trades | Hit |
|---|---|---|---|---|---|
| 3y, no lag (v1 behaviour) | +0.617 | +10.03% | -8.35% | 19 | 63.2% |
| 3y, lag=45 (v2 fix) | +0.641 | +10.44% | -8.72% | 20 | 55.0% |
| 20y, no lag | +0.258 | +38.02% | -26.19% | 93 | 54.8% |
| 20y, lag=45 (v2 full) | +0.165 | +21.83% | -30.76% | 96 | 51.0% |

**Разложение 3-летнего результата по контролируемым изменениям** (точное v1-окно
2023-09-18 → 2026-10-16, 800 баров, прямой прогон):

| Что меняется | Sharpe | Δ |
|---|---|---|
| точное v1-окно, lag=0, cap=999 (эмуляция v1) | +0.4811 | — |
| точное v1-окно, lag=45, cap=999 | +0.4598 | **−0.0213** (цена устранения look-ahead) |
| точное v1-окно, lag=0, cap=40 | +0.4811 | **±0.0000** (cap на этом окне не влияет) |
| sweep-окно (старт 2023-10-17), lag=0 | +0.617 | **+0.136** от сдвига старта на месяц |

Отсюда: v1-числа **частично** завышены look-ahead (**−0.021 Sharpe** при корректном
лаге), а весь остальной разрыв 0.4811 → 0.617 — это **чувствительность к границе
окна** (сдвиг старта на один месяц). Per-pair cap 40% на этом окне не срабатывает
(notional не упирается в cap при стартовом NAV). Ни один из этих эффектов не
объясняет перехода к 20-летней выборке: там Sharpe **+0.165**, и это и есть
честная репрезентативная цифра.

## v2.4 Headline v2 (20 лет, 10 bps RT)

| Метрика | Значение |
|---|---|
| Sharpe | **+0.165** |
| Total return | +21.83% |
| Annualised | +0.99% |
| Max DD | **-30.76%** (worst 2009-03-02) |
| Worst day | -4.06% (2008-10-06) |
| Hit rate | 51.0% |
| Trades | 96 |
| Avg holding days | 222.0 |
| Avg carry (per trade) | 82.1 bps |
| Profit factor | 1.4578 |
| Final NAV | $1,218,287 |

### Годы

| Год | Return |
|---|---|
| 2006 | -0.53% |
| 2007 | -2.57% |
| 2008 | -21.71% |
| 2009 | +26.29% |
| 2010 | +9.33% |
| 2011 | +2.51% |
| 2012 | +6.76% |
| 2013 | -4.16% |
| 2014 | -5.41% |
| 2015 | -3.54% |
| 2016 | +3.80% |
| 2017 | -4.27% |
| 2018 | +5.43% |
| 2019 | +3.37% |
| 2020 | -2.49% |
| 2021 | +1.36% |
| 2022 | +3.90% |
| 2023 | -0.12% |
| 2024 | +9.30% |
| 2025 | -4.85% |
| 2026 | +4.38% |

## v2.5 Per-pair (20 лет)

| Pair | Trades | Net$ | % of net | Carry$ | Spot$ | Hit |
|---|---|---|---|---|---|---|
| AUDUSD=X | 6 | +110,098 | +48.0% | +89,110 | +22,488 | 67% |
| NZDUSD=X | 14 | +92,236 | +40.2% | +120,076 | -24,340 | 50% |
| JPY=X | 10 | +83,195 | +36.2% | +69,430 | +16,264 | 90% |
| USDSEK=X | 22 | +47,931 | +20.9% | +47,436 | +5,995 | 50% |
| EURUSD=X | 13 | +9,998 | +4.4% | +34,318 | -21,070 | 38% |
| USDCHF=X | 4 | +184 | +0.1% | +57,811 | -56,627 | 75% |
| USDCAD=X | 8 | -7,192 | -3.1% | +716 | -5,909 | 25% |
| GBPUSD=X | 4 | -36,053 | -15.7% | +2,800 | -37,853 | 50% |
| USDNOK=X | 15 | -70,859 | -30.9% | +66,285 | -133,394 | 40% |

Топ-пара **AUDUSD=X = +48.0%** (порог red flag 60% не превышен).
Худшая — **USDNOK=X = -70,859** (40% hit), ровно та, где реальные
издержки выше модельных. Carry-компонента суммарно положительна по всем парам,
но **4 из 9 пар убыточны по net**: на длинной выборке спот съедает carry-премию.

## v2.6 Ablation (20 лет, 10 bps RT)

| Вариант | Sharpe | Total ret | Max DD | Trades |
|---|---|---|---|---|
| v2 full (lag=45, cap=40) | +0.165 | +21.83% | -30.76% | 96 |
| no publication lag (v1 behaviour) | +0.258 | +38.02% | -26.19% | 93 |
| ex USDSEK | +0.185 | +24.46% | -30.77% | 81 |
| max_positions=2 | +0.219 | +22.47% | -19.54% | 63 |

## v2.7 Cost sensitivity (20 лет)

| Cost | Sharpe | Total ret | Max DD | Trades | Hit |
|---|---|---|---|---|---|
| 10 bps RT (baseline) | +0.165 | +21.83% | -30.76% | 96 | 51.0% |
| 25 bps RT | +0.135 | +16.54% | -31.80% | 96 | 51.0% |
| 40 bps RT (stress) | +0.105 | +11.25% | -32.84% | 96 | 50.0% |

При 25 bps RT Sharpe = **+0.135**, при 40 bps = **+0.105**.

## v2.8 Kill criteria (2/5)

| Критерий | Результат | Факт |
|---|---|---|
| net Sharpe ≥ 0.4 | FAIL | +0.165 |
| net Sharpe ≥ 0.7 (paper) | FAIL | +0.165 |
| max DD ≤ 15% | FAIL | -30.76% |
| hit rate ≥ 50% | PASS | 51.0% |
| avg carry ≥ 50 bps/yr | PASS | 82.1bps |

Правила STEP 9:
- Sharpe +0.165 < 0.5 → **CLOSE**
- Sharpe(25 bps) +0.135 < 0.4 → **CLOSE**

## v2.9 Вердикт v2: **CLOSE**

На 20-летней выборке (2006–2026, включая GFC 2008, Euro crisis 2011-12, yen unwind 2024)
с устранённым look-ahead и per-pair cap: **Sharpe +0.165**, max DD **-30.76%**,
годовая доходность **+0.99%**. При реалистичных 25 bps RT Sharpe
падает до **+0.135**. Ниже порога закрытия (0.4), втрое ниже paper-порога (0.7);
просадка -30.76% превышает red-flag (15%).

**v1-результат (0.4811) не воспроизводится**: он был получен на 3-летнем благоприятном
rate-regime (USD high-yield) и частично усилен look-ahead. На честной 20-летней выборке
G10 carry в этой реализации не покрывает издержки и просадку.

**Гипотеза закрывается. v3 не запускаем.**

## v2.10 Что имело бы смысл, если бы гипотезу продолжали (не сейчас)

1. **Другой сигнал**: forward-implied carry через CIP-девиацию от спота — без месячного лага FRED.
2. **Risk-off оверлей** на funding-ногах: 30-дневный vol-фильтр не спасает от GFC-подобных −30% DD.
3. **Пропускать затяжные отрицательные carry-режимы**: USD/EUR в минусе 20 лет, спотом это не отбивается.
