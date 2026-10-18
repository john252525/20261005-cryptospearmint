# SEC Event Scraper — Week 1

Implementation of `docs/event-driven/SEC_PIPELINE_SPEC.md`. Provides EDGAR
full-text-search ingestion for event-driven research (spin-offs, mergers,
activist stakes, chapter 11).

## Install

    python3 -m venv .venv
    .venv/bin/pip install requests pandas pyyaml pydantic pytest python-dateutil pytest-asyncio

## CLI

    # backfill a historical window
    .venv/bin/python -m src.scraper.cli backfill --forms 10-12B \
        --start 2015-01-01 --end 2026-01-01 --max 2000 --db state/scraper.db

    # daily run (yesterday -> today)
    .venv/bin/python -m src.scraper.cli daily --forms 8-K,DEFM14A,10-12B,SCHEDULE 13D,DEFA14A

    # inspect DB
    .venv/bin/python -m src.scraper.cli stats --db state/scraper.db

    # refresh ticker map (weekly is enough)
    .venv/bin/python -m src.scraper.cli tickers

## Modules

- `edgar_client.py` — HTTP client. Mandatory `User-Agent` with contact,
  0.12 s inter-request gap (<= 8.3 req/s, under SEC's 10 req/s), retries
  with 2/4/8 s exponential backoff on 429/5xx/timeout, hard fail on 403.
  Normalizes `SC 13D` -> `SCHEDULE 13D` (SEC FTS returns 0 for the former).
- `storage.py` — SQLite schema. Idempotency via
  `PRIMARY KEY (accession_no, primary_document)`.
- `parser.py` — regex event classifier + ±200 char summary window.
  No NLP by design.
- `pipeline.py` — FTS pagination (100/page), CIK-level dedup for spin-offs
  and 13D, per-row error isolation.
- `cli.py` — argparse front-end.

## Schema

    event_filings(accession_no, primary_document, filing_type, cik, ticker,
                  company_name, filing_date, event_type, summary_text,
                  url_primary, scanned_at)
        PRIMARY KEY (accession_no, primary_document)

    scrape_runs(run_id, started_at, finished_at, query, forms,
                start_date, end_date, fetched, inserted, duplicates, errors)

`event_type` values: `merger_agreement`, `merger_proxy`, `chapter_11`,
`spin_off_announced`, `spin_off_registration`, `spin_off_registration_amend`,
`activist_13d`, `activist_13d_amend`, `antitrust_catalyst`,
`definitive_proxy_additional`, `other_8k`, `other`.

## Rate limits

SEC allows <= 10 req/s. Client enforces 0.12 s spacing (~8.3 req/s). On 429
or 5xx it backs off 2/4/8 s, 3 attempts, then counts the row as an error
without killing the run. 403 aborts immediately (bad User-Agent).

## Known limits

- FTS caps one query at 10,000 hits. The pipeline logs a warning and stops;
  split the window by date for larger backfills.
- `10-12B` and `SCHEDULE 13D` primary documents are NOT downloaded — the
  form itself is the signal. 8-K / DEFM14A / DEFA14A docs are downloaded
  for text classification.
- Activist-vs-passive classification is not attempted (regex is unreliable);
  all 13D entries are flagged `activist_13d` for manual triage.
