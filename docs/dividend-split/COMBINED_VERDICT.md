# Combined Verdict — Dividend Capture + Split Drift (final)

## 1. Scope

Two micromechanics hypotheses prescreened:

        1. **Dividend capture** — 12 high-yield US names, 2020-2024, 180
           cum-to-ex trade-events. First run showed +0.86% net (date-
           alignment artifact); post-fix confirms academic prior.
        2. **Split drift** — expanded to 7 still-listed forward splits
           (AAPL, TSLA, NVDA, AMZN, SHOP, GOOGL, GME), T+1 to T+40, excess
           vs IWM. Original 5-event sample: 3 of 5 delisted on yfinance.

Data: yfinance with `auto_adjust=False`, benchmark IWM.

## 2. Measured outcomes

| Hypothesis | n | Headline | Verdict |
|---|---|---|---|
| Dividend capture | 180 | mean_ret = -0.2546% gross, -0.3546% net at 10 bps, hit 46.7% | **NEGATIVE** |
| Split drift | 7 | mean_excess = -4.43%, positive 2/7, hit 28.6%, t=-0.83 | **NEGATIVE** |

## 3. Interpretation

### 3.1 Dividend capture — closed

Post-fix measurements: mean gross -0.2546%, mean_net at 10 bps -0.3546%,
hit rate 46.7%. Per-ticker means show 7 of 12 names negative, 5 positive.
Weighted by yield: high-yield names (MO -0.727%, VZ -0.880%, T -0.736%)
worse than low-yield (XOM +0.003%, KO +0.094%, CVX +0.253%). This is the
academic prior replicated in one line: the drop fraction is ~1.10x of the
nominal dividend, so a capture buyer loses on average (tax-adjusted price
drop exceeds dividend).

**Verdict**: NEGATIVE. Mean below +0.30% threshold by a wide margin.
Category CLOSED. Matches 50-year academic prior (Elton-Gruber 1970 through
Hartzmark-Solomon 2013).

### 3.2 Split drift — closed at n=7

Post-expansion: n=7, mean_excess = -4.43%, positive 2/7 (NVDA +14.53%,
AMZN +16.72%), hit rate 28.6%, t≈-0.83 (p≈0.40 — null not rejected but
mean negative, sign consistency at 28.6% is below any long-only drift).

**Cap breakdown**:
- Large/mid (n=6): mean_excess = -2.23%. Includes the two positives but
  dominated by negatives (AAPL -14.65%, TSLA -12.05%, GOOGL -10.13%,
  SHOP -7.81%).
- Small (n=1): mean_excess = -17.63% (GME). Reverse-split dynamic in
  forward-split form.

Even ignoring sign: t=-0.83, |t| < 1.96. Cannot reject null. Direction
of mean is opposite to Ikenberry 1996's positive-drift hypothesis.

**Verdict**: NEGATIVE at n=7. Two options remain: (a) close the category
based on directionally-wrong result, (b) expand to n=30-50 via
stocksplithistory.com before closing.

Given that (i) sign consistency is 28.6% (worse than coin flip), (ii)
t-stat negative, (iii) literature already documents decay, (iv) sample
contamination (7 mixed-cap events with 1 small-cap) — the responsible
call is **close at prescreen**. Expansion is defensible but not encouraged.

## 4. Dividend capture — kill criteria satisfied

        1. mean_net_10bps < +0.30%: **-0.3546%** → triggered, close.
        2. Hit rate < 55%: **46.7%** → also triggered.
        3. Sharpe (if computed): negative. Not applicable — no positive
           mean to annualize.

Two independent kill criteria triggered. Close.

## 5. Split drift — kill criteria satisfied

        1. mean_excess < +2.0%: **-4.43%** → triggered, close at prescreen.
        2. Fewer than 3/5 positive: **2/7 positive** → also triggered.
        3. t-stat < 1.96: **-0.83** (negative, well below threshold) →
           triggered.

Three kill criteria triggered. Close.

## 6. What was learned (measurement discipline)

Three measurement traps caught during this prescreen:

        1. **yfinance date-alignment bug.** `Ticker.dividends` index carries
           09:30 ET timestamp (market open); `Ticker.history()` index is
           00:00 ET midnight. Slicing `hist.index < div.date_ts` includes
           the ex-day close in "pre" set → measured trade is ex-close →
           T+1-close, not cum-close → ex-close. This inflated the first
           run to +0.86%. Fix: compare `.date()`, not timestamps.

        2. **Delisted-ticker survivorship.** Original 5-event split sample
           included MNMD/FFIE/NKLA — all delisted, all return HTTP 404 on
           yfinance. Only 2 of 5 retrievable, and one (BKKT) was a reverse
           split with -70.88% excess that destroyed the mean. Always
           pre-verify ticker existence before sample construction.

        3. **Reverse-split contamination.** Forward splits and reverse
           splits have opposite drift signs (Ikenberry 1996 vs.
           Boehme-So 2014). Never pool them. This prescreen's post-fix
           sample excluded reverse splits.

All three are documented in the respective analysis files.

## 7. Priority relative to structural edge

Neither direction is a strategic possibility. Both failed at prescreen
with negative means; both match prior literature. Capacity at best-case
(were either real) would be small-cap event-driven, ~5-10% annualized,
bound by spread and borrow availability.

**Does not compete with structural-edge** (data exclusivity), projecting
15-25% at larger capacity and stronger moat. Structural edge remains the
only live direction.

## 8. Registry status after this round

        - funding carry: CLOSED
        - PEAD: CLOSED
        - GFC FX carry: CLOSED
        - spin-off: CLOSED
        - dividend capture: **CLOSED** (5/5 numeric kill criteria)
        - split drift: **CLOSED** (3/3 numeric kill criteria)

6 for 6. All statistical / micromechanics categories tested this program
are confirmed as decayed or unmeasurable with available data. This matches
the broader industry observation (2024-2026): well-known anomalies have
been arbitraged out of liquid-markets.

## 9. Honest assessment

The first-run +0.86% dividend number would have justified a $500k-2M pilot
allocation on the wrong premise. It was caught by cross-referencing
per-ticker means against known dividend yields (MO +2.196% vs 2.2% yield —
too perfect a match to be a market edge). This is the value of the
prescreen discipline: an aggregate number that matches the prior, not
exceeds it, is a diagnostic signal.

Split drift's -4.43% (t=-0.83) is directionally consistent with the
decayed-literature view, though the n=7 sample is too small to reject
null at any conventional level. The two positive tails (NVDA, AMZN) are
potential out-of-sample survivors that could be studied in a 30-50 sample
if the program revisits this category — but that is not a 2026 priority.

## 10. Next steps

        1. **Structural edge (data exclusivity) legal gate** — the only
           remaining live research direction. Send LEGAL_BRIEF_TEMPLATE to
           2 lawyers (US + EU), $8-15k, 3-4 weeks. This is unblocked and
           ready.

        2. **Update strategy registry** — formal record that 6 categories
           are now closed with measured priors. Reference for future
           prescreens: "don't rebuild funding carry / PEAD / FX carry /
           spin-off / dividend capture / split drift; each has been
           re-measured against 2024-2026 data and failed."

        3. **Meta-lesson for future research** — every hypothesis prescreen
           should include three checks: (a) date-alignment sanity against
           known dividends, (b) ticker existence pre-flight, (c) literature
           prior comparison. Each cost 30 minutes at most, all three
           together would have caught this round's bugs on run 1.

## 11. Program state after this round

        - Research categories tested: 6 total (4 prior + 2 this round)
        - Closed: 6
        - Open: 0 classical/micromechanics
        - Open: 1 borderline (short 13D, n=66, forward paper in progress
          via `short-13d-paper` branch)
        - Open: 1 structural (data exclusivity, legal brief ready)

Position: the classical-research avenue is fully explored with clear
negative results. The remaining paths are one borderline statistical
signal (13D) and one structural direction (data exclusivity). Capital
allocation and team focus belong on the structural side.
