#!/usr/bin/env python3
"""Scan backtest results through QA checks.

Two input formats supported:

  1. ``*.metrics.json``   — single backtest, runs the 9 checks from
     ``qa.backtest_checks.run_backtest_checks``.

  2. ``*_grid_*.csv``     — grid scan (one row per param combo).
     Runs grid-level checks: negative economics, top-gap, parameter
     sensitivity, rank stability. Rows are read with pandas.

Exit codes:
  0  all clean (or --fail-on not reached)
  1  at least --fail-on checks failed on one or more backtests
  2  config error (missing dir, no files)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa.backtest_checks import run_backtest_checks  # noqa: E402
from qa.overfitting import parameter_sensitivity, rank_stability  # noqa: E402
from qa.registry import record  # noqa: E402

log = logging.getLogger("qa.scan")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")


# -----------------------------------------------------------
# helpers
# -----------------------------------------------------------
def _res(passed, value, threshold, msg, severity="warning"):
    return {"passed": bool(passed), "value": value, "threshold": threshold,
            "message": msg, "severity": severity}


def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        log.error("bad json %s: %s", p, e)
        return {}


def _read_grid_csv(p: Path) -> list[dict]:
    try:
        import pandas as pd
    except ImportError:
        log.error("pandas not installed, cannot read %s", p)
        return []
    try:
        df = pd.read_csv(p)
    except Exception as e:
        log.error("fail read csv %s: %s", p, e)
        return []
    df = df.where(df.notna(), None)
    return df.to_dict("records")


def _find_sibling(p: Path, suffixes: list[str]) -> Path | None:
    stem = p.name.replace(".metrics.json", "")
    for s in suffixes:
        cand = p.parent / f"{stem}{s}"
        if cand.exists():
            return cand
    return None


def _load_trades(p: Path | None) -> list[dict]:
    if not p or not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return data
    return data.get("trades", []) if isinstance(data, dict) else []


# -----------------------------------------------------------
# mode 1: metrics.json
# -----------------------------------------------------------
def _check_one_metrics(metrics_path: Path, fail_on: int) -> tuple[str, dict, int]:
    raw = _read_json(metrics_path)
    if isinstance(raw, dict) and "metrics" in raw:
        metrics = raw["metrics"]
        embedded_trades = raw.get("trades") or []
        embedded_params = raw.get("params") or {}
    else:
        metrics = raw
        embedded_trades, embedded_params = [], {}
    backtest_id = metrics_path.name.replace(".metrics.json", "")
    trades_path = _find_sibling(metrics_path, [".trades.json", ".fills.json"])
    trades = _load_trades(trades_path) if trades_path else []
    if not trades and isinstance(embedded_trades, list):
        trades = embedded_trades
    params = embedded_params or (metrics.get("params") if isinstance(metrics, dict) else None) or {}
    results = run_backtest_checks(metrics, trades, params)
    failed = sum(1 for r in results.values() if not r["passed"])
    return backtest_id, results, failed


# -----------------------------------------------------------
# mode 2: grid CSV
# -----------------------------------------------------------
def _check_grid_csv(csv_path: Path, fail_on: int) -> tuple[str, dict, int]:
    rows = _read_grid_csv(csv_path)
    backtest_id = csv_path.stem  # e.g. funding_carry_grid_v3_20261016

    results: dict[str, dict] = {}

    # 1) negative economics — that's the headline for funding-carry grid
    net_pnl = []
    for r in rows:
        if not r:
            continue
        v = r.get("net_pnl_usd")
        if v is None:
            continue
        try:
            net_pnl.append(float(v))
        except (TypeError, ValueError):
            continue
    if net_pnl:
        best = max(net_pnl); worst = min(net_pnl)
        zeros = sum(1 for v in net_pnl if v == 0.0)
        active = [v for v in net_pnl if v != 0.0]
        best_active = max(active) if active else 0.0
        results["positive_net_pnl"] = _res(
            best_active > 0, round(best_active, 4), ">0",
            f"best_active={best_active:.2f} best_all={best:.2f} "
            f"worst={worst:.2f} zeros={zeros}/{len(net_pnl)}")
    else:
        results["positive_net_pnl"] = _res(True, None, None, "n/a: no net_pnl")

    # 2) top-gap signal on Sharpe
    sh = sorted([float(r["sharpe"]) for r in rows if r and r.get("sharpe") is not None],
                reverse=True)
    if len(sh) >= 3:
        # rest excludes top-1 as in metrics-mode
        import statistics as _st
        sigma = max(_st.pstdev(sh[1:]) if len(sh) > 2 else 0.0, 1e-9)
        gap = (sh[0] - sh[1]) / sigma
        results["top_gap_sigma"] = _res(
            gap <= 3.0, round(gap, 3), 3.0,
            f"top1-top2={gap:.2f}σ over {len(sh)} rows")
    else:
        results["top_gap_sigma"] = _res(True, None, 3.0, "n/a: too few rows")

    # 3) parameter sensitivity on Sharpe + net_pnl
    for metric in ("sharpe", "net_pnl_usd"):
        s = parameter_sensitivity(rows, metric=metric, elasticity_flag=5.0)
        results[f"sensitivity_{metric}"] = _res(
            not any(d.get("flag") for d in s["params"].values()),
            s.get("worst_ratio"), 5.0,
            f"worst param={s.get('worst')} ratio={s.get('worst_ratio')}")

    # 4) rank stability on Sharpe (top-5 should survive ±10% noise)
    st = rank_stability(rows, metric="sharpe", top_k=min(5, len(rows)),
                        noise_frac=0.10, n_trials=100, seed=42)
    results["rank_stability_sharpe"] = _res(
        st.get("stable", True), st.get("score"), 0.5,
        f"top-{st.get('top_k')} overlap={st.get('score')} "
        f"({st.get('trials')} trials)")

    # 5) fee magnitude sanity — grid shows fees_usd vs funding_pnl_usd.
    # Flag fails if even the BEST parameter combo cannot cover fees from funding.
    ratios = []
    for r in rows:
        if not r:
            continue
        v = r.get("ratio_funding_to_fees")
        if v is None:
            continue
        try:
            ratios.append(float(v))
        except (TypeError, ValueError):
            continue
    if ratios:
        best = max(ratios)
        results["funding_vs_fees_ratio"] = _res(
            best >= 1.0, round(best, 4), 1.0,
            f"best funding/fees={best:.4f} across {len(ratios)} rows")
    else:
        results["funding_vs_fees_ratio"] = _res(True, None, 1.0, "n/a: no ratio")

    failed = sum(1 for r in results.values() if not r["passed"])
    return backtest_id, results, failed


# -----------------------------------------------------------
# output
# -----------------------------------------------------------
def _print_one(backtest_id: str, results: dict, fail_on: int) -> str:
    passed = sum(1 for r in results.values() if r["passed"])
    critical = [k for k, r in results.items()
                if not r["passed"] and r.get("severity") == "critical"]
    warnings = [k for k, r in results.items()
                if not r["passed"] and r.get("severity") != "critical"]
    verdict = "FAIL" if (critical or len(warnings) >= fail_on) else "PASS"
    icon = "✅" if verdict == "PASS" else ("❌" if critical else "⚠️ ")
    suffix = f"  [CRITICAL: {critical}]" if critical else ""
    print(f"{icon} {backtest_id}  {passed}/{len(results)} passed  → {verdict}{suffix}")
    for name, r in results.items():
        sev = r.get("severity", "warning")
        if r["passed"]:
            print(f"    ok   {name:24s} [{sev:8s}] value={r['value']}")
        else:
            print(f"    FAIL {name:24s} [{sev:8s}] value={r['value']} "
                  f"thr={r['threshold']} :: {r['message']}")
    return verdict


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="backtest/results")
    ap.add_argument("--db", default="state/backtest_qa.db")
    ap.add_argument("--fail-on", type=int, default=2)
    ap.add_argument("--no-registry", action="store_true")
    a = ap.parse_args()

    base = Path(a.results_dir)
    if not base.exists():
        log.error("results dir not found: %s", base)
        return 2

    metrics_files = sorted(base.rglob("*.metrics.json"))
    grid_files = sorted(base.rglob("*_grid_*.csv"))

    if not metrics_files and not grid_files:
        log.warning("no .metrics.json nor *_grid_*.csv under %s", base)
        return 2

    print(f"scanning {len(metrics_files)} metrics files + "
          f"{len(grid_files)} grid files under {base}")

    verdicts: dict[str, str] = {}
    hard_fails: list[dict] = []

    for p in metrics_files + grid_files:
        if p.name.endswith(".metrics.json"):
            bid, results, failed = _check_one_metrics(p, a.fail_on)
        else:
            bid, results, failed = _check_grid_csv(p, a.fail_on)
        verdict = _print_one(bid, results, a.fail_on)
        verdicts[bid] = verdict
        critical = [k for k, r in results.items()
                    if not r["passed"] and r.get("severity") == "critical"]
        warnings = [k for k, r in results.items()
                    if not r["passed"] and r.get("severity") != "critical"]
        if critical or len(warnings) >= a.fail_on:
            hard_fails.append({"backtest_id": bid,
                               "critical": critical, "warnings": warnings})
        if not a.no_registry:
            try:
                record(bid, results, db_path=a.db, fail_threshold=a.fail_on)
            except Exception as e:
                log.error("registry write for %s: %s", bid, e)

    total = len(verdicts)
    n_pass = sum(1 for v in verdicts.values() if v == "PASS")
    n_fail = total - n_pass
    print(f"\n=== SUMMARY: {total} checked, {n_pass} passed, {n_fail} failed")
    if hard_fails:
        print("=== HARD FAILS:")
        for h in hard_fails:
            parts = []
            if h.get("critical"):
                parts.append(f"critical={h['critical']}")
            if h.get("warnings"):
                parts.append(f"warnings={h['warnings']}")
            print(f"    {h['backtest_id']}: {' / '.join(parts)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
