"""Funding-carry backtest: long spot + short perp, delta-neutral.

PnL = funding credits на short-ноге минус round-trip fees.
При идеальной нейтральности цена не влияет: equity = cash.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
import yaml
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.data.fetch_funding import fetch_funding, write_lake  # noqa: E402
from strategies.funding_carry import funding_carry_signals  # noqa: E402


def _utc_index(idx) -> pd.DatetimeIndex:
    """Naive → localize UTC; aware → convert UTC. Без ошибок на обоих вариантах."""
    idx = pd.DatetimeIndex(idx)
    return idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")


def load_bars(symbol: str, interval: str) -> pd.Series:
    f = REPO_ROOT / "data" / "bars" / f"{symbol.upper()}_{interval}.parquet"
    if not f.exists():
        raise SystemExit(
            f"bars not found: {f}\n  run: make fetch-crypto "
            f"SYMBOL={symbol} INTERVAL={interval} DAYS=90")
    df = pl.read_parquet(f).sort("ts")
    s = df["close"].to_pandas().astype(float)
    s.index = _utc_index(df["ts"].to_pandas())
    logger.info("bars: {} rows, {} .. {}", len(s), s.index[0], s.index[-1])
    return s


def load_funding(symbol: str, start: str, end: str) -> pd.Series:
    cache = REPO_ROOT / "data" / "lake" / f"{symbol.upper()}_funding.parquet"
    if cache.exists():
        df = pl.read_parquet(cache)
        logger.info("funding: cached {} rows from {}", df.height, cache)
    else:
        df = fetch_funding(symbol, start, end)
        write_lake(df, cache)
        logger.info("funding: fetched {} rows -> {}", df.height, cache)
    ts = _utc_index(df["ts"].to_pandas())
    return pd.Series(df["funding_rate"].to_numpy(), index=ts, name="funding_rate")


def simulate(close: pd.Series, funding: pd.Series,
             entries: pd.Series, exits: pd.Series, *,
             init_cash: float, spot_fee: float, perp_fee: float,
             deploy_ratio: float) -> dict:
    tz = close.index.tz
    def _align(s: pd.Series, fill=False, method=None) -> pd.Series:
        if s.index.tz is None and tz is not None:
            idx = s.index.tz_localize(tz)
        elif s.index.tz is not None and tz is not None:
            idx = s.index.tz_convert(tz)
        else:
            idx = s.index
        s2 = s.copy()
        s2.index = idx
        if method:
            return s2.reindex(close.index, method=method).fillna(fill).astype(bool)
        return s2.reindex(close.index).fillna(fill)

    f_on = _align(funding, fill=0.0)
    e_on = _align(entries, fill=False, method="ffill")
    x_on = _align(exits,   fill=False, method="ffill")

    cash = float(init_cash)
    spot_qty = 0.0
    perp_qty = 0.0
    in_pos = False
    entry_ts, entry_px, entry_cash = None, 0.0, cash

    trades: list[dict] = []
    funding_rows: list[dict] = []
    equity = np.empty(len(close), dtype=float)

    for i, (ts, px_raw) in enumerate(zip(close.index, close.values, strict=False)):
        px = float(px_raw)

        if in_pos:
            fr = float(f_on.iat[i])
            if fr != 0.0:
                amount = fr * abs(perp_qty) * px
                cash += amount
                funding_rows.append({"ts": str(ts), "rate": fr,
                                     "amount_usd": round(amount, 6)})

            if bool(x_on.iat[i]):
                cash -= abs(perp_qty) * px * (spot_fee + perp_fee)
                cash += (spot_qty + perp_qty) * px
                trade_pnl = cash - entry_cash
                trades.append({
                    "entry_ts": str(entry_ts), "exit_ts": str(ts),
                    "entry_px": round(entry_px, 6), "exit_px": round(px, 6),
                    "notional": round(abs(perp_qty) * entry_px, 2),
                    "pnl_usd": round(trade_pnl, 4),
                    "ret_pct": round(trade_pnl / entry_cash * 100.0, 4),
                    "forced_exit": False,
                })
                in_pos = False
                spot_qty = perp_qty = 0.0

        if (not in_pos) and bool(e_on.iat[i]):
            notional = cash * deploy_ratio / 2.0
            if notional > 1.0:
                entry_cash = cash
                spot_qty = notional / px
                perp_qty = -spot_qty
                cash -= notional * (spot_fee + perp_fee)
                in_pos = True
                entry_ts, entry_px = ts, px

        # forced close на последнем баре, чтобы Trades/ret_reflect всю позицию
        if in_pos and i == len(close) - 1:
            closed_px = px
            cash -= abs(perp_qty) * closed_px * (spot_fee + perp_fee)
            cash += (spot_qty + perp_qty) * closed_px
            trade_pnl = cash - entry_cash
            trades.append({
                "entry_ts": str(entry_ts), "exit_ts": str(ts),
                "entry_px": round(entry_px, 6), "exit_px": round(closed_px, 6),
                "notional": round(abs(perp_qty) * entry_px, 2),
                "pnl_usd": round(trade_pnl, 4),
                "ret_pct": round(trade_pnl / entry_cash * 100.0, 4),
                "forced_exit": True,
            })
            in_pos = False
            spot_qty = perp_qty = 0.0

        equity[i] = cash + (spot_qty + perp_qty) * px

    eq = pd.Series(equity, index=close.index, name="equity")
    dd = (eq / eq.cummax() - 1.0) * 100.0

    daily = eq.resample("1D").last().dropna()
    dret = daily.pct_change().dropna()
    sharpe = float(math.sqrt(365.0) * dret.mean() / dret.std()) if dret.std() > 0 else 0.0

    n = len(trades)
    wins = sum(1 for t in trades if t["pnl_usd"] > 0)
    funding_total = sum(r["amount_usd"] for r in funding_rows)

    stats = {
        "engine": "funding-carry-pandas-v1",
        "bars": len(close),
        "init_cash": round(init_cash, 2),
        "final_equity": round(float(eq.iloc[-1]), 2),
        "Total Return [%]": round((float(eq.iloc[-1]) / init_cash - 1.0) * 100.0, 4),
        "Max Drawdown [%]": round(float(dd.min()), 4),
        "Sharpe Ratio": round(sharpe, 4),
        "Trades": n,
        "Wins": wins,
        "Win Rate [%]": round((wins / n * 100.0) if n else 0.0, 2),
        "Funding Income [USDT]": round(funding_total, 2),
        "Funding Events": len(funding_rows),
    }
    return {"stats": stats, "equity": eq, "drawdown": dd,
            "trades": trades, "funding": funding_rows}


def run(cfg_path: Path) -> Path:
    cfg = yaml.safe_load(Path(cfg_path).read_text())
    d = cfg["data"]
    symbol = d["symbols"][0].upper()
    interval = d.get("interval", "1m")
    start, end = d["start"], d["end"]
    p = cfg["strategy"]["params"]
    b = cfg["backtest"]

    close = load_bars(symbol, interval)
    close = close.loc[(close.index >= pd.Timestamp(start, tz="UTC"))
                      & (close.index <= pd.Timestamp(end, tz="UTC"))]
    if close.empty:
        raise SystemExit(f"no bars in [{start}, {end}] for {symbol}_{interval}")

    funding = load_funding(symbol, start, end)
    entries, exits = funding_carry_signals(
        funding,
        lookback=int(p.get("lookback", 21)),
        entry_thr=float(p["entry_thr"]),
        exit_thr=float(p["exit_thr"]),
        stat=p.get("stat", "median"),
    )
    logger.info("signals: {} entries, {} exits", int(entries.sum()), int(exits.sum()))

    res = simulate(close, funding, entries, exits,
                   init_cash=b["init_cash"], spot_fee=b["spot_fee"],
                   perp_fee=b["perp_fee"], deploy_ratio=b["deploy_ratio"])

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = REPO_ROOT / "backtest_funding" / stamp
    out.mkdir(parents=True, exist_ok=True)
    (out / "stats.json").write_text(json.dumps(res["stats"], indent=2), encoding="utf-8")
    (out / "config.yaml").write_text(Path(cfg_path).read_text(), encoding="utf-8")
    res["equity"].to_csv(out / "equity.csv")
    res["drawdown"].to_csv(out / "drawdown.csv")
    if res["trades"]:
        pd.DataFrame(res["trades"]).to_csv(out / "trades.csv", index=False)
    if res["funding"]:
        pd.DataFrame(res["funding"]).to_csv(out / "funding.csv", index=False)

    s = res["stats"]
    logger.info("trades={} ret={:.2f}% dd={:.2f}% sharpe={:.2f} funding={:.2f}",
                s["Trades"], s["Total Return [%]"], s["Max Drawdown [%]"],
                s["Sharpe Ratio"], s["Funding Income [USDT]"])
    logger.info("artifacts -> {}", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/funding_carry.yaml")
    a = ap.parse_args()
    run(REPO_ROOT / a.config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
