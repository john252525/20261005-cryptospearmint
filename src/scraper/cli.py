"""CLI entry point: python3 -m src.scraper.cli <command>."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from typing import List, Optional

from .edgar_client import EdgarClient
from .pipeline import run_batch
from .storage import Storage

DEFAULT_DB = "data/event_filings.db"
DAILY_FORMS = ["8-K", "DEFM14A", "10-12B", "SC 13D", "DEFA14A"]


def _parse_forms(raw: str) -> List[str]:
    return [p.strip() for p in raw.split(",") if p.strip()]


def _progress(fetched: int, total: int) -> None:
    print(f"  ... discovered {fetched}/{total}", file=sys.stderr)


def cmd_backfill(args: argparse.Namespace) -> int:
    forms = _parse_forms(args.forms)
    summary = run_batch(
        forms=forms,
        start_date=args.start,
        end_date=args.end,
        max_filings=args.max,
        query=args.query or "",
        db_path=args.db,
        fetch_doc_text=not args.no_docs,
        progress_cb=_progress,
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["errors"] == 0 or summary["inserted"] > 0 else 1


def cmd_daily(args: argparse.Namespace) -> int:
    forms = _parse_forms(args.forms) if args.forms else DAILY_FORMS
    end = args.end or date.today().isoformat()
    start = args.start or (date.fromisoformat(end) - timedelta(days=1)).isoformat()
    summary = run_batch(
        forms=forms,
        start_date=start,
        end_date=end,
        max_filings=args.max,
        db_path=args.db,
        fetch_doc_text=not args.no_docs,
    )
    print(json.dumps(summary, indent=2))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    with Storage(args.db) as st:
        print(json.dumps(st.stats(), indent=2, sort_keys=True))
    return 0


def cmd_tickers(args: argparse.Namespace) -> int:
    cli = EdgarClient()
    tm = cli.get_ticker_map(force=args.force)
    print(json.dumps({"entries": len(tm), "sample": list(tm.items())[:3]}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="scraper", description="SEC EDGAR event scraper")
    p.add_argument("--verbose", "-v", action="count", default=0)
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("backfill", help="fetch a historical window")
    b.add_argument("--forms", required=True, help="comma-separated form names")
    b.add_argument("--start", required=True)
    b.add_argument("--end", required=True)
    b.add_argument("--max", type=int, default=1000)
    b.add_argument("--query", default="")
    b.add_argument("--db", default=DEFAULT_DB)
    b.add_argument("--no-docs", action="store_true", help="skip doc download")
    b.set_defaults(func=cmd_backfill)

    d = sub.add_parser("daily", help="fetch yesterday -> today")
    d.add_argument("--forms", default="")
    d.add_argument("--start", default=None)
    d.add_argument("--end", default=None)
    d.add_argument("--max", type=int, default=2000)
    d.add_argument("--db", default=DEFAULT_DB)
    d.add_argument("--no-docs", action="store_true")
    d.set_defaults(func=cmd_daily)

    s = sub.add_parser("stats", help="show DB stats")
    s.add_argument("--db", default=DEFAULT_DB)
    s.set_defaults(func=cmd_stats)

    t = sub.add_parser("tickers", help="download ticker map")
    t.add_argument("--force", action="store_true")
    t.set_defaults(func=cmd_tickers)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    level = logging.WARNING if args.verbose == 0 else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
