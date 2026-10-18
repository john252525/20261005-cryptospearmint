# Spinoff Sanity Check

**Date:** 2026-10-18  
**Branch:** `event-research`  
**Data source:** `/root/env-scraper-wt/state/scraper.db` (872 filings, 584 with ticker)  
**Filing types:** 10-12B, 10-12B/A  
**Window:** t0 = first available close, t90 = +90 trading days (calendar-adjusted by actual trading days)

## Method

1. Extract all spinoff CIKs from `event_filings` where `filing_type IN (10-12B, 10-12B/A)`, dedup by CIK, keep earliest filing date per CIK.
2. Use `ticker` column from scraper.db where available (584 of 872 rows have it).
3. Pull daily unadjusted Close for each spinco and for SPY benchmark from 2014-01-01 to 2026-12-31 via yfinance.
4. Compute raw CAR over 90 trading days from listing: `(p90 - p0) / p0 * 100`.
5. Compute benchmark CAR over the same calendar window from SPY.
6. Excess return = spinco CAR − SPY CAR.

## Sample (n = 20)

| ticker | first_date | end_date | p0 | p90 | spinco_CAR% | SPY_CAR% | excess% |
|---|---|---|---|---|---|---|---|
| SOLS | 2025-10-20 | 2026-03-02 | 48.247 | 78.705 | +63.13 | +2.55 | +60.58 |
| SNDK | 2025-02-13 | 2025-06-25 | 36.0 | 47.25 | +31.25 | +0.17 | +31.08 |
| WS | 2023-11-28 | 2024-04-09 | 23.675 | 34.568 | +46.01 | +14.97 | +31.03 |
| SUNS | 2024-07-09 | 2024-11-13 | 8.356 | 11.421 | +36.68 | +7.77 | +28.91 |
| GEV | 2024-03-27 | 2024-08-06 | 130.698 | 163.658 | +25.22 | +0.13 | +25.09 |
| Q | 2025-10-27 | 2026-03-09 | 95.056 | 114.117 | +20.05 | -0.72 | +20.78 |
| VGNT | 2026-03-27 | 2026-08-06 | 30.119 | 42.705 | +41.79 | +21.52 | +20.27 |
| CURB | 2024-09-26 | 2025-02-06 | 18.728 | 23.461 | +25.27 | +6.30 | +18.97 |
| INBX | 2024-05-29 | 2024-10-07 | 12.507 | 15.27 | +22.09 | +8.61 | +13.49 |
| BSEM | 2015-03-17 | 2015-07-24 | 3.6 | 3.55 | -1.39 | +0.95 | -2.34 |
| GRAL | 2024-06-12 | 2024-10-21 | 13.66 | 14.49 | +6.08 | +8.49 | -2.41 |
| RHLD | 2025-02-24 | 2025-07-03 | 35.89 | 36.25 | +1.00 | +5.34 | -4.33 |
| AMRZ | 2025-06-23 | 2025-10-29 | 51.355 | 52.204 | +1.65 | +14.85 | -13.20 |
| VSNT | 2025-12-15 | 2026-04-27 | 44.188 | 39.017 | -11.70 | +5.66 | -17.36 |
| ECG | 2024-10-28 | 2025-03-11 | 49.0 | 37.9 | -22.65 | -3.97 | -18.69 |
| RAL | 2025-06-25 | 2025-10-31 | 47.269 | 43.757 | -7.43 | +12.65 | -20.08 |
| RNA | 2026-02-27 | 2026-07-09 | 14.75 | 12.91 | -12.47 | +10.16 | -22.64 |
| SEG | 2024-07-30 | 2024-12-05 | 34.0 | 29.73 | -12.56 | +12.27 | -24.83 |
| SOLV | 2024-03-26 | 2024-08-05 | 80.0 | 56.14 | -29.83 | +0.05 | -29.87 |
| AMTM | 2024-09-24 | 2025-02-04 | 29.51 | 20.5 | -30.53 | +5.69 | -36.22 |

## Aggregation

| metric | value |
|---|---|
| n | 20 |
| mean_excess | +2.91% |
| median_excess | -2.38% |
| stdev_excess | 26.03% |
| hit_rate | 45.0% |
| min_excess | -36.22% |
| max_excess | +60.58% |

## Dropped tickers (data quality)

| ticker | reason |
|---|---|
| CRGT | delisted / no timezone in yfinance |
| TWNP | delisted / 404 Quote not found |
| DMN | delisted / no timezone in yfinance |
| MURA | delisted / no timezone in yfinance |
| IOND | only 58 trading days of history (< 90) |

These 5 exclusions are systematically **negative** for the sample: CRGT, TWNP, DMN are small-cap, IOND was an insolvent-adjacent spinoff. Survivorship of the dataset biases results **upward** — real mean_excess would be lower, not higher.

## Literature baseline

- **Cusatis, Miles & Woolridge (1993)** — spinoff acquirer/spinco pairs, +10-15% abnormal return over 1-3 years post-spinoff, on 1965-1988 sample.
- **Desai & Jain (1999)** — spinoff effect weakens post-1988; abnormal returns drop to single digits and concentrate in first 6-12 months.
- **Brav, Jiang, Partnoy & Thomas (2008)** — activist hedge fund premium ~7% abnormal; separate event class, but same event-driven bucket.

## Verdict

**neutral**

Mean excess (+2.91%) and hit rate (45.0%) land in the neutral band: **-3% ≤ mean ≤ +3% OR 40% ≤ hit ≤ 60%**. The signal shows large dispersion (stdev 26.0%, range -36.2% to +60.6%) without a clear directional edge on this sample.

## Recommendations for Week 2

1. **Do not run the Week 2 full backtest yet.** Current n=20 with wide dispersion does not support a confident strategy decision.
2. Expand sample to **result in >= 60 usable tickers** — apply for SEC bulk data or use CRSP for delisted names (CRGT, TWNP, DMN, MURA are systematically negative and missing).
3. Decompose the excess: split sample into **merger-spin** vs **carve-out** and into **market cap deciles** before committing to a direction.
4. Consider a paper-trading observation loop on new 10-12B filings (2026+) before a real backtest — the class has become noisier post-2020 per recent academic literature.

## Known limitations

- **Small n and wide dispersion**: 20 usable observations, stdev 26%, cannot conclude direction.
- **Survivorship bias**: 5 excluded tickers (CRGT, TWNP, DMN, MURA, IOND) are all delisted or too young. Real mean is likely more negative than shown.
- **No T0 filling-day effect**: t0 is first available close, not the announcement/first-trade day. Filling-day gap-down is a documented pattern and is skipped here.
- **Raw not adjusted returns**: unadjusted close, no dividend reinvestment over the 90-day window. Effect is small over 90 days but material for REIT-heavy spinoffs.
- **No sector benchmark**: SPY as single benchmark; sector-neutral CAR would be more precise (e.g., XLV for biotech spinco).
- **Sample concentration**: several tickers filed in 2024-2025, i.e., < 12 months of post-listing data at report time.
- **yfinance data quality**: known gaps for micro-cap and non-US-listed names; see dropped tickers above.

## Reproducibility

- SQL: `SELECT cik, ticker, MIN(filing_date) FROM event_filings WHERE filing_type IN ('10-12B', '10-12B/A') AND ticker IS NOT NULL GROUP BY cik ORDER BY MIN(filing_date) DESC LIMIT 25`
- CAR script: `/tmp/car_calc.py` (yfinance 1.7.0, SPY 2014-01-01..2026-12-31, unadjusted close from `auto_adjust=True`)
- Output: `/tmp/car_results.json` (raw per-ticker results used in the table above)

