# Dividend Capture — Prescreen Analysis

## 1. Executive Summary

Dividend capture (buy on cum-dividend close, sell on ex-dividend close) is
a micromechanics trade: the buyer of record at cum-close receives the cash
dividend, and in an efficient market the price drops approximately by the
dividend amount on the ex-open. The trade is profitable only if the
overnight drop is less than the dividend OR the stock recovers intraday
before the ex-close exit.

Academic consensus (pre-2010) held the trade to be unprofitable net of
transaction costs, with a raw ex-day return near zero for large caps.
**This prescreen contradicts that for the 2020-2024 sample**: measured
gross mean return of +0.96% per trade, and +0.86% net at 10 bps cost, is
larger than what prior literature predicted. Section 6 reports the actual
number. Section 7 explains the discrepancy. Section 8 gives the
recommendation — which is nuanced, not "pursue immediately".

## 2. Mechanism

### 2.1 Cum-dividend and ex-dividend dates

A stock trades cum-dividend through the trading day before the ex-date.
On the ex-date, new buyers no longer have the right to the declared
dividend. The buyer of record at cum-close receives the dividend even
though the position is sold on ex-date. The economic value of the stock
must drop by the after-tax value of the dividend on the ex-open.

### 2.2 Price drop mechanics

In an efficient market with rational taxable investors, the expected
overnight drop equals the dividend amount adjusted for the tax
differential between capital gains and dividend income. For US equities,
dividends are taxed at ordinary rates for non-qualified treatment (up to
37%) and preferential rates (20% + NIIT) for qualified dividends, while
capital gains are taxed at preferential rates. When after-tax dividends
are less valuable than after-tax capital gains, the theoretical overnight
drop **exceeds** the nominal dividend.

Empirical work through 2010 showed the drop fraction at 0.80-1.00x. If
the price over-drops, the residual return to a dividend-capture buyer
is **negative** — that's the classic result. If the price under-drops
(drop fraction <1.0), the residual return is **positive** — that's what
this prescreen measures in 2020-2024.

### 2.3 Where the "capture" actually comes from

The trade is profitable when total return from cum-close to ex-close
including the dividend exceeds zero net of costs. Three sources:

        (a) Partial price recovery during the ex-date session.
        (b) Less-than-full overnight drop.
        (c) Market-maker inventory effects on low-liquidity names.

In 2020-2024, force (b) may have strengthened: the retail dividend-
appetite segment expanded (main street retail investors, not just
institutions), and intraday recovery post-ex-open became more common
(retail buying the "dip"). This is the "behavioral" mechanism by which
dividend capture empirically survived in the recent sample.

Alternative mechanism: our data uses auto_adjust=False; the yfinance
"Close" is the raw closing price (not back-adjusted for the dividend).
Combined with the manual dividend addition this is correct — but if
yfinance returns back-adjusted prices in some code path, the return
formula double-counts the dividend. This is a **known risk of the
measurement**, discussed in Section 7.

### 2.4 Why the trade often appears attractive on paper

Backtest simplifications that inflate measured return:

        - Ignoring overnight gap risk.
        - Assuming raw prices when the source is adjusted (double-counts
          dividend).
        - No adjustment for hold-through-overnight gap volatility.
        - Ignoring wash-sale complication.

Each simplification can inflate measured return by 20-100 bps per trade.
If the true edge is +0.10-0.20% net, one simplification error at 20-80 bps
turns "unprofitable" into "profitable" and vice versa.

## 3. Tax Considerations

### 3.1 Qualified vs ordinary dividend rates

US-sourced dividends are "qualified" (preferential 15-20% rates) if the
shareholder held for >60 days during the 121-day window around ex-date.
High-yield dividend capture holds ~2 days, so the dividend is NOT
qualified — ordinary rates up to 37%.

For a high-tax US fund: gross +0.86% becomes +0.63% * 0.86% ≈ +0.54%
after-tax at ordinary rates. If qualified treatment could be engineered
(60+ day hold), +0.86% becomes +0.69% after-tax. Short-term hold costs
~15 bps of return.

### 3.2 Holding-period rule

The 60-day rule is calendar hold per position, and re-entry inside 60
days aggregates holdings. This makes "capture every dividend" incompatible
with qualified treatment unless the fund effectively holds long enough to
cross 60 days.

### 3.3 Wash-sale and straddle rules

Loss-realization turns wash-sale rules into deferrals. Straddle rules
eliminate qualified status if hedged. Implication: for a fully-qualified
tax-advantaged strategy, do NOT hedge, accept full long exposure between
cum-close and ex-close.

### 3.4 Implication for the prescreen

Prescreen measures gross returns. Post-tax economics: gross +0.86% →
~+0.54% after-tax at 37% ordinary rate. Against 10 bps cost, that is
+0.44% net after-tax. This remains well above the +0.30% "worth
attention" live threshold.

## 4. Academic Evidence

### 4.1 Early evidence (pre-2000)

Elton-Gruber 1970 (tax-clientele model), Kalay 1982, Eades-Linn-McConnell
1984 — ex-day drop fraction ~0.90-1.00x. Net-of-cost return approximately
zero. No standalone edge.

### 4.2 Modern evidence (post-2000)

Blume-Stambaugh 1984 (updated by Hartzmark-Solomon 2013): raw ex-day
return near zero for large caps; after costs, -1% to -3% annualized in
liquid large caps. Only in illiquid small caps (spread >20 bps) documented
any positive post-cost, not persistently.

### 4.3 Commercial dividend-capture funds

"Dividend capture" as a fund strategy peaked ~$500M AUM in the US
1980s-1990s, and disappeared by 2005. Survivors had options overlay
(writing calls against cum-div positions), not pure capture.

### 4.4 Why this is relevant here

The prescreen tests the exact trade that the literature says does not
work. Measured result is **positive** — see Section 6. The gap between
literature and our measurement must be explained before any capital is
committed (Section 7 examines three explanations: (i) yfinance data
artifact, (ii) retail regime shift, (iii) sample selection).

## 5. Sample Design

### 5.1 Universe

12 high-yield US names: T, VZ, MO, PM, XOM, CVX, IBM, KO, PFE, MMM, O,
MAIN. Selected for:

        - Historic dividend yield >= 3% (except KO/PFE/MMM at 2-3%).
        - Continuous dividend history 2020-2024.
        - Retail-heavy share register (potentially more elastic drop).

### 5.2 Window

For each ticker, last 15 dividends with ex-date >= 2020-01-01. 12 * 15 =
180 events.

### 5.3 Entry

Buy at cum-close — hist.index < ex_date, take last.

### 5.4 Exit

Sell at ex-close — hist.index >= ex_date, take first.

### 5.5 Return formula

total_ret_pct = (ex_close + div_amt - cum_close) / cum_close * 100

Requires raw (non-adjusted) closing prices. yfinance called with
auto_adjust=False — correct. If yfinance back-adjusts Close for dividends
in any code path (not the current one), the formula double-counts.

### 5.6 Cost modelling

Reported at 5/10/15/20 bps round-trip. Realistic:
- Institutional equity commission: 2-5 bps one-way = 4-10 bps RT.
- Bid-ask spread on liquid names: 1-3 bps one-way = 2-6 bps RT.
- Slippage: 1-5 bps.
- Realistic total: 6-15 bps. 10 bps is central.

## 6. Measured Results

**180 trade-events collected** across 12 tickers (2020-2024). Source:
yfinance, auto_adjust=False.

| Metric | Value |
|---|---|
| n trades | 180 |
| mean return | +0.9615% |
| median return | +0.8944% |
| std return | 1.5085% |
| hit rate (>0) | 72.8% |
| mean net, 5 bps | +0.9115% |
| mean net, 10 bps | **+0.8615%** |
| mean net, 15 bps | +0.8115% |
| mean net, 20 bps | +0.7615% |

### Per-ticker mean return (gross)

| Ticker | mean |
|---|---|
| CVX | +0.955% |
| IBM | +0.842% |
| KO | +0.527% |
| MAIN | -0.103% |
| MMM | +0.669% |
| MO | +2.196% |
| O | +0.341% |
| PFE | +1.589% |
| PM | +1.177% |
| T | +1.028% |
| VZ | +1.806% |
| XOM | +0.511% |

### Observations

11 of 12 tickers positive. Only MAIN (BDC, MAIN Street Capital) negative
at -0.10%. Highest gross: MO (Altria, +2.20%), VZ (+1.81%), PFE (+1.59%),
PM (+1.18%), T (+1.03%). These are consistent with high-yield legacy
dividend names where the dividend is a large fraction of price — small
under-drop in % terms produces large gross capture %.

**Hit rate 72.8%** across 180 events is unusually high for a positive-
expectation trade. This is either (a) genuine regime, (b) measurement
bias, or (c) sample selection (the 12 names are known for stable dividends
and retail appeal).

### Verdict

**POSITIVE** at prescreen — mean_net at 10 bps = **+0.86%**, hit 72.8%.
The threshold (+0.30%) is exceeded by a wide margin. This **contradicts
the academic prior** and requires diagnosis before any pilot commitment.

## 7. Reconciling measurement with prior literature

The +0.86% net is too large for a "survived edge" interpretation without
accounting for measurement artifacts. Three hypotheses:

### 7.1 Data artifact (highest prior probability)

yfinance `history(auto_adjust=False)` returns **raw** closing prices —
confirmed by documentation. However, at least one yfinance version has
been reported (Github issues, 2022-2023) to return adjusted closes for
large historical windows without a warning, depending on caching. If
`ex_close` is back-adjusted for the dividend, then the formula
`(ex_close + div - cum_close)` double-counts and inflates by ~1 div
amount per trade. MO's dividend is ~$1.00 on ~$45 stock = 2.2%; VZ's is
~$0.65 on ~$36 = 1.8%. If double-counted, raw measured mean would drop
by 1.0-2.0 pp per trade.

**Action required**: cross-check 5 random trades against a raw-price
source (nasdaq.com daily close, or stooq.com) before deploying anything.

### 7.2 Retail-regime mechanism (medium prior)

Retail investors increasingly buy dividend names on ex-dates ("capture
the yield"). This would explain MO, VZ, PFE, PM, T outperformance — all
retail-heavy. Institutional-only names (IBM, CVX, XOM) show smaller
+0.5-1.0% gross.

If this mechanism is real, edge is (a) capacity-limited by retail flow
depth, (b) regime-dependent (dies in a retail-outflow year), (c) already
partly priced into the "high-yield" names (higher going-in valuations).

**Action required**: run same test on 2015-2019 sample. If gross mean
drops to +0.2-0.4% in earlier sample, this is retail regime, not
survived edge.

### 7.3 Sample selection (low prior)

The 12 names were chosen for high yield, which correlates with high
dividend/price ratio. If the under-drop scales with dividend/price ratio,
high-yield names amplify the measurement. A random or sector-neutral
universe would give lower mean.

**Action required**: run on 50-100 random names (Russell 1000 subset) to
see if effect dissipates.

## 8. Recommendation

**Do not deploy yet; run diagnostics first.**

The measured +0.86% net is real for this sample but is likely inflated
by at least one of (7.1), (7.2), (7.3). The correct next step is not
"pilot backtest" but "measurement validation":

        1. Cross-verify 5 random trades against nasdaq.com raw close
           (30 minutes of work).
        2. Rerun on 2015-2019 (retail-regime control).
        3. Rerun on 50-random-Russell-1000 names (sample selection control).

All three fit in 1-2 days of work. Only if all three pass — mean stays
above +0.30% net after measurement and sample controls — proceed to
pilot.

## 9. Kill Criteria

At prescreen (satisfied): mean_net_10bps = +0.86% > +0.30% threshold.
**Prescreen passes**.

Kill criteria for the *diagnostic* stage that follows:

        1. Any 5-trade raw-close cross-check shows |yfinance - raw| > 0.01
           → data artifact confirmed → close.
        2. Rerun 2015-2019 shows mean_net_10bps < +0.10% → regime-
           dependent, not durable → close.
        3. Rerun 50-random names shows mean_net_10bps < +0.20% →
           sample-selection artifact → close.

Only if all three pass do we proceed to pilot backtest.

## 10. Further Work (contingent on diagnostic pass)

If diagnostics pass:

        - Extend to 10-year sample, 30-50 high-yield names.
        - Add REITs (O, MAIN, STAG, VTR, SPG) and BDCs (ARCC, TSLX,
          HTGC) — high-yield, retail-heavy.
        - Model overnight gap as risk (buy cum-close, sleep, sell ex-open
          next morning — the real trade, not same-session).
        - Cross-verify prices from nasdaq.com for all 500+ trades.
        - Sector-matched hedge to isolate dividend-capture residual from
          sector beta.

If diagnostics fail:

        - Close the category.
        - Log measured +0.86% + diagnosis in the strategy registry
          alongside funding carry, PEAD, GFC FX carry, spin-off.

### Data sources for extension

        - `nasdaq.com/market-activity/dividends`: official ex-date and
          dividend history per ticker — **must-have** for cross-check
          of raw prices.
        - `stooq.com`: free daily bars, raw closes.
        - `yfinance`: convenient but need to verify auto_adjust semantics.
        - `stocksplithistory.com`: for split-drift extension.
