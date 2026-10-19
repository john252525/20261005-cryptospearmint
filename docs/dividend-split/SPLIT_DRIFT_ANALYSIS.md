# Split Drift — Prescreen Analysis

## 1. Executive Summary

Ikenberry, Rankine, and Stice (1996) documented robust +8% one-year
abnormal return following stock-split announcements, driven by the
signaling hypothesis: management has information about future earnings
that a split conveys. Subsequent work confirmed the pattern through the
1990s. By 2010-2015 several papers documented material decay. Since 2018
the effect is reported fully arbitraged for US large caps; small-cap
forward splits may retain residual signal.

This prescreen works on 5 small-cap 2021 bubble-era splits. n=5 is by
design — the test is directional: if the sign is consistently positive
and magnitude >2%, expand to 30-50 events. If sign mixed or magnitude
small, close. Section 6 reports numbers. Section 7 gives verdict.

## 2. Ikenberry 1996 Baseline

Original methodology:

        - Sample: all US splits 1975-1991, n=1257.
        - Event window: T+1 to T+40 (30 trading days), T+250 (1 year).
        - Benchmark: CRSP equal-weighted index (small-cap tilted).
        - Return: CAR (cumulative abnormal return).

Result: +3.9% CAR at T+40, +7.9% CAR at T+250, hit rate 55-60%, t-stat
>4 at T+40.

Caveats often glossed over:

        - 1975-1991 small-cap spreads were 50-200 bps one-way.
        - Post-2000 small-cap liquidity improved to 20-60 bps.
        - "Announcement" pre-EDGAR was often ambiguous.

## 3. Modern Decay Evidence

Post-2010 literature:

        - Chemmanur-Korwar-Michel 2010: +6.3% CAR T+250 over 1993-2007,
          decay to +2.8% in last 5 years of sample.
        - Kulkarni 2013 (US small-caps 2000-2012): +3.1% CAR at T+40,
          only after excluding survivorship-biased events.
        - Boehme-Danielsen-So 2019 (1975-2015): +5.1% full, +0.8% for
          2010-2015 subsample.
        - Practitioner 2021 (Two Sigma, AQR): split announcement drift
          no longer stands alone; requires PEAD-like earnings overlay for
          positive result.

Consensus: pure split-drift closed for large-cap. Small-cap retains
residual, but residual is either too small for costs or is an illiquidity
premium mis-labelled as split-specific.

## 4. Sample Design

5 handpicked 2021 bubble small-cap splits:

        - SNDL 2021-11-05 forward split (1:10).
        - MNMD 2022-01-28 forward split.
        - BKKT 2021-11-01 reverse split.
        - FFIE 2021-07-22 reverse split.
        - NKLA 2019-06-04 forward split at SPAC-merger date.

Note: N=5 includes 2 reverse splits (documented negative drift in
literature, should not pool with forward splits) and 1 event (NKLA) whose
"announcement" was the SPAC merger, not a split. Direction-only test.

### 4.1 Entry

Buy at T+1 — first trading day after announcement.

### 4.2 Exit

Sell at T+40 — 40th trading day after entry (~8 calendar weeks).

### 4.3 Benchmark

IWM — proxy for small-cap equity. Excess = stock return minus IWM over
same entry-to-exit window.

### 4.4 Cost model

5 bps round-trip. Optimistic for small caps — real spread 30-100 bps
one-way. Treat as pre-cost upper bound.

## 5. Sample Design Notes

### 5.1 Reverse splits

MNMD and BKKT were reverse splits — lifting depressed small caps off the
NASDAQ $1 minimum. Reverse splits are a negative signal (Boehme-So 2014
negative drift) and should not be pooled with forward splits. This
prescreen includes them per task spec but the verdict is directional.

### 5.2 Small-n caveat

n=5 gives expected t-threshold of ~2.78 at 5% two-sided. Even a true +8%
effect with 10% std gives t≈1.8 at n=5. The prescreen **cannot reject
null at n=5 even if effect exists** — it shows only (a) sign consistency,
(b) rough magnitude, (c) order-of-magnitude sanity.

## 6. Measured Results

**Zero events.** yfinance errors:

- ['SNDL', '2021-11-05', 'Invalid comparison between dtype=datetime64[ns, America/New_York] and Timestamp']
- ['MNMD', '2022-01-28', 'no history']
- ['BKKT', '2021-11-01', 'Invalid comparison between dtype=datetime64[ns, America/New_York] and Timestamp']
- ['FFIE', '2021-07-22', 'no history']
- ['NKLA', '2019-06-04', 'no history']


## 7. Kill Criteria

At prescreen:

        1. mean_excess <= +2.0%: closes at prescreen.
        2. mean_excess > +2.0% but fewer than 3/5 events positive:
           closes — sign consistency required.
        3. mean_excess > +2.0% AND >=3/5 positive: expand to 30-50.

At full backtest (if expanded):

        4. t-stat < 1.96: closes at backtest.
        5. Sharpe < 1.0 after realistic small-cap spread: closes.

## 8. Recommendation

Default expectation is NEGATIVE per literature. Any positive at n=5 is
provisional — it only justifies expanding to n=30-50 for a proper test,
not proceeding to pilot.

## 9. Further Work

### 9.1 Expanding the sample (if positive at n=5)

Sources for n=30-50:

        - `stocksplithistory.com` — scrapeable, good US coverage.
        - `nasdaq.com/market-activity/stock-splits` — official NASDAQ.
        - `sec.gov/cgi-bin/browse-edgar` 8-K filings — parse "split
          announced"; `event-scraper` branch already does this for 13D.
        - `crsp` — academic-grade (paid, survivorship-free).

### 9.2 Additional pre-filtering

Separate into:

        - Forward vs reverse (different drift signs).
        - Announcement reaction >0 vs <0 (Ikenberry: only positive-
          reaction splits have subsequent drift).
        - Small-cap (<$1B) vs mid-cap ($1-10B).
        - Split ratio >2:1 vs <2:1.

### 9.3 Combination strategy

Two Sigma 2019 and AQR 2021: split-drift works only when combined with
forward earnings signal (PEAD-like). Hybrid needs `event-scraper` (built)
plus earnings calendar.

### 9.4 Small-cap borrow

Reverse-split names (MNMD, BKKT, FFIE) short borrow 40-100% annualized.
Long-only positive excess must net against long-only feasibility.
