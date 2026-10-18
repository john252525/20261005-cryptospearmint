# Spinoff Week 2 Backtest — Full Sample

**Date:** 2026-10-18  
**Branch:** `event-research`  
**Data source:** `/root/env-scraper-wt/state/scraper.db` (filing types 10-12B, 10-12B/A, dedup by CIK)  
**Benchmark:** SPY  
**Window:** t0 = first available yfinance close post-listing, t90 = +90 trading days  

## Method

1. Extract all spinoff CIKs with non-empty ticker from `event_filings`, `filing_type IN (10-12B, 10-12B/A)`, dedup by CIK keeping earliest filing date.
2. Batch-download daily unadjusted close for all tickers + SPY via yfinance 1.7.0 (`auto_adjust=True`, `threads=True`).
3. For each ticker with >= 90 trading days: p0 = first available close, p90 = close at index +90. Both matched to SPY on the same calendar dates.
4. Excess = spinco 90-day return - SPY 90-day return over the same calendar window.
5. One-sample t-test: mean_excess / (stdev / sqrt(n)). Verdict by t-stat and mean-magnitude bands.

**Important methodological caveat:** the median gap between `filing_date` and `first_trade` in the sample is **67 days**. This means the "first available close" is **not** the day the spinoff starts trading — for many rows yfinance has no complete history until weeks later. The 90-day CAR therefore measures *post-listing drift*, **not** the filing-day/announcement effect that the literature (Cusatis-Miles-Woolridge 1993) refers to. This is a material limitation, not a footnote.

## Sample coverage

| field | value |
|---|---|
| n_ok (full CAR computed) | 141 |
| n_delisted (no yfinance data) | 15 |
| n_insufficient (< 90d or bad ticker) | 3 |
| total entries | 159 |
| median filing->trade lag (days) | 67 |

## Metrics

| metric | value |
|---|---|
| mean_excess | +5.14% |
| median_excess | -2.38% |
| stdev | 49.37% |
| hit_rate | 41.8% |
| t_stat | 1.24 |
| 95% CI | [-3.01%, +13.29%] |

## Interpretation

- **t_stat = 1.24** — below the 1.96 threshold for 95% significance. The mean is *not* statistically distinguishable from zero.
- **95% CI [-3.01%, +13.29%]** — contains zero. We cannot rule out +0% mean excess.
- **Mean (+5.14%) vs median (-2.38%):** the mean is +7.5 p.p. above the median. The distribution is heavily right-skewed: a handful of large winners (see Top 5) pull the mean up while the typical spinoff underperforms SPY by 2.38% over 90 days.
- **hit_rate = 41.8%** — more than half of spinoffs *underperform* their benchmark on 90-day drift.
- **stdev = 49.4%** — dispersion is larger than the mean by 10x. This is a fat-tailed distribution, not a robust factor.

## Verdict

**neutral**

Within the ruleset (positive requires t>1.96 AND mean>3%; negative requires t<-1.96 OR mean<-3%; everything else neutral), the outcome is neutral. Two independent facts drive this: (a) the mean does not clear the significance threshold (t=1.24), (b) the median is negative. Any "+5.14% mean" claim **cannot be used as a strategy edge** without decomposition of the right tail.

## Comparison with Week 1 sanity (n=20)

| | Week 1 | Week 2 |
|---|---|---|
| n | 20 | 141 |
| mean_excess | +2.91% | +5.14% |
| median_excess | -2.38% | -2.38% |
| stdev | 26.03% | 49.37% |
| t_stat | 0.50 | 1.24 |
| hit_rate | 45.0% | 41.8% |
| verdict | neutral | neutral |

Week 2 confirms the conclusion on a 7x larger sample and stronger statistics. Mean moved up (+2.91% to +5.14%) because a few huge outliers entered the sample, but the median stayed at -2.38% — **exactly identical** to Week 1's median. Hit rate dropped from 45% to 41.8%. t-stat improved from 0.50 to 1.24, still far below 1.96. **The overall signal is not statistically significant and not symmetric across the distribution.**

## Top 5 / Worst 5

| rank | ticker | first_trade | excess% |
|---|---|---|---|
| 1 | TGGI | 2014-01-02 | +295.79 |
| 2 | MDIA | 2020-01-06 | +198.94 |
| 3 | BHVN | 2022-09-23 | +151.58 |
| 4 | LINK | 2014-01-02 | +135.79 |
| 5 | XPEL | 2019-07-01 | +97.75 |

| rank | ticker | first_trade | excess% |
|---|---|---|---|
| 1 | NIKA | 2024-03-14 | -104.58 |
| 2 | RENX | 2023-09-19 | -96.00 |
| 3 | ORBS | 2022-05-18 | -89.35 |
| 4 | APVO | 2016-07-20 | -76.93 |
| 5 | AQB | 2017-01-11 | -73.68 |

## Delisted tickers excluded from the mean

- Count: **15**
- Tickers: VSTO, BLD, HBI, RGPX, CHX, EQTNP, AAN, TSVT, ZIMV, EHAB, KLG, MURA, DMN, TWNP, CRGT

The delisted set includes well-known spinoffs: **VSTO** (Vista Outdoor), **HBI** (Hanesbrands), **BLD** (TopBuild), **CHX** (ChampionX), **AAN** (Aaron's), **KLG** (Kellogg), **MURA** (Mural Oncology). These are exactly the negative-tail cases the strategy would have to hold. Excluding them **inflates the mean upward** — the true population mean is likely lower than +5.14%. This is survivorship bias in its purest form, and it does not favour the "positive" hypothesis.

## Known limitations

1. **Filling-day effect is missing.** Median filing-to-trade lag is 67 days, so we measure drift starting weeks after listing, not the event itself.
2. **Survivorship bias.** 15 delisted = 9.6% of tradable tickers excluded. All of them are likely losers; mean is biased up.
3. **No costs.** Zero transaction costs, zero slippage. A spinoff strategy will at minimum pay ~10-15 bps round-trip per leg, eating 0.1-0.3% of 90-day excess.
4. **No sector benchmark.** SPY only. Small-cap spinoffs vs large-cap SPY means beta and size mismatch dominates CAR.
5. **Fat tails.** stdev 49.4% > mean +5.1% by 10x. This is not a Gaussian CAR distribution. t-test assumptions are violated but even so, the mean is not significant.
6. **90-day horizon only.** CMW 1993 look at 1-3 years. Signal may be in the longer tail but 90-day window cannot see it.

## Recommendation for Week 3

Per the task ruleset, verdict = **neutral** requires the "expand or pivot" branch. Neither "full backtest" nor "pivot to activist" is supported by this evidence alone. The concrete next steps:

1. **Do not proceed to full Week 3 backtest with current sample.** The t-stat is 1.24, CI includes zero, and the mean-median gap of 7.5 p.p. shows the "edge" is outlier-driven, not structural.
2. **Close the survivorship gap first.** Pull historical prices for the 15 delisted tickers via CRSP, Datastream, or a paid vendor. If delisted spinoffs are, as expected, systematic losers, the mean will move closer to the median — likely turning the verdict to **negative**.
3. **Fix the filling-day gap.** Re-run CAR from the actual first-trading-date (SEC gives this via the 10-12B filing cover page), not the yfinance first-available close. Median lag 67 days means 60%+ of the measured window is drift, not event.
4. **Evaluate a fused event strategy (spinoff + activist 13D)** as the more promising direction. Both use the same scraper; both have stronger a-priori literature support (Brav et al. 2008 for activism).

## Reproducibility

- Extract: `SELECT cik, MIN(filing_date), MIN(ticker) FROM event_filings WHERE filing_type IN ('10-12B', '10-12B/A') AND ticker IS NOT NULL GROUP BY cik` — 159 rows.
- Batch download: `yf.download(tickers + ['SPY'], start='2014-01-01', end='2026-12-31', auto_adjust=True, threads=True, group_by='ticker')` — shape (3217, 815).
- CAR script: `/tmp/week2_car.py`, output `/tmp/week2_results.json`.
- Delisted detection: `raw[tk]['Close'].dropna()` empty = delisted (yfinance returns all-NaN row for delisted).

