# S&P 500 Additions — Data Acquisition Plan

**Scope:** obtain a backtestable history of S&P 500 additions (announce + effective dates, universe, tickers) for the strategy in SP500_ADDITIONS_DEEP_DIVE.md.
**Date:** 2026-10-17
**Status:** capability checklist; four options + recommendation.

---

## TL;DR

- **Option A (Wikipedia)** — current 503 constituents + `Date added` 2007-2026; no delisted, no announce dates. Free, 4h to parse.
- **Option B (spglobal.com scrape)** — 403 in this environment. With UA-bypass or vendor becomes primary announce source for live trading.
- **Option C (SEC EDGAR full-text)** — works today (155 hits for `"will replace" "S&P 500"` in 8-K). Good for announce-date reconstruction from ~2001.
- **Option D (CRSP / WRDS)** — gold standard for survivorship-bias-free backtest. $500-2000/mo.
- **Recommendation:** A + C for Phase 1 backtest. D only if Phase 1 shows edge and Phase 2 requires clean validation.

---

## Option A — Wikipedia S&P 500 history

**Pros:** free, immediate; `Date added` column covers 2007-2026 with 8-22 additions/year (verified this session).

**Cons:** no "Date removed" column; the "Selected changes to the list" section was removed from the article (verified `grep -c 'Selected changes' → 0`); no announce dates (only effective, approximated by Date added); no delisted prices.

**Cost:** $0. **Effort:** 4h to convert page to parquet.

**Usage:** bootstrap universe; cannot be standalone historical additions source.

**Tested:** working, 570,665 bytes, 503 rows with Date added, years 2007-2026: {2007:11, 2008:16, 2009:12, 2010:8, 2011:10, 2012:14, 2013:9, 2014:8, 2015:14, 2016:21, 2017:22, 2018:13, 2019:20, 2020:10, 2021:10, 2022:14, 2023:14, 2024:16, 2025:17, 2026:18}.

---

## Option B — Scrape S&P DJI press releases

**Pros:** authoritative announce + effective dates; sector context; "promotion from MidCap" vs fresh addition.

**Cons:** spglobal.com 403 with any UA from this environment (verified); pre-2010 archive requires Wayback crawl; intraday timing unavailable without vendor.

**Cost:** $0 if UA-bypass works; else $500-3000/mo (Eagle Alpha, Bloomberg, FactSet).

**Effort:** 1-3 days scraper + 1-2 weeks backfill 2010-2026 via Wayback.

**Usage:** primary live signal (Phase 1) and announce-vs-effective source for backtest.

**Tested:** HTTP 403 blocking direct scrape.

---

## Option C — SEC EDGAR full-text search

**Pros:** free, no key; earliest public signal (8-K item 8.01) sometimes precedes S&P PR; 155 hits returned this session for `"will replace" "S&P 500"` in 8-K.

**Cons:** weakly precise (~15-20% of true additions); no effective dates; not all additions self-report.

**Cost:** $0. **Effort:** 1d to build repeatable query with date+ticker extraction.

**Usage:** cross-validate A's `Date added` against `announce date`; augment backtest with "announce window" events.

**Tested:** working. `GET https://efts.sec.gov/LATEST/search-index?q=%22will+replace%22+%22S%26P+500%22&forms=8-K` → JSON, `hits.total.value=155`. Rate-limit: 10 req/s, 1h backoff on 429. `User-Agent` mandatory.

---

## Option D — CRSP / Compustat (paid)

**Pros:** survivorship-bias-free from 1957; adjusted + unadjusted prices; corporate actions clean; float-adjusted caps; historically reconstructed add/remove dates.

**Cons:** $500-2000/mo; not real-time (T+1 daily files); 2-4 weeks onboarding.

**Cost:** $500-2000/mo (WRDS academic) or $1500-3000/mo (vendor resale).

**Effort:** 2-4 weeks onboarding.

**Usage:** Phase 2 mandatory. Without CRSP, "sharpe on additions" is a sample-of-survivors estimate off by 50-100 bps annualized.

**Tested:** not acquired.

---

## Recommendation

### Phase 1 (weeks 1-3) — build the pipeline

1. **Primary:** Option A → bootstrap current universe + recent additions 2007-2026.
2. **Cross-validation:** Option C → EDGAR FTS on 200-500 ticker subsample to validate Date added vs public announce.
3. **Live signal source:** Option B via Twitter mirror of @spglobal RSS, or 30-day vendor trial (Eagle Alpha / FactSet).
4. **Backtest universe:** A ∪ C with a **delisted dummy** derived from `ticker dropped from Wikipedia S&P 500 on date D` — proxy, flagged in methodology.

### Phase 2 (weeks 4-12) — validate, then decide D

- If Phase 1 backtest shows **mean announce-to-effective ≥ 0.5% net** AND **≥ 8/15 base rate on candidate prediction** → commit Option D.
- If **< 0.5% net** or **< 8/15 base rate** → do not acquire CRSP; report negative result; pivot.

---

## Delta between options

| Capability | A | B | C | D |
|---|---|---|---|---|
| Current universe | ✅ | ✅ | ❌ | ✅ |
| Historical adds 2007-2026 | ✅ | ✅ | ⚠️ | ✅ |
| Historical adds pre-2007 | ⚠️ | ⚠️ | ⚠️ | ✅ |
| Announcement date | ❌ | ✅ | ⚠️ | ✅ |
| Effective date | ✅ (≈) | ✅ | ❌ | ✅ |
| Survivorship-bias-free | ❌ | ❌ | ❌ | ✅ |
| Delisted ticker prices | ❌ | ❌ | ❌ | ✅ |
| Cost | $0 | $0-3000/mo | $0 | $500-2000/mo |
| Engineering effort | 4h | 1-3d | 1d | 2-4wk |

---

## Exact reproduction commands

    # Wikipedia
    curl -s -m 20 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' \
      -H 'User-Agent: research contact@example.com' -o /tmp/sp500.html
    wc -c /tmp/sp500.html     # → 570665
    python3 -c 'import pandas as pd; t = pd.read_html("/tmp/sp500.html"); print(len(t), list(t[0].columns))'
    # → 2, ['Symbol','Security','GICS Sector','GICS Sub-Industry','Headquarters Location','Date added','CIK','Founded']

    # SEC EDGAR full-text
    curl -s 'https://efts.sec.gov/LATEST/search-index?q=%22will+replace%22+%22S%26P+500%22&forms=8-K' \
      -H 'User-Agent: research contact@example.com'
    # → {"hits":{"total":{"value":155, ...}},...}

    # spglobal.com (expected 403)
    curl -s -m 20 'https://www.spglobal.com/spdji/en/index-announcements/' \
      -H 'User-Agent: research contact@example.com'
    # → HTTP 403

---

## Open questions

1. Is `web.archive.org` a reliable source for spglobal.com PR archive pre-2010?
2. Does S&P DJI disclose "candidate / watchlist" sets anywhere?
3. Does CRSP provide **T-minus-one** announce dates as public signals, or only **ex-post** event reconstruction? (Critical for the "predictability gate" in the deep-dive §6.)
