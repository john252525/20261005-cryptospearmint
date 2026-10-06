"""SMA(20/50) cross на pandas. Артефакты в backtest/<ts>/.

Причина отказа от vectorbt в default-пути: vectorbt 1.0.0 на текущих
numpy 2.2 / numba 0.68 уходит в deadlock внутри Portfolio.from_signals
(JIT-компиляция без выхода). Pandas-движок детерминирован, работает на
10k бар за ~50ms.
TODO: walk-forward, grid search, Sortino/Calmar.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import polars as pl
import yaml
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config  # noqa: E402


def sma_cross_signals(close: pd.Series, *, fast: int = 20,
                      slow: int = 50) -> tuple[pd.Series, pd.Series]:
    if fast >= slow:
        raise ValueError(f"fast ({fast}) must be < slow ({slow})")
    f = close.rolling(fast, min_periods=fast).mean()
    s = close.rolling(slow, min_periods=slow).mean()
    above = (f > s).fillna(False).astype(bool)
    prev = above.shift(1, fill_value=False).astype(bool)
    return above & ~prev, ~above & prev


def load_close(cfg) -> pd.Series:
    path = Path(cfg.data.bars_dir) / f"{cfg.crypto.symbol.upper()}_{cfg.crypto.interval}.parquet"
    if not path.exists():
        raise SystemExit(f"data not found: {path}\nrun: make fetch-crypto")
    df = pl.read_parquet(path).sort("ts")
    s = df["close"].to_pandas().astype(float)
    s.index = pd.DatetimeIndex(df["ts"].to_pandas())
    logger.info("loaded {} bars from {}", len(s), path)
    return s


def _bar_minutes(index: pd.DatetimeIndex) -> float:
    if len(index) < 2:
        return 1.0
    step = pd.Series(index).diff().dropna().dt.total_seconds().median()
    return max(float(step) / 60.0, 1e-9)


def simulate(close: pd.Series, entries: pd.Series, exits: pd.Series,
             *, init_cash: float, fees: float) -> dict:
    """Long-only, single-unit. Возвращает equity, drawdown, trades, stats."""
    cash = init_cash
    qty = 0.0
    in_pos = False
    equity: list[float] = []
    trades: list[dict] = []
    entry_px = 0.0
    entry_ts = None

    for ts, price, is_e, is_x in zip(close.index, close.values,
                                      entries.values, exits.values,
                                      strict=False):
        px = float(price)
        if bool(is_e) and not in_pos:
            fill = px * (1.0 + fees)
            qty = cash / fill
            cash -= qty * fill
            in_pos = True
            entry_px = fill
            entry_ts = ts
        elif bool(is_x) and in_pos:
            fill = px * (1.0 - fees)
            cash += qty * fill
            trades.append({
                "entry_ts": str(entry_ts), "exit_ts": str(ts),
                "entry_price": round(entry_px, 6), "exit_price": round(fill, 6),
                "qty": round(qty, 8),
                "pnl": round(qty * (fill - entry_px), 4),
                "ret_pct": round((fill / entry_px - 1.0) * 100.0, 4),
            })
            in_pos = False
            qty = 0.0
            entry_px = 0.0
            entry_ts = None
        equity.append(cash + qty * px)

    eq = pd.Series(equity, index=close.index, name="equity")
    ret = eq.pct_change().fillna(0.0)

    idx = close.index
    step_min = _bar_minutes(idx)
    bars_per_year = 365.0 * 24.0 * 60.0 / step_min

    total_return = (eq.iloc[-1] / init_cash - 1.0) * 100.0
    bh = close / close.iloc[0] * init_cash
    bh_return = (bh.iloc[-1] / init_cash - 1.0) * 100.0

    dd = (eq / eq.cummax() - 1.0) * 100.0
    max_dd = float(dd.min())

    std = ret.std()
    sharpe = (math.sqrt(bars_per_year) * ret.mean() / std) if std > 0 else 0.0

    n = len(trades)
    wins = sum(1 for t in trades if t["pnl"] > 0)
    win_rate = (wins / n * 100.0) if n else 0.0

    final = float(eq.iloc[-1])
    open_pos = None
    if in_pos:
        open_pos = {
            "open_since": str(entry_ts),
            "entry_price": round(entry_px, 6),
            "last_price": round(float(close.iloc[-1]), 6),
            "unrealized_pnl": round(qty * (float(close.iloc[-1]) - entry_px), 4),
        }

    stats = {
        "engine": "pandas-v1",
        "bars": len(close),
        "final_equity": round(final, 2),
        "Total Return [%]": round(total_return, 4),
        "Buy and Hold [%]": round(bh_return, 4),
        "Max Drawdown [%]": round(max_dd, 4),
        "Sharpe Ratio": round(sharpe, 4),
        "Trades": n,
        "Wins": wins,
        "Win Rate [%]": round(win_rate, 2),
        "open_position": open_pos,
    }
    return {"stats": stats, "equity": eq, "drawdown": dd, "trades": trades}


def run(cfg) -> Path:
    close = load_close(cfg)
    entries, exits = sma_cross_signals(close,
                                       fast=cfg.backtest.fast,
                                       slow=cfg.backtest.slow)
    result = simulate(close, entries, exits,
                      init_cash=cfg.backtest.init_cash,
                      fees=cfg.backtest.fees)
    stats = result["stats"]

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = REPO_ROOT / "backtest" / stamp
    out.mkdir(parents=True, exist_ok=True)

    (out / "stats.json").write_text(
        json.dumps(stats, indent=2, default=str), encoding="utf-8")
    (out / "config.yaml").write_text(
        yaml.safe_dump({"crypto": cfg.crypto.model_dump(mode="json"),
                        "backtest": cfg.backtest.model_dump(mode="json")},
                       sort_keys=False), encoding="utf-8")
    result["equity"].to_csv(out / "equity.csv")
    result["drawdown"].to_csv(out / "drawdown.csv")
    if result["trades"]:
        pd.DataFrame(result["trades"]).to_csv(out / "trades.csv", index=False)

    logger.info("trades={} return={:.2f}% max_dd={:.2f}% sharpe={:.2f} (bh {:.2f}%)",
                stats["Trades"], stats["Total Return [%]"],
                stats["Max Drawdown [%]"], stats["Sharpe Ratio"],
                stats["Buy and Hold [%]"])
    logger.info("artifacts -> {}", out)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/example.yaml")
    a = p.parse_args()
    run(load_config(REPO_ROOT / a.config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
