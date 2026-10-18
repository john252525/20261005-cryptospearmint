"""Regex-based event type detection + summary extraction.

Deliberately NOT NLP. The spec requires >= 90% precision on a 50-record
manual sample, which simple regex hits for the whitelisted cases.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

# --- 8-K patterns --------------------------------------------------------
_MERGER_PATTERNS = [
    re.compile(r"agreement\s+and\s+plan\s+of\s+merger", re.I),
    re.compile(r"merger\s+agreement", re.I),
    re.compile(r"(entered into|execution of).{0,80}merger\s+agreement", re.I),
]
_CHAPTER11_PATTERNS = [
    re.compile(r"chapter\s+11", re.I),
    re.compile(r"voluntary\s+petition.{0,80}chapter\s+11", re.I),
    re.compile(r"commenced.{0,80}chapter\s+11", re.I),
    re.compile(r"item\s+1\.03", re.I),
]
_SPINOFF_PATTERNS = [
    re.compile(r"spin[-\s]?off", re.I),
    re.compile(r"separation\s+and\s+distribution\s+agreement", re.I),
    re.compile(r"record\s+date.{0,100}distribution", re.I),
]
_ANTITRUST_PATTERNS = [
    re.compile(r"second\s+request", re.I),
    re.compile(r"hart[-\s]?scott[-\s]?rodino", re.I),
    re.compile(r"waiting\s+period.{0,80}(expired|terminated)", re.I),
]
_ACTIVIST_PATTERNS = [
    re.compile(r"purpose\s+of\s+transaction", re.I),
    re.compile(
        r"(may engage in|intends to engage in).{0,200}"
        r"(discussions|negotiations)", re.I,
    ),
    re.compile(r"seek(ing)?\s+(to\s+)?(representation|board\s+seats?)", re.I),
]


def _normalize(text: Optional[str]) -> str:
    if not text:
        return ""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", text)).strip()


def _first_match(patterns, text: str) -> Optional[re.Match]:
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m
    return None


def detect_event_type(
    filing_type: str,
    summary_text: str = "",
    primary_doc_text: str = "",
) -> str:
    """Map (form, text) -> event_type.

    Ordering matters: 8-K text may mention several things; we prefer the
    highest-signal categories first (merger > chapter11 > antitrust >
    spin_off > other_8k) — matching the spec's priority.
    """
    ft = (filing_type or "").upper().strip()
    text = _normalize(f"{summary_text} {primary_doc_text}")

    if ft.startswith("8-K"):
        if _first_match(_MERGER_PATTERNS, text):
            return "merger_agreement"
        if _first_match(_CHAPTER11_PATTERNS, text):
            return "chapter_11"
        if _first_match(_ANTITRUST_PATTERNS, text):
            return "antitrust_catalyst"
        if _first_match(_SPINOFF_PATTERNS, text):
            return "spin_off_announced"
        return "other_8k"

    if ft == "DEFM14A":
        return "merger_proxy"
    if ft in ("10-12B", "10-12B/A"):
        return "spin_off_registration"
    if ft in ("SCHEDULE 13D", "SC 13D", "SCHEDULE 13D/A", "SC 13D/A"):
        return "activist_13d"
    if ft == "DEFA14A":
        return "definitive_proxy_additional"
    return "other"


def extract_summary(
    text: str,
    event_type: str,
    window: int = 200,
) -> Optional[str]:
    """Return ~1-2 sentences (±window chars) around the first event match."""
    if not text:
        return None
    norm = _normalize(text)
    if not norm:
        return None
    patterns = {
        "merger_agreement": _MERGER_PATTERNS,
        "chapter_11": _CHAPTER11_PATTERNS,
        "spin_off_announced": _SPINOFF_PATTERNS,
        "spin_off_registration": _SPINOFF_PATTERNS,
        "antitrust_catalyst": _ANTITRUST_PATTERNS,
        "activist_13d": _ACTIVIST_PATTERNS,
    }.get(event_type)
    if patterns is None:
        return norm[: 2 * window]
    m = _first_match(patterns, norm)
    if not m:
        return norm[: 2 * window]
    start = max(0, m.start() - window)
    end = min(len(norm), m.end() + window)
    return norm[start:end].strip()


def extract_details(text: str, event_type: str) -> Tuple[Optional[str], Optional[str]]:
    """Returns (summary, ticker_hint). ticker_hint currently always None."""
    return extract_summary(text, event_type), None
