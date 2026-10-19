# Form 4 Insider Clustering Backtest, 2015-2024

Status: FINAL research hypothesis. Verdict NEGATIVE.
Owner: research / quantitative signals
Data: SEC bulk Form 3/4/5 datasets (`insider-transactions-data-sets`), 40 quarters 2015q1..2024q4
Benchmark: SPY total-return proxy (auto-adjusted closes), costs 30 bps round trip

## 1. Hypothesis

Insiders possess material non-public information by definition (Sec. 16 definition of
insider status, not an empirical claim). Classic academic evidence
(Lakonishok & Lee 2001; Jeng, Metrick & Zeckhauser 2003) reports +6-8% abnormal
returns over 6-12 months for aggregated insider *purchases*, with clustering
(2 or more distinct insiders buying the same issuer within 30 days) reported as
the strongest sub-signal.

Claim under test: an equal-weight basket of cluster events, entered after the last
purchase of the cluster, held 180 calendar days, delivers positive abnormal return
versus SPY net of realistic costs.

Rationale for expecting weaker decay than PEAD: Form 4 signal requires per-filing
parsing, cannot be extracted from a standard price/volume bulk feed, and is therefore
less crowded. This reasoning is explicitly falsifiable and is what this backtest tests.

## 2. Method

### 2.1 Data source and why it matters

The SEC daily-index crawl (`/Archives/edgar/daily-index/YYYY/QTRn/form.YYYYMMDD.idx`
plus one HTTP fetch per individual filing) was attempted first and abandoned, for two
measured reasons:

- Volume: a full quarter contains ~126,000 Form 4 filings (measured, 2024q1 = 126,077).
  The per-filing crawl needs one request each; SEC throttles to roughly 10 req/s and
  returns HTTP 429 aggressively. Sustained measured crawl throughput was 0.22-1.0
  filings/s before throttling. A full 2015-2024 crawl (~5M filings) is not feasible.
- Fragility: per-filing XML parsing is a regex job against many legacy variants, and
  any 429 window silently loses filings.

The SEC publishes pre-parsed quarterly bulk datasets that remove both problems.
Location (verified, HTTP 200 for every quarter used):

    https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{YYYY}q{Q}_form345.zip

Each ZIP contains tab-separated tables joined on `ACCESSION_NUMBER`:

| File | Role in this study |
|------|--------------------|
| SUBMISSION.tsv | filing metadata: DOCUMENT_TYPE, ISSUERCIK, ISSUERTRADINGSYMBOL, FILING_DATE |
| NONDERIV_TRANS.tsv | non-derivative transactions: TRANS_CODE, TRANS_DATE, TRANS_SHARES, TRANS_PRICEPRICEPERSHARE |
| REPORTINGOWNER.tsv | reporting owner identity: RPTOWNERCIK (insider dedup key) |
| DERIV_TRANS.tsv | derivative transactions -- NOT used (excluded by design) |
| FOOTNOTES.tsv, OWNER_SIGNATURE.tsv, *_HOLDING.tsv | not used |

Important consequence: `ISSUERTRADINGSYMBOL` is supplied by SEC, so the
CIK to ticker mapping is complete inside the dataset. No external mapping step
and no mapping loss.

### 2.2 Ingestion filters

    universe      ACCESSION_NUMBER with DOCUMENT_TYPE == '4'  (excludes '4/A', '3', '5')
    transaction   TRANS_CODE == 'P'  (open-market purchase only)
    excluded      'S' sale, 'A' grant/award, 'M' option exercise, 'F' tax withholding,
                  'D' disposition, 'G' gift, 'J' other, all derivative rows
    dedup         distinct RPTOWNERCIK per issuer

Raw counts across the full dataset (all 40 quarters, no filtering on transaction date):

| Metric | Count |
|--------|-------|
| SUBMISSION rows (forms 3, 4, 5, incl. amendments) | 2,047,468 |
| Form 4 filings (DOCUMENT_TYPE == '4') | 1,827,551 |
| P-code (open-market purchase) transaction rows | 478,669 |
| Distinct issuer CIKs with >=1 P transaction | 7,932 |
| Distinct reporting owner CIKs | 39,590 |

Note the row inflation: a single filing can contain several P rows, and each row is
expanded across its reporting owners, so P-rows exceed P-filings. This is intended --
the cluster test needs (issuer, owner, date) triples, not filing counts.

### 2.3 Cluster construction

Definition, applied per issuer CIK:

    sort all P transactions for the issuer by transaction_date
    slide a 30-calendar-day window from each not-yet-consumed transaction
    if the window contains >= 2 distinct RPTOWNERCIK -> emit one cluster event
    cluster_start = first transaction date in window
    cluster_end   = last transaction date in window
    advance past cluster_end + 1 day (prevents overlapping duplicate events)
    dedup on (issuer CIK, cluster_end)

Result: 25,971 cluster events overall, of which 25,844 fall in the 2015-2024
cluster_end window. Events outside that window are transaction-date spillover
(filings made in-scope can report an earlier transaction date) and are dropped.

### 2.4 Event timing, benchmark, costs

    entry   first close on or after (cluster_end + 1 calendar day), i.e. first trading
            day strictly after the last insider purchase of the cluster
    exit    first close on or after (entry + 180 calendar days)
    return  r_stock = exit_close / entry_close - 1
    bench   r_spy  = SPY_close(at exit date) / SPY_close(at entry date) - 1
    cost    30 bps round trip, subtracted from every event
    excess  r_stock - r_spy - 0.0030

Entry deliberately uses the *last* purchase of the cluster, not the first, so that the
signal is actionable: at cluster_start the observer does not yet know a cluster will form.
This is the conservative (and correct) choice.

### 2.5 Attrition and filters

| Filter | Dropped | Remaining |
|--------|---------|-----------|
| cluster events in 2015-2024 | -- | 25,844 |
| no usable price series (delisted, no yfinance data, <50 obs) | 10,856 | 14,988 |
| unusable entry/exit date inside series | 50 | 14,938 |
| entry price < $1.00 (liquidity floor) | 446 | 14,492 |

Final backtest sample: 14,492 events across 2,966 distinct tickers, 2015-2024.

The $1.00 liquidity floor exists because sub-dollar microcaps produce mechanically
enormous percentage moves from tick-size noise. Results are also reported for the
raw sample to keep the floor's effect visible.

## 3. Aggregate results

Primary statistic is the winsorized (1st/99th percentile) mean, because raw mean is
dominated by a handful of microcap outliers (top event +2064%).

| Metric | Raw | Winsorized 1/99 |
|--------|-----|-----------------|
| n | 14,492 | 14,492 |
| mean excess (30 bps) | -0.84% | -2.22% |
| median excess | -4.27% | -4.27% |
| stdev | 51.72% | 36.30% |
| t-stat (mean) | -1.95 | -7.38 |
| hit rate (excess > 0) | 41.6% | 41.6% |
| CI 95% (mean) | [-1.68%, +0.00%] | [-2.82%, -1.63%] |

Decomposition of the same 14,492 events, before subtracting costs:

| Component | Mean |
|-----------|------|
| mean stock 180d return | +7.23% |
| mean SPY same-window return | +7.77% |
| gross excess (before cost) | -0.54% |
| net excess (30 bps) | -0.84% |

The mechanism is visible here: cluster stocks returned +7.23% over six months, which is
indistinguishable from simply owning SPY (+7.77%). The insider signal carried no
information about relative performance in this sample.

### 3.1 Distribution

| Percentile | Excess return |
|------------|---------------|
| p5 | -55.95% |
| p10 | -41.63% |
| p25 | -20.45% |
| p50 | -4.27% |
| p75 | +10.67% |
| p90 | +33.45% |
| p95 | +57.23% |

Median is negative by a wide margin and the hit rate is 41.6%. This is not a
mean-vs-median ambiguity: both central statistics point the same way.

## 4. Year-by-year stability (winsorized)

| Year | n | mean excess | median excess | t |
|------|---|-------------|---------------|---|
| 2015 | 1,285 | -3.37% | -2.26% | -4.48 |
| 2016 | 1,230 | +3.62% | +2.55% | +4.13 |
| 2017 | 1,079 | -1.12% | -3.46% | -1.21 |
| 2018 | 1,326 | -0.75% | -2.74% | -0.94 |
| 2019 | 1,362 | -7.09% | -8.39% | -7.37 |
| 2020 | 1,765 | +10.42% | +2.51% | +8.91 |
| 2021 | 1,381 | -11.37% | -9.09% | -12.52 |
| 2022 | 1,792 | -3.63% | -4.47% | -4.47 |
| 2023 | 1,762 | -8.05% | -10.28% | -9.13 |
| 2024 | 1,510 | -1.65% | -3.88% | -1.65 |

by_year_positive (mean): 2 / 10.

The two positive years are 2016 (+3.62%) and 2020 (+10.42%). Both are plausible
small-cap recovery regimes rather than insider information: 2016 was a post-February
small-cap rebound and 2020 was the post-COVID liquidity rally in which small caps
massively outperformed SPY. In neither year does the insider signal need to be
invoked to explain the number. Every other year is negative, and 2021/2023 are
strongly negative with |t| > 9.

## 5. Slicing: where the negative result comes from

### 5.1 By cluster size

| Cluster size | n | mean excess | median | t | hit |
|--------------|---|-------------|--------|---|-----|
| 2 insiders | 6,428 | -1.59% | -3.71% | -3.56 | 42.1% |
| 3 | 3,054 | -2.17% | -4.79% | -3.28 | 41.5% |
| 4 | 1,622 | -3.07% | -4.79% | -3.36 | 39.7% |
| 5 | 1,089 | -2.61% | -5.36% | -2.26 | 40.5% |
| 6 | 701 | -2.49% | -3.98% | -1.79 | 42.1% |
| >= 8 | 1,163 | -3.42% | -3.38% | -3.28 | 42.9% |
| >= 10 | 625 | -3.74% | -2.94% | -2.54 | 44.2% |
| >= 15 | 171 | -4.83% | -5.04% | -1.56 | 44.4% |

Monotonic in the wrong direction: larger clusters perform worse, not better. If
clustering carried information, conviction should rise with the number of independent
insiders. It does not. This is the single most damaging result for the hypothesis,
because cluster size is the natural strength knob and it is flat-to-negative.

### 5.2 By entry price (liquidity proxy)

| Entry price | n | mean excess | median | t | hit |
|-------------|---|-------------|--------|---|-----|
| $1-5 | 2,284 | +5.71% | -3.38% | +5.41 | 44.5% |
| $5-15 | 5,153 | -1.04% | -3.17% | -2.23 | 42.9% |
| $15-50 | 4,995 | -3.52% | -4.24% | -8.44 | 41.4% |
| $50+ | 2,040 | -10.62% | -9.11% | -12.93 | 35.4% |

The only positive cell is $1-5, and its median is still -3.38% while its mean is
+5.71% with stdev 50.4%. That signature is a lottery-ticket distribution, not an
edge: a minority of sub-$5 names re-rate violently, the typical one loses. A
tradeable strategy cannot harvest a mean that lives in the tail while the median
is negative, and the $1 floor already removed the worst offenders.

The $50+ tier is unambiguously bad (-10.62% mean, -9.11% median, t = -12.93), which
is the opposite of the "insiders at quality companies know something" story.

## 6. Extreme events (illustration, not evidence)

Top 5 by excess return:

| Ticker | Cluster end | Excess | Entry px | Cluster size |
|--------|-------------|--------|----------|--------------|
| DRIO | 2019-08-28 | +2064.1% | $7.66 | 2 |
| WGS | 2023-11-17 | +1447.6% | $1.39 | 2 |
| DRIO | 2019-07-09 | +1241.2% | $9.46 | 5 |
| GME | 2020-12-18 | +1174.8% | $3.88 | 2 |
| TNDM | 2018-03-06 | +1065.6% | $3.97 | 5 |

Worst 5 by excess return:

| Ticker | Cluster end | Excess | Entry px | Cluster size |
|--------|-------------|--------|----------|--------------|
| RNAZ | 2023-09-28 | -120.2% | $18,590.88 | 2 |
| BKGM | 2022-10-17 | -112.6% | $32,672.37 | 3 |
| ASTI | 2023-10-24 | -111.5% | $109.00 | 5 |
| CCG | 2015-11-25 | -111.0% | $75.00 | 3 |
| RTNB | 2017-06-29 | -110.8% | $8.79 | 3 |

Two observations. First, the top five are recognisable speculative episodes (GME is
the meme squeeze; DRIO, WGS, TNDM are clinical/revenue re-ratings). Attributing them
to insider foresight is not required and is probably wrong. Second, the worst five
contain clearly unadjusted price artefacts (RNAZ entry price $18,590.88, BKGM
$32,672.37 are reverse-split unadjusted series in the yfinance pull). Those events
are data noise and they land in the left tail, which is exactly why the winsorized
statistic is the primary one and the raw mean is reported only for transparency.

## 7. Cost sensitivity (winsorized)

| Round-trip cost | mean excess | median excess | t |
|-----------------|-------------|---------------|---|
| 15 bps | -2.07% | -4.12% | -6.88 |
| 30 bps | -2.22% | -4.27% | -7.38 |
| 50 bps | -2.42% | -4.47% | -8.04 |

The result is not a cost artefact. Even at zero cost the gross excess is -0.54%,
because the stocks matched SPY rather than beat it. Cost sensitivity is reported
only to close off the objection; it cannot rescue a signal that is negative before
costs.

## 8. Verdict

VERDICT: NEGATIVE.

Applying the pre-registered rule:

    POSITIVE   mean > +3% AND t > 1.96 AND hit > 55%   -> not met (mean -2.22%, t -7.38, hit 41.6%)
    MARGINAL   mean > 0   AND t > 1.0                  -> not met (mean negative, t negative)
    NEGATIVE   otherwise                               -> MET

The hypothesis is rejected on the pre-registered criteria, on the primary point
estimate, on the median, on the hit rate, and on the conditioning variable that
should have helped most (cluster size). It is also rejected in 8 of 10 individual years.

## 9. Recommendation

Close the Form 4 insider-cluster research line. Do not forward-paper it. Specifically:

- Do not extend the sample backwards (pre-2015) hoping for a different answer.
  The negative result is driven by the *shape* of the conditioning variable
  (larger clusters are worse) and by the 2021/2023 magnitude, neither of which is a
  pre-2015 period effect.
- Do not re-specify entry timing. Entering at cluster_start instead of cluster_end
  would use information not available at decision time; that is look-ahead, not alpha.
- Do not relax the P-code filter to include option exercises or grants. Those are
  compensation events, not conviction purchases, and including them would be a
  different (weaker) hypothesis.

This closes the final research hypothesis in the queue. With Form 4 rejected, the
research-paradigm ledger reads: every classical anomaly tested here (PEAD, value,
momentum variants) is either decayed or crowded, and the one signal with a genuine
information-theoretic justification -- insider trading -- does not survive contact
with 2015-2024 data at daily resolution.

Consequence for strategy allocation: further work belongs in structural edge, not
research edge. Structural edge means data exclusivity, access, or execution
advantage that cannot be replicated by another desk running the same public filings
through the same filters. Form 4 is the definitive example of a public, parseable,
widely-mirrored dataset: SEC publishes it in pre-parsed bulk form specifically so
that anyone can build this signal in an afternoon. The measured absence of edge is
what that availability predicts.

## 10. Known limitations

Stated plainly, including the ones that would bias results *in favour* of the hypothesis:

1. Survivorship-like attrition, upward-biasing. 10,856 of 25,844 clusters (42%) were
   dropped because the ticker had no usable yfinance series -- overwhelmingly
   delisted, acquired, or renamed microcaps. The final sample therefore over-represents
   issuers that still trade today. Delisted-then-collapsed names are excluded, which
   should bias measured returns UP. The result is negative despite this bias.
2. Reverse-split artefacts in the left tail. Several worst events show unadjusted
   entry prices in the thousands (RNAZ $18,590, BKGM $32,672). Winsorization handles
   this for the headline number but the raw mean is contaminated. Median and
   winsorized mean are the reportable statistics.
3. Form 4 only, amendments excluded. DOCUMENT_TYPE == '4' excludes '4/A'. Amendments
   are a small share (~1.8% in 2024q1: 1,122 of 62,488) and mostly correct prior
   filings; excluding them is standard but is a deviation from a perfect reconstruction.
4. Transaction date vs filing date. Clustering uses transaction_date, entry uses
   cluster_end + 1 day. In reality a cluster is only *knowable* after the last filing
   is disseminated, which can lag the transaction date by up to 2 business days. Using
   cluster_end therefore assumes up to ~2 days of look-ahead. This biases results UP.
   The negative finding stands under that favourable assumption.
5. Mid-cluster entry complexity not modelled. The design enters once, after the last
   purchase. A live implementation would have to decide whether to add on each new
   insider, and would hold partial positions through the cluster. Not modelled; would
   add noise, not edge.
6. Daily closes only. Entry/exit use daily closes from yfinance. No intraday, no
   slippage model beyond the flat 30 bps, no borrow/short constraints. For long-only
   cluster buys the relevant cost is spread + impact, which 30 bps covers for
   mid-caps but understates for the $1-5 tier.
7. Benchmark is SPY, not a factor model. No size, value, or momentum adjustment.
   Given that the cluster population skews small-cap, SPY is a *hard* benchmark: a
   small-cap factor benchmark would likely make the excess worse, not better, since
   small caps outperformed over much of 2015-2024. Sector/industry neutrality is also
   absent.
8. Event overlap. A single issuer can contribute multiple cluster events across the
   decade, and events overlap in calendar time across issuers, so the 14,492
   observations are not independent. The reported t-statistics are therefore
   optimistic (too large in magnitude). This is a caveat on the *precision* of the
   negative estimate, not on its sign; the median, hit rate, and year-by-year pattern
   are unaffected by cross-sectional dependence.
9. No short side. The result speaks only to long cluster buys. Whether cluster
   absence or insider selling predicts, is untested here.
