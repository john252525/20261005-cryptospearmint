"""General backtest QA checks — applicable to any backtest in the repo."""
from __future__ import annotations
import json, logging, math, statistics
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("qa.backtest")

TH = {
    "fee_dev_pct": 5.0,
    "turnover_dev_pct": 20.0,
    "min_sharpe_years_for_flag": 3.0,
    "sharpe_flag": 4.0,
    "win_rate_flag": 0.70,
    "grid_cells_flag": 100,
    "grid_gap_sigma_flag": 3.0,
    "dd_vol_ratio_flag": 0.30,
    "lookahead_min_delay_ms": 1.0,
}
_EDGE_EXEMPT = {"delta_neutral", "market_neutral", "arbitrage", "carry",
                "funding_carry", "funding-carry", "basis", "cash_and_carry"}

SEVERITY = {
    "look_ahead":           "critical",
    "survivorship":         "warning",
    "adjusted_prices":      "warning",
    "overfitting_signals":  "warning",
    "fee_consistency":      "critical",
    "fill_realism":         "warning",
    "sharpe_sanity":        "warning",
    "turnover_consistency": "warning",
    "dd_vs_vol":            "warning",
}
_CRYPTO_SUFFIXES = ("USDT", "USDC", "BUSD", "DAI", "PERP", "USD", "-PERP", "/USDT")


def _pick(d, *keys):
    if not d:
        return None
    for k in keys:
        v = d.get(k)
        if v is not None and v != "":
            return v
    return None


def _rows(trades):
    if trades is None:
        return []
    if hasattr(trades, "to_dict"):
        try:
            return trades.to_dict("records")
        except Exception:
            return []
    if isinstance(trades, list):
        return [t for t in trades if isinstance(t, dict)]
    return []


def _ts(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) / (1.0 if abs(v) < 1e12 else 1e3)
    s = str(v)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s).timestamp()
    except (ValueError, TypeError):
        return None


def _is_equity(metrics, trades):
    ac = (metrics or {}).get("asset_class")
    if ac:
        return str(ac).lower() in ("equity", "stock", "stocks", "adr")
    syms = set()
    for t in trades[:200]:
        s = t.get("symbol") or t.get("ticker")
        if s:
            syms.add(str(s).upper())
    if not syms:
        return False
    crypto = sum(1 for s in syms if any(s.endswith(x) for x in _CRYPTO_SUFFIXES))
    return crypto < len(syms) / 2


def _r(passed, value, threshold, msg):
    return {"passed": passed, "value": value,
            "threshold": threshold, "message": msg}


def check_look_ahead(metrics, trades, params):
    tc = _pick(metrics, "trades_count", "n_trades", "n_fills")
    tc_i = 0
    if tc is not None:
        try: tc_i = int(tc)
        except (TypeError, ValueError): tc_i = 0
    if len(trades) > tc_i:
        tc_i = len(trades)
    ac = str(metrics.get("asset_class") or "").lower()
    known = ac in ("equity", "stock", "stocks", "adr",
                   "crypto", "cryptocurrency", "perp", "perpetual", "futures")
    if tc_i == 0:
        return _r(True, 0, 0, "n/a: no trades")
    has_ts = False
    for t in trades[:50]:
        if any(t.get(k) is not None
               for k in ("signal_ts", "fill_ts", "signal_bar", "fill_bar")):
            has_ts = True
            break
    if not has_ts:
        if known:
            return _r(False, "missing_signal_ts", None,
                      f"no signal/fill timestamps in trades; asset_class={ac}; "
                      f"cannot verify look-ahead leakage (trades_count={tc_i})")
        return _r(True, "unknown_class_skip", None,
                  f"n/a: no timestamps, asset_class='{ac}' not in known set")
    min_ms = TH["lookahead_min_delay_ms"]
    bad_ts, bad_bar, n = [], [], 0
    for i, t in enumerate(trades):
        s_ts, f_ts = _ts(t.get("signal_ts")), _ts(t.get("fill_ts"))
        if s_ts is not None and f_ts is not None:
            n += 1
            if (f_ts - s_ts) * 1000.0 < min_ms:
                bad_ts.append(i)
        sb, fb = t.get("signal_bar"), t.get("fill_bar")
        if sb is not None and fb is not None and int(fb) <= int(sb):
            bad_bar.append(i)
    bad = len(set(bad_ts) | set(bad_bar))
    return _r(bad == 0, bad, 0, f"violations={bad} (fill <= signal)")



def check_survivorship(metrics, trades, params):
    if not _is_equity(metrics, trades):
        return _r(True, None, None, "n/a: non-equity")
    years = _pick(metrics, "years", "n_years", "lookback_years", "horizon_years")
    u0 = _pick(metrics, "universe_count_start", "universe_size_start")
    u1 = _pick(metrics, "universe_count_end", "universe_size_end")
    delisted = _pick(metrics, "delisted_count", "delisted_tickers_count", "n_delisted") or 0
    if years is None:
        return _r(True, None, None, "n/a: no horizon")
    if float(years) < 3.0 - 0.05:
        return _r(True, delisted, 0, f"short horizon ({years}y)")
    if int(delisted) == 0:
        return _r(False, 0, ">0", f"no delisted tickers over {years}y")
    if u0 is not None and u1 is not None and u0 == u1:
        return _r(False, f"{u0}->{u1}", "shrink", f"universe flat over {years}y")
    return _r(True, delisted, ">0", f"delisted={delisted} uni {u0}->{u1}")


def check_adjusted_prices(metrics, trades, params):
    if not _is_equity(metrics, trades):
        return _r(True, None, None, "n/a: non-equity")
    if metrics.get("adjusted") is True or metrics.get("price_kind") == "adjusted":
        return _r(True, "metrics.adjusted", True, "adjusted per metadata")
    keys = set()
    for t in trades[:50]:
        keys |= {str(k).lower() for k in t.keys()}
    hit = {k for k in keys if k in ("adjclose", "adj_close", "adj_price")}
    if hit:
        return _r(True, sorted(hit), "adjclose", "adjclose present")
    return _r(False, None, "adjclose", "no adjusted price field (equity)")


def check_overfitting_signals(metrics, trades, params):
    grid_size = _pick(metrics, "grid_size", "n_grid_cells") or _pick(params or {}, "grid_size", "n_grid_cells")
    if grid_size is None:
        return _r(True, None, None, "n/a: no grid metadata")
    try:
        gi = int(grid_size)
    except (TypeError, ValueError):
        return _r(True, grid_size, None, "n/a: grid_size not numeric")
    if gi < TH["grid_cells_flag"]:
        return _r(True, gi, TH["grid_cells_flag"], f"grid={gi} below flag")
    top = _pick(metrics, "grid_top_metrics", "top_metrics", "grid_scores_sorted")
    if not top or len(top) < 3:
        return _r(True, gi, TH["grid_cells_flag"], f"grid={gi}>flag but no scores")
    vals = sorted([float(x) for x in top if x is not None], reverse=True)
    rest = vals[2:]
    sigma = max(statistics.pstdev(rest) if len(rest) > 1 else 0.0, 1e-9)
    gap = (vals[0] - vals[1]) / sigma
    return _r(gap <= TH["grid_gap_sigma_flag"], round(gap, 3),
              TH["grid_gap_sigma_flag"], f"grid={gi}, top gap {gap:.2f}σ")


def check_fee_consistency(metrics, trades, params):
    # Only trust params.fee_bps / params.fee_schedule as independent source.
    # Do not fall back to metrics.fee_bps - that value is usually derived from
    # the very trades we're trying to verify (tautology).
    fee_bps = _pick(params or {}, "fee_bps", "taker_fee_bps", "fee_bp")
    if fee_bps is None and params and params.get("fee_schedule"):
        venue = str(params.get("fee_schedule"))
        sched = {"binance_spot": 10.0, "binance_usdm": 5.0,
                 "binance_usdm_maker": 2.0,
                 "bybit_spot": 10.0, "bybit_linear": 5.5,
                 "bybit_linear_maker": 2.0}
        fee_bps = sched.get(venue)
        if fee_bps is None:
            return _r(None, "unknown_fee_schedule", TH["fee_dev_pct"],
                      f"params.fee_schedule='{venue}' not recognized")
    if fee_bps is None:
        return _r(None, "not_provided", TH["fee_dev_pct"],
                  "fee_bps not independently provided "
                  "(params.fee_bps or params.fee_schedule); "
                  "consistency check is tautological")
    reported = _pick(metrics, "total_fees", "fees_total",
                     "total_fee_usd", "fees_usd")
    if reported is None or float(reported) == 0:
        return _r(False, None, TH["fee_dev_pct"], "no reported fees")
    if not trades:
        return _r(True, 0.0, TH["fee_dev_pct"],
                  f"reported={float(reported):.2f} traded=0 "
                  f"(degenerate: no trades, cannot verify)")
    recomputed = sum(abs(float(t.get("qty", 0)) * float(t.get("price", 0)))
                     for t in trades) * float(fee_bps) / 1e4
    dev = abs(recomputed - float(reported)) / abs(float(reported)) * 100.0
    return _r(dev <= TH["fee_dev_pct"], round(dev, 3), TH["fee_dev_pct"],
              f"fee_bps={fee_bps} recomputed={recomputed:.2f} "
              f"reported={float(reported):.2f}")



def check_fill_realism(metrics, trades, params):
    wr = _pick(metrics, "win_rate", "hit_rate", "winrate")
    if wr is None:
        return _r(True, None, None, "n/a: no win_rate")
    try:
        wr_f = float(wr)
    except (TypeError, ValueError):
        return _r(True, wr, None, "n/a: win_rate not numeric")
    if wr_f > 1.0:
        wr_f /= 100.0
    edge = _pick(params or {}, "edge_type", "strategy_type", "edge") or \
           _pick(metrics, "edge_type", "strategy_type", "edge")
    edge_s = str(edge).lower() if edge else ""
    if wr_f <= TH["win_rate_flag"]:
        return _r(True, round(wr_f, 4), TH["win_rate_flag"], f"win_rate={wr_f:.2%}")
    if any(e in edge_s for e in _EDGE_EXEMPT):
        return _r(True, round(wr_f, 4), TH["win_rate_flag"], f"high WR, edge={edge_s} exempt")
    return _r(False, round(wr_f, 4), TH["win_rate_flag"],
              f"win_rate={wr_f:.2%} > {TH['win_rate_flag']:.0%} without edge")


def check_sharpe_sanity(metrics, trades, params):
    sharpe = _pick(metrics, "sharpe", "sharpe_ratio", "sr")
    if sharpe is None:
        return _r(True, None, None, "n/a: no sharpe")
    try:
        sh = float(sharpe)
    except (TypeError, ValueError):
        return _r(True, sharpe, None, "n/a: non-numeric")
    if sh <= TH["sharpe_flag"]:
        return _r(True, round(sh, 3), TH["sharpe_flag"], f"sharpe={sh:.2f}")
    years = _pick(metrics, "years", "n_years", "lookback_years", "horizon_years")
    if years is None or float(years) >= TH["min_sharpe_years_for_flag"]:
        return _r(False, round(sh, 3), TH["sharpe_flag"],
                  f"sharpe={sh:.2f} over {years or '?'}y")
    return _r(True, round(sh, 3), TH["sharpe_flag"], f"high but horizon {years}y<3y")


def check_turnover_consistency(metrics, trades, params):
    fee_bps = _pick(params or {}, "fee_bps", "taker_fee_bps", "fee_bp") or \
              _pick(metrics, "fee_bps", "taker_fee_bps")
    if fee_bps is None:
        return _r(True, None, None, "n/a: no fee_bps")
    reported = _pick(metrics, "total_fees", "fees_total", "total_fee_usd", "fees_usd")
    if reported is None or float(reported) == 0:
        return _r(True, None, None, "n/a: no reported fees")
    n = _pick(metrics, "trades_count", "n_trades", "n_fills")
    avg_notional = _pick(metrics, "avg_trade_notional", "avg_notional", "notional_per_trade")
    if trades:
        n = n or len(trades)
        if avg_notional is None:
            ns = [abs(float(t.get("qty", 0)) * float(t.get("price", 0))) for t in trades]
            avg_notional = sum(ns) / len(ns) if ns else 0.0
    if n is None or avg_notional is None:
        return _r(True, None, None, "n/a: no turnover metadata")
    try:
        n_i, avg_f = int(n), float(avg_notional)
    except (TypeError, ValueError):
        return _r(True, None, None, "n/a: non-numeric")
    recomputed = n_i * avg_f * float(fee_bps) / 1e4
    denom = abs(float(reported))
    if denom == 0:
        return _r(True, None, None, "n/a: reported=0")
    dev = abs(recomputed - denom) / denom * 100.0
    return _r(dev <= TH["turnover_dev_pct"], round(dev, 3), TH["turnover_dev_pct"],
              f"n={n_i} avg={avg_f:.2f} recomputed={recomputed:.2f} reported={denom:.2f}")


def check_dd_vs_vol(metrics, trades, params):
    max_dd = _pick(metrics, "max_dd", "max_drawdown", "max_dd_pct")
    vol = _pick(metrics, "annual_vol", "vol_annual", "volatility_annual", "ann_vol")
    if max_dd is None or vol is None:
        return _r(True, None, None, "n/a: no max_dd or annual_vol")
    try:
        dd, v = abs(float(max_dd)), float(vol)
    except (TypeError, ValueError):
        return _r(True, None, None, "n/a: non-numeric")
    if v <= 0:
        return _r(True, None, None, "n/a: vol<=0")
    ratio = dd / v
    return _r(ratio >= TH["dd_vol_ratio_flag"], round(ratio, 3), TH["dd_vol_ratio_flag"],
              f"max_dd={dd:.4f} vol={v:.4f} ratio={ratio:.3f}")


CHECKS = {
    "look_ahead":           check_look_ahead,
    "survivorship":         check_survivorship,
    "adjusted_prices":      check_adjusted_prices,
    "overfitting_signals":  check_overfitting_signals,
    "fee_consistency":      check_fee_consistency,
    "fill_realism":         check_fill_realism,
    "sharpe_sanity":        check_sharpe_sanity,
    "turnover_consistency": check_turnover_consistency,
    "dd_vs_vol":            check_dd_vs_vol,
}


def run_backtest_checks(metrics, trades, params=None):
    metrics = dict(metrics or {})
    params = dict(params or {})
    if params.get("asset_class") and not metrics.get("asset_class"):
        metrics["asset_class"] = params["asset_class"]
    rows = _rows(trades)
    is_eq = _is_equity(metrics, rows)
    out = {}
    for name, fn in CHECKS.items():
        try:
            out[name] = fn(metrics, rows, params)
        except Exception as e:
            log.exception("check %s crashed", name)
            out[name] = _r(False, "exception", None, f"crash: {e}")
        # dynamic severity: adjusted_prices critical only for equity
        if name == "adjusted_prices" and is_eq:
            out[name]["severity"] = "critical"
        else:
            out[name]["severity"] = SEVERITY.get(name, "warning")
    return out


