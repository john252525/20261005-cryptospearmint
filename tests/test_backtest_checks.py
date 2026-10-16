"""Synthetic tests for the general backtest QA framework."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa.backtest_checks import run_backtest_checks  # noqa: E402
from qa.overfitting import parameter_sensitivity, rank_stability, walk_forward  # noqa: E402


# -------------------------------------------------- helpers
def _good_trades():
    return [
        {"signal_ts": "2025-01-15T08:00:00.000Z", "fill_ts": "2025-01-15T08:01:00.000Z",
         "signal_bar": 1, "fill_bar": 2, "symbol": "BTCUSDT",
         "qty": 1.0, "price": 42000.0},
        {"signal_ts": "2025-01-15T09:00:00.000Z", "fill_ts": "2025-01-15T09:01:00.000Z",
         "signal_bar": 3, "fill_bar": 4, "symbol": "BTCUSDT",
         "qty": 1.0, "price": 42100.0},
    ]


def _good_metrics():
    return {
        "trades_count": 2,
        "avg_trade_notional": 42050.0,
        "total_fees": 2 * 42050.0 * 5.0 / 1e4,
        "fee_bps": 5.0,
        "sharpe": 1.2,
        "max_dd": 0.12,
        "annual_vol": 0.15,
        "win_rate": 0.55,
        "years": 2.0,
        "asset_class": "crypto",
    }


def _good_params():
    return {"fee_bps": 5.0, "edge_type": "funding_carry"}


def _fail_names(results):
    return [k for k, r in results.items() if not r["passed"]]


# -------------------------------------------------- tests
def test_honest_case_all_pass():
    r = run_backtest_checks(_good_metrics(), _good_trades(), _good_params())
    assert _fail_names(r) == [], _fail_names(r)


def test_look_ahead_same_bar_fill():
    trades = _good_trades()
    for t in trades:
        t["fill_bar"] = t["signal_bar"]
    r = run_backtest_checks(_good_metrics(), trades, _good_params())
    assert r["look_ahead"]["passed"] is False


def test_look_ahead_fill_before_signal_ts():
    trades = _good_trades()
    trades[0]["fill_ts"] = "2025-01-15T07:59:59.000Z"
    r = run_backtest_checks(_good_metrics(), trades, _good_params())
    assert r["look_ahead"]["passed"] is False


def test_survivorship_equity_no_delisted():
    m = {"asset_class": "equity", "years": 5.0, "delisted_count": 0,
         "universe_count_start": 500, "universe_count_end": 500}
    r = run_backtest_checks(m, [], {"fee_bps": 5.0})
    assert r["survivorship"]["passed"] is False


def test_survivorship_equity_shrinking_universe_ok():
    m = {"asset_class": "equity", "years": 5.0, "delisted_count": 42,
         "universe_count_start": 500, "universe_count_end": 480}
    r = run_backtest_checks(m, [], {"fee_bps": 5.0})
    assert r["survivorship"]["passed"] is True


def test_survivorship_crypto_na():
    r = run_backtest_checks({"asset_class": "crypto", "years": 5.0}, [], {"fee_bps": 5.0})
    assert r["survivorship"]["passed"] is True


def test_adjusted_prices_equity_missing():
    r = run_backtest_checks({"asset_class": "equity", "years": 5.0},
                            [{"symbol": "AAPL", "price": 100.0, "qty": 1.0}],
                            {"fee_bps": 5.0})
    assert r["adjusted_prices"]["passed"] is False


def test_adjusted_prices_equity_metadata_ok():
    r = run_backtest_checks({"asset_class": "equity", "years": 5.0, "adjusted": True},
                            [], {"fee_bps": 5.0})
    assert r["adjusted_prices"]["passed"] is True


def test_overfitting_grid_over_100_sigma_gap():
    m = {"grid_size": 500,
         "grid_top_metrics": [10.0, 2.0, 1.9, 1.85, 1.8, 1.75, 1.7, 1.65, 1.6, 1.55]}
    r = run_backtest_checks(m, [], {"fee_bps": 5.0})
    assert r["overfitting_signals"]["passed"] is False


def test_overfitting_grid_small_na():
    r = run_backtest_checks({"grid_size": 20}, [], {"fee_bps": 5.0})
    assert r["overfitting_signals"]["passed"] is True


def test_overfitting_grid_big_but_stable_scored():
    m = {"grid_size": 500,
         "grid_top_metrics": [2.0, 1.95, 1.9, 1.85, 1.8, 1.75, 1.7]}
    r = run_backtest_checks(m, [], {"fee_bps": 5.0})
    assert r["overfitting_signals"]["passed"] is True


def test_fee_consistency_good_and_bad():
    m_ok = _good_metrics()
    assert run_backtest_checks(m_ok, _good_trades(), _good_params())["fee_consistency"]["passed"] is True
    m_bad = dict(m_ok); m_bad["total_fees"] = 999.0
    assert run_backtest_checks(m_bad, _good_trades(), _good_params())["fee_consistency"]["passed"] is False


def test_win_rate_above_70_no_edge_flagged():
    m = _good_metrics(); m["win_rate"] = 0.80; m.pop("asset_class", None)
    r = run_backtest_checks(m, _good_trades(),
                            {"fee_bps": 5.0, "edge_type": "momentum"})
    assert r["fill_realism"]["passed"] is False


def test_win_rate_above_70_with_carry_edge_ok():
    m = _good_metrics(); m["win_rate"] = 0.80
    r = run_backtest_checks(m, _good_trades(),
                            {"fee_bps": 5.0, "edge_type": "funding_carry"})
    assert r["fill_realism"]["passed"] is True


def test_sharpe_above_4_over_3y_flagged():
    m = _good_metrics(); m["sharpe"] = 5.2; m["years"] = 4.0
    r = run_backtest_checks(m, _good_trades(), _good_params())
    assert r["sharpe_sanity"]["passed"] is False


def test_sharpe_above_4_short_horizon_ok():
    m = _good_metrics(); m["sharpe"] = 5.2; m["years"] = 1.0
    r = run_backtest_checks(m, _good_trades(), _good_params())
    assert r["sharpe_sanity"]["passed"] is True


def test_turnover_consistency_flagged_when_mismatch():
    m = _good_metrics(); m["total_fees"] = 42.0; m["trades_count"] = 1000
    r = run_backtest_checks(m, [], _good_params())
    assert r["turnover_consistency"]["passed"] is False


def test_dd_vs_vol_ratio_flagged():
    m = _good_metrics(); m["max_dd"] = 0.02; m["annual_vol"] = 0.20
    r = run_backtest_checks(m, _good_trades(), _good_params())
    assert r["dd_vs_vol"]["passed"] is False


def test_params_missing_is_graceful():
    r = run_backtest_checks({"sharpe": 1.0}, [], None)
    assert isinstance(r, dict) and len(r) == 9
    assert all(isinstance(v, dict) and "passed" in v for v in r.values())


def test_sensitivity_on_linear_grid_flags_overfit():
    scan = [{"p": p, "q": q, "sharpe": float(p) ** 4}
            for p in (1, 2, 3, 4) for q in (0.1, 0.2, 0.3)]
    s = parameter_sensitivity(scan, metric="sharpe", elasticity_flag=5.0)
    assert s["params"]["p"]["flag"] is True, s
    assert s["params"]["q"]["flag"] is False, s


def test_rank_stability_flat_grid_unstable():
    scan = [{"x": i, "sharpe": 1.0} for i in range(50)]
    st = rank_stability(scan, metric="sharpe", top_k=5, n_trials=30, seed=1)
    assert st["score"] <= 0.8, st


def test_rank_stability_clear_winner_stable():
    scan = [{"x": i, "sharpe": 1.0 + 0.5 * i} for i in range(20)]
    st = rank_stability(scan, metric="sharpe", top_k=5, n_trials=30, seed=1)
    assert st["score"] >= 0.9, st


def test_walk_forward_detects_degradation():
    wf = walk_forward(lambda a: {"sharpe": 3.0},
                      lambda a: {"sharpe": 0.3},
                      windows=[("a", "b"), ("c", "d")], metric="sharpe")
    assert wf["flag"] is True, wf
    assert wf["n_windows"] == 2


def test_walk_forward_keeps_edge():
    wf = walk_forward(lambda a: {"sharpe": 2.0},
                      lambda a: {"sharpe": 1.8},
                      windows=[("a", "b"), ("c", "d")], metric="sharpe")
    assert wf["flag"] is False, wf
