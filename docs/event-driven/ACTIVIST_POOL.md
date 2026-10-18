# Activist 13D Pool — preparation

## Purpose

Foundation for an activist-track sanity check. We need a clean pool of
13D-family filings before Week 3 CAR analysis.

## Method

- Source: `event_filings` where `filing_type LIKE %13D%`
- Backfill: `SCHEDULE 13D,SC 13D,SC 13D/A` for 2024-10-01 → 2026-10-17,
  `--max 500`
- Attempted activist-name matching in `company_name` (20 names: Elliott,
  Pershing Square, Icahn, Starboard, Third Point, ValueAct, Trian, JANA,
  Sachem Head, Ancora, Engine No. 1, Politan, Macellum, Greenlight, Corvex,
  Barington, Land and Buildings, Engaged Capital, Eminence, Blackwells)

## Critical finding — matching by activist name does NOT work

`event_filings.company_name` and `event_filings.cik` both refer to the
**issuer** (target company), not to the 13D filer. Example rows:

    ticker  company_name                          filing_type
    SAFX    XCF Global, Inc.  (SAFX)              SCHEDULE 13D/A
    TRXB    TRex Bio, Inc.  (TRXB)                SCHEDULE 13D
    GDTC    CytoMed Therapeutics Ltd  (GDTC)      SCHEDULE 13D/A

The only activist "hit" was `IEP` → `ICAHN ENTERPRISES L.P. (IEP)` — the
issuer, not Carl Icahn as filer. Naive keyword matching therefore yields a
pool of target companies, not a pool of activist campaigns.

**Consequence:** the pool below is **by-emitter (target), not by-activist**.
A correct activist pool requires scraping the 13D XML itself (the
`<filingPerson>` block in `primary_doc.xml`) to extract the actual filer
name. Our current schema has no `filer_name` column.

## Pool size

- 13D-family filings in DB: **500**
- distinct emitter tickers: **337**
- year coverage: **2026 only** (FTS returned newest-first and hit `--max 500`
  before reaching 2024–2025; larger backfill needed for a multi-year pool)

## By emitter (top-15 by filing count)

| ticker | count |
|--------|-------|
| RAKR | 6 |
| TRMD | 5 |
| GME-WT | 5 |
| TROO | 4 |
| SWRD | 4 |
| RENT | 4 |
| NFEGP | 4 |
| MG | 4 |
| HERZ | 4 |
| GREEL | 4 |
| ATER | 4 |
| AIFU | 4 |
| XBPEW | 3 |
| TH | 3 |
| SSTI | 3 |

## By year

| year | count |
|------|-------|
| 2026 | 500 |

## Schema caveat

`event_type` labeling inherited from pipeline CIK-dedup is unreliable for
13D: a plain `SCHEDULE 13D` sometimes carries `activist_13d_amend` when it
is the earliest row inside the fetch window (original filing predates
2024-10-01). Distribution:

    SCHEDULE 13D/A  activist_13d        271
    SCHEDULE 13D/A  activist_13d_amend  108
    SCHEDULE 13D    activist_13d         88
    SCHEDULE 13D    activist_13d_amend   33

Reliable primary-vs-amend labeling requires a filer-scoped query or a
wider window that captures the original submission.

## Next steps (Week 3)

- Extend backfill: `--max 2000`, start 2015-01-01, split by year to stay
  under the FTS 10,000-hit cap
- Add a `filer_name` column by parsing the 13D `primary_doc.xml`
  (element `<filingPerson><filingPersonName>`) — this unlocks real activist
  matching
- Only then run CAR sanity (T0 → T+30, T+90, SPY benchmark)
- Extend activist list to 40–50 names including non-US funds
