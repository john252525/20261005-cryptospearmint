"""Binance public REST -> data/bars/<SYM>_<TF>.parquet."""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import polars as pl
from loguru import logger

URL = "https://api.binance.com/api/v3/klines"
PAGE_LIMIT = 1000

COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]
FLOATS = ["open", "high", "low", "close", "volume", "quote_volume",
          "taker_buy_base", "taker_buy_quote"]
OUT = ["ts", "ts_close", "open", "high", "low", "close", "volume", "trades"]


def _ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def fetch_klines(symbol: str, interval: str, start: datetime, end: datetime,
                 *, timeout: float = 30.0) -> pl.DataFrame:
    s_ms, e_ms = _ms(start), _ms(end)
    if s_ms >= e_ms:
        raise ValueError("start must be before end")
    frames: list[pl.DataFrame] = []
    cursor = s_ms
    with httpx.Client(timeout=timeout) as c:
        while cursor < e_ms:
            r = c.get(URL, params={"symbol": symbol.upper(), "interval": interval,
                                   "startTime": cursor, "endTime": e_ms,
                                   "limit": PAGE_LIMIT})
            r.raise_for_status()
            rows = r.json()
            if not rows:
                break
            frames.append(pl.DataFrame(rows, schema=COLS, orient="row"))
            cursor = int(rows[-1][0]) + 1
            if len(rows) < PAGE_LIMIT:
                break
            time.sleep(0.1)
    if not frames:
        return pl.DataFrame(schema={c: pl.Float64 for c in OUT})
    df = pl.concat(frames).with_columns(
        pl.col("open_time").cast(pl.Int64).pipe(lambda s: pl.from_epoch(s, time_unit="ms")).alias("ts"),
        pl.col("close_time").cast(pl.Int64).pipe(lambda s: pl.from_epoch(s, time_unit="ms")).alias("ts_close"),
    )
    df = df.with_columns(
        [pl.col(c).cast(pl.Float64) for c in FLOATS] + [pl.col("trades").cast(pl.Int64)]
    )
    return df.select(OUT).sort("ts").unique(subset=["ts"], keep="last")


def write_bars(df: pl.DataFrame, bars_dir: Path, symbol: str, interval: str) -> Path:
    out = bars_dir / f"{symbol.upper()}_{interval}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.parquet")
    df.write_parquet(tmp, compression="zstd")
    tmp.replace(out)
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--interval", default="1m")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--bars-dir", default="data/bars")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=a.days)
    logger.info("fetch {} {} {}d -> {}", a.symbol, a.interval, a.days, a.bars_dir)
    df = fetch_klines(a.symbol, a.interval, start, end)
    if df.is_empty():
        logger.error("no data returned")
        return 1
    out = write_bars(df, Path(a.bars_dir), a.symbol, a.interval)
    logger.info("wrote {} rows -> {}", df.height, out)
    logger.info("range: {} .. {}", df["ts"][0], df["ts"][-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
