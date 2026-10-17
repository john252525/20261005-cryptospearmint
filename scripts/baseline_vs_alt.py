"""Funding distribution per symbol over N days."""
from __future__ import annotations
import argparse, asyncio, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.strategies.funding_carry.config import FundingCarrySettings
from src.strategies.funding_carry.backtest import fetch_history

DEFAULT_SYMBOLS = ["BTCUSDT","ETHUSDT","SOLUSDT","DOGEUSDT","WIFUSDT",
                   "AVAXUSDT","LINKUSDT","ARBUSDT","OPUSDT"]


def stats_row(sym, funding_df):
    r = funding_df["funding_rate"].astype(float).values * 1e4
    if len(r) == 0:
        return None
    return {"symbol": sym, "n_events": int(len(r)),
            "median_bps": float(np.median(r)), "mean_bps": float(np.mean(r)),
            "std_bps": float(np.std(r)),
            "p10_bps": float(np.percentile(r, 10)),
            "p90_bps": float(np.percentile(r, 90)),
            "p99_bps": float(np.percentile(r, 99)),
            "max_bps": float(np.max(r)), "min_bps": float(np.min(r)),
            "pct_gt_5bps": float((r > 5.0).mean()),
            "pct_gt_10bps": float((r > 10.0).mean()),
            "pct_abs_gt_1bps": float((np.abs(r) > 1.0).mean())}


async def _main(days, symbols):
    s = FundingCarrySettings(symbols=symbols, days=days)
    data = await fetch_history(s)
    rows = []
    for sym in symbols:
        if sym not in data:
            print("skip", sym); continue
        r = stats_row(sym, data[sym]["funding"])
        if r: rows.append(r)
    df = pd.DataFrame(rows)
    out = Path(s.results_dir); out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    pq = out / f"funding_distribution_{stamp}.parquet"
    df.to_parquet(pq, index=False); df.to_csv(pq.with_suffix(".csv"), index=False)
    print(df.to_string(index=False)); print("saved_to:", pq)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS))
    a = p.parse_args()
    syms = [x.strip().upper() for x in a.symbols.split(",") if x.strip()]
    asyncio.run(_main(a.days, syms))


if __name__ == "__main__":
    main()
