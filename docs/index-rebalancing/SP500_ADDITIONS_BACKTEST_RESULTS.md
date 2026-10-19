# S&P 500 Additions — Phase 1 Empirical Backtest Results

**Date:** 2026-10-06
**Branch:** `sp500-additions-backtest`
**Base:** `2f80865` (deep dive + data plan)
**Status:** Phase 1 complete — empirical verdict rendered

---

## 1. Summary

Phase 1 tests whether buying S&P 500 additions before the effective date,
benchmarked against SPY and net of costs, produces a tradable excess return.
This is the last open structural research hypothesis after the classical
academic factors were closed with numbers (funding carry Sharpe 0.17/20y,
PEAD 0.70 -> 0.30 -> -1.15, FX carry 0.165/20y, spin-off median -2.38%,
dividend capture -0.35%, split drift -4.43%).

Using 189 S&P 500 additions with effective dates from 2015-01 through 2026
(Wikipedia "List of S&P 500 companies"), of which **155 were usable** after
data and window filters:

| Metric | Value |
|--------|-------|
| n_usable | 155 |
| mean net excess (20 bps) | +0.958% |
| median net excess (20 bps) | +0.157% |
| stdev | 6.059% |
| t_stat | +1.968 |
| CI_95 | [+0.004%, +1.912%] |
| hit_rate | 51.0% |

Headline mean is positive but the **median is near zero** and **hit rate is
a coin flip**. The result is statistically indistinguishable from noise once
survivorship bias and multiple-testing are considered. Verdict: **MARGINAL /
non-significant in practice** — see Section 7.

---

## 2. Method

### 2.1 Data source
- Universe: additions from Wikipedia "List of S&P 500 companies" table,
  column "Date added" >= 2015-01-01.
- Wikipedia width on fetch: 570,665 bytes; parsed with pandas.read_html.
- Survivorship caveat: Wikipedia lists only **current** constituents. Tickers
  added then later removed are absent. This biases the sample upward (see 7.1).

### 2.2 Timing proxy
The exact announcement date is not in the Wikipedia table — only the
**effective date** is. We build an entry proxy:

- effective_date = Date added
- entry_date = first trading close with index >= (effective_date - 7 calendar days)
- exit_date  = first trading close with index >= effective_date

The -7 calendar day entry proxes the pre-announcement / announcement-window
drift that the academic literature attributes to forced index buying. Holding
period is therefore typically 6-7 calendar days (~5 trading days).

### 2.3 Prices
- Prices: yfinance, auto_adjust=True (split + dividend adjusted), batch
  download with group_by='ticker'.
- Stock window: 2014-06-01 to 2025-06-01.
- Benchmark: SPY, same adjustment, window aligned to 2025-06-01 so late
  additions are not benchmarked against a stale SPY endpoint.
- Ticker normalization: BRK.B -> BRK-B for yfinance compatibility.

### 2.4 Return computation
For each event:

    car_stock = (p_exit - p_entry) / p_entry * 100
    car_spy   = (spy_exit - spy_entry) / spy_entry * 100
    net_excess = car_stock - car_spy - 0.20   # 20 bps round-trip cost

Costs: 20 bps default (10 bps per side), sensitivity to 10/30 bps in 5.

### 2.5 Aggregate statistics
- mean, median, stdev (ddof=1)
- se = stdev / sqrt(n)
- t_stat = mean / se
- CI_95 = mean +/- 1.96 * se
- hit = (# net_excess > 0) / n * 100
- by_year grouping on effective year, shown when n >= 3

---

## 3. Sample

| Item | Count |
|------|-------|
| n_extracted (Wikipedia >= 2015) | 189 |
| n_usable (passed all filters) | 155 |
| n_skipped | 34 |

Skip reasons (aggregate, 34 total):
- 4 failed bulk download (HONA, Q, VYLR, FDXF) — yfinance had no price data
  in the 2014-06..2025-06 window for these recent/2025-2026 additions.
- Remainder: insufficient history (< 5 closes), empty entry/exit window,
  entry_date >= exit_date, or price outside [1.0, 5000] sanity range.

Additions by effective year (raw, before filters):

| Year | Count |
|------|-------|
| 2015 | 14 |
| 2016 | 21 |
| 2017 | 22 |
| 2018 | 13 |
| 2019 | 20 |
| 2020 | 10 |
| 2021 | 10 |
| 2022 | 14 |
| 2023 | 14 |
| 2024 | 16 |
| 2025 | 17 |
| 2026 | 18 |

Usable events by effective year (post-filter):

| Year | n | mean net | median net | hit |
|------|---|----------|------------|-----|
| 2015 | 13 | +0.544% | -0.768% | 46% |
| 2016 | 19 | -0.554% | -0.554% | 37% |
| 2017 | 22 | -0.333% | -0.544% | 45% |
| 2018 | 13 | -2.336% | -4.193% | 15% |
| 2019 | 20 | +2.867% | +1.874% | 60% |
| 2020 | 10 | +2.187% | +0.718% | 60% |
| 2021 | 10 | +3.014% | +0.524% | 60% |
| 2022 | 14 | +2.629% | +1.752% | 71% |
| 2023 | 13 | +1.721% | +2.186% | 69% |
| 2024 | 16 | -0.478% | -0.892% | 44% |
| 2025 |  5 | +5.743% | +3.077% | 80% |

2026 additions exist on Wikipedia but have no price data in the window yet
(hence entering the skip bucket). 2025 has only 5 usable because the price
window ends 2025-06-01.

---

## 4. Aggregate metrics

| Metric | Value |
|--------|-------|
| n_usable | 155 |
| mean net excess | +0.958% |
| median net excess | +0.157% |
| stdev | 6.059% |
| standard error | 0.487% |
| t_stat | +1.968 |
| CI_95 | [+0.004%, +1.912%] |
| hit_rate | 51.0% |

Interpretation:
- The 95% CI lower bound is +0.004% — it clears zero by a hair. This is a
  borderline result, not a robust effect.
- The median (+0.157%) is 6x smaller than the mean (+0.958%). The mean is
  driven by right-tail outliers (MRNA, COIN, etc. in 6), while the typical
  event returns ~0.
- hit_rate 51.0% means the sign of the net excess is essentially random.

---

## 5. Cost sensitivity

Raw excess mean (before cost) = +1.158%. Net after bps deduction:

| Round-trip cost | mean net excess |
|-----------------|-----------------|
| 10 bps | +1.058% |
| 20 bps | +0.958% |
| 30 bps | +0.858% |

The t-stat (1.968) is computed at 20 bps. At 10 bps it would be marginally
higher (~1.99) and at 30 bps marginally lower (~1.95); none of these crosses
a robust significance horizon. The effect is cost-insensitive in the 10-30
bps range because the spread of daily returns (6.06% stdev) dwarfs costs.
Costs are not the reason this fails — the noise floor is.

---

## 6. Tail events

### Top 5 net excess

| Ticker | Effective | Hold days | Net | Stock | SPY |
|--------|-----------|-----------|-----|-------|-----|
| MRNA | 2021-07-21 | 7 | +30.37% | +30.2% | -0.4% |
| COIN | 2025-05-19 | 7 | +25.16% | +27.4% | +2.0% |
| DD | 2019-06-03 | 6 | +18.65% | +16.9% | -2.0% |
| CARR | 2020-04-03 | 7 | +18.15% | +16.3% | -2.1% |
| CEG | 2022-02-02 | 7 | +16.92% | +22.6% | +5.5% |

### Worst 5 net excess

| Ticker | Effective | Hold days | Net | Stock | SPY |
|--------|-----------|-----------|-----|-------|-----|
| SOLV | 2024-04-01 | 6 | -14.47% | -13.6% | +0.7% |
| HPE | 2015-11-02 | 7 | -13.59% | -11.8% | +1.6% |
| ON | 2022-06-21 | 7 | -9.25% | -8.3% | +0.8% |
| SMCI | 2024-03-18 | 7 | -8.18% | -7.4% | +0.6% |
| FTNT | 2018-10-11 | 7 | -7.86% | -13.6% | -6.0% |

Note: several top events are **spin-off / carve-out listings** rather than
classic index-announcement additions (DD = DuPont post spin, CARR = Carrier
spin from UTX, CEG = Constellation spin from Exelon). These enter the index
through a spin-off path and their return is dominated by spin-off dynamics,
not forced index buying. This contaminates the "pure additions" reading (see
7.4). Excluding spin-off-type additions would likely pull the mean down and
push the result toward NEGATIVE.

---

## 7. VERDICT: MARGINAL (non-significant in practice)

By the pre-registered rule:

    POSITIVE  if mean > 1.5 and t > 1.96 and hit > 55
    MARGINAL  if mean > 0 and t > 1.0
    else NEGATIVE

Here mean = +0.958 (fails the 1.5 bar), t = +1.968 (passes the >1.96 bar by
0.008), hit = 51.0 (fails the 55 bar). Rule output: **MARGINAL**.

But the honest read is that this is **a statistical null dressed as a
positive mean**:

1. **t=1.968 does not survive multiple testing.** This program has now run
   ~7 independent factor tests (funding carry, PEAD, FX carry, spin-off,
   dividend capture, split drift, S&P additions). At Bonferroni alpha for
   7 tests, the required t is ~2.7. 1.968 fails hard.
2. **hit_rate 51%** — the effect has no directional edge on the typical trade.
3. **median +0.16%** — the typical addition nets approximately zero; the mean
   is carried entirely by a handful of right-tail outliers, several of which
   are spin-offs (not index-announcement additions).
4. **Survivorship bias inflates every number above.** Wikipedia only has
   current constituents. Names that were added and later *removed* (the sub-
   set most likely to include the losers — acquisitions, declines, index
   deletions) are simply absent. The true population mean is therefore
   **lower than +0.958%**, plausibly at or below zero.

VERDICT: **MARGINAL on the rule, but honestly closer to NEGATIVE.** Not
tradable, not statistically robust.

---

## 8. Recommendation

**Close the research. Do not proceed to forward paper trading.**

Rationale:
- The observed mean cannot be separated from noise (51% hit, median ~0,
  t < multiple-testing threshold, survivorship inflates it).
- Building a live scraper + forward-monitoring pipeline to chase a +0.16%
  median with 6% daily dispersion is unjustifiable allocation of effort.
- Unlike the classical factors, this hypothesis does have a real academic
  prior (Harris & Gurel, Shleifer) — the pre-2010 premium was real. The
  post-2015 sample here shows it has decayed / been arbitraged away, which is
  itself the useful finding: the anomaly is dead in the modern regime.
- The data-exclusivity angle in SP500_DATA_ACQUISITION_PLAN.md (CRSP / delisted
  universe) is the only path that could *rescue* a definitive result, but the
  observed effect is far too weak to justify that spend. All-in data purchase
  is not warranted for a null.

One caveat if revisited: a decisive test would need (a) the full delisted
additions universe (CRSP-style), (b) true announcement dates, (c) intraday
entry, and (d) spin-off-type additions excluded. Absent (a), no sample we
build here can overturn a null that is already this weak.

---

## 9. Known limitations

### 9.1 Survivorship bias (primary)
Wikipedia contains only *current* S&P 500 members. Additions subsequently
removed are missing. Removed names skew negative (delisting / underperformance).
The measured +0.958% is therefore an **upper bound**; the population mean is
lower.

### 9.2 Effective vs announcement timing
Entry is a -7 calendar day proxy for the announcement. Actual announcement
dates vary (typically 1-2 weeks before effective for S&P DJI). Some drift
captured may be pre-announcement, some may be post-announcement leak. There is
no per-event announcement timestamp in the source.

### 9.3 No intraday / no auction modeling
Only daily closes are used. Real index rebalancing volume concentrates at the
effective-date close (MOC imbalance). Capturing that requires intraday data,
not modeled here.

### 9.4 Spin-off contamination
A subset of "additions" are spin-off/carve-out listings (DD, CARR, CEG, etc.)
entering the index via their parent. Their returns reflect spin-off dynamics
(known median ~-2.38% per earlier work), not classic forced index buying. No
clean separation applied in this Phase 1.

### 9.5 Sample window and coverage
yfinance coverage limits (HONA, Q, VYLR, FDXF missing; 2026 additions lack
data in window) trim the tail of the sample. Effect is small but reduces
n and skews toward mid-decade events.

### 9.6 No swap / hedge-eco  modeling
This is a long-stock / short-SPY excess-return backtest. A production trade
would face borrow costs, short-SPY financing, and slippage on both legs;
none modeled here. These biases are all *favorable* to the strategy in this
backtest (no net effect on verdict, only reinforcing the null).

---

## 10. Artifacts

- Results CSV: `/tmp/sp500_results.csv` (155 rows, per-event columns)
- Backtest script: `/tmp/sp500_backtest.py`
- Additions input: `/tmp/additions.csv` (189 rows)
- Raw source: `/tmp/sp500.html` (570,665 bytes)

---

## 11. Program status after Phase 1

All structural research hypotheses now have empirical numbers. Summary of
factor program outcomes:

| Factor | Result | Verdict |
|--------|--------|---------|
| Funding carry | Sharpe 0.17 / 20y | closed |
| PEAD | 0.70 -> 0.30 -> -1.15 | closed |
| FX carry | Sharpe 0.165 / 20y | closed |
| Spin-off | median -2.38% | closed |
| Dividend capture | -0.35% | closed |
| Split drift | -4.43% | closed |
| **S&P additions** | **mean +0.96%, median +0.16%, t 1.97, hit 51%** | **MARGINAL -> close** |

The consistent pattern across the program: naive academic anomalies have
decayed post-2010 in liquid US equity / FX. This Phase 1 confirms S&P
additions are no exception — the historical premium is arbitraged away.

