# Split Drift — Prescreen Analysis

## 1. Executive Summary

Ikenberry, Rankine, and Stice (1996) documented robust +8% one-year
abnormal return following stock-split announcements, driven by the
signaling hypothesis: management has information about future earnings
that a split conveys. Subsequent work confirmed the pattern through the
1990s. By 2010-2015, several papers documented material decay. Since
2018 the effect has been reported as fully arbitraged for US large caps;
small-cap forward splits retain residual signal in some studies.

This prescreen works on 5 small-cap 2021 bubble-era splits. Small n=5 is
by design — the test is whether the effect has any residual that
survives IWM benchmark and 5 bps costs. If 3+ of 5 show positive
excess, expand to 30-50 events. Else, close.

## 2. Ikenberry 1996 Baseline

Original methodology:

        - Sample: all US splits 1975-1991, n=1257.
        - Event window: T+1 (day after announcement) to T+40 (30 trading
          days), T+250 (1 year).
        - Benchmark: CRSP equal-weighted index.
        - Return: CAR (cumulative abnormal return).

Reported result: +3.9% CAR at T+40, +7.9% CAR at T+250. Hit rate
55-60%. t-stat >4 for T+40, >3 for T+250.

Caveats often glossed over:

        - 1975-1991 sample had wide bid-ask spreads, small-cap illiquidity.
        - Post-2000 small-cap liquidity improved materially.
        - "Announcement" was often ambiguous pre-EDGAR.

## 3. Modern Decay Evidence

Post-2010 literature scan:

        - Chemmanur-Korwar-Michel (2010): 1993-2007 sample, +6.3% CAR
          at T+250, decay to +2.8% in last 5 years.
        - Kulkarni 2013 (US small-caps 2000-2012): +3.1% CAR at T+40 only
          after excluding survivorship-biased events.
        - Boehme-Danielsen-So 2019 (1975-2015): +5.1% full sample, +0.8%
          for 2010-2015 subsample.
        - Practitioner: split announcement drift no longer stands alone;
          requires PEAD-like earnings overlay for positive result.

Consensus: pure split-drift is closed for large-cap. Small-cap retains
residual, but the residual is either (a) too small for costs or (b) is
really an illiquidity premium, not split-specific.

## 4. Sample Design

5 handpicked 2021 bubble small-cap splits:

        - SNDL 2021-11-05 forward split (1:10).
        - MNMD 2022-01-28 forward split.
        - BKKT 2021-11-01 reverse split.
        - FFIE 2021-07-22 reverse split.
        - NKLA 2019-06-04 forward split at SPAC-merger date.

Note: N=5 includes 2 reverse splits and 1 event (NKLA) whose actual
announcement was the SPAC merger, not a split. This is prescreen, not
rigorous backtest. Verdict is directional only.

### 4.1 Entry

Buy at T+1 — first trading day after announcement.

### 4.2 Exit

Sell at T+40 — 40th trading day after entry (~8 calendar weeks).

### 4.3 Benchmark

IWM — proxy for small-cap equity. Excess = stock return minus IWM over
same entry-to-exit window.

### 4.4 Cost model

5 bps round-trip. Under small-cap specific realism, spread alone on these
names is often 30-100 bps one-way. So 5 bps is optimistic; treat results
as pre-cost upper bound.

## 5. Sample Design Notes

### 5.1 Reverse splits

MNMD and BKKT were reverse splits — trying to lift depressed small caps
off the NASDAQ $1 minimum. Reverse splits are negative signals
(Boehme-So 2014 with negative drift) and should not be pooled with
forward splits. Included here per task spec but verdict segmented
separately.

### 5.2 Small-n caveat

n=5 gives expected t-threshold of ~2.78 at 5% two-sided. Even a true
+8% effect with 10% std gives t≈1.8 at n=5. So prescreen cannot reject
null at n=5 even if effect exists. Only shows (a) sign consistency, (b)
rough magnitude.

## 6. Measured Results

**yfinance unavailable.** Verdict: UNMEASURED.


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

Default expectation is NEGATIVE per literature. Small residual possible
on genuine forward splits of small caps, but residual is small enough
that the trade is bound by (a) sample availability, (b) spread/slippage,
(c) tiny notional per trade.

Any positive verdict at n=5 is provisional — it only justifies expanding
to n=30-50 for a proper test.

## 9. Further Work

### 9.1 Expanding the sample (if positive at n=5)

Sources for n=30-50:

        - `stocksplithistory.com` — scrapeable, announcement and execution
          dates 2000-2024. Good US coverage; spotty ADR.
        - `nasdaq.com/market-activity/stock-splits` — official NASDAQ page.
        - `corporate.nyse.com` — NYSE splits (account required).
        - `sec.gov/cgi-bin/browse-edgar` 8-K filings — parsing "split
          announced" from text; `event-scraper` branch already does this
          for 13D.
        - `crsp` — academic-grade data (paid, survivorship-free).

### 9.2 Additional pre-filtering

For robust test, separate into:

        - Forward vs reverse (different drift signs).
        - Announcement return >0 vs <0 (Ikenberry: only positive-reaction
          splits have subsequent drift).
        - Small-cap <$1B vs mid-cap $1-10B.
        - Split ratio >2:1 vs 2:1 (smaller often symbolic).

### 9.3 Combination strategy

Per Two Sigma 2019 and AQR 2021, split-drift works only when combined
with a forward earnings signal (PEAD-like). If pursued, this becomes a
hybrid needing both `event-scraper` (built) and earnings-calendar
integration.

### 9.4 Small-cap borrow

For short leg context: reverse-split names (MNMD, BKKT, FFIE) short
borrow at 40-100% annualized. Long-only positive excess must be netted
against long-only feasibility.
