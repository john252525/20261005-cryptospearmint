"""Tests for backtest_to_metrics converter."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import backtest_to_metrics as btm  # noqa: E402


def _grid_csv(p):
    p.write_text(
        "min_funding,tier,trades_count,funding_pnl_usd,fees_usd,net_pnl_usd,"
        "sharpe,max_dd,hit_rate\n"
        "0.5,vip0,10,5.0,50.0,-45.0,-2.0,-0.05,0.1\n"
        "1.0,vip0,5,3.0,25.0,-22.0,-1.5,-0.03,0.2\n"
        "2.0,vip1_bnb,0,0.0,0.0,0.0,0.0,0.0,0.0\n"
    )


def _trades_parquet(p):
    import pandas as pd
    df = pd.DataFrame([
        {"signal_ts": "2025-01-15T08:00:00Z", "fill_ts": "2025-01-15T08:01:00Z",
         "qty": 1.0, "price": 42000.0, "fee": 21.0, "pnl": 10.0},
        {"signal_ts": "2025-01-15T09:00:00Z", "fill_ts": "2025-01-15T09:01:00Z",
         "qty": 1.0, "price": 42100.0, "fee": 21.0, "pnl": -5.0},
        {"signal_ts": "2025-01-15T10:00:00Z", "fill_ts": "2025-01-15T10:01:00Z",
         "qty": 1.0, "price": 42200.0, "fee": 21.0, "pnl": 8.0},
    ])
    df.to_parquet(p, index=False)


def test_convert_grid_csv(tmp_path):
    src = tmp_path / "funding_carry_grid_20261017.csv"
    out = tmp_path / "funding_carry_grid_20261017.metrics.json"
    _grid_csv(src)
    r = btm.convert(src, out, force=False)
    assert r["status"] == "ok", r
    m = json.loads(out.read_text())
    for k in ("sharpe", "max_dd", "win_rate", "trades_count",
              "total_fees", "fee_bps", "years", "grid_size", "grid_top_metrics"):
        assert k in m, f"missing {k}"
    assert m["trades_count"] == 10
    assert m["grid_size"] == 3
    assert len(m["grid_top_metrics"]) == 3


def test_convert_trades_parquet(tmp_path):
    src = tmp_path / "funding_carry.trades.parquet"
    out = tmp_path / "funding_carry.trades.metrics.json"
    _trades_parquet(src)
    r = btm.convert(src, out, force=False)
    assert r["status"] == "ok", r
    m = json.loads(out.read_text())
    assert m["trades_count"] == 3
    assert m["total_fees"] == 63.0
    assert 0 < m["win_rate"] < 1.0
    assert m.get("sharpe") is not None and "max_dd" in m


def test_idempotent_skip(tmp_path):
    src = tmp_path / "funding_carry_grid_20261017.csv"
    out = tmp_path / "funding_carry_grid_20261017.metrics.json"
    _grid_csv(src)
    out.write_text('{"sentinel": true}')
    r = btm.convert(src, out, force=False)
    assert r["status"] == "skipped", r
    assert r["reason"] == "exists"
    assert json.loads(out.read_text()) == {"sentinel": True}


def test_force_overwrite(tmp_path):
    src = tmp_path / "funding_carry_grid_20261017.csv"
    out = tmp_path / "funding_carry_grid_20261017.metrics.json"
    _grid_csv(src)
    out.write_text('{"sentinel": true}')
    r = btm.convert(src, out, force=True)
    assert r["status"] == "ok", r
    m = json.loads(out.read_text())
    assert "sentinel" not in m
    assert m["trades_count"] == 10
