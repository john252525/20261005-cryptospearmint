"""Fetch funding rate history from Binance USD-M futures (public, no API key).

Binance платит funding каждые 8 часов на большинстве пар (0:00, 8:00, 16:00 UTC).
Endpoint: https://fapi.binance.com/fapi/v1/fundingRate (max 1000 записей/запрос).
"""
from __future__ import annotations
import argparse, sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import polars as pl
from dotenv import load_dotenv
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
PAGE_LIMIT = 1000


def _f(v) -> float | None:
    """'' или None -> None; иначе float()."""
    if v in (None, "", "null"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_ms(v: str) -> int:
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def fetch_funding(symbol: str, start: str, end: str, *, timeout: float = 30.0) -> pl.DataFrame:
    s_ms, e_ms = _to_ms(start), _to_ms(end)
    rows: list[dict] = []
    cursor = s_ms
    with httpx.Client(timeout=timeout) as c:
        while cursor < e_ms:
            r = c.get(FUNDING_URL, params={
                "symbol": symbol.upper(),
                "startTime": cursor,
                "endTime": e_ms,
                "limit": PAGE_LIMIT,
            })
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            rows.extend(batch)
            cursor = int(batch[-1]["fundingTime"]) + 1
            if len(batch) < PAGE_LIMIT:
                break
    if not rows:
        return pl.DataFrame(schema={
            "ts": pl.Datetime(time_zone="UTC"),
            "funding_rate": pl.Float64,
            "mark_price": pl.Float64,
        })
    df = pl.DataFrame({
        "ts": [datetime.fromtimestamp(int(r["fundingTime"]) / 1000, tz=timezone.utc) for r in rows],
        "funding_rate": [float(r["fundingRate"]) for r in rows],
        "mark_price": [_f(r.get("markPrice")) for r in rows],
    })
    return df.sort("ts").unique(subset=["ts"], keep="last")


def write_lake(df: pl.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.parquet")
    df.write_parquet(tmp, compression="zstd")
    tmp.replace(path)
    return path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default=None, help="одиночный символ")
    p.add_argument("--symbols", default=None, help="comma-separated list, напр. BTCUSDT,ETHUSDT")
    p.add_argument("--start", default="2022-01-01")
    p.add_argument("--end", default="2025-01-01")
    return p.parse_args()


def _symbols_from_args(a: argparse.Namespace) -> list[str]:
    if a.symbols:
        return [s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    if a.symbol:
        return [a.symbol.upper()]
    return ["BTCUSDT"]


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    a = parse_args()
    symbols = _symbols_from_args(a)
    logger.info("fetching funding for {} symbols: {}", len(symbols), symbols)

    failed: list[str] = []
    for sym in symbols:
        try:
            df = fetch_funding(sym, a.start, a.end)
            if df.is_empty():
                logger.error("no data for {}", sym)
                failed.append(sym)
                continue
            out = (REPO_ROOT / "data/lake" / "source=binance_futures"
                   / f"symbol={sym}" / "tf=8h_funding" / "data.parquet")
            write_lake(df, out)
            fr = df["funding_rate"]
            pos_share = float((fr > 0).mean()) * 100
            implied_apy = float(fr.mean()) * 3 * 365 * 100
            logger.info("[{}] {} events | mean={:.6f} pos_share={:.1f}% gross_apy={:.2f}%",
                        sym, df.height, fr.mean(), pos_share, implied_apy)
        except Exception as e:
            logger.exception("[{}] fetch failed: {}", sym, e)
            failed.append(sym)

    logger.info("done. ok={} failed={}", len(symbols) - len(failed), failed or "none")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
