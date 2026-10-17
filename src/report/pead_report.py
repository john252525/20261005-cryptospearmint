"""CLI report for PEAD backtest results: top wins/losses and surprise buckets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

BUCKETS = [(5, 10, "5-10%"), (10, 20, "10-20%"), (20, float("inf"), "20%+")]


def _bucket(s: float) -> str:
    a = abs(s)
    for lo, hi, label in BUCKETS:
        if lo <= a < hi:
            return label
    return "<5%"


def load_latest(results_dir: str) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    rd = Path(results_dir)
    metrics = sorted(rd.glob("pead_*.metrics.json"))
    if not metrics:
        raise SystemExit(f"no metrics found in {rd}")
    m_path = metrics[-1]
    tag = m_path.name.replace(".metrics.json", "")
    tr_path = rd / f"{tag}.trades.parquet"
    trades = pd.read_parquet(tr_path) if tr_path.exists() else pd.DataFrame()
    return trades, json.loads(m_path.read_text()), pd.DataFrame()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pead.report")
    ap.add_argument("--results-dir", default="backtest/results")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    trades, metrics, _ = load_latest(args.results_dir)

    report: dict = {"metrics": metrics}
    if not trades.empty and "pnl" in trades.columns:
        real = trades[trades["symbol"] != "QQQ"]
        wins = real.sort_values("pnl", ascending=False).head(args.top)
        losses = real.sort_values("pnl", ascending=True).head(args.top)
        report["top_wins"] = wins[["symbol", "direction", "entry_date", "pnl"]].to_dict("records")
        report["top_losses"] = losses[["symbol", "direction", "entry_date", "pnl"]].to_dict("records")
        if "surprise_pct" in real.columns:
            real = real.copy()
            real["bucket"] = real["surprise_pct"].apply(_bucket)
            report["surprise_buckets"] = (
                real.groupby("bucket")["pnl"].agg(["count", "mean", "sum"]).reset_index().to_dict("records")
            )
    else:
        report["top_wins"] = []
        report["top_losses"] = []
        report["surprise_buckets"] = []

    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return 0

    print("=== PEAD report ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    print("\nTop wins:")
    for r in report["top_wins"]:
        print(f"  {r['symbol']:<6} {r['direction']:<5} {r['entry_date']}  pnl={r['pnl']:.2f}")
    print("\nTop losses:")
    for r in report["top_losses"]:
        print(f"  {r['symbol']:<6} {r['direction']:<5} {r['entry_date']}  pnl={r['pnl']:.2f}")
    print("\nSurprise buckets:")
    for r in report["surprise_buckets"]:
        print(f"  {r['bucket']:<8} n={r['count']:<3} mean_pnl={r['mean']:.2f} sum_pnl={r['sum']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
