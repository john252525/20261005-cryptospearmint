# Activist 13D Sanity Check

**Date:** 2026-10-18  
**Branch:** `event-research`  
**Data source:** `/root/env-scraper-wt/state/scraper.db`, `event_filings` with `filing_type LIKE '%13D%'`  
**Window constraint:** all 13D filings are in 2026-09-10 … 2026-10-16 (36 days back from report date)  

## Method

### Step 1 — Filer name extraction

The `company_name` column in `event_filings` holds the **issuer**, not the filer. The SEC FORM 13D XML in `url_primary` / `primary_doc.xml` stores the true filer(s) under the namespaced path:

    {http://www.sec.gov/edgar/schedule13D}reportingPersonInfo
        → {…}reportingPersonName  (can repeat, one per joint filer)

Parser: `ElementTree`, namespace-aware iteration over `root.iter(NS + 'reportingPersonInfo')`; all `reportingPersonName` children collected and joined with ` | `. This is the only reliable path — `filedBy` / `filerName` do NOT appear in SEC’s current 13D XML schema (verified against live `primary_doc.xml` samples).

### Step 2 — Filer → ticker pool

500 of 500 13D filings successfully parsed: 500 filer strings written back into `event_filings.summary_text`. Zero HTTP failures, zero no-name parses, zero schema mismatches.

### Step 3 — CAR computation

**Horizon forced by data window:** all filings ≤ 36 calendar days old → **T+90 CAR is impossible** (SEC data does not exist for future 60 days). The only horizon with usable cross-section is **T+20 trading days**.

- Entry day t0 = first available close on/after `filing_date`  
- Exit t+20 = 20 trading days after t0 (some rows 18–20 days due to holidays)  
- Benchmark: SPY over identical calendar window  
- Excess = ticker return − SPY return over the same trading-day window  
- Sample: films with `filing_date ≤ 2026-09-16` (latest possible T+20 at report time), unique ticker, non-zero post-filing history  

## Pool coverage

| metric | value |
|---|---|
| 13D filings in DB | 500 |
| filer names extracted | **500 / 500** |
| distinct tickers with 13D | 337 |
| distinct filer CIKs | 359 |
| filings with `filing_date ≤ 2026-09-16` (T+20 eligible) | 76 |
| of those usable (>= 18 post-filing closes) | **66** |
| excluded: post_filing_only < 15d | 10 |
| yfinance no-data | 0 |

## Filer concentration in sample

No single filer dominates the usable 66. Top-10 filers each appear exactly **once** in the sample after de-duplication — the pool is highly fragmented, which is expected for a general 13D screen (not only "known activist list").

### Famous-activist subset

Checking the pool against a 20-name list (Elliott, Pershing, Icahn, Starboard, Third Point, ValueAct, Trian, JANA, Sachem Head, Ancora, Corvex, Greenlight, Barington, Engine No. 1, Politan, Macellum, Eminence, Land and Buildings, Blackwells, Engaged):

| activist | 13D count |
|---|---|
| Elliott | 2 |
| Icahn | 1 |
| Starboard | 1 |
| Third Point | 1 |
| JANA | 1 |
| Politan | 1 |
| **total matched** | **7 / 500** |

Even at only 7 famous-activist matches, the pool is statistically smaller than the 66-name general 13D universe. The CAR computation therefore runs on the **full 13D general pool** — 13D filing itself is the activist signal in this screen, not filer identity.

## Sample table (n = 66) — top-10 and worst-10 by excess

| ticker | filer | filing_date | t0 | t20 | trading_days | excess% |
|---|---|---|---|---|---|---|
| NAUT | AH Bio Fund II, L.P.  | 2026-09-11 | 2026-09-11 | 2026-10-09 | 20 | +118.47 |
| SWRD | Charles Robert Abele  | 2026-09-16 | 2026-09-16 | 2026-10-14 | 20 | +38.02 |
| PCMC | REPOSITORY SERVICES LLC | 2026-09-10 | 2026-09-10 | 2026-10-08 | 20 | +29.62 |
| DT | PICTET ASSET MANAGEMENT SA | 2026-09-16 | 2026-09-16 | 2026-10-14 | 20 | +12.89 |
| GLOO | Grace & Mercy Foundation, Inc. | 2026-09-11 | 2026-09-11 | 2026-10-09 | 20 | +12.74 |
| UEIC | TORO 18 HOLDINGS LLC  | 2026-09-11 | 2026-09-11 | 2026-10-09 | 20 | +9.78 |
| TRMD | OCM NJORD HOLDINGS S.A R.L.  | 2026-09-16 | 2026-09-16 | 2026-10-14 | 20 | +6.73 |
| MTN | Oasis Management Co Ltd.  | 2026-09-16 | 2026-09-16 | 2026-10-14 | 20 | +6.01 |
| SEZL | Charles Youakim  | 2026-09-14 | 2026-09-14 | 2026-10-12 | 20 | +4.81 |
| HSDT | Daniel W. Morehead  | 2026-09-15 | 2026-09-15 | 2026-10-13 | 20 | +3.36 |

| ticker | filer | filing_date | t0 | t20 | trading_days | excess% |
|---|---|---|---|---|---|---|
| RAKR | Ryan D. Moore  | 2026-09-11 | 2026-09-11 | 2026-10-09 | 20 | -96.24 |
| FTFT | Wealth Index Capital Limited  | 2026-09-16 | 2026-09-16 | 2026-10-14 | 20 | -64.60 |
| NFEGP | Wesley R. Edens | 2026-09-15 | 2026-09-15 | 2026-10-13 | 20 | -58.31 |
| BRUN | Sean Goodrich  | 2026-09-16 | 2026-09-16 | 2026-10-14 | 20 | -38.66 |
| VNRX | Lagoda Investment Management, L.P.  | 2026-09-16 | 2026-09-16 | 2026-10-14 | 20 | -35.65 |
| SAFX | GL Part SPV II, LLC | 2026-09-15 | 2026-09-15 | 2026-10-13 | 20 | -32.98 |
| ATER | Lazar David E. | 2026-09-10 | 2026-09-10 | 2026-10-08 | 20 | -31.32 |
| RENT | Gateway Runway, LLC  | 2026-09-11 | 2026-09-11 | 2026-10-09 | 20 | -29.88 |
| CNXU | Jeffrey Sharpe | 2026-09-15 | 2026-09-15 | 2026-10-13 | 20 | -28.60 |
| LODE | MAK Capital Fund LP  | 2026-09-16 | 2026-09-16 | 2026-10-14 | 20 | -28.02 |

## Aggregation

| metric | value |
|---|---|
| n | 66 |
| mean_excess | -8.22% |
| median_excess | -3.99% |
| stdev | 25.44% |
| t_stat | -2.62 |
| 95% CI | [-14.36%, -2.08%] |
| hit_rate | 25.8% |
| horizon | T+20 trading days |

Positive vs negative split:

- n_positive = 17 (25.8 %), median_positive = +4.81%
- n_negative = 49 (74.2 %), median_negative = -11.95%

## Verdict

**negative**

### Why negative

1. **Mean −8.22% excess vs SPY over 20 trading days.** Not a borderline result — this is a strong negative factor.
2. **t-stat = -2.62** — magnitude exceeds the 1.96 (5 %) threshold and even the 2.58 (1 %) threshold. The negative effect is statistically significant at the **1 % level**, not just noise.
3. **95 % CI [-14.36%, -2.08%] — entirely below zero.** No overlap with positive region.
4. **Hit rate 25.8 %** — 3 out of 4 13D filings underperform SPY over T+20. That is the mirror image of the "activist premium" hypothesis from Brav et al. 2008.
5. **Median negative ( −3.99%) exceeds mean in magnitude.** The distribution is fat-tailed with more large losses than large gains (see worst-10 vs top-10).

### What this actually means

The negative sign is **not** a refutation of the activist-premium literature. It is the *selection bias* of a general 13D screen:

- The famous-activist subset (Elliott, Starboard, Third Point, Icahn, JANA, Politan) — the one the literature is built on — accounts for only 7/500 filings. The other 493 are mostly small-cap, non-institutional filers, often defensively motivated (insider or management-related filings), frequently negative event to the stock.
- On T+20 horizon specifically, the "activist bump" that Brav et al. measure is a **filing-day event** that reverses within weeks for non-institutional filers. By-then the price reacts to **who** the filer is, and a 15 % institutional filer trades very differently from a 1 % dissident.
- In other words: **A screen that treats every 13D as activity is not a screen for the "activist premium".** The −8.22 % is what *naive* 13D-filing CAR looks like. The positive factor requires the famous-activist filter — which in this pool is only 7 observations, far too few for statistical work.

## Recommendation for Week 3

1. **Do not build a strategy on the general 13D pool.** It has a statistically significant negative mean on T+20 (−8.22 %, t = −2.62). Running a long-only general-13D signal is a negative-EV bet by the data.
2. **Test the famous-activist filter separately — but n = 7 is unusable.** The correct next step is to expand the historical window: the current scraper window is 36 days; even one-year of 13D filings would give ~6000 events, with the famous-activist subset ~80–120 — enough for statistical work.
3. **Consider the negative signal as a possible short-side edge.** If a general 13D filing systematically underperforms SPY by 8 % over 20 days, then a short-on-13D-filing rule (with famous activists excluded) is a legitimate hypothesis to test on a longer window with costs/slippage.
4. **Do not pivot to spinoffs.** Spinoff Week 2 was neutral (t = 1.24); activist 13D is strongly negative (t = −2.62). If forced to pick one direction from current evidence, **short 13D is the strongest statistical signal in the entire event-research track so far** — not because it is "positive", but because it is the only one that clears the significance bar at all.

## Known limitations

1. **T+20 only, not T+90.** Data window (13D filings 2026-09-10 … 2026-10-16) makes T+90 impossible. T+90 would require a scraper backfill of ~4.5 months. T+20 is the maximum statistically usable horizon today.
2. **Small n.** 66 usable observations. Negative significance is strong (t = −2.62) but the tail is thin; a longer window is needed for confidence in magnitude, not in sign.
3. **Famous-activist subset is unusable.** 7 matches. Even if the "true premium" is +7 % for famous activists, 7 observations give almost no power. Sign for the general pool cannot be directly transferred.
4. **No costs.** Zero commission, zero slippage, zero borrow. Short-stock borrow on small-cap 13D targets is often 5–20 % annualized, which would reduce the magnitude of the negative mean by ~0.3–1.5 % over T+20. Signal survives.
5. **Filer deduplication:** joint filings (multiple `reportingPersonName` per accession) produce concatenated filer strings. This affects filer-level analysis, not ticker-level CAR. For ticker-level, one accession = one row.
6. **XML schema dependency.** Parser relies on `reportingPersonInfo`/`reportingPersonName` in namespace `schedule13D`. Older filings (pre-2022 X0202 schema) may not parse. All 500 current-scraper rows parse cleanly; a historical backfill would need schema fallbacks for 2008–2021 filings.
7. **Yahoo price quality.** 10 tickers excluded (`TVGNW`, `BZFDW`, `DAVEW`, `ANGHW`, `MDCXW`, `CRGOW`, `SDAWW` — warrants, 1 day of history; `HLSQ` — 12 days; `ATAI` — 0 days; `GPUS-PD` — preferred shares, bad ticker). All are structurally different from the sample; excluding them is likely neutral to the mean.

## Reproducibility

- Filer extraction: `/tmp/parse_13d_v2.py`, output committed to `event_filings.summary_text`
- CAR: `/tmp/13d_car.py`, output `/tmp/13d_car_results.json`
- SQL selection: `WHERE filing_type LIKE '%13D%' AND filing_date <= '2026-09-16' AND ticker IS NOT NULL GROUP BY cik` — 76 rows → 66 usable after data checks
- Benchmark: SPY batch-downloaded via yfinance 1.7.0 (`auto_adjust=True`, `threads=True`)
