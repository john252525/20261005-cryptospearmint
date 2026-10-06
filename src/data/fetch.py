"""Fetch OHLCV into data/lake. Реализовано: binance public klines."""
from __future__ import annotations
import argparse, sys
from datetime import datetime, timezone
from pathlib import Path
import httpx, polars as pl
from dotenv import load_dotenv
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from data import lake_path  # noqa: E402

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
PAGE_LIMIT = 1000
KLINE_COLUMNS = ["open_time","open","high","low","close","volume","close_time",
                 "quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"]
FLOAT_COLUMNS = ["open","high","low","close","volume","quote_volume","taker_buy_base","taker_buy_quote"]
OUTPUT_COLUMNS = ["ts","ts_close","open","high","low","close","volume","trades"]

def _to_ms(v: str) -> int:
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

def fetch_binance_klines(symbol: str, interval: str, start: str, end: str, *, timeout: float = 30.0) -> pl.DataFrame:
    s_ms, e_ms = _to_ms(start), _to_ms(end)
    if s_ms >= e_ms:
        raise ValueError("start must be before end")
    frames: list[pl.DataFrame] = []
    cursor = s_ms
    with httpx.Client(timeout=timeout) as c:
        while cursor < e_ms:
            r = c.get(BINANCE_KLINES_URL, params={"symbol": symbol.upper(), "interval": interval,
                                                  "startTime": cursor, "endTime": e_ms, "limit": PAGE_LIMIT})
            r.raise_for_status()
            rows = r.json()
            if not rows:
                break
            frames.append(pl.DataFrame(rows, schema=KLINE_COLUMNS, orient="row"))
            cursor = int(rows[-1][0]) + 1
            if len(rows) < PAGE_LIMIT:
                break
    if not frames:
        return pl.DataFrame(schema={c: pl.Float64 for c in OUTPUT_COLUMNS})
    df = pl.concat(frames).with_columns(
        pl.col("open_time").cast(pl.Int64).pipe(lambda s: pl.from_epoch(s, time_unit="ms")).alias("ts"),
        pl.col("close_time").cast(pl.Int64).pipe(lambda s: pl.from_epoch(s, time_unit="ms")).alias("ts_close"),
    )
    df = df.with_columns([pl.col(c).cast(pl.Float64) for c in FLOAT_COLUMNS] + [pl.col("trades").cast(pl.Int64)])
    return df.select(OUTPUT_COLUMNS).sort("ts").unique(subset=["ts"], keep="last")

def write_lake(df: pl.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.parquet")
    df.write_parquet(tmp, compression="zstd")
    tmp.replace(path)
    return path

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="binance", choices=["binance","polygon","databento","bybit"])
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--timeframe", default="1d")
    p.add_argument("--start", default="2022-01-01")
    p.add_argument("--end", default="2024-12-31")
    return p.parse_args()

def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    a = parse_args()
    if a.source != "binance":
        logger.error("source={} not implemented", a.source)
        return 2
    logger.info("fetch {} {} {}", a.source, a.symbol, a.timeframe)
    df = fetch_binance_klines(a.symbol, a.timeframe, a.start, a.end)
    if df.is_empty():
        logger.error("no data")
        return 1
    out = write_lake(df, lake_path(a.source, a.symbol, a.timeframe))
    logger.info("wrote {} rows -> {}", df.height, out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
