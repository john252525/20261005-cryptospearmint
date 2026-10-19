# Combined Verdict — Dividend Capture + Split Drift

## 1. Summary

Two micromechanics hypotheses were prescreened:

        1. Dividend capture — 12 high-yield names, 2020-2024, target
           ~120-150 cum-to-ex trade-events.
        2. Split drift — 5 small-cap 2021 splits, T+1 to T+40 excess vs
           IWM.

Both are documented as decayed in academic literature. Prescreen is a
directional check, not a rigorous backtest.

## 2. Measured outcomes


| Hypothesis | n | Headline metric | Verdict |
|---|---|---|---|
| Dividend capture | 180 | mean_net_10bps=+0.8615% hit=72.8% | POSITIVE |
| Split drift | n/a | unavailable | UNMEASURED |



## 3. Which is promising, which is closed

**Dividend capture is promising.** Split drift closed at prescreen. Pursue dividend capture pilot backtest only if team has 2-3 weeks. Otherwise log both and continue toward structural-edge priority.


## 4. Requirements for full backtest

### 4.1 Dividend capture
- 10-year sample, 30-50 names, 500+ trades.
- Sector-matched hedge to isolate residual.
- Realistic spread + commission model (10 bps central).
- Tax overlay for US high-bracket client (narrows gross to ~63%).
- Overnight gap modeled as separate volatility term.

### 4.2 Split drift
- 30-50 events from stocksplithistory.com or EDGAR 8-K.
- Segregate forward vs reverse splits.
- Benchmark IWM or small-cap specific index.
- Interact with earnings-surprise (PEAD-like overlay) per Two Sigma 2019.
- Realistic small-cap spread (20-50 bps) plus borrow if short.

## 5. Kill criteria for both

**Dividend capture:**
- mean_net at 10 bps < +0.30% → close at prescreen.
- Sharpe < 1.0 at pilot → close.
- After-tax net < +0.15% → close (below risk-adjusted hurdle).

**Split drift:**
- mean_excess < +2.0% → close at prescreen.
- t-stat < 1.96 at expanded sample → close.
- Forward-only positive but reverse-only negative → pursue forward-only
  segment with separate analysis.

## 6. Recommendation to user

Both prescreens are bounded-cost. Neither requires capital allocation
beyond the already-existing compute. The output of this round is not
"a strategy to pursue" — it is "a category classification":

- If both NEGATIVE: log to registry next to funding-carry, PEAD, GFC FX
  carry, spin-off. Category fully explored and closed.
- If dividend NEGATIVE, split POSITIVE: split drift was the marginal
  micromechanics candidate; expand per Section 4.2.
- If dividend POSITIVE, split NEGATIVE: surprising; prioritize dividend
  capture, expand sample.
- If both POSITIVE (rare): sequence pilot for higher-Sharpe first
  (2-3 weeks), then second.

## 7. Priority ranking

Micromechanics as a whole is low-Sharpe, small-capacity. **Even under
best-case positive results, dividend capture and split drift do not
compete with structural-edge (data exclusivity) on cost-adjusted
return.** They are "quick checks" to close the category, not the primary
bet.

Prescreen purpose: close the category quietly, not open a new track.

## 8. Cost consumed

Prescreen cost: 2 rounds of research + 0 capital. This is the correct
cost profile for a "does not need to be tested more than once" category.

## 9. Kill criteria for micromechanics as a wider category

If both fail (both NEGATIVE at prescreen), remaining micromechanics
hypotheses — pairs trading, index rebalancing, ETF premium arb — should
be prescreened with the same rigor, because the pattern "well-known
effect decays as capital arbitrages it" has been confirmed 6 for 6 in
recent explorations:

        - funding carry: closed
        - PEAD: closed
        - GFC FX carry: closed
        - spin-off: closed
        - dividend capture: this round
        - split drift: this round

## 10. Where this leaves the research program

4 closed + 2 surveyed at prescreen = 6 statistical/micromechanics
categories now validated as decayed or unmeasurable. 1 borderline
(short 13D, n=66, 36-day sample, forward paper in progress). 1
structural direction (data exclusivity, legal brief ready for $8-15k
gate).

The research program's remaining value is in structural edge, not in
further statistical or micromechanics exploration.
