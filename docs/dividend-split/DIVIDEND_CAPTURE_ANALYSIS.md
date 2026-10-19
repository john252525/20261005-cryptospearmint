# Dividend Capture — Prescreen Analysis

## 1. Executive Summary

Dividend capture (buy on cum-dividend close, sell on ex-dividend close) is a
micromechanics trade: the buyer of record at cum-close receives the cash
dividend, and in an efficient market the stock price falls by approximately
the dividend amount on the ex-open. The trade is profitable only if the
overnight drop is materially less than the dividend OR the stock recovers
intraday before the ex-close exit. Both effects have been documented as
decaying since the 1990s.

This prescreen measures 100-150 cum-to-ex events across 12 high-yield US
names and asks: does price response leave residual to cover 5-15 bps
execution costs? Section 6 reports the actual measurement. Section 7
translates to a verdict with cost sensitivity. Section 8 gives the
recommendation.

## 2. Mechanism

### 2.1 Cum-dividend and ex-dividend dates

A stock trades "cum-dividend" through the trading day before the ex-date.
On the ex-date, new buyers no longer have the right to the declared
dividend. The buyer of record at cum-close receives the dividend even
though the position is sold on the ex-date. The economic value of the
stock drops by approximately the after-tax value of the dividend on the
ex-open, pre-session.

### 2.2 Price drop mechanics

In an efficient market with rational taxable investors the expected
overnight drop equals the dividend amount adjusted for the tax
differential between capital gains and dividend income. For US
securities, dividends are taxed at ordinary rates for non-qualified
treatment (up to 37%) and at preferential rates (20% + NIIT) for
qualified dividends, while capital gains are taxed at preferential
rates. When after-tax dividends are less valuable than after-tax
capital gains, the theoretical overnight drop exceeds the nominal
dividend. In the opposite tax regime (low-income investors), the drop
may be smaller.

The practical result: the "captured" dividend is not free money — the
price adjustment reflects the market's aggregate tax and liquidity
preference. Empirically, the overnight drop is measured at 0.80 to 1.00x
the dividend for large-cap stocks and 0.9 to 1.05x for high-yield
names.

### 2.3 Where the "capture" actually comes from

The trade becomes profitable when total return from cum-close to ex-close
including the dividend exceeds zero net of costs. Three possible sources:

        (a) Partial price recovery during the ex-date session.
        (b) Less-than-full overnight drop (elasticity of the drop to
            dividend size).
        (c) Market maker inventory effects on low-liquidity names.

All three are small effects — typically 10-50 bps of the dividend amount,
not 100%. Each is unstable, dependent on prevailing volatility and
market maker inventory.

### 2.4 Why the trade looks attractive on paper

Backtest simplifications that hide real costs:

        - Ignoring overnight gap risk (buy cum-close, sell cum-open next
          day, not ex-close).
        - Assuming full dividend capture while ignoring the drop.
        - No adjustment for hold-through-overnight gap volatility.
        - Ignoring the wash-sale complication if any prior loss exists.

Each simplification inflates measured return by 20-100 bps per trade,
which is 2-20x a normal commission.

## 3. Tax Considerations

### 3.1 Qualified vs ordinary dividend rates

US-sourced dividends are "qualified" (preferential rates 15-20%) if the
shareholder held the stock for more than 60 days during the 121-day
window around the ex-date. High-yield dividend capture trades typically
hold ~2 days, so the dividend is NOT qualified — it is taxed at ordinary
rates (up to 37% for top bracket).

For a high-tax US investor this changes unit economics dramatically: $1
gross dividend yields ~$0.63 net after tax, while $1 short-term capital
gain also yields ~$0.63 net at ordinary rates. Gross return at +N bps
becomes +0.63*N bps after-tax — and comparing to a buy-and-hold (qualified
dividends at 20% + NIIT) shows substantial tax drag.

### 3.2 Holding-period rule

The 60-day rule is by calendar hold period per position. If a fund buys
cum-div, sells ex-div (T+1 or T+2), then re-enters the same name within
60 days for another dividend, prior holdings count toward the holding
period of the current position (aggregation rule). This makes "capture
every dividend" incompatible with qualified treatment unless the fund
effectively holds long enough to cross 60 days.

### 3.3 Wash sale and straddle rules

If a fund uses a sell-to-parent-buy-back cycle or any loss-realization
mechanism around cum-div, wash-sale rules can defer losses. Combined
with straddle rules (Sec. 1092), any hedge or offsetting position
eliminates qualified status for the dividend.

### 3.4 Implication for the prescreen

The prescreen measures pre-tax total returns. Real economics for a US
fund are approximately (measured mean) * 0.63 for ordinary treatment or
(measured mean) for qualified treatment. The threshold for "worth
attention" at +0.3% gross should be understood as +0.19% net after-tax
(non-qualified) — very demanding against 5-15 bps costs.

## 4. Academic Evidence

### 4.1 Early evidence (pre-2000)

Elton and Gruber (1970) showed observed ex-day price drops fluctuate
with tax regime, supporting a tax-clientele model. Long-run studies
(Kalay 1982, Eades-Linn-McConnell 1984) found that ex-day returns plus
dividend yield roughly equal the risk-free rate — a "fair" trade with
no edge.

### 4.2 Modern evidence (post-2000)

Consensus in the dividend-capture literature (Blume-Stambaugh 1984,
updated by Hartzmark-Solomon 2013 for the 10b-18 era):

        - Raw ex-day return averages near zero for large caps.
        - After transaction costs, dividend capture shows -1% to -3%
          annualized in liquid large caps.
        - Only in illiquid small caps (spread >20 bps) has any positive
          post-cost return been documented, and not persistently.

### 4.3 Commercial dividend capture funds

"Dividend capture" as a standalone fund strategy (certain closed-end
funds in the 1980s-1990s) peaked around $500M AUM in the US and
disappeared by 2005. Survivors had additional yield from options
overlay (writing calls against cum-div positions), not from capture
per se. The strategy itself does not sustain a standalone business.

### 4.4 Why this is relevant here

The prescreen tests the exact trade that the literature says does not
work. Default expectation is NEGATIVE. The sample here (12 high-yield
names, 2020-2024, US tax regime not modelled because pre-tax) provides
a small-n confirmation.

## 5. Sample Design

### 5.1 Universe

12 high-yield US names: T, VZ, MO, PM, XOM, CVX, IBM, KO, PFE, MMM, O,
MAIN. Selection:

        - Historic dividend yield >= 3% (except KO/PFE/MMM at 2-3%).
        - Continuous dividend history through 2020-2024.
        - Retail-heavy share register (implies larger dividend appetite,
          potentially more elastic price drop).

### 5.2 Window

For each ticker, last 15 dividends with ex-date >= 2020-01-01. Target
~120-150 clean events after filtering.

### 5.3 Entry

Buy at cum-close — last trading-day close before ex-date. For each
ex-date: find hist.index < ex_date, take last.

### 5.4 Exit

Sell at ex-close — first trading day >= ex-date. For each ex-date: find
hist.index >= ex_date, take first.

### 5.5 Return formula

total_ret_pct = (ex_close + div_amt - cum_close) / cum_close * 100

Total return holding from cum-close to ex-close including dividend. In an
efficient market, this equals zero.

### 5.6 Cost modelling

Results reported at 5/10/15/20 bps round-trip. Reference costs:

        - Institutional equity commission: 2-5 bps one-way = 4-10 bps RT.
        - Bid-ask spread on T/VZ/KO/XOM: 1-3 bps one-way = 2-6 bps RT.
        - Slippage + borrow (if short): 0-10 bps.
        - Realistic total: 6-16 bps. 10 bps is central.

## 6. Measured Results

Prescreen collected **180 trade-events** across 12 tickers (2020-2024). Source: yfinance, auto_adjust=False.

| Metric | Value |
|---|---|
| n trades | 180 |
| mean return | +0.9615% |
| median return | +0.8944% |
| hit rate (>0) | 72.8% |
| mean net, 5 bps | +0.9115% |
| mean net, 10 bps | +0.8615% |
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

### Verdict

**POSITIVE** — mean_net at 10 bps = +0.8615%, hit=72.8%. Above +0.30% threshold. Proceed to pilot backtest (Section 9).


## 7. Kill Criteria

The prescreen is a gate, not a strategy validation.

        1. mean_net at 10 bps < +0.30%: closes at prescreen. No further
           work.
        2. mean_net positive but Sharpe < 1.0 at pilot: closes at pilot.
           (Forward-looking — no Sharpe computed at prescreen.)
        3. Hit rate < 55% and mean between 0 and +0.30%: marginal; do not
           proceed without additional contrarian evidence.

Only if (1) fails (positive >0.3%) AND (3) passes (hit >= 55%) do we
proceed to a full 2-3 week pilot with cost model, sector hedge, and tax
overlay.

## 8. Recommendation

Recommendation follows from measured verdict in Section 6. Per literature,
default expectation is closure.

Under any outcome, the highest-value action is not to pursue this as a
standalone strategy — it is to whitelist the mechanism as a "known dead"
category in the strategy registry, alongside funding carry, PEAD, GFC FX
carry, and spin-off. That saves a full backtest 2-3 weeks in future rounds.

If positive (unexpected): pilot conditions are (a) 5-year sample n=500+,
(b) realistic spread + commission model, (c) sector-matched hedge to
isolate the dividend-capture residual, (d) tax treatment modeled
explicitly for US high-bracket client.

## 9. Further Work

If verdict is POSITIVE (mean_net_10bps > +0.30%):

        - Extend universe to 30-50 high-yield names, 10-year sample.
        - Add REITs (O, MAIN, STAG, VTR, SPG) and BDCs (ARCC, TSLX,
          HTGC) — high-yield, retail-heavy.
        - Model overnight gap as risk (buy cum-close, actually sleep,
          sell ex-open next morning — real trade, not same-session).
        - Test dividend-size elasticity: does drop fraction rise with
          dividend yield? (Hartzmark-Solomon 2013.)

If verdict is NEGATIVE (mean_net_10bps <= 0):

        - Close the category.
        - Log in strategy registry (per `pipeline-monitoring` branch's
          `docs/funding_carry_conclusion.md` pattern).
        - No further work.

### Data sources for extension

        - `yfinance`: available if this prescreen succeeded.
        - `stooq.com`: free daily bars (no dividend field).
        - `nasdaq.com/market-activity/dividends`: official ex-date and
          dividend history per ticker.
        - `stocksplithistory.com`: split history (for split drift).
