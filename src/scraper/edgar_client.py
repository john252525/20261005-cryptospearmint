"""SEC EDGAR HTTP client.

Design notes (from docs/event-driven/SEC_PIPELINE_SPEC.md):
- SEC requires an identifying User-Agent with a contact address.
- Rate limit: no more than 10 req/sec. We serialize with a 0.12 s gap
  (=> <= 8.3 req/sec) so we stay safely under, per the task brief.
- Retry with exponential backoff on 429/503/timeouts.
- FTS endpoint is https://efts.sec.gov/LATEST/search-index and accepts
  ONLY the documented form names, e.g. "SCHEDULE 13D" (not "SC 13D").
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import requests

log = logging.getLogger(__name__)

FTS_URL = "https://efts.sec.gov/LATEST/search-index"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
ARCHIVES_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{doc}"
)

# SEC FTS accepts only canonical form names; "SC 13D" returns 0 hits.
FORM_ALIASES = {
    "SC 13D": "SCHEDULE 13D",
    "SC 13D/A": "SCHEDULE 13D/A",
    "SC 13G": "SCHEDULE 13G",
    "SC 13G/A": "SCHEDULE 13G/A",
}

DEFAULT_UA = "trading-desk-research research contact@example.com"
MIN_INTERVAL_SEC = 0.12  # >= SEC-safe (10 req/s ceiling), as per brief
RETRY_STATUSES = (429, 500, 502, 503, 504)
MAX_RETRIES = 3


class EdgarError(RuntimeError):
    """Non-retryable EDGAR failure (e.g. 403 / bad request)."""


@dataclass
class FilingHit:
    """Normalized FTS hit."""

    accession_no: str
    primary_document: str
    filing_type: str
    cik: str
    ticker: Optional[str]
    company_name: Optional[str]
    filing_date: str
    url_primary: str
    raw: Dict[str, Any] = field(default_factory=dict)


_TICKER_RE = re.compile(r"\(([A-Z][A-Z0-9.\-]{0,9})\)")


def _pad_cik(cik: str) -> str:
    """Zero-pad CIK to 10 digits."""
    digits = re.sub(r"\D", "", str(cik))
    return digits.zfill(10)


def _archive_url(cik: str, accession_no: str, doc: str) -> str:
    """Deterministic archive URL: CIK without leading zeros, accession without dashes."""
    cik_int = str(int(re.sub(r"\D", "", cik)))
    acc_nodash = accession_no.replace("-", "")
    return ARCHIVES_URL.format(cik_int=cik_int, acc_nodash=acc_nodash, doc=doc)


class EdgarClient:
    """Thin, polite EDGAR client.

    Parameters
    ----------
    user_agent : str
        Must contain a contact address. SEC blocks anonymous clients.
    min_interval : float
        Seconds between requests; >= 0.12 keeps us under 10 req/sec.
    session : requests.Session | None
        Injectable for tests.
    sleeper : callable
        Injectable sleep (monkeypatch in tests to avoid real waits).
    timeout : float
        Per-request timeout.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_UA,
        min_interval: float = MIN_INTERVAL_SEC,
        session: Optional[requests.Session] = None,
        sleeper=time.sleep,
        clock=time.monotonic,
        timeout: float = 20.0,
    ) -> None:
        if "@" not in user_agent:
            raise ValueError("User-Agent must include a contact email")
        self.user_agent = user_agent
        self.min_interval = min_interval
        self.timeout = timeout
        self._sleep = sleeper
        self._clock = clock
        self._last_request_at: Optional[float] = None
        self._lock = threading.Lock()
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
            }
        )
        self._ticker_map: Optional[Dict[str, Dict[str, str]]] = None

    # -- low level ---------------------------------------------------------

    def _throttle(self) -> None:
        with self._lock:
            if self._last_request_at is not None:
                elapsed = self._clock() - self._last_request_at
                if elapsed < self.min_interval:
                    self._sleep(self.min_interval - elapsed)
            self._last_request_at = self._clock()

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Performs request with throttle + backoff. Returns response or raises."""
        last_exc: Optional[BaseException] = None
        for attempt in range(MAX_RETRIES):
            self._throttle()
            try:
                resp = self.session.request(
                    method, url, timeout=self.timeout, **kwargs
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exc = exc
                wait = 2 ** attempt
                log.warning("net error %s on %s, backoff %ss", exc, url, wait)
                self._sleep(wait)
                continue

            if resp.status_code == 403:
                raise EdgarError(
                    f"403 Forbidden from {url}; check User-Agent "
                    f"({self.user_agent!r})"
                )
            if resp.status_code in RETRY_STATUSES:
                wait = 2 ** attempt
                log.warning(
                    "status %s on %s, backoff %ss (attempt %s)",
                    resp.status_code, url, wait, attempt + 1,
                )
                self._sleep(wait)
                last_exc = EdgarError(f"{resp.status_code} from {url}")
                continue
            if resp.status_code >= 400:
                raise EdgarError(f"{resp.status_code} from {url}")
            return resp
        raise EdgarError(f"retries exhausted for {url}: {last_exc}")

    # -- public API --------------------------------------------------------

    def search_fts(
        self,
        query: str = "",
        forms: Optional[Iterable[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        from_: int = 0,
        size: int = 100,
    ) -> Dict[str, Any]:
        """EDGAR full-text search.

        Returns the raw JSON dict; caller inspects hits.hits / hits.total.
        """
        params: Dict[str, Any] = {"from": int(from_), "size": int(size)}
        if query:
            params["q"] = query
        if forms:
            # SEC only accepts canonical names; "SC 13D" yields 0 hits.
            canonical = [FORM_ALIASES.get(f.upper(), f) for f in forms]
            params["forms"] = ",".join(canonical)
        if start_date and end_date:
            params["dateRange"] = "custom"
            params["startdt"] = start_date
            params["enddt"] = end_date
        resp = self._request("GET", FTS_URL, params=params)
        try:
            return resp.json()
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise EdgarError(f"FTS returned non-JSON: {exc}") from exc

    def get_ticker_map(self, force: bool = False) -> Dict[str, Dict[str, str]]:
        """CIK(10) -> {ticker, title}. Cached after first call."""
        if self._ticker_map is not None and not force:
            return self._ticker_map
        resp = self._request("GET", TICKERS_URL)
        raw = resp.json()
        out: Dict[str, Dict[str, str]] = {}
        for _idx, rec in raw.items():
            cik10 = _pad_cik(rec.get("cik_str", ""))
            out[cik10] = {
                "ticker": (rec.get("ticker") or "").upper() or "",
                "title": rec.get("title") or "",
            }
        self._ticker_map = out
        log.info("ticker_map loaded: %d entries", len(out))
        return out

    def get_filing_metadata(self, cik: str) -> Dict[str, Any]:
        """Submissions API for a single CIK (recent filings history)."""
        url = SUBMISSIONS_URL.format(cik10=_pad_cik(cik))
        resp = self._request("GET", url)
        return resp.json()

    def get_primary_doc(self, accession_no: str, cik: str, doc: str) -> str:
        """Download primary document body as text (may be HTML)."""
        url = _archive_url(cik, accession_no, doc)
        resp = self._request("GET", url)
        resp.encoding = resp.encoding or "utf-8"
        return resp.text

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def parse_hits(payload: Dict[str, Any], ticker_map: Optional[Dict[str, Dict[str, str]]] = None) -> List[FilingHit]:
        """Turn an FTS payload into normalized FilingHit objects."""
        hits = ((payload or {}).get("hits") or {}).get("hits") or []
        out: List[FilingHit] = []
        for h in hits:
            src = h.get("_source") or {}
            hit_id = h.get("_id") or ""
            if ":" in hit_id:
                acc, doc = hit_id.split(":", 1)
            else:
                acc, doc = src.get("adsh", ""), src.get("file_type", "")
            ciks = src.get("ciks") or []
            cik10 = _pad_cik(ciks[0]) if ciks else ""
            display = (src.get("display_names") or [""])[0]
            ticker: Optional[str] = None
            if ticker_map and cik10 in ticker_map:
                ticker = ticker_map[cik10].get("ticker") or None
            if not ticker:
                m = _TICKER_RE.search(display)
                if m:
                    ticker = m.group(1)
            company_name = re.sub(r"\s+\(CIK.*$", "", display).strip() or None
            filing_date = src.get("file_date", "")
            form = src.get("form", "")
            out.append(
                FilingHit(
                    accession_no=acc,
                    primary_document=doc,
                    filing_type=form,
                    cik=cik10,
                    ticker=ticker,
                    company_name=company_name,
                    filing_date=filing_date,
                    url_primary=_archive_url(cik10, acc, doc) if cik10 and acc and doc else "",
                    raw=src or {},
                )
            )
        return out


def total_hits(payload: Dict[str, Any]) -> int:
    """Extract hits.total (may be int or {'value': N})."""
    total = ((payload or {}).get("hits") or {}).get("total")
    if isinstance(total, dict):
        return int(total.get("value") or 0)
    return int(total or 0)
