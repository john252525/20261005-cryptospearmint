"""Batch orchestration: FTS -> filter -> download -> classify -> store.

Behaviours locked in from the spec:
- Paginate FTS by `from` in steps of 100 (SEC hard cap 10000 per query;
  we warn and stop rather than silently truncate).
- CIK dedup for spin-off forms: within a batch the earliest filing per CIK
  is the event (`spin_off_registration`); later ones are amendments
  (`spin_off_registration_amend`). Same idea for SCHEDULE 13D.
- A single failed filing must NOT kill the run. It is inserted without
  summary_text and counted in `errors`.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Iterable, List, Optional

from .edgar_client import EdgarClient, FilingHit, total_hits
from .parser import detect_event_type, extract_summary
from .storage import Storage

log = logging.getLogger(__name__)

PAGE_SIZE = 100
FTS_HARD_CAP = 10000
AMEND_FORMS = {"10-12B/A", "SCHEDULE 13D/A", "SC 13D/A"}
SPINOFF_FORMS = {"10-12B", "10-12B/A"}
ACTIVIST_FORMS = {"SCHEDULE 13D", "SC 13D", "SCHEDULE 13D/A", "SC 13D/A"}


def _apply_cik_dedup(hits: List[FilingHit]) -> Dict[tuple, str]:
    """Compute (accession, doc) -> final event_type applying CIK dedup rules."""
    result: Dict[tuple, str] = {}

    by_cik_spin: Dict[str, List[FilingHit]] = {}
    by_cik_act: Dict[str, List[FilingHit]] = {}
    for h in hits:
        ft = (h.filing_type or "").upper()
        if ft in SPINOFF_FORMS:
            by_cik_spin.setdefault(h.cik, []).append(h)
        elif ft in ACTIVIST_FORMS:
            by_cik_act.setdefault(h.cik, []).append(h)

    def _assign(group_map, primary_label: str, amend_label: str) -> None:
        for _cik, group in group_map.items():
            group_sorted = sorted(group, key=lambda x: (x.filing_date, x.accession_no))
            for idx, h in enumerate(group_sorted):
                result[(h.accession_no, h.primary_document)] = (
                    primary_label if idx == 0 else amend_label
                )

    _assign(by_cik_spin, "spin_off_registration", "spin_off_registration_amend")
    # 13D: primary SCHEDULE 13D is the event; /A amendments are separate
    _assign(by_cik_act, "activist_13d", "activist_13d_amend")
    return result


def run_batch(
    forms: Iterable[str],
    start_date: str,
    end_date: str,
    max_filings: int = 1000,
    *,
    query: str = "",
    db_path: str = "data/event_filings.db",
    storage: Optional[Storage] = None,
    client: Optional[EdgarClient] = None,
    fetch_doc_text: bool = True,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    """One batch run. Returns counters dict."""
    t0 = time.monotonic()
    forms_list = list(forms)
    own_storage = storage is None
    st = storage or Storage(db_path)
    cli = client or EdgarClient()
    fetched = inserted = duplicates = errors = 0
    run_id = st.start_run(query, forms_list, start_date, end_date)

    try:
        ticker_map = {}
        try:
            ticker_map = cli.get_ticker_map()
        except Exception as exc:  # noqa: BLE001 - ticker map is best-effort
            log.warning("ticker_map unavailable: %s", exc)

        # --- gather hits (all pages) -------------------------------------
        collected: List[FilingHit] = []
        for form in forms_list:
            from_ = 0
            while True:
                if from_ >= FTS_HARD_CAP:
                    log.warning(
                        "form=%s: hit FTS 10000 cap; narrow the date window",
                        form,
                    )
                    break
                if len(collected) >= max_filings:
                    break
                payload = cli.search_fts(
                    query=query,
                    forms=[form],
                    start_date=start_date,
                    end_date=end_date,
                    from_=from_,
                    size=PAGE_SIZE,
                )
                total = total_hits(payload)
                page = EdgarClient.parse_hits(payload, ticker_map)
                if not page:
                    break
                collected.extend(page)
                from_ += len(page)
                if progress_cb:
                    progress_cb(len(collected), total)
                if from_ >= total:
                    break
            if len(collected) >= max_filings:
                log.info("reached max_filings=%s, stopping discovery", max_filings)
                break

        collected = collected[:max_filings]
        fetched = len(collected)

        # --- classify + store -------------------------------------------
        event_override = _apply_cik_dedup(collected)

        for hit in collected:
            try:
                if hit.cik and hit.accession_no and hit.primary_document:
                    form_upper = (hit.filing_type or "").upper()
                    needs_text = form_upper.startswith("8-K") or form_upper in (
                        "DEFM14A", "DEFA14A",
                    )
                    doc_text = ""
                    if fetch_doc_text and needs_text:
                        try:
                            doc_text = cli.get_primary_doc(
                                hit.accession_no, hit.cik, hit.primary_document
                            )
                        except Exception as exc:  # noqa: BLE001
                            log.warning(
                                "doc fetch failed %s: %s", hit.accession_no, exc
                            )
                            errors += 1
                            doc_text = ""

                    base_event = detect_event_type(
                        hit.filing_type, "", doc_text
                    )
                    event_type = event_override.get(
                        (hit.accession_no, hit.primary_document),
                        base_event,
                    )
                    summary = extract_summary(doc_text, event_type) if doc_text else None

                    ok = st.insert_filing(
                        {
                            "accession_no": hit.accession_no,
                            "primary_document": hit.primary_document,
                            "filing_type": hit.filing_type,
                            "cik": hit.cik,
                            "ticker": hit.ticker,
                            "company_name": hit.company_name,
                            "filing_date": hit.filing_date,
                            "event_type": event_type,
                            "summary_text": summary,
                            "url_primary": hit.url_primary,
                        }
                    )
                    if ok:
                        inserted += 1
                    else:
                        duplicates += 1
                else:
                    errors += 1
            except Exception as exc:  # noqa: BLE001 - one bad row must not kill run
                log.error("row failed %s: %s", getattr(hit, "accession_no", "?"), exc)
                errors += 1
    finally:
        st.finish_run(run_id, fetched, inserted, duplicates, errors)
        elapsed = time.monotonic() - t0
        if own_storage:
            st.close()

    return {
        "run_id": run_id,
        "fetched": fetched,
        "inserted": inserted,
        "duplicates": duplicates,
        "errors": errors,
        "elapsed_sec": round(elapsed, 2),
    }
