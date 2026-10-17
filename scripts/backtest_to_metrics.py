#!/usr/bin/env python3
"""Convert backtest artifacts (grid CSV / trades parquet) into the
metrics.json schema accepted by qa.backtest_checks.run_backtest_checks.

Idempotent: skips if output exists unless --force.
"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path


def _is_grid(p: Path) -> bool:
    return p.suffix.lower() == ".csv" and "grid" in p.name.lower()

def _is_trades(p: Path) -> bool:
    n = p.name.lower()
    return p.suffix.lower() == ".parquet" and ("trades" in n or "fills" in n)

def _as_float(v, default=0.0):
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _read_grid_csv(p: Path) -> list[dict]:
    import pandas as pd
    df = pd.read_csv(p)
    df = df.where(df.notna(), None)
    return df.to_dict("records")


def _read_trades_parquet(p: Path) -> list[dict]:
    import pandas as pd
    df = pd.read_parquet(p)
    df = df.where(df.notna(), None)
    return df.to_dict("records")


def grid_to_metrics(rows: list[dict], source: str) -> dict:
    if not rows:
        raise ValueError("empty grid")
    active = [r for r in rows if int(_as_float(r.get("trades_count", 0))) > 0]
    pool = active or rows
    best = max(pool, key=lambda r: _as_float(r.get("net_pnl_usd", 0)))

    sharpe_vals = sorted(
        (_as_float(r.get("sharpe", 0)) for r in rows if r.get("sharpe") is not None),
        reverse=True)[:20]

    fees = _as_float(best.get("fees_usd", 0))
    funding = _as_float(best.get("funding_pnl_usd", 0))
    trades_count = int(_as_float(best.get("trades_count", 0)))
    hit_rate = _as_float(best.get("hit_rate", 0))
    fee_bps = 5.0  # default taker; refine per venue if needed
    avg_notional = 0.0
    if trades_count > 0 and fee_bps > 0:
        avg_notional = (fees * 1e4) / (trades_count * fee_bps) if fees > 0 else 0.0

    return {
        "sharpe": _as_float(best.get("sharpe", 0)),
        "max_dd": _as_float(best.get("max_dd", 0)),
        "win_rate": hit_rate,
        "hit_rate": hit_rate,
        "trades_count": trades_count,
        "avg_trade_notional": avg_notional,
        "total_fees": fees,
        "fee_bps": fee_bps,
        "years": 0.25,  # grid horizon assumed 90d unless parent pipeline overrides
        "total_return": _as_float(best.get("net_pnl_usd", 0)),
        "net_pnl_usd": _as_float(best.get("net_pnl_usd", 0)),
        "funding_pnl_usd": funding,
        "grid_size": len(rows),
        "grid_top_metrics": sharpe_vals,
        "asset_class": "crypto",
        "params": {"fee_bps": fee_bps, "edge_type": "funding_carry", "source": source},
    }


def trades_to_metrics(rows: list[dict], source: str) -> dict:
    if not rows:
        raise ValueError("empty trades")
    pnls = [_as_float(r.get("pnl", r.get("net_pnl_usd", 0))) for r in rows]
    fees = sum(abs(_as_float(r.get("fee", 0))) for r in rows)
    notionals = [abs(_as_float(r.get("qty", 0)) * _as_float(r.get("price", 0))) for r in rows]
    avg_notional = (sum(notionals) / len(notionals)) if notionals else 0.0
    n = len(rows)
    wins = sum(1 for p in pnls if p > 0)
    win_rate = (wins / n) if n else 0.0

    mu = sum(pnls) / n if n else 0.0
    var = (sum((p - mu) ** 2 for p in pnls) / n) if n > 1 else 0.0
    std = math.sqrt(var)
    sharpe = (mu / std * math.sqrt(252)) if std > 1e-12 else 0.0

    cum = peak = 0.0
    max_dd = 0.0
    for p in pnls:
        cum += p
        peak = max(peak, cum)
        dd = (peak - cum) / (abs(peak) + 1e-9)
        max_dd = max(max_dd, dd)

    fee_bps = (fees / (n * avg_notional) * 1e4) if (n and avg_notional > 0) else 0.0

    ts_all = []
    for r in rows:
        for k in ("ts", "fill_ts", "signal_ts"):
            v = r.get(k)
            if v is None:
                continue
            try:
                ts_all.append(float(v))
            except (TypeError, ValueError):
                pass
    years = ((max(ts_all) - min(ts_all)) / (365 * 24 * 3600)) if len(ts_all) >= 2 else 0.0

    return {
        "sharpe": sharpe,
        "max_dd": max_dd,
        "win_rate": win_rate,
        "trades_count": n,
        "avg_trade_notional": avg_notional,
        "total_fees": fees,
        "fee_bps": fee_bps,
        "years": years,
        "total_return": sum(pnls),
        "net_pnl_usd": sum(pnls),
        "asset_class": "crypto",
        "params": {"fee_bps": fee_bps, "source": source},
    }


def convert(input_path: Path, out_path: Path, force: bool = False) -> dict:
    if out_path.exists() and not force:
        return {"status": "skipped", "reason": "exists", "out": str(out_path)}
    if input_path.suffix.lower() == ".json":
        return {"status": "skipped", "reason": "already_json", "out": str(input_path)}
    if _is_grid(input_path):
        metrics = grid_to_metrics(_read_grid_csv(input_path), str(input_path))
    elif _is_trades(input_path):
        metrics = trades_to_metrics(_read_trades_parquet(input_path), str(input_path))
    else:
        raise ValueError(f"unrecognized input: {input_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metrics, indent=2))
    return {"status": "ok", "out": str(out_path), "keys": list(metrics.keys())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CSV/parquet -> metrics.json converter")
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = convert(Path(a.input), Path(a.out), a.force)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(json.dumps(r, indent=2))
    return 0 if r.get("status") in ("ok", "skipped") else 3


if __name__ == "__main__":
    raise SystemExit(main())
