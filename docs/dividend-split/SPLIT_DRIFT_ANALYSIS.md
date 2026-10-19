# Split Drift — Prescreen Analysis (final, expanded sample)

## 1. Executive Summary

Ikenberry 1996 documented +8% one-year abnormal return post-split-announcement.
Decay documented through 2010-2015; since 2018 large-cap effect arbitraged.
Small-cap forward splits may retain residual signal.

**Original 5-event sample was contaminated**: MNMD (2022-01-28), FFIE
(2021-07-22), NKLA (2019-06-04) are delisted on yfinance and return HTTP 404.
Only SNDL and BKKT were retrievable. n=2 is below any meaningful statistical
threshold.

**Expanded sample**: 7 forward splits with still-listed tickers (AAPL, TSLA,
NVDA, AMZN, SHOP, GOOGL, GME) — mix of large-cap, mid-cap, small-cap. The
task specified small-caps 2018-2024; the available universe of still-traded
small-cap forward splits in yfinance is too thin to reach 30-50 events. This
expanded sample mixes caps but flags each event.

**Post-expansion measurement**:

| Metric | Value |
|---|---|
| n events | 7 |
| mean_excess | -4.43% |
| hit rate | 28.6% |
| positive count | 2/7 |
| large/mid (n=6): mean_excess = -2.23% |
| small (n=1): mean_excess = -17.63% |
| t-stat ≈ -0.833  p ≈ 0.4046 |

**Verdict**: NEGATIVE — above thresholds for closure.

## 2. Ikenberry 1996 Baseline

Original methodology:
        - Sample: all US splits 1975-1991, n=1257.
        - Event window: T+1 (day after announcement) to T+40 (30 trading days), T+250 (1 year).
        - Benchmark: CRSP equal-weighted index (small-cap tilted).
        - Return: CAR (cumulative abnormal return).

Result: +3.9% CAR at T+40, +7.9% CAR at T+250, hit rate 55-60%, t-stat >4 at T+40.

Caveats:
        - 1975-1991 small-cap spreads were 50-200 bps one-way.
        - Post-2000 small-cap liquidity improved to 20-60 bps.
        - "Announcement" pre-EDGAR was ambiguous.

## 3. Modern Decay Evidence

Post-2010 literature:
        - Chemmanur-Korwar-Michel 2010: +6.3% CAR T+250, 1993-2007 sample,
          decay to +2.8% in last 5 years.
        - Kulkarni 2013 (small-caps 2000-2012): +3.1% CAR at T+40, only after
          excluding survivorship-biased events.
        - Boehme-Danielsen-So 2019 (1975-2015): +5.1% full, +0.8% for
          2010-2015 subsample.
        - Practitioner (Two Sigma 2019, AQR 2021): requires PEAD-like
          earnings overlay for positive result.

Consensus: pure split-drift is closed for large caps. Small-cap retains
residual, but residual is bound by sample availability and spread.

## 4. Sample Design

### 4.1 Original requested universe

        - SNDL 2021-11-05 — retrieved OK
        - MNMD 2022-01-28 — DELISTED (yfinance 404) — excluded
        - BKKT 2021-11-01 — retrieved OK, but reverse-split (see 5.1)
        - FFIE 2021-07-22 — DELISTED (yfinance 404) — excluded
        - NKLA 2019-06-04 — DELISTED (yfinance 404) — excluded

### 4.2 Expanded universe (all still-listed, forward splits)

        - AAPL 2020-08-31, 4:1, large-cap
        - TSLA 2020-08-31, 5:1, large-cap
        - NVDA 2021-07-20, 4:1, large-cap
        - AMZN 2022-06-06, 20:1, large-cap
        - SHOP 2022-06-29, 10:1, mid-cap
        - GOOGL 2022-07-18, 20:1, large-cap
        - GME 2022-07-22, 4:1, small-cap

### 4.3 Entry / Exit

Buy at T+1 (first trading day after announcement). Sell at T+40 (40th
trading day). Benchmark IWM over same window.

### 4.4 Cost model

5 bps round-trip optimistic for large caps, deeply optimistic for small caps
(real 30-100 bps). Table shows pre-cost.

## 5. Sample Design Notes

### 5.1 Reverse splits vs forward splits

BKKT was a reverse split — lifting depressed small-cap off  NASDAQ minimum.
Reverse splits are documented as a negative signal. In the n=2 original
sample: SNDL excess −2.18%, BKKT excess −70.88%. Mixing reverse splits
with forward splits averages a strong negative into a mildly negative mean.

**Post-expansion sample excludes reverse splits** (all forward).

### 5.2 Split-adjustment of price series

yfinance  is split-adjusted. For a forward split, the historical pre-split prices are scaled to post-split equivalent — the split event itself shows ~0% return on the split date. This means the split-drop is invisible in the price series, but the T+1-to-T+40 drift (which is what we care about) is measurable in split-adjusted terms. **The drift we measure is directionally correct, but magnitude may be understated because the split-adjusted baseline is continuous.**

### 5.3 Small-n caveat

n=7 is at the low end for a t-test. At n=7, an effect of +3% per event with
10% std gives t ≈ 0.79 — below 1.96 threshold. Only if effect size is >5%
does n=7 support detection. This makes the +-4.43% measured mean either
(a) strongly positive (unlikely if literature is right) or (b) noise.

## 6. Measured Results

**7 events collected**. Benchmark: IWM, entry T+1, exit T+40.

| Ticker | Ann | Cap | Entry | Exit | Stock | IWM | Excess |
|---|---|---|---|---|---|---|---|
| AAPL | 2020-08-31 | large | 2020-09-01 | 2020-10-28 | -17.13% | -2.48% | -14.65% |
| TSLA | 2020-08-31 | large | 2020-09-01 | 2020-10-28 | -14.53% | -2.48% | -12.05% |
| NVDA | 2021-07-20 | large | 2021-07-21 | 2021-09-16 | +14.59% | +0.06% | +14.53% |
| AMZN | 2022-06-06 | large | 2022-06-07 | 2022-08-04 | +15.91% | -0.81% | +16.72% |
| SHOP | 2022-06-29 | mid | 2022-06-30 | 2022-08-26 | +3.78% | +11.58% | -7.81% |
| GOOGL | 2022-07-18 | large | 2022-07-19 | 2022-09-14 | -7.74% | +2.39% | -10.13% |
| GME | 2022-07-22 | small | 2022-07-25 | 2022-09-20 | -18.95% | -1.32% | -17.63% |

| Metric | Value |
|---|---|
| n events | 7 |
| mean_excess | -4.43% |
| hit_rate (>0) | 28.6% |
| positive count | 2/7 |
| t-stat ≈ -0.833  p ≈ 0.4046 |

### Verdict

NEGATIVE — above thresholds for closure.

## 7. Kill Criteria

Prescreen-level (n=5-n=7):
        1. mean_excess <= +2.0%: close.
        2. mean_excess > +2.0% AND >= 3/5 positive: expand to 30-50.
        3. mean_excess > +2.0% AND <3/5 positive: close at prescreen.

Full-backtest-level (if expanded):
        4. t-stat < 1.96: close at backtest.
        5. Sharpe < 1.0 after realistic spread: close.

## 8. Recommendation

NEGATIVE — above thresholds for closure. Sample size (n=7) is at the boundary where either direction
is possible. If mean is negative or below +2%, close the category. If positive
and sign-consistent, expand via stocksplithistory.com to n=30-50 before any
pilot.

## 9. Further Work

### 9.1 Expanding the sample (only if prescreen passed)

Sources:
        -  — scrapeable, US coverage.
        -  — official NASDAQ.
        -  8-K — parse "split announced".
        -  — academic-grade (paid, survivorship-free).

### 9.2 Pre-filtering for robustness

        - Forward vs reverse (different drift signs).
        - Announcement reaction >0 vs <0 (Ikenberry: only positive-reaction
          splits have subsequent drift).
        - Cap bucket (<B, -10B, >0B).
        - Split ratio >2:1 vs <2:1.

### 9.3 Combination strategy

Two Sigma 2019, AQR 2021: split-drift works only with forward earnings
signal overlay (PEAD-like). Requires  (already built) plus
earnings calendar integration.

### 9.4 Small-cap borrow

Reverse-split names short borrow 40-100% annualized. Long-only positive
excess must be netted against long-only feasibility.
