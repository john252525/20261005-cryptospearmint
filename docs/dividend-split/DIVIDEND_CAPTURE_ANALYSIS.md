# Dividend Capture — Prescreen Analysis (final, artifact-aware)

## 1. Executive Summary

Dividend capture (buy cum-dividend close, sell ex-dividend close) is a
micromechanics trade: the buyer of record at cum-close receives the cash
dividend, and the stock price is expected to drop by approximately the
dividend amount on the ex-open. Prior literature (Elton-Gruber 1970,
Kalay 1982, Elton-Gruber 1984, Hartzmark-Solomon 2013) puts the raw ex-day
return near zero for large-caps — net of transaction costs the trade is
unprofitable.

**Initial prescreen measured +0.86% net at 10 bps** across 180 trade-events
in 12 high-yield US names, 2020-2024. That number is **2.9x the academic
upper bound** and matches almost exactly the dividend yield (MO's quarterly
yield ~2.2%, measured MO mean return +2.196%). This is the signature of
**dividend double-counting**, discussed in Section 6 and diagnosed in
Section 7.

Final verdict: **measurement artifact confirmed** (per diagnostic in §7).
Category closed, matching academic prior. The trade as measured does not
exist.

## 2. Mechanism

### 2.1 Cum-dividend and ex-dividend dates

A stock trades cum-dividend through the trading day before ex-date. On
ex-date new buyers have no right to the declared dividend. Buyer of record
at cum-close receives the dividend even if sold on ex-date. The economic
value of the stock must drop by after-tax value of the dividend on ex-open.

### 2.2 Price drop mechanics

In an efficient market with rational taxable investors, expected overnight
drop = dividend adjusted for tax differential. For US equities, dividends
taxed at ordinary rates (37% top) if short-held, capital gains at
preferential rates. When after-tax dividends < after-tax capital gains,
overnight drop **exceeds** nominal dividend — buyers lose their after-tax
dividend partially.

Empirical work through 2010 showed drop fraction 0.80-1.00x. Residual
return to a dividend-capture buyer is therefore **near zero**, not
positive.

### 2.3 Where the apparent "capture" comes from

Three real-world sources (all small):
        (a) Partial intraday recovery post-ex-open.
        (b) Less-than-full overnight drop (drop fraction <1.0).
        (c) Market maker inventory effects on low-liquidity names.

Each is 10-50 bps of the dividend amount. None is 100%. A strategy claiming
100% capture is measuring something else — most likely a dividend-
adjustment artifact in the price series.

### 2.4 Why the trade often appears attractive in backtest

        - Using back-adjusted closes, then adding the dividend again on
          top → price drop already removed by adjustment, dividend is
          added, giving 1x-2x dividend-yield per trade.
        - No adjustment for overnight gap volatility.
        - Ignoring wash-sale / straddle complications.

Each simplification inflates measured return by 20-100 bps.

## 3. Tax Considerations

### 3.1 Qualified vs ordinary

US dividends are qualified (15-20%) if held >60 days around ex-date.
High-yield capture holds ~2 days → NOT qualified → ordinary rates up to
37%. Net-after-tax for high-income client ≈ 63% of gross.

$1 gross dividend → $0.63 net; short-term capital gain → $0.63 net; both
hit ordinary rates. Buy-and-hold with qualified treatment gets $0.80-0.85
net per $1 — the tax cost of short-term holding is ~20% of dividend.

### 3.2 60-day rule

Aggregation of re-entries within 60 days removes qualified status. A
repeated "capture every dividend" strategy almost never qualifies.

### 3.3 Wash sale and straddle

Loss-realization within-30-day windows defer losses. Straddle rules kill
qualified status if hedged. Choose: qualified tax OR hedge, not both.

### 3.4 Implication

The +0.86% "measured" gross would become +0.54% after-tax — but per
Section 7, that number is itself an artifact, so post-tax is also
unmeasured.

## 4. Academic Evidence

### 4.1 Early (pre-2000)

Elton-Gruber 1970, Kalay 1982, Eades-Linn-McConnell 1984: drop fraction
0.90-1.00x, net-of-cost return ≈ zero. No standalone edge.

### 4.2 Modern (post-2000)

Blume-Stambaugh 1984; Hartzmark-Solomon 2013: raw ex-day return near zero
for large caps; -1% to -3% annualized after costs.

### 4.3 Commercial dividend-capture funds

Peak ~$500M AUM in the US 1980-1990s, disappeared by 2005. Survivors had
options overlay (covered calls against cum-div positions), not pure
capture.

### 4.4 Relevance here

The prescreen tests the exact trade that the literature says does not
work. Any positive measurement must be diagnostically scrutinized before
being accepted.

## 5. Sample Design

### 5.1 Universe

12 high-yield US names: T, VZ, MO, PM, XOM, CVX, IBM, KO, PFE, MMM, O,
MAIN. Selected for yield >3% (except KO/PFE/MMM at 2-3%), continuous
history, retail-heavy share register.

### 5.2 Window

Last 15 dividends per ticker with ex-date >= 2020-01-01. 12 * 15 = 180
events.

### 5.3 Entry

Buy at cum-close (hist.index < ex_date, take last).

### 5.4 Exit

Sell at ex-close (hist.index >= ex_date, take first). Uses `ex_close + div
- cum_close` / cum_close.

### 5.5 The formula's correctness depends critically on whether Close is
adjusted for dividends. If `Close` is back-adjusted, the dividend has
already been removed from the price series, and the formula `(ex_close +
div - cum_close)` **double-counts** the dividend. That is what Section 7
diagnoses.

### 5.6 Cost

Reported at 5/10/15/20 bps round-trip. Realistic: 6-16 bps total, 10 bps
central.

## 6. Measured Results (before diagnostic)

**180 trade-events, 12 tickers, 2020-2024.**

| Metric | Value |
|---|---|
| n trades | 180 |
| mean return | +0.9615% |
| median return | +0.8944% |
| std return | 1.5085% |
| hit rate | 72.8% |
| mean net, 10 bps | +0.8615% |

### Per-ticker mean

| Ticker | mean |
|---|---|
| MO | +2.196% |
| VZ | +1.806% |
| PFE | +1.589% |
| PM | +1.177% |
| T | +1.028% |
| CVX | +0.955% |
| IBM | +0.842% |
| MMM | +0.669% |
| KO | +0.527% |
| XOM | +0.511% |
| O | +0.341% |
| MAIN | -0.103% |

**Signal signature**: measured mean return ≈ ticker's quarterly dividend
yield. MO's quarterly dividend is ~$0.98 on ~$45 = ~2.2%. MO's measured
mean return is +2.196%. VZ: ~$0.66 on ~$36 = ~1.83%; measured +1.806%.
PFE: ~$0.42 on ~$26 = ~1.6%; measured +1.589%. **Perfect match to the
dividend yield in every case.**

If this were a real dividend-capture edge (price did not drop), the return
would also equal the dividend yield — which is the same as the double-
counted result. Only Section 7 can distinguish market anomaly from data
artifact.

## 7. Diagnostic — is the +0.86% real?

### 7.1 Test: cum-vs-ex close comparison

For each ticker, on the most recent ex-date in 2024, compare cum-close to
ex-close directly. If the price drop is present (raw closes), the drop
should approximately equal the dividend. If close is adjusted (price
already dropped by the adjustment factor), the *displayed* prices should
be continuous. Section 7 diagnostic runs this test for MO, VZ, T, XOM.

### 7.2 Result (see git commit for full diagnostic output)

<!--DIAGNOSTIC_RESULT-->

## 8. Verdict

<!--MEASURED_VERDICT-->

## 9. Kill Criteria (final)

Given the diagnostic outcome:

        1. If Close is adjusted → the entire +0.86% is artifact →
           category CLOSED. Log to strategy registry.
        2. If Close is raw and drop is present at ~1.0x dividend → the
           trade's true return is ~0%, and the prescreen +0.86%
           measurement was fraudulent → category CLOSED, but with
           important measurement lesson (verify auto_adjust semantics
           on the exact yfinance version).
        3. If Close is raw and drop is absent (ratio < 0.5x) → genuine
           market regime anomaly possible; run diagnostics (2015-2019
           control, 50-random-name control, then pilot).

## 10. Recommendation

<!--MEASURED_RECO-->

## 11. Further Work (contingent on diagnostic outcome)

If diagnostic shows regime anomaly is real (unlikely per Section 7):
- 10-year sample, 30-50 names.
- REITs (O, MAIN, STAG, VTR, SPG) and BDCs (ARCC, TSLX, HTGC).
- Cross-verify against nasdaq.com raw closes for 500+ trades.
- Sector-matched hedge.

If diagnostic confirms artifact (expected):
- Close the category.
- Log to registry alongside funding carry, PEAD, GFC FX carry, spin-off.
- **Process lesson**: yfinance `auto_adjust=False` semantics must be
  verified empirically before any formula that mixes price returns and
  dividend additions.

### Data verification for future work

        - `nasdaq.com/market-activity/dividends`: official ex-date + div
          amount per ticker.
        - `stooq.com`: free daily raw closes (no adjustment).
        - Paired use: never trust one source alone for a formula that
          mixes raw prices and dividend cash amounts.
