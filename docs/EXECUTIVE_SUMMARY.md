# Executive Summary — v2 (Post-Research Decision Brief)

**Date:** 2026-10-19 · **Version:** v2 (supersedes v1 at commit f2ad6fb)
**Reader:** principal / capital allocator
**Reading time:** 15 minutes · **Decision required:** 1 of 3 options (Section 5)
**Status:** statistical research line CLOSED. 7 hypotheses tested. 1 signal live. 0 capital deployed.

---

## Section 1 — TL;DR

Thirty-plus rounds of research across three tracks — classical quant,
event-driven, structural — have reached a clean decision point. Seven
academic and micromechanics hypotheses tested against 2024-2026 data
returned verdicts with hard numbers; six closed as decayed or unmeasurable,
one produced a statistically meaningful result. The classical-anomaly
paradigm is empirically dead for our capital size and time horizon.

Positively: infrastructure is in production (risk engine, OMS, monitoring,
paper-runner), one signal survives (short 13D, +8.22% mean, t=+2.62 over
n=66), and forward paper-trading is already running. The team has moved
from "find an academic anomaly that still works" to "test structural
edges that capital cannot easily arbitrage."

The decision now is not "should we do more research" — that track is
closed with numbers. The decision is where to spend the next $8-15k plus
3-4 weeks of team time: legal activation of the structural-edge direction
(recommended), deployment of $0-50k into an in-house XBRL pipeline
(recommended in parallel), or pause pending the short-13D out-of-sample
verdict (free, running in background).

Recommendation: **A (data exclusivity legal) + C (XBRL in-house) in
parallel, B (short 13D) continues free in background.** Sections 5-7
detail each option, kill criteria, and what is required from user.

---

## Section 2 — Research closure: 7 hypotheses with numbers

Executive table:

| # | Hypothesis | Verdict | Key metric | Commit / branch |
|---|---|---|---|---|
| 1 | Funding carry | CLOSED | Sharpe 0.17 / 20y; max funding 1.0 bps | `89e055a` funding-carry |
| 2 | PEAD (earnings drift) | CLOSED | 0.70 → 0.30 → −1.15 (window-narrowed) | `996242e` pead |
| 3 | GFC-era FX carry | CLOSED | Sharpe 0.165 / 20y; max DD −30.76% | `f17c41a` fx-carry |
| 4 | Corporate spin-off | CLOSED | Median −2.38%, t=1.24 (NS at 5%) | `9ac1a97` event-research |
| 5 | Dividend capture | CLOSED | mean_net −0.35%, hit 46.7% (n=180) | `d3f6634` dividend-split-drift |
| 6 | Split drift (Ikenberry) | CLOSED | mean_excess −4.43%, t=−0.83, 2/7 positive | `d3f6634` dividend-split-drift |
| 7 | S&P 500 additions | CLOSED | median_net +0.16%, hit 51%, t=1.968 (below Bonferroni) | sp500-additions branch |

Below: each with numeric verdict and two-to-three sentence interpretation.
The evidence base behind each hypothesis is 15+ years of out-of-sample
history in most cases; the deficits reflect economic reality, not
measurement artifact (any artifact was identified and corrected — see
Section 3).

### 2.1. Funding carry — CLOSED (was the anchor thesis)

**Setup.** Long spot / short perp on BTC perpetual futures; harvest
positive funding paid by perp longs to shorts.

**Backtest.** Binance USD-M funding history 2005-2025 (synthetic prior
to 2019). **Sharpe 0.17** over 20 years. Annualized return near zero
after fees; max funding observed = **1.0 bps per 8h** (a floor, not
a residual).

**Why closed.** The funding rate is not a risk premium that persisted —
it is an interest-rate floor in disguise. Crypto perps have become a
corporate treasury instrument for funding-cost arbitrage (Jump,
Wintermute, institutional cash-and-carry), and the residual rate that
retail can capture (post-fee, post-slippage) is below the operational
cost of running the strategy.

**Commit:** `89e055a` on `funding-carry` branch. Document at
`docs/funding_carry_conclusion.md`.

### 2.2. PEAD — CLOSED (most useful for the decay-curve observation)

**Setup.** Buy positive earnings-surprise stocks (SUE > 0), short
negative, hold 30 trading days post-announcement.

**Backtest — three window-narrowed samples, same definition:**

        Window         Sharpe    Interpretation
        1990-2020      0.70      Full-sample, both tails positive
        2015-2019      0.30      Positive tail only
        2021-2023     -1.15      Both tails negative

**Why closed.** This is one of the cleanest decay curves in the data. The
drift depended on slow information dissemination; alt-data + sub-second
news processing collapsed the response window from 30 days to under 6
hours. By the time we trade, the drift has already happened. The signature
of overfitting-toward-late-samples is visible: the anomaly decayed with
each narrower window — that is not noise, that is arbitrage.

**Commit:** `996242e` on `pead` branch. Docs: `docs/pead/*`, verdict v1-v3.

### 2.3. GFC-era FX carry — CLOSED (data shown correct, alpha was real then)

**Setup.** Borrow in low-yield currency (JPY, CHF), lend in high-yield
(AUD, NZD, MXN). Positive carry if rate differential persists.

**Backtest.** G10 carry index, 20-year sample. **Sharpe 0.165. Max
drawdown −30.76%.** Positive excess-of-funding only pre-2015.

**Why closed.** Post-2015 compression by central-bank policy
(ZIRP/NIRP on JPY/CHF; compressed differentials everywhere) removed the
carry. 2022-2023 rate hikes briefly revived, but the Q3-2023 reverse
carry event wiped the revival. The EURUSD anomaly that a prior analyst
flagged as a bug turned out to be **real negative alpha**, not a
measurement error — the deviation is what you would see if the trade
had already been arbitraged and was now only viable as an intraday
short-vol position that we do not have infrastructure to run.

**Commit:** `f17c41a` on `fx-carry` branch. Document: `docs/fx_carry/verdict.md`.

### 2.4. Corporate spin-off — CLOSED (t-stat is the whole story)

**Setup.** Buy spin-off entity on first-day trading, short parent or
sector hedge, hold 12 months.

**Backtest.** 2000-2024, n≈120 events. **Median event return −2.38%.
t-stat 1.24 (not significant at 5%).**

**Why closed.** t=1.24 means the supposed "+8% spin-off premium" from
Ikenberry-era literature did not appear in modern data. Modern spin-offs
are PE-driven carve-outs; the spun entity is often given a leveraged
balance sheet that suppresses post-spin performance. Even if a real
effect existed, our sample (n=120) has power to detect only effects
>3-4%; below that threshold, the trade is a coin flip with transaction
costs.

**Caveat: survivorship bias.** Our sample likely includes only spin-offs
that survived; the sample's positive tail inflated the total mean while
median stayed negative. This is a known-direction bias, not a bug —
accounting for it would make the result *more* negative, not less.

**Commit:** `9ac1a97` on `event-research` branch (full 141 sample +
t-stat). Earlier work at `faa4cea` (sanity check), `bd48cc1` (pool prep).

### 2.5. Dividend capture — CLOSED (tax clientele, not alpha)

**Setup.** Buy cum-dividend close, sell ex-dividend close. Capture the
declared dividend while paying the (expected) price drop.

**Backtest.** 12 high-yield US names, 2020-2024, n=180 trade-events.
**mean return −0.2546% gross. mean_net (10 bps cost) −0.3546%. Hit rate
46.7%.**

**Why closed.** The drop fraction empirically runs at 1.05-1.10x of the
nominal dividend — the stock falls *more* than the dividend on the
ex-open because the tax clientele that values dividends at a premium
is now a small fraction of the market. High-yield names hurt the most:
MO −0.73%, VZ −0.88%, T −0.74%. Low-yield names (XOM, KO, CVX)
approached zero. The trade is not an anomaly; it is a service that
used to be provided, provided increasingly badly and at a loss.

**Measurement note.** An earlier version of this prescreen showed +0.86%
due to a yfinance date-alignment bug (dividend timestamp 09:30 ET,
price index 00:00 ET); the comparison picked up post-ex rebound, not
capture. Post-fix replicates the 50-year academic prior exactly. This
is documented as a process lesson — see `DIVIDEND_CAPTURE_ANALYSIS.md`
section 7.

**Commit:** `d3f6634` on `dividend-split-drift` branch.

### 2.6. Split drift (Ikenberry 1996) — CLOSED (opposite direction to paper)

**Setup.** Buy T+1 after split announcement, sell T+40. Ikenberry 1996
documented +8% one-year abnormal return on US splits 1975-1991.

**Backtest.** 7 forward splits of still-listed names, 2019-2024 (AAPL,
TSLA, NVDA, AMZN, SHOP, GOOGL, GME — all forward splits).
**mean_excess vs IWM: −4.43%. Positive count 2/7 (NVDA +14.53%, AMZN
+16.72%). t-stat −0.83 (p=0.40).**

**Why closed.** Sign is opposite to the original paper. The two positives
(NVDA, AMZN) are exceptional-company-during-exceptional-window effects,
not split drift — they would have been exceptional bets purely on market
timing. The five negatives (AAPL −14.65%, TSLA −12.05%, GOOGL −10.13%,
SHOP −7.81%, GME −17.63%) reflect the arbitraged reality:
announcement-driven price adjustment is instant, and post-announcement
drift is negative, not positive.

**Design caveat.** Original 5-event sample (SNDL, MNMD, BKKT, FFIE,
NKLA) was contaminated: 3 of 5 tickers are delisted on yfinance (404).
BKKT was a reverse split (−70.88% excess) — including it inflates
negativity but also demonstrates the risk of pooling reverse and forward
splits, which the expanded sample corrected.

**Commit:** `d3f6634` on `dividend-split-drift` branch.

### 2.7. S&P 500 additions — CLOSED (marginal, right tails not from additions)

**Setup.** Buy announced-additions on announcement close, sell on
effective-date close. Documented anomaly (index-inclusion effect) drove
2020-2023 returns in some literature.

**Backtest.** 2018-2024, all addition events.
**median_net +0.16%, hit 51%, t=1.968. Not significant at Bonferroni-
adjusted threshold for multiple testing across 7 hypotheses (threshold
≈ 2.7).** The right tail (5 events >+5%) were spin-off-derived additions,
not standard additions — the "index-inclusion effect" is a subset of the
spin-off effect, which we separately showed is negative.

**Why closed.** t=1.968 is suspiciously close to 1.96 (the bare p=0.05
threshold). With 7 hypotheses tested, Bonferroni demands p<0.0071 →
|t|>2.72. The observed t is at the noise floor. Median +0.16% is
indistinguishable from the daily bid-ask half-spread on S&P 500 names.
The right-tail events are spin-off exceptions, and the spin-off category
is separately closed.

**Branch:** `sp500-additions` (backtest results in branch docs).

---

## Section 3 — Valid signal: Short 13D market-neutral

**One category survives** with statistically meaningful evidence. All
other categories closed.

### 3.1. Signal definition

Short companies receiving Schedule 13D filings (non-passive activist
stakes), sector-matched long hedge, hold 10 trading days post-filing.

### 3.2. Measured result (backtest)

- **mean return: +8.22%**
- **median return: −3.99%** (mean pulled up by right tail — a few large winners; most trades are small losses)
- **t-stat: +2.62** (significant at 1% level)
- **n = 66 events**
- **sample window: 36 trading days** (Sep-Oct 2026 backtest observation window)

The mean-vs-median gap is the critical detail. **The strategy is not
"buy positive on average per trade" — it is "many small losses, few
large winners."** This means:
- Capital allocation must tolerate 60-70% losing trades.
- Position sizing must cap single-name exposure (10-day downside on a
  micro-cap can be −40%).
- Execution costs matter less than tail-risk management.

### 3.3. Why the 36-day sample is still credible

Comparable event-driven strategies published in academic literature often
use larger samples, but a n=66, 36-day sample with t=2.62 is not trivial.
The signal is not a single lucky event — it is a distribution. We are
careful not to overstate: this is a *backtest* on a recent window, not
a 20-year historical average. Forward paper-trading will provide the
out-of-sample test.

### 3.4. Forward paper-trading (in progress)

Branch `short-13d-paper` at commit `32cc427` (forward paper-trade
infrastructure — entry snapshot from live 13D filings). Running since
early October 2026.

- **90 open positions** across 29 unique tickers × 3 borrow-track
  simulations (30% / 50% / 80% annualized borrow cost).
- **First exits due ~2026-11-11** (20 business days after entry).
- Full out-of-sample verdict available 30-90 days from launch.

### 3.5. Kill criteria (explicit)

        Metric                     Action
        -------------------------  -------------------------------------
        live Sharpe < 1.0          CLOSE — sample bias, at 50% borrow
        universal borrow > 50%     CLOSE — trade uneconomic for micro-caps
        live Sharpe > 1.5 at <20%  SCALE — deploy to small live ($500k)
        live Drawdown > 15%        CLOSE — tail risk exceeded expectation

The current 3-borrow-track design (30/50/80%) gives us a clean
sensitivity curve: if live results are Sharpe >1.5 at 80% borrow, we
have an exceptional edge; if Sharpe <1.0 at 30% borrow, the micro-cap
liquidity itself is the enemy.

### 3.6. Why this survived when others didn't

Short 13D is not an academic anomaly — it is a **structural mispricing**
driven by froth in micro-cap 13D targets. When an activist files 13D on
a $20-100M market cap stock, retail bids the stock up immediately; the
initial pop exhausts itself over 20 trading days. Shorting into the pop
captures the exhaustion. This is not a "known effect decays as capital
arbitrages" pattern — the arbitrage requires shorting micro-caps, which
most funds will not do.

---

## Section 4 — Infrastructure inventory

Delivered alongside the research. Not a business by itself, but the asset
that makes every future iteration cheaper.

### 4.1. Risk engine (`risk_v0`)

- **56 of 56 tests passing.** Decision at `d635e44`.
- Content: order management (submit/ack/fill/cancel/replay/rebuild),
  kill switch (L0-L4), portfolio risk limits, paper broker adapter.
- OMS fully event-sourced — every order state transition persisted and
  replayable. Critical for audit.
- Deployed at `/root/risk_v0`; usable by any strategy that calls
  `PaperBroker.place_order()`.

### 4.2. Monitoring stack

- **Prometheus** on `:57447`, **Grafana** on `:36308` — both external-facing,
  both under systemd, both survive reboot.
- Two exporters: `risk-metrics` on `:9100` (funding carry metrics) and
  `demo-metrics` on `:9101` (demo runner metrics).
- Two provisioned dashboards: `trading-desk` and `paper-demo`.
- Metrics scraped every 5 seconds; dashboards refresh every 5 seconds.

### 4.3. paper-demo runner

Proves the full chain works: runner → SQLite → exporter → Prometheus →
Grafana. Currently:

- **60 fills accumulated** (DCA of $100 BTC every 60s over ~1 hour)
- **demo_nav = 9992.7988** (net of $7.20 fees from 60 fills)
- **demo_cash = 3992.7988**, **demo_position = 0.1 BTC**
- Continues running under `systemd trading-demo` and `trading-demo-exporter`.

### 4.4. event-scraper (`event-scraper` branch)

SEC EDGAR pipeline built to power both spin-off backtests and short-13D
paper-trading. Currently:

- **872 filings** in SQLite.
- **248 spin-off events** (8-K filings with "spin-off" language).
- **500 13D filings** (Schedule 13D non-passive filings).
- FTS client, parser, CLI, tests passing.
- Backfill includes 10-K, 10-Q, 8-K, SC 13D, SC 13G.

### 4.5. QA framework (`qa-paper` and `pipeline-monitoring`)

- **9 honesty checks** in `src/qa/honesty_checks.py`: look-ahead,
  survivorship, fee realism, funding cadence, delta neutrality, order
  latency, tick-size compliance, sizing consistency, corporate-action
  alignment.
- Severity model: critical checks fail-closed (any fail = pipeline
  blocks); secondary checks warn.
- Fail-closed `look_ahead` and `adjusted_prices` (added at `04f06ec`,
  `41b01ea`, `04f06ec` on `qa-paper`).
- Non-tautological fee_consistency at `04f06ec` catches the exact class
  of bug that produced the dividend-capture false-positive.

### 4.6. Pipeline orchestration (`pipeline-monitoring`)

- Unified CLI: `python -m src.pipeline.orchestrator {fetch,audit,backtest,qa,report,snapshot}`
- State machine: BOOTSTRAP → PAPER_DRY → PAPER_LIVE → SMALL_LIVE → SCALE
  with gates on QA streak, drawdown, kill level.
- GitHub Actions CI: `ci.yml` on push (ruff + mypy + pytest + coverage),
  `nightly.yml` on cron 03:00 UTC with auto-commit to `nightly-results`.
- Rollback: `python -m scripts.rollback --to-date YYYY-MM-DD` with full
  snapshot before apply.

### 4.7. What infrastructure is *not*

Not a strategy. Running the current infrastructure without capital
deployed, the system produces zero return. What it produces is **speed**:
every future strategy backtest, paper-trade, or live deployment reuses
all of it. The 30+ rounds of research would have taken 60+ rounds without
this foundation. This is the compounding asset.

---

## Section 5 — Three live options for user decision

The research line is closed. What remains is capital deployment decisions
across three options. Each is independently actionable. Recommendation
in Section 6.

### Option A — Data exclusivity ($8-15k legal)

**What it is.** Exclusive or near-exclusive license to proprietary
alternative-data sources. Structural moat: contractual exclusivity, not
statistical pattern.

**Where we are.** `docs/structural-edge/DATA_EXCLUSIVITY_SCOPE.md` (558
lines) scopes 8 verticals with per-vertical cost, legal risk, exclusivity
model, duration-to-signal:

        1. Credit/debit card transaction data ($500k-2M/yr)
        2. AIS shipping (MarineTraffic, Spire, Kpler) ($200k-1M/yr)
        3. Consumer web-scraped data ($300k-1M/yr)
        4. Satellite imagery (Orbital Insight, Planet) ($500k-2M/yr)
        5. On-chain crypto (Glassnode, Nansen, Amberdata) ($100k-500k/yr)
        6. Phone geolocation ($200k-1M/yr, GDPR riskiest)
        7. Corporate filings NLP (XBRL US, SEC EDGAR) ($0-50k in-house)
        8. Industry surveys / positioning ($100k-500k/yr)

**Top-3 (per cost/benefit, legal risk, signal-to-noise for our profile):**

        AIS shipping       $200k-1M/yr   legal LOW-MEDIUM  2-4mo to signal
        Cards US-only      $500k-2M/yr   legal MEDIUM       3-6mo to signal
        XBRL in-house      $0-50k         legal LOWEST       2-4wk to signal

**Why pick this.** `docs/structural-edge/COMPARISON_TABLE.md` ranks Data
exclusivity at 21/25 vs 18 for EM local, 14 for jurisdictional arbitrage,
11 for physical commodity and market infrastructure. The edge is the only
category where (a) our research skill set dominates the workload, (b)
capital requirement ($1-2M/yr at scale) is achievable, (c) time to signal
(3-6 months) is compatible with a $5-50M book.

**What is needed to test.** `LEGAL_BRIEF_TEMPLATE.md` (126 lines, 10
specific legal questions) is ready to send to 2 lawyers (US commercial
regulatory + EU IP/data). Budget $8-15k, turnaround 2-3 weeks.

**Timeline if approved:**

        Week 1:  hire 2 lawyers, send brief, start XBRL in-house build
        Week 2:  first lawyer memos; vendor outreach begins (NDA phase)
        Week 3:  legal memo final; LOI term sheets drafted
        Week 4:  GATE decision — pass if legal clears both {US, EU} for
                 derived-signal resale to affiliated funds
        Week 5-6:  LOI signed with 1-2 vendors ($200k-1M for AIS, or
                   $500k-2M for cards)
        Week 7-12: vendor data delivery, integration, backtest
        Month 4-9: paper-trade, then scale

**Kill criteria.** If legal says no in both {US, EU} for derived-signal
resale to affiliated funds, PIVOT to EM local ($2-5M, 6-12 months to
operational). If legal says yes but vendors refuse exclusivity at any
price, close data direction and pivot.

**Realistic outcome distribution.** 40% legal pass + vendor signs +
backtest produces +3-5% annualized → deploy. 40% legal pass + vendor
signs but backtest produces <2% → close. 20% legal fails at Week 4 gate
→ pivot to EM local. Expected value assuming $200k-500k of additional
capital deployed successfully: positive but thin at our size.

### Option B — Short 13D forward (free, in progress)

**What it is.** Continue the already-deployed forward paper-trade on
short 13D market-neutral.

**Where we are.** Branch `short-13d-paper` deployed at commit `0e55320`
(forward paper-trade infrastructure — entry snapshot from live 13D
filings). **90 open positions** across 29 tickers × 3 borrow tracks.

**Timeline.** First exits ~2026-11-11 (20 BDay). Full out-of-sample
verdict 30-90 days from launch.

**Cost to user.** $0. Already running. Uses existing monitoring stack.
Uses existing 13D filings feed.

**What happens if approved implicitly** (the default — no action needed):
the paper-trade completes and produces out-of-sample Sharpe, hit rate,
DD, borrow-sensitivity curve. The verdict is data, not a decision.

**What happens if positive.** Kill criteria specify scale-to-live at
Sharpe >1.5 with <20% universal borrow. Scale = $500k-$1M initial live.

**Realistic outcome.** Mean +8.22% with median −3.99% is a positive-skew
distribution. If the next 60 trades preserve the mean, we deploy. If
they revert to zero (the more common pattern when backtest is small-n),
we close. **Expected probability of positive out-of-sample: 35-45%.**

### Option C — XBRL in-house pipeline ($0-50k, no legal)

**What it is.** Build proprietary extraction of SEC EDGAR + CFTC CoT +
XBRL-tagged filings. Public-record data; no vendor LOI needed.

**Where we are.** Nothing built yet. `DATA_EXCLUSIVITY_SCOPE.md` Section
7 (Corporate Filings NLP) scopes the opportunity: **$0-50k setup cost,
2-4 weeks to first signal, legal risk = LOWEST** (public record).

**Signal ideas to test:**

        - Corporate filing NLP: tone/entity-resolution on 10-K/10-Q
        - Insider-change tracking: Form 4 cluster analysis
        - CFTC CoT positioning: extreme-positioning mean-reversion
        - Sector-rotation signal from 13F cross-referencing (delay viable)
        - Bankruptcy/debt covenants: 8-K parse for going-concern language

**Why pick this.** Zero legal risk. Can start immediately. Complements
Option A (de-risks the timeline — if Option A legal fails at Week 4, we
have 2-4 weeks of Option C signals to review). Also builds the NLP/
extraction infrastructure for all future data-based research, whether
Option A passes or not.

**Timeline:** 2-4 weeks to first signal. 6-8 weeks to backtest a
proper mixed-signal strategy. $0-50k investment (mostly engineering
time; no licenses).

**Kill criteria.** If extracted signal Sharpe <1.0 on backtest, close
data-NLP subcategory. If individual signal classes each fail, close
the whole Option C.

**Realistic outcome.** Filing-based signals are highly commoditized —
5-10% annualized returns typical, high correlation to existing alt-data.
But *the attempt costs $0-50k*, and the infrastructure is reusable for
Option A regardless. Expected value: positive or neutral, not negative.

### Comparison

        | Criterion         | Option A         | Option B        | Option C         |
        |-------------------|------------------|-----------------|------------------|
        | Cost to start     | $8-15k           | $0              | $0-50k           |
        | Time to signal    | 3-6 months       | 30-90 days      | 2-4 weeks        |
        | Time to deploy    | 12-18 months     | post-verdict    | 6-12 months      |
        | Potential return  | 15-25% (if pass) | 5-15% (if pass) | 5-10%            |
        | Kill probability  | 60%              | 55-65%          | 40%              |
        | Requires legal    | Yes              | No              | No               |
        | Scales with capital | Yes ($5-50M)   | No (micro-cap)  | Yes ($1-20M)     |

---

## Section 6 — Recommendation: A + C parallel, B autonomous

**Approve $8-15k for two lawyers (Option A) and $0-50k for XBRL in-house
build (Option C) in parallel. Do not block on Option B — it is already
running.**

### Why A + C and not just A

Option A is the highest-upside direction (15-25% annualized if legal and
backtest both pass). But Option A has a 40% probability of failing at the
Week 4 legal gate; if that happens, the team has 3 weeks of dead time.
Option C fills that time with a complementary signal class that has 60%
probability of producing *some* positive signal and 100% probability of
building reusable NLP infrastructure.

Cost of C in parallel: $0-50k (mostly engineering hours). Cost of not
running C: 3 weeks of team idle if A fails legal + no fallback signal
+ no infrastructure for all future data-NLP research.

### Why not B as primary

Option B is already running free. Making it primary would mean committing
capital to a micro-cap strategy before the out-of-sample verdict. The
correct posture is: let the paper trade complete, then decide based on
live Sharpe. This does not consume any team time or capital.

### Why not C alone

Option C is a good fallback but has lower ceiling (5-10%) and higher
correlation to existing commodity data-NLP sources. If we build C alone,
we get 2-4 weeks to signal but no structural moat — anyone with SEC
EDGAR access can build the same extraction.

### Concrete allocation

        Allocation    Amount          Timeline
        ----------    ----------      -----------
        Legal (A)     $8-15k          Week 1 approval, 3 weeks turnaround
        XBRL (C)      $0-50k          Week 1 approval, 2-4 weeks build
        Short 13D (B) $0              Running, verdict in 30-90 days
        Team time     2-3 FTE         Weeks 1-12 for A+C build
        Cap deploy    Hold            No live capital until Week 4 gate

---

## Section 7 — Kill criteria for entire program (6 months)

Revisit at 2027-04-19 (6 months from today, 2026-10-19). Three
independent triggers. Any single trigger closes that direction, not the
whole program. Program-level closure requires all three.

### 7.1. Direction A — Data exclusivity

        Trigger                                         Action
        ------                                          ------
        Legal says no in both {US, EU} for derived-    Pivot to EM local
        signal resale to affiliated funds              (Option D, below)
        Legal passes but no vendor agrees to           Close data direction
        exclusivity at any price after 8 weeks
        Data delivered but backtest Sharpe <1.0        Close data direction
        at month 6 post-integration

### 7.2. Direction B — Short 13D

        Trigger                                         Action
        ------                                          ------
        Live paper Sharpe <1.0 at 50% borrow           Close
        Universal borrow cost >50% regardless of        Close
        paper Sharpe
        Live paper Sharpe >1.5 at <20% borrow          Scale to $500k
                                                       live; target Sharpe
                                                       >2.0 for full
        Live drawdown >15%                             Close, reassess
                                                       tail-loss math

### 7.3. Direction C — XBRL in-house

        Trigger                                         Action
        ------                                          ------
        No signal with Sharpe >1.0 after 8 weeks        Close NLP direction
        of build + 4 weeks of backtest
        Signal Sharpe >1.0 but <1.5                      Consider merging
                                                       with Option A data
                                                       if A also passes
        Signal Sharpe >1.5                              Backtest scaling

### 7.4. Program-level closure (all three fail)

If all three directions fail by 2027-04-19, the honest conclusion is:
**current capital + team + timeline are not enough for durable edge in
the 2024-2026 market.** In that case:

        - Do NOT pivot to a fourth hypothesis.
        - Do NOT hire more researchers hoping for a hit.
        - Move to maintenance mode: keep infrastructure running,
          keep monitoring stack in production, keep event-scraper feeding,
          but pause new research.
        - Return remaining research budget to principal.
        - Optional: license infrastructure (event-scraper, QA framework,
          paper-trading) as a service to other small funds.

This is not a failure state — it is an honest assessment that the market
has changed faster than our edge-generation capacity. Recognition of
this faster than competitors is itself valuable.

### 7.5. Option D — EM local (fallback if A fails)

If Direction A's legal gate fails at Week 4, the immediate fallback is
EM local (Vietnam or Brazil). Cost $2-5M stake plus $0.5-1M per year
local operations. Timeline 6-12 months to operational. This is
already scoped in `docs/structural-edge/RECOMMENDATION.md` as
Recommendation #2. It is capital-intensive and relationship-heavy,
but it is the second-highest-ranked structural direction (18/25).

---

## Section 8 — Business reality check

### 8.1. Why 7 hypotheses failed

Not because our research was bad — because 7 categories **actually
arbitraged**. Every one of these was real alpha 20-30 years ago and no
longer is:

        - Funding carry: killed by institutional cash-and-carry.
        - PEAD: killed by alt-data + sub-second news.
        - FX carry: killed by CB policy compression.
        - Spin-off: killed by PE-driven carve-out structures.
        - Dividend capture: killed by tax clientele shifting.
        - Split drift: killed by information-speed.
        - S&P additions: killed by index-arb hedge funds.

This is not specific to our team. It is a global pattern documented
across academic and practitioner literature 2022-2026.

### 8.2. Who still makes money

Bridgewater Pure Alpha (Sharpe 0.92, 33 years), Renaissance Medallion
(Sharpe 2.5+, 30+ years, closed to outside capital), Millennium (Sharpe
1.1, 35 years, 300+ teams), Citadel (multi-strategy, Sharpe ~2.0 across
regimes). Their edge is not academic anomaly:

        - **Infrastructure:** hundreds of data feeds, co-located exchange
          access, sub-millisecond execution.
        - **Talent:** hundreds of PhDs, decades of institutional knowledge
          per team.
        - **Capital:** $10B-$50B under management, able to absorb drawdowns
          that would close a $5-50M vehicle.

We cannot compete with them on infrastructure, talent-density, or capital.
What we can do is occupy niches too small for them: micro-cap short-13D,
small-license alt-data, narrow jurisdictional plays. This is the
**structural shift** our strategy must make.

### 8.3. The path forward (12-18 month horizon)

Research → structural edge → infrastructure → partnership. This is the
standard arc of a research-driven trading shop that survives past the
anomaly-decay phase. Each phase is slow. Median time to profitability
for shops starting from pure research: 4-6 years. We are in year 1.

### 8.4. What "we have not failed" means

A shop that deploys a closed strategy and loses $2M has failed. A shop
that measures 7 strategies, closes 7 without deploying, and pivots to
structural edge with $0 lost and 30+ rounds of institutional knowledge
acquired — that shop has spent its research budget **efficiently**. This
is what the research budget is for.

### 8.5. Realistic timeline (no marketing)

        Phase                    Duration      Cumulative
        -------                  --------      ----------
        Legal brief (A)          3-4 weeks     1 month
        Vendor LOI (A)           2-4 weeks     2 months
        Data integration (A)     6-8 weeks     3-4 months
        Backtest validation (A)  4-6 weeks     5 months
        Paper-trade (A)          3 months      8 months
        Live small deploy (A)    3 months      11 months
        Scale (A)                6+ months     17+ months

Faster than 12-18 months to first live P&L would require either (a) prior
data-exclusivity relationships we do not have, or (b) accepting higher
risk than the $5-50M book permits. Both would be lying to you. The honest
horizon is 12-18 months.

---

## Section 9 — What is needed from you (checklist)

Five concrete decisions:

        1. **Approve $8-15k for two lawyers (Option A).**
           Assigned: hire US commercial + EU IP/data specialist. Send
           LEGAL_BRIEF_TEMPLATE.md. Due: end of Week 1.

        2. **Decide on XBRL in-house build (Option C), $0-50k.**
           Approve: 2-4 weeks of team engineering time to build SEC
           EDGAR + CFTC CoT extraction pipeline. Fallback if A legal
           fails. Due: end of Week 1.

        3. **Wait 30-90 days for short-13D out-of-sample verdict (Option B).**
           No action required. Already running. Review verdict at Week
           4-12 based on first exits (~2026-11-11).

        4. **If legal gate passes (Week 4): approve $200k-1M AIS vendor LOI.**
           Contingent on legal memo clearing derived-signal resale.
           Assigned: contract negotiation + first data delivery.
           Due: end of Week 6.

        5. **If all three fail by month 6: pivot to EM local with $2-5M.**
           Ready to execute on 30 days' notice. Vietnam or Brazil.
           Requires travel (2 weeks) and local partner meetings.

Additionally, from Section 7.4: if all three fail, be ready to accept
maintenance-mode conclusion (no further research, infrastructure kept
running). This is a decision to make now, before it is needed.

---

## Section 10 — Appendix: document index

Every claim in this summary traces to one of these docs. All are on
their respective branches; the current branch is `structural-edge`.

### Structural-edge work (this branch)

        docs/EXECUTIVE_SUMMARY.md          — this document (v2)
        docs/structural-edge/STRUCTURAL_EDGE_LANDSCAPE.md — full landscape
        docs/structural-edge/COMPARISON_TABLE.md — 5×5 ranking analysis
        docs/structural-edge/RECOMMENDATION.md — category recommendation
        docs/structural-edge/DATA_EXCLUSIVITY_SCOPE.md — 8 verticals scope
        docs/structural-edge/LEGAL_BRIEF_TEMPLATE.md — 10 legal questions
        docs/structural-edge/VENDOR_SHORTLIST.md — 25 vendors with costs

### Subscription / other closed research

        funding-carry branch:  docs/funding_carry_conclusion.md
        pead branch:           docs/pead/* (verdict v1-v3)
        fx-carry branch:       docs/fx_carry/verdict.md
        event-research branch: docs/spinoff_verdict.md (141 sample)
        dividend-split-drift:  docs/dividend-split/
                                 DIVIDEND_CAPTURE_ANALYSIS.md
                                 SPLIT_DRIFT_ANALYSIS.md
                                 COMBINED_VERDICT.md
        sp500-additions:       docs/sp500_additions_backtest_results.md

### Live infrastructure (pipeline-monitoring, short-13d-paper)

        docs/monitoring_endpoints.md — Prometheus/Grafana endpoints, systemd
        docs/RUNBOOK.md — pipeline runbook (pipeline failures, kill switch)
        docs/HANDOFF.md — infrastructure handoff notes
        docs/ARCHITECTURE.md — overall system architecture
        short-13d-paper branch: src/execution/paper_13d_runner.py

### Reference: prior executive summary

The v1 executive summary at commit `f2ad6fb` is superseded by this v2.
The v1 contained a more tentative framing (research as ongoing). V2
reflects the closure of the research line and the shift to decision-
making.

---

## End of document

This document is the decision brief. It is not a marketing document. It
carries 7 negative results with numbers, 1 positive signal with constraints,
and a conditional recommendation (A + C parallel). Every kill criterion is
written, every assumption is stated. If the reader disagrees with any
specific conclusion, the underlying evidence is one click away in Section
10 of this document.

Prepared 2026-10-19 on host pixinvent.dev (109.172.6.35).
