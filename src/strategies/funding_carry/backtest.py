"""Event-driven 90d funding-carry backtest (Binance public data)."""
from __future__ import annotations
import argparse, asyncio, json, logging, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import httpx, numpy as np, pandas as pd
from .config import FundingCarrySettings
from .signal import classify

log = logging.getLogger(__name__)
_POS_TO_DIR = {1: "long_spot_short_perp", -1: "short_spot_long_perp"}


def target_pos(funding_bps: float, basis_bps: float, s: FundingCarrySettings) -> int:
    d, _ = classify(funding_bps, basis_bps, s.min_funding_bps, s.max_basis_bps)
    if d == "long_spot_short_perp":
        return 1
    if d == "short_spot_long_perp":
        return -1
    return 0


def synthetic_data(symbols, days=90, seed=42, funding_mean_bps=1.6,
                   funding_phi=0.80, funding_sigma_bps=2.5,
                   basis_sigma_bps=12.0) -> Dict[str, Dict[str, pd.DataFrame]]:
    rng = np.random.default_rng(seed); n = days * 3
    ts = pd.date_range(end=pd.Timestamp.now(tz="UTC").normalize(),
                       periods=n, freq="8h")
    out = {}
    for sym in symbols:
        f = np.empty(n); f[0] = funding_mean_bps
        eps = rng.normal(0, funding_sigma_bps, n)
        for i in range(1, n):
            f[i] = funding_mean_bps + funding_phi * (f[i - 1] - funding_mean_bps) + eps[i]
        basis = rng.normal(0, basis_sigma_bps, n) * 0.4
        base = {"BTCUSDT": 60000.0, "ETHUSDT": 3000.0, "SOLUSDT": 150.0}.get(sym, 100.0)
        px = base * np.cumprod(1.0 + rng.normal(0, 0.004, n))
        out[sym] = {"funding": pd.DataFrame({"ts": ts, "funding_rate": f / 1e4}),
                    "spot": pd.DataFrame({"ts": ts, "close": px}),
                    "perp": pd.DataFrame({"ts": ts, "close": px * (1.0 + basis / 1e4)})}
    return out


def simulate_symbol(symbol, funding, spot, perp, s):
    sp = spot.sort_values("ts")[["ts", "close"]].rename(columns={"close": "spot_close"})
    pp = perp.sort_values("ts")[["ts", "close"]].rename(columns={"close": "perp_close"})
    f = funding.sort_values("ts")[["ts", "funding_rate"]].reset_index(drop=True)
    m = pd.merge_asof(f, sp.sort_values("ts"), on="ts", direction="backward")
    m = pd.merge_asof(m, pp.sort_values("ts"), on="ts", direction="backward")
    m = m.dropna(subset=["spot_close", "perp_close", "funding_rate"]).reset_index(drop=True)
    if len(m) < 3:
        return pd.DataFrame(columns=["ts", "symbol", "position", "pnl", "equity"]), []
    m["basis_bps"] = (m["perp_close"] - m["spot_close"]) / m["spot_close"] * 1e4
    capital = float(s.max_pos_per_symbol_usd)
    notional = capital * float(s.target_leverage)
    cost_bps = s.cost_bps_per_leg_change
    pos = 0; cash = 0.0; acc_f = acc_b = acc_fee = 0.0
    entry_basis = 0.0; entry_i = 0; trades, rows = [], []

    def close_trade(exit_i):
        nonlocal acc_f, acc_b, acc_fee, entry_i
        acc_fee += cost_bps / 1e4 * notional
        trades.append({"symbol": symbol, "entry_ts": m.at[entry_i, "ts"],
                       "exit_ts": m.at[exit_i, "ts"], "direction": _POS_TO_DIR[pos],
                       "entry_basis_bps": entry_basis, "funding_usd": acc_f,
                       "basis_usd": acc_b, "fees_usd": acc_fee,
                       "pnl_usd": acc_f + acc_b - acc_fee,
                       "hold_intervals": max(1, exit_i - entry_i)})
        acc_f = acc_b = acc_fee = 0.0

    n = len(m)
    for i in range(1, n):
        cash_prev = cash
        fb_prev = float(m.at[i - 1, "funding_rate"]) * 1e4
        b_prev = float(m.at[i - 1, "basis_bps"])
        desired = target_pos(fb_prev, b_prev, s)
        if desired != pos:
            if pos != 0:
                cash -= cost_bps / 1e4 * notional
                close_trade(i - 1)
            if desired != 0:
                cash -= cost_bps / 1e4 * notional
                acc_fee = cost_bps / 1e4 * notional
                entry_basis = b_prev; entry_i = i - 1
            pos = desired
        fb_i = float(m.at[i, "funding_rate"]) * 1e4
        b_i = float(m.at[i, "basis_bps"])
        pnl_f = pos * (fb_i / 1e4) * notional
        pnl_b = pos * ((b_prev - b_i) / 1e4) * notional
        cash += pnl_f + pnl_b
        if pos != 0:
            acc_f += pnl_f; acc_b += pnl_b
        rows.append({"ts": m.at[i, "ts"], "symbol": symbol, "position": pos,
                     "funding_bps": fb_i, "basis_bps": b_i,
                     "pnl": cash - cash_prev, "equity": capital + cash})
    if pos != 0:
        cash_prev = cash
        cash -= cost_bps / 1e4 * notional
        close_trade(n - 1)
        rows.append({"ts": m.at[n - 1, "ts"], "symbol": symbol, "position": 0,
                     "funding_bps": float(m.at[n - 1, "funding_rate"]) * 1e4,
                     "basis_bps": float(m.at[n - 1, "basis_bps"]),
                     "pnl": cash - cash_prev, "equity": capital + cash})
    return pd.DataFrame(rows), trades


def compute_metrics(daily_pnl, trades, total_capital, periods_per_day=3):
    daily_ret = daily_pnl / total_capital
    std = float(daily_ret.std(ddof=1)) if len(daily_ret) > 1 else 0.0
    mean = float(daily_ret.mean()) if len(daily_ret) else 0.0
    sharpe = (mean / std * np.sqrt(365.0)) if std > 1e-12 else 0.0
    cycle_ret = daily_pnl / periods_per_day / total_capital
    c_std = float(cycle_ret.std(ddof=1)) if len(cycle_ret) > 1 else 0.0
    c_mean = float(cycle_ret.mean()) if len(cycle_ret) else 0.0
    sharpe_cycle = (c_mean / c_std * np.sqrt(365.0 * periods_per_day)) if c_std > 1e-12 else 0.0
    equity = 1.0 + daily_ret.cumsum()
    max_dd = float((equity / equity.cummax() - 1.0).min()) if len(equity) else 0.0
    n_trades = len(trades)
    wins = sum(1 for t in trades if t["pnl_usd"] > 0)
    entry_bases = [abs(t["entry_basis_bps"]) for t in trades]
    return {"total_return": float(equity.iloc[-1] - 1.0) if len(equity) else 0.0,
            "sharpe": float(sharpe), "sharpe_per_cycle": float(sharpe_cycle),
            "max_dd": max_dd,
            "avg_basis_at_entry_bps": float(np.mean(entry_bases)) if entry_bases else 0.0,
            "hit_rate": float(wins / n_trades) if n_trades else 0.0,
            "trades_count": int(n_trades),
            "funding_pnl_usd": float(sum(t["funding_usd"] for t in trades)),
            "basis_pnl_usd": float(sum(t["basis_usd"] for t in trades)),
            "fees_usd": float(sum(t["fees_usd"] for t in trades)),
            "avg_hold_intervals": float(np.mean([t["hold_intervals"] for t in trades])) if n_trades else 0.0,
            "total_capital_usd": float(total_capital)}


def run_backtest(settings, data=None, seed=None):
    if data is None:
        data = asyncio.run(fetch_history(settings))
    frames, trades = [], []
    for sym in settings.symbols:
        if sym not in data:
            log.warning("no data for %s", sym); continue
        fr, tr = simulate_symbol(sym, data[sym]["funding"],
                                 data[sym]["spot"], data[sym]["perp"], settings)
        if not fr.empty:
            frames.append(fr); trades.extend(tr)
    if not frames:
        empty = pd.DataFrame(columns=["ts", "pnl", "equity"])
        return empty, compute_metrics(pd.Series(dtype=float), [], 1.0), []
    stacked = pd.concat(frames, ignore_index=True)
    stacked = stacked.assign(ts=pd.to_datetime(stacked["ts"], utc=True))
    total_capital = settings.max_pos_per_symbol_usd * max(1, len(settings.symbols))
    daily_pnl = stacked.set_index("ts")["pnl"].resample("1D").sum().fillna(0.0)
    daily = daily_pnl.rename("pnl").to_frame()
    daily["ret"] = daily["pnl"] / total_capital
    daily["equity"] = 1.0 + daily["ret"].cumsum()
    m = compute_metrics(daily_pnl, trades, total_capital, settings.funding_intervals_per_day)
    m["symbols"] = list(settings.symbols); m["days"] = settings.days
    m["cost_bps_per_leg_change"] = settings.cost_bps_per_leg_change
    m["round_trip_cost_bps"] = settings.round_trip_cost_bps
    m["generated_at"] = datetime.now(timezone.utc).isoformat()
    return daily, m, trades


def save_results(daily, metrics, trades, settings):
    out_dir = Path(settings.results_dir); out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    p = out_dir / f"funding_carry_{stamp}.parquet"
    daily.to_parquet(p, index=True)
    with open(out_dir / f"funding_carry_{stamp}.metrics.json", "w") as fh:
        json.dump(metrics, fh, indent=2, default=str)
    if trades:
        pd.DataFrame(trades).to_parquet(out_dir / f"funding_carry_{stamp}.trades.parquet",
                                        index=False)
    return p


async def _get(client, url, params, tries=5):
    for attempt in range(tries):
        try:
            r = await client.get(url, params=params, timeout=30.0)
            if r.status_code in (418, 429):
                await asyncio.sleep(2 ** attempt); continue
            r.raise_for_status(); return r.json()
        except Exception:
            if attempt == tries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    return []


async def _fetch_funding(client, symbol, days, s):
    end = int(time.time() * 1000); start = end - days * 86_400_000
    out = []; cursor = start
    while cursor < end:
        batch = await _get(client, f"{s.binance_fapi}/fapi/v1/fundingRate",
                           {"symbol": symbol, "startTime": cursor,
                            "endTime": end, "limit": 1000})
        if not batch:
            break
        out.extend(batch)
        last = batch[-1]["fundingTime"]
        if last <= cursor or len(batch) < 1000:
            break
        cursor = last + 1
    return out


async def _fetch_klines(client, base, path, symbol, days, interval="8h"):
    end = int(time.time() * 1000); start = end - days * 86_400_000
    return await _get(client, f"{base}{path}",
                      {"symbol": symbol, "interval": interval,
                       "startTime": start, "endTime": end, "limit": 1000})


async def fetch_history(settings, client=None):
    own = client is None
    if own:
        client = httpx.AsyncClient(timeout=30.0)
    out = {}
    for sym in settings.symbols:
        try:
            fr, sp, pp = await asyncio.gather(
                _fetch_funding(client, sym, settings.days, settings),
                _fetch_klines(client, settings.binance_spot, "/api/v3/klines",
                              sym, settings.days),
                _fetch_klines(client, settings.binance_fapi, "/fapi/v1/klines",
                              sym, settings.days))
        except Exception as exc:
            log.error("history %s: %s", sym, exc); continue
        if not fr or not sp or not pp:
            log.warning("incomplete history %s", sym); continue
        funding = pd.DataFrame({
            "ts": pd.to_datetime([r["fundingTime"] for r in fr], unit="ms", utc=True),
            "funding_rate": [float(r["fundingRate"]) for r in fr]
        }).drop_duplicates("ts").sort_values("ts")
        spot = pd.DataFrame({
            "ts": pd.to_datetime([r[0] for r in sp], unit="ms", utc=True),
            "close": [float(r[4]) for r in sp]
        }).drop_duplicates("ts").sort_values("ts")
        perp = pd.DataFrame({
            "ts": pd.to_datetime([r[0] for r in pp], unit="ms", utc=True),
            "close": [float(r[4]) for r in pp]
        }).drop_duplicates("ts").sort_values("ts")
        out[sym] = {"funding": funding, "spot": spot, "perp": perp}
    if own:
        await client.aclose()
    return out


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=None)
    p.add_argument("--symbols", type=str, default=None)
    p.add_argument("--synthetic", action="store_true")
    a = p.parse_args()
    s = FundingCarrySettings()
    if a.days is not None:
        s.days = a.days
    if a.symbols:
        s.symbols = [x.strip().upper() for x in a.symbols.split(",") if x.strip()]
    data = synthetic_data(s.symbols, s.days, s.seed) if a.synthetic else None
    daily, m, trades = run_backtest(s, data=data)
    path = save_results(daily, m, trades, s)
    print(f"\n=== Funding carry backtest ({s.days}d) ===")
    for k in ("total_return", "sharpe", "sharpe_per_cycle", "max_dd",
              "avg_basis_at_entry_bps", "hit_rate", "trades_count",
              "funding_pnl_usd", "basis_pnl_usd", "fees_usd"):
        print(f"{k:>26}: {m.get(k)}")
    print(f"{'saved_to':>26}: {path}\n")


if __name__ == "__main__":
    main()
