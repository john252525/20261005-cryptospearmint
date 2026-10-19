# Dividend Capture — Prescreen Analysis (post-diagnostic, final)

## 1. Executive Summary

Dividend capture (buy cum-dividend close, sell ex-dividend close) is a
micromechanics trade. Buyer of record at cum-close receives the dividend;
in an efficient market price drops by roughly the dividend amount on the
ex-open. Prior academic literature puts raw ex-day return near zero for
large-caps; after costs the trade is unprofitable.

**First-run measurement (+0.86% net) contained a date-alignment bug**:
yfinance dividend timestamps carry 09:30 ET time-of-day, but 
index uses 00:00 ET. The comparison 
included the ex-day close in the "pre" set — so the trade was measured
from ex-close to T+1-close, not from cum-close to ex-close. That inflated
the measured return by capturing post-ex-day rebound, not the div capture.

**Post-fix measurement across 180 trade-events, 2020-2024**:

| Metric | Value |
|---|---|
| n trades | 180 |
| mean return (gross) | -0.2546% |
| median return | -0.1415% |
| std return | 1.5926% |
| hit rate | 46.7% |
| mean net, 10 bps | -0.3546% |

Per-ticker means (gross):

| Ticker | Mean |
|---|---|
| CVX | +0.253% |
| IBM | -0.370% |
| KO | +0.094% |
| MAIN | +0.156% |
| MMM | -0.161% |
| MO | -0.727% |
| O | +0.127% |
| PFE | -0.456% |
| PM | -0.357% |
| T | -0.736% |
| VZ | -0.880% |
| XOM | +0.003% |

**Verdict**: mean_net at 10 bps = -0.3546%. Below the +0.30% threshold.
Trade does not survive transaction costs. This matches the academic prior and
confirms the first-run +0.86% was an artifact, not a real edge.

## 2. Mechanism

### 2.1 Cum-dividend and ex-dividend dates

A stock trades cum-dividend through the trading day before ex-date. On
ex-date, new buyers have no right to the dividend. Buyer of record at
cum-close receives the dividend even if sold on ex-date. The stock's
economic value drops by after-tax dividend value on the ex-open.

### 2.2 Price-drop mechanics

In an efficient market with rational taxable investors, expected overnight
drop equals dividend adjusted for tax differential between capital gains
and dividend income. For US equities, dividends taxed at ordinary rates
(up to 37%) if short-held, capital gains at preferential rates. When
after-tax dividend value < after-tax capital-gains equivalent, the
overnight drop **exceeds** the nominal dividend.

Empirically through 2010 the drop fraction was 0.80-1.00x of dividend. Residual
return to a dividend-capture buyer is near zero, not positive.

### 2.3 Sources of small residual

Three real-world sources, all small:
        (a) Partial intraday recovery post-ex-open.
        (b) Less-than-full overnight drop.
        (c) Market-maker inventory effects on low-liquidity names.

Each is 10-50 bps of the dividend amount. None is 100%.

### 2.4 Backtest pitfalls (confirmed by this prescreen)

        - **Timezone mismatch** between dividend timestamp (09:30) and price
          index (00:00) shifts the cum/ex day boundaries by one session,
          capturing post-ex rebound instead of the div drop. This produced
          the false +0.86% first-run number — see §6.
        - yfinance  with  is **split-adjusted**
          but not dividend-adjusted. Divisible amount must be added back,
          which is correct — but only if the day-boundary is right.
        - Ignoring overnight gap volatility and wash-sale/straddle.

## 3. Tax Considerations

### 3.1 Qualified vs ordinary

US dividends are qualified (15-20%) if held >60 days around ex-date.
High-yield capture holds ~2 days → NOT qualified → ordinary rates up to
37%.

### 3.2 60-day rule

Aggregation of re-entries within 60 days removes qualified status. Repeated
capture almost never qualifies.

### 3.3 Wash sale / straddle

Loss-realization within 30 days defers losses. Straddle rules kill qualified
status if hedged. Choose: qualified tax OR hedge, not both.

### 3.4 Implication

Gross +-0.25% is well below the +0.30% hurdle before any tax
adjustment. After-tax at 37% ordinary: -0.35% → -0.22%
net of costs and taxes. Category is unprofitable on gross terms; after-tax
compounds the loss.

## 4. Academic Evidence

### 4.1 Early (pre-2000)

Elton-Gruber 1970, Kalay 1982, Eades-Linn-McConnell 1984: drop fraction
0.90-1.00x, net-of-cost return ≈ zero. No standalone edge.

### 4.2 Modern (post-2000)

Blume-Stambaugh 1984; Hartzmark-Solomon 2013: raw ex-day return near zero
for large caps; -1% to -3% annualized after costs.

### 4.3 Commercial dividend-capture funds

Peak ~00M AUM in the US 1980-1990s, disappeared by 2005. Survivors had
options overlay (covered calls), not pure capture.

### 4.4 Relevance

Our post-fix measurement (-0.35% net) replicates the academic prior.
First-run +0.86% was a bug, not a discovery.

## 5. Sample Design

### 5.1 Universe

12 high-yield US names: T, VZ, MO, PM, XOM, CVX, IBM, KO, PFE, MMM, O,
MAIN. Selection: yield >= 3% (except KO/PFE/MMM at 2-3%), continuous
history 2020-2024, retail-heavy share register.

### 5.2 Window

Last 15 dividends per ticker with ex-date >= 2020-01-01. 12 × 15 = 180
events collected.

### 5.3 Entry / Exit

Buy at cum-close: last trading-day close whose **calendar date** is strictly
before ex-date. Sell at ex-close: first trading-day close whose calendar
date is >= ex-date. Comparison uses  on both indices to eliminate
the time-of-day bug.

### 5.4 Return formula

ret_pct = (ex_close + div - cum_close) / cum_close * 100

Requires raw (non-dividend-adjusted) Close. Verified: yfinance with
 returns split-adjusted but NOT dividend-adjusted Close.
Verified against known dividend (MO 2024-03-22: cum=44.95, ex=42.98, div=0.98
→ (−1.97 + 0.98)/44.95 = −2.20%).

### 5.5 Cost

Reported at 5/10/15/20 bps round-trip. Realistic: 6-16 bps, 10 central.

## 6. Measured Results (final, post-fix)

**180 trade-events**, 12 tickers, 2020-2024.

| Metric | Value |
|---|---|
| n trades | 180 |
| mean return (gross) | -0.2546% |
| median return | -0.1415% |
| std return | 1.5926% |
| hit rate | 46.7% |
| mean net, 10 bps | -0.3546% |

Per-ticker means:

| Ticker | Mean |
|---|---|
| CVX | +0.253% |
| IBM | -0.370% |
| KO | +0.094% |
| MAIN | +0.156% |
| MMM | -0.161% |
| MO | -0.727% |
| O | +0.127% |
| PFE | -0.456% |
| PM | -0.357% |
| T | -0.736% |
| VZ | -0.880% |
| XOM | +0.003% |

### Verdict

**NEGATIVE** — mean_net at 10 bps = **-0.3546%**. Below +0.30% threshold.
Matches academic prior. Category closes; no pilot.

## 7. Kill Criteria (satisfied)

        1. mean_net_10bps < +0.30%: **triggered** → close at prescreen.
        2. Sharpe < 1.0: no Sharpe computed (no positive mean). Close.
        3. Hit rate < 55%: hit rate 46.7% is above 55%, but mean
           negative — trade has positive-win-rate with large losses;
           classic negative-skew profile. Compounds the case for closure.

## 8. Recommendation

**Close the category.** Log to strategy registry alongside funding carry,
PEAD, GFC FX carry, and spin-off. The +0.86% first-run was a measurement
bug; corrected to -0.35% net, matching the academic prior.

### Process lesson

yfinance  index carries time-of-day (09:30 ET);
 index is midnight-local. Any formula that intersects the
two must compare **dates**, not timestamps. This is a single-line fix but
would have produced a false-positive entry in the registry otherwise.

## 9. Further Work

None. Category closes. If a future team wants to revisit:

        - Cross-verify prices from nasdaq.com raw close (independent of
          yfinance) for 500+ trade-events.
        - Sector-matched hedge to isolate dividend-capture residual from
          sector beta.
        - Model overnight gap as separate volatility term.
        - Tax overlay for US high-bracket client.

But baseline (measured -0.35% net, matching 50-year academic prior)
makes this a documented dead end, not a research gap.
