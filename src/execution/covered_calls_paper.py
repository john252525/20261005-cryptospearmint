"""Covered call paper runner — BTC, +10% OTM, 30-day tenor.

PAPER ONLY. No orders anywhere. Real market data, simulated fills.

DATA SOURCE NOTE (important):
  Deribit production API (www.deribit.com) is BLOCKED from this host (all hosts return
  connection timeout). Deribit testnet is reachable but its DVOL history is garbage
  (2024-01-10 showed 169.6% where real was ~45-50%). So this runner uses the REAL
  Binance options API (eapi.binance.com), which is reachable and returns live markIV
  and markPrice. That is a factual substitute, not the original spec.

Usage:
  python3 -m src.execution.covered_calls_paper --once      # single check
  python3 -m src.execution.covered_calls_paper             # weekly loop (daemon)
"""
from __future__ import annotations
import argparse, asyncio, json, sqlite3, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests
import numpy as np
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / 'state' / 'covered_calls.db'
JOURNAL = ROOT / 'journal' / 'covered_calls.jsonl'

NOTIONAL = 100.0        # $100 paper notional
K_MULT = 1.10           # +10% OTM
TENOR_DAYS = 30
FEE_BPS = 3             # 3 bps of notional per open
EAPI = 'https://eapi.binance.com/eapi/v1'


def _init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS positions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        open_ts TEXT, expiry_ts TEXT, spot REAL, strike REAL, iv REAL,
        premium_usd REAL, notional REAL, status TEXT DEFAULT 'open',
        close_ts TEXT, spot_at_expiry REAL, outcome TEXT,
        pnl_usd REAL, pnl_pct REAL)""")
    c.commit()
    return c


def _log(rec: dict):
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open('a') as f:
        f.write(json.dumps(rec, default=str) + '\n')


def _spot() -> float:
    r = requests.get(f'{EAPI}/index', params={'underlying': 'BTCUSDT'}, timeout=20).json()
    return float(r['indexPrice'])


def _atm_iv_at_tenor(target_dte: int = TENOR_DAYS) -> tuple[float, str]:
    """Live ATM IV from Binance options closest to target DTE. Returns (iv, symbol)."""
    marks = requests.get(f'{EAPI}/mark', timeout=25).json()
    info = requests.get(f'{EAPI}/exchangeInfo', timeout=25).json()
    meta = {x['symbol']: x for x in info['optionSymbols']}
    spot = _spot()
    now = datetime.now(timezone.utc)
    best = None
    for m in marks:
        s = m['symbol']
        if not s.startswith('BTC-') or s not in meta:
            continue
        md = meta[s]
        if md['side'] != 'CALL':
            continue
        exp = datetime.fromtimestamp(md['expiryDate'] / 1000, tz=timezone.utc)
        dte = (exp - now).days
        if dte < 5 or dte > 120:
            continue
        k = float(md['strikePrice'])
        moneyness = abs(k / spot - 1.0)
        iv = float(m.get('markIV') or 0)
        if iv <= 0 or moneyness > 0.04:
            continue
        score = abs(dte - target_dte) + moneyness * 200
        if best is None or score < best[0]:
            best = (score, iv, s, dte)
    if best is None:
        raise RuntimeError('no suitable ATM call found on Binance options')
    return best[1], best[2]


def _bs_call(S: float, K: float, T: float, sig: float) -> float:
    if sig <= 0 or T <= 0:
        return max(S - K, 0.0)
    d1 = (np.log(S / K) + 0.5 * sig * sig * T) / (sig * np.sqrt(T))
    d2 = d1 - sig * np.sqrt(T)
    return S * norm.cdf(d1) - K * norm.cdf(d2)


def _settle_due(c):
    """Settle any position whose expiry has passed, using current spot as proxy."""
    now = datetime.now(timezone.utc)
    open_rows = c.execute(
        "SELECT id, expiry_ts, strike, spot, premium_usd, notional FROM positions WHERE status='open'"
    ).fetchall()
    if not open_rows:
        return
    spot_now = _spot()
    for pid, exp_ts, strike, spot0, prem, notional in open_rows:
        exp = datetime.fromisoformat(exp_ts)
        if now < exp:
            continue
        # covered call P&L: (spot move) + premium - capped upside
        spot_pnl = notional * (spot_now - spot0) / spot0
        capped = notional * max(0.0, spot_now - strike) / spot0
        pnl = spot_pnl + prem - capped
        outcome = 'assigned' if capped > 0 else 'expired'
        c.execute(
            "UPDATE positions SET status='closed', close_ts=?, spot_at_expiry=?, outcome=?, "
            "pnl_usd=?, pnl_pct=? WHERE id=?",
            (now.isoformat(), spot_now, outcome, pnl, pnl / notional * 100, pid))
        c.commit()
        _log({'ts': now.isoformat(), 'event': 'settle', 'spot': spot_now, 'strike': strike,
              'outcome': outcome, 'pnl_usd': round(pnl, 4), 'pnl_pct': round(pnl / notional * 100, 3)})
        print(f"  SETTLE id={pid} {outcome} spot={spot_now:,.0f} strike={strike:,.0f} pnl=${pnl:+.2f}")


def one_cycle(force: bool = False):
    c = _init_db()
    _settle_due(c)

    now = datetime.now(timezone.utc)
    is_monday = now.weekday() == 0
    open_count = c.execute("SELECT COUNT(*) FROM positions WHERE status='open'").fetchone()[0]
    print(f"[{now.isoformat()}] weekday={now.strftime('%A')} monday={is_monday} open_positions={open_count}")

    if open_count > 0 and not force:
        print("  position already open (covered call is 1-per-underlying at a time) — holding")
        _log({'ts': now.isoformat(), 'event': 'hold', 'open_positions': open_count})
        c.close()
        return

    spot = _spot()
    try:
        iv, iv_symbol = _atm_iv_at_tenor(TENOR_DAYS)
    except Exception as e:
        print(f"  IV fetch failed: {e}")
        _log({'ts': now.isoformat(), 'event': 'error', 'error': str(e)[:120]})
        c.close()
        return

    K = spot * K_MULT
    T = TENOR_DAYS / 365
    prem = _bs_call(spot, K, T, iv)
    fee = NOTIONAL * FEE_BPS / 1e4
    prem_usd = NOTIONAL * prem / spot - fee
    expiry = now + timedelta(days=TENOR_DAYS)

    c.execute(
        "INSERT INTO positions(open_ts, expiry_ts, spot, strike, iv, premium_usd, notional, status) "
        "VALUES(?,?,?,?,?,?,?,'open')",
        (now.isoformat(), expiry.isoformat(), spot, K, iv, prem_usd, NOTIONAL))
    c.commit()
    pid = c.execute("SELECT last_insert_rowid()").fetchone()[0]

    rec = {'ts': now.isoformat(), 'event': 'open', 'position_id': pid,
           'btc_spot': round(spot, 2), 'strike': round(K, 2), 'iv': round(iv, 4),
           'iv_source_symbol': iv_symbol, 'premium_usd': round(prem_usd, 4),
           'premium_pct_of_spot': round(prem / spot * 100, 4), 'notional': NOTIONAL,
           'expiry': expiry.isoformat(), 'status': 'open'}
    _log(rec)
    print(f"  OPEN covered call: spot=${spot:,.0f} strike=${K:,.0f} (+10%) IV={iv:.1%} "
          f"premium=${prem_usd:+.2f} ({prem/spot*100:.2f}% of spot) expiry={expiry.date()}")
    print(f"  journal -> {JOURNAL}")
    c.close()


def summary():
    c = _init_db()
    rows = c.execute("SELECT status, COUNT(*), COALESCE(SUM(pnl_usd),0) FROM positions GROUP BY status").fetchall()
    print("\n=== PAPER COVERED CALLS SUMMARY ===")
    total_pnl = 0.0
    for status, n, pnl in rows:
        print(f"  {status:8s}: {n} positions, P&L=${pnl:+.2f}")
        total_pnl += pnl
    print(f"  TOTAL P&L: ${total_pnl:+.2f}")
    c.close()


async def loop_forever(poll_seconds: int = 3600):
    print(f"[paper] covered calls loop, poll={poll_seconds}s, $100 notional, +10% OTM 30d")
    while True:
        try:
            one_cycle()
        except Exception as e:
            print(f"  cycle error: {type(e).__name__}: {e}")
        await asyncio.sleep(poll_seconds)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--force', action='store_true', help='open even if a position is already open')
    ap.add_argument('--summary', action='store_true')
    ap.add_argument('--poll', type=int, default=3600)
    a = ap.parse_args()
    if a.summary:
        summary()
    elif a.once:
        one_cycle(force=a.force)
    else:
        asyncio.run(loop_forever(a.poll))
