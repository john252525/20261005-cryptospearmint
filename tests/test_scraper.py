"""Tests for src/scraper (Week 1)."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from unittest.mock import MagicMock

import pytest

from src.scraper.edgar_client import (
    EdgarClient,
    _archive_url,
    _pad_cik,
    total_hits,
)
from src.scraper.parser import detect_event_type, extract_summary
from src.scraper.pipeline import _apply_cik_dedup, run_batch
from src.scraper.storage import Storage


# ---------------------------------------------------------------- helpers

def _tmp_db() -> Storage:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    return Storage(path)


def _fts_payload(rows, total=None):
    return {
        "hits": {
            "total": {"value": total if total is not None else len(rows)},
            "hits": [
                {
                    "_id": f"{r['accession_no']}:{r['primary_document']}",
                    "_source": {
                        "ciks": [r["cik"]],
                        "display_names": [f"{r.get('company_name','Co')}  (CIK {r['cik']})"],
                        "form": r["filing_type"],
                        "file_date": r["filing_date"],
                        "adsh": r["accession_no"],
                        "file_type": r["primary_document"],
                    },
                }
                for r in rows
            ],
        }
    }


class FakeClient:
    """Minimal EdgarClient stand-in for run_batch tests."""

    def __init__(self, payloads, docs=None, ticker_map=None):
        self.payloads = payloads  # iterable of payload dicts, one per page
        self.docs = docs or {}
        self._ticker_map = ticker_map or {}
        self.search_calls = []
        self.doc_calls = []

    def get_ticker_map(self, force=False):
        return self._ticker_map

    def search_fts(self, query="", forms=None, start_date=None, end_date=None,
                   from_=0, size=100):
        self.search_calls.append({"forms": forms, "from_": from_})
        if from_ < len(self.payloads):
            return self.payloads[from_ // 100] if len(self.payloads) == 1 else self.payloads[from_ // 100]
        return {"hits": {"hits": [], "total": {"value": 0}}}

    def get_primary_doc(self, accession_no, cik, doc):
        self.doc_calls.append((accession_no, cik, doc))
        return self.docs.get(accession_no, "")


# ---------------------------------------------------------------- tests

def test_ticker_map_parses(monkeypatch):
    """get_ticker_map returns CIK -> ticker for known entries."""
    cli = EdgarClient(session=MagicMock(), sleeper=lambda s: None)
    raw = {
        "0": {"cik_str": 1818201, "ticker": "CCC", "title": "CCC Intelligent Solutions"},
        "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    }
    resp = MagicMock()
    resp.json.return_value = raw
    cli._request = lambda *a, **kw: resp
    tm = cli.get_ticker_map()
    assert tm["0001818201"]["ticker"] == "CCC"
    assert tm["0000320193"]["ticker"] == "AAPL"
    # cached
    tm2 = cli.get_ticker_map()
    assert tm2 is tm


def test_archive_url_no_leading_zeros():
    """Verified example from spec."""
    url = _archive_url("0001818201", "0001193125-26-422320", "d140608d8k.htm")
    assert url == (
        "https://www.sec.gov/Archives/edgar/data/1818201/"
        "000119312526422320/d140608d8k.htm"
    )
    assert _pad_cik("1818201") == "0001818201"


def test_detect_merger_from_8k():
    text = ("Item 1.01 Entry into Agreement and Plan of Merger. Holders "
            "will receive $7.75 per share in cash.")
    assert detect_event_type("8-K", "", text) == "merger_agreement"


def test_detect_chapter11_from_8k():
    text = "The company commenced voluntary petition under chapter 11."
    assert detect_event_type("8-K", "", text) == "chapter_11"


def test_detect_spin_off_from_10_12b():
    assert detect_event_type("10-12B", "", "spin-off registration") == "spin_off_registration"
    assert detect_event_type("10-12B/A", "", "amend") == "spin_off_registration"
    assert detect_event_type("10-12B", "separation and distribution agreement", "") == "spin_off_registration"


def test_detect_activist_from_13d():
    assert detect_event_type("SCHEDULE 13D", "", "") == "activist_13d"
    assert detect_event_type("SC 13D/A", "", "") == "activist_13d"


def test_storage_insert_duplicate_returns_false():
    with _tmp_db() as st:
        rec = dict(
            accession_no="0001-26-000001",
            primary_document="doc.htm",
            filing_type="10-12B",
            cik="0000000001",
            filing_date="2026-01-01",
            event_type="spin_off_registration",
            url_primary="https://x",
        )
        assert st.insert_filing(rec) is True
        assert st.insert_filing(rec) is False


def test_storage_dedup_three_two_unique():
    with _tmp_db() as st:
        base = dict(filing_type="8-K", cik="0000000002", filing_date="2026-01-02",
                    event_type="other_8k", url_primary="https://x")
        a = {"accession_no": "A", "primary_document": "d1.htm", **base}
        b = {"accession_no": "B", "primary_document": "d2.htm", **base}
        assert st.insert_filing(a) is True
        inserted = 0
        duplicates = 0
        for rec in (a, b, a):
            if st.insert_filing(rec):
                inserted += 1
            else:
                duplicates += 1
        # a was already inserted once above, so first `a` here is duplicate too
        # Assert net: exactly 2 unique rows total, and the loop yields 1 insert + 2 dups
        assert inserted == 1
        assert duplicates == 2
        total = st._conn.execute("SELECT COUNT(*) FROM event_filings").fetchone()[0]
        assert total == 2


def test_run_batch_mocked():
    """End-to-end with fake client: 5 filings -> 5 inserted, 0 errors."""
    rows = [
        dict(accession_no=f"ACC{i}", primary_document=f"d{i}.htm",
             filing_type="10-12B", cik=f"000000000{i}",
             filing_date=f"2026-0{i+1}-0{i+1}", company_name=f"Company {i}")
        for i in range(1, 6)
    ]
    payload = _fts_payload(rows)
    fake = FakeClient(payloads=[payload])
    with _tmp_db() as st:
        summary = run_batch(
            forms=["10-12B"],
            start_date="2026-01-01",
            end_date="2026-03-31",
            max_filings=100,
            storage=st,
            client=fake,
            fetch_doc_text=False,
        )
        assert summary["fetched"] == 5
        assert summary["inserted"] == 5
        assert summary["duplicates"] == 0
        assert summary["errors"] == 0

        rows_db = [
            tuple(r)
            for r in st._conn.execute(
                "SELECT filing_type, event_type, COUNT(*) FROM event_filings GROUP BY 1,2"
            ).fetchall()
        ]
        assert rows_db == [("10-12B", "spin_off_registration", 5)]

        # second run -> all duplicates (idempotency)
        summary2 = run_batch(
            forms=["10-12B"], start_date="2026-01-01", end_date="2026-03-31",
            max_filings=100, storage=st, client=fake, fetch_doc_text=False,
        )
        assert summary2["inserted"] == 0
        assert summary2["duplicates"] == 5


def test_cik_dedup_spinoff_mark_amendments():
    """Same CIK multiple 10-12B -> earliest=registration, later=_amend."""
    from src.scraper.edgar_client import FilingHit

    def h(acc, cik, date_, doc="d.htm"):
        return FilingHit(accession_no=acc, primary_document=doc,
                         filing_type="10-12B", cik=cik, ticker=None,
                         company_name=None, filing_date=date_, url_primary="u")

    hits = [
        h("A3", "0000000001", "2026-03-01"),
        h("A1", "0000000001", "2026-01-01"),
        h("A2", "0000000001", "2026-02-01"),
        h("B1", "0000000002", "2026-01-15"),
    ]
    mapping = _apply_cik_dedup(hits)
    assert mapping[("A1", "d.htm")] == "spin_off_registration"
    assert mapping[("A2", "d.htm")] == "spin_off_registration_amend"
    assert mapping[("A3", "d.htm")] == "spin_off_registration_amend"
    assert mapping[("B1", "d.htm")] == "spin_off_registration"


def test_extract_summary_window():
    long_text = "padding " * 100 + "Agreement and Plan of Merger signed. " + "trailing " * 100
    s = extract_summary(long_text, "merger_agreement", window=50)
    assert "Agreement" in s
    # window bounds
    assert len(s) <= 50 * 2 + 200


def test_total_hits_formats():
    assert total_hits({"hits": {"total": {"value": 42}}}) == 42
    assert total_hits({"hits": {"total": 7}}) == 7
    assert total_hits({}) == 0
