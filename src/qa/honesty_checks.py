"""QA honesty checks for funding-carry paper pipeline."""
from __future__ import annotations
import json, logging, os, sqlite3, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("qa.honesty")
TH = {
    "fee_deviation_pct": 5.0, "min_slippage_bps": 0.5, "min_latency_ms": 80.0,
    "funding_hours_utc": {0, 8, 16}, "funding_tolerance_min": 5,
    "limit_touch_atol_bps": 0.5, "leg_qty_mismatch_pct": 0.5,
    "delta_pct_nav": 2.0, "conflict_window_s": 1.0, "reconcile_dev_pct": 0.5,
    "funding_max_pct_nav_per_day": 0.3, "alert_streak": 2,
}
FEES = {"binance_usdm": {"taker": 5.0, "maker": 2.0},
        "binance_spot": {"taker": 10.0, "maker": 10.0},
        "bybit_linear": {"taker": 5.5, "maker": 2.0},
        "bybit_spot":   {"taker": 10.0, "maker": 10.0}}


def _ts(s):
    if isinstance(s, (int, float)):
        return float(s) / (1.0 if abs(s) < 1e12 else 1e3)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).timestamp()


def _load(p):
    out = []
    for ln, line in enumerate(open(p, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            log.error("journal line %d: %s", ln, e)
    return out


def _iter(events, *t):
    w = set(t)
    return [e for e in events if e.get("event_type") in w]


def _r(passed, value, threshold, msg):
    return {"passed": bool(passed), "value": value, "threshold": threshold, "message": msg}


def check_fees_match_schedule(ev, cfg):
    sc = FEES.get(cfg.get("venue", "binance_usdm"), FEES["binance_usdm"])
    devs = []
    for e in _iter(ev, "fill"):
        exp = sc.get(e.get("liquidity", "taker"), sc["taker"])
        n = abs(float(e.get("qty", 0)) * float(e.get("price", 0)))
        if n < 10:
            continue
        act = abs(float(e.get("fee", 0))) / n * 1e4
        devs.append(abs(act - exp) / exp * 100)
    if not devs:
        return _r(False, None, TH["fee_deviation_pct"], "no fills>$10")
    w = max(devs)
    return _r(w <= TH["fee_deviation_pct"], round(w, 3), TH["fee_deviation_pct"],
              f"worst={w:.2f}% over {len(devs)} fills")


def check_slippage_simulated(ev, cfg):
    vals, bad = [], []
    for e in _iter(ev, "fill"):
        if e.get("order_type") != "market":
            continue
        mid, px, side = float(e["mid"]), float(e["price"]), e["side"]
        bps = abs(px - mid) / mid * 1e4
        adverse = (side == "buy" and px >= mid) or (side == "sell" and px <= mid)
        vals.append(bps)
        if bps < TH["min_slippage_bps"] or not adverse:
            bad.append(bps)
    if not vals:
        return _r(True, 0, TH["min_slippage_bps"], "no market fills")
    m = min(vals)
    return _r(m >= TH["min_slippage_bps"] and not bad, round(m, 4),
              TH["min_slippage_bps"], f"min={m:.3f} viol={len(bad)}")


def check_latency_recorded(ev, cfg):
    sub = {e["order_id"]: _ts(e["ts"]) for e in _iter(ev, "order_submit")}
    lat, bad = [], 0
    for e in _iter(ev, "fill"):
        oid = e.get("order_id")
        if oid not in sub:
            continue
        ms = (_ts(e["ts"]) - sub[oid]) * 1000
        lat.append(ms)
        if ms < TH["min_latency_ms"]:
            bad += 1
    if not lat:
        return _r(False, None, TH["min_latency_ms"], "no submit/fill pairs")
    m = min(lat)
    return _r(m >= TH["min_latency_ms"], round(m, 2), TH["min_latency_ms"],
              f"min={m:.2f}ms viol={bad}")


def check_funding_cadence(ev, cfg):
    tol = TH["funding_tolerance_min"] * 60
    bad, n = 0, 0
    for e in _iter(ev, "funding_credit"):
        n += 1
        dt = datetime.fromtimestamp(_ts(e["ts"]), tz=timezone.utc)
        sf = min(abs(((dt.hour - H) % 24) * 3600 + dt.minute * 60 + dt.second)
                 for H in TH["funding_hours_utc"])
        sf = min(sf, 24 * 3600 - sf)
        if sf > tol:
            bad += 1
    return _r(bool(n) and not bad, bad, 0, f"funding_events={n} off_window={bad}")


def check_limit_fills_crossed(ev, cfg):
    bad, n = 0, 0
    for e in _iter(ev, "fill"):
        if e.get("order_type") != "limit":
            continue
        n += 1
        t = e.get("market_touch")
        if t is None:
            bad += 1
            continue
        atol = e["price"] * TH["limit_touch_atol_bps"] / 1e4
        if e["side"] == "buy" and t > e["price"] + atol:
            bad += 1
        if e["side"] == "sell" and t < e["price"] - atol:
            bad += 1
    return _r(not bad, bad, 0, f"limit_fills={n} uncrossed={bad}")


def check_ts_monotonic(ev, cfg):
    prev, bad = None, 0
    for i, e in enumerate(ev):
        ts = _ts(e["ts"])
        if prev is not None and ts < prev:
            bad += 1
            log.error("non-monotonic at line %d", i)
        prev = ts
    return _r(bad == 0, bad, 0, f"non_monotonic={bad}")


def check_both_legs_executed(ev, cfg):
    opens = {e["position_id"]: {"spot": None, "perp": None}
             for e in _iter(ev, "position_open")}
    for e in _iter(ev, "fill"):
        pid, leg = e.get("position_id"), e.get("leg")
        if pid in opens and leg in ("spot", "perp"):
            opens[pid][leg] = e
    bad = 0
    for _, l in opens.items():
        if not l["spot"] or not l["perp"]:
            bad += 1
            continue
        sq, pq = abs(float(l["spot"]["qty"])), abs(float(l["perp"]["qty"]))
        if abs(sq - pq) / max(sq, 1e-12) * 100 > TH["leg_qty_mismatch_pct"]:
            bad += 1
    return _r(not bad and bool(opens), bad, 0, f"opens={len(opens)} broken={bad}")


def check_delta_within_target(ev, cfg):
    bad, n, w = 0, 0, 0.0
    for e in _iter(ev, "delta_snapshot"):
        n += 1
        nav = float(e["nav_usd"])
        pct = abs(float(e["delta_usd"])) / nav * 100 if nav else 0.0
        w = max(w, pct)
        if pct > TH["delta_pct_nav"]:
            bad += 1
    return _r(not bad, round(w, 4), TH["delta_pct_nav"], f"snapshots={n} breaches={bad}")


def check_funding_reversal_closed(ev, cfg):
    by_sym, closes = defaultdict(list), defaultdict(list)
    for e in _iter(ev, "funding_credit"):
        by_sym[e["symbol"]].append(e)
    for e in _iter(ev, "position_close"):
        closes[e["symbol"]].append(_ts(e["ts"]))
    bad = 0
    for s, es in by_sym.items():
        es.sort(key=lambda e: _ts(e["ts"]))
        for a, b in zip(es, es[1:]):
            if a["funding_rate"] * b["funding_rate"] < 0:
                tf = _ts(b["ts"])
                if not any(t > tf for t in closes.get(s, [])):
                    bad += 1
    return _r(not bad, bad, 0, f"unclosed_flips={bad}")


def check_no_conflicting_orders(ev, cfg):
    by_key = defaultdict(list)
    for e in _iter(ev, "order_submit"):
        m = e.get("market") or e.get("leg") or cfg.get("default_market", "perp")
        by_key[(e["symbol"], m)].append(_ts(e["ts"]))
    bad = 0
    for ts in by_key.values():
        ts.sort()
        for a, b in zip(ts, ts[1:]):
            if b - a < TH["conflict_window_s"]:
                bad += 1
    return _r(bad == 0, bad, 0, f"conflicts={bad} groups={len(by_key)}")


def check_reconcile_with_testnet(ev, cfg):
    db = cfg.get("sqlite_path")
    if not db or not Path(db).exists():
        return _r(False, None, TH["reconcile_dev_pct"], "no sqlite/reconcile log")
    con = sqlite3.connect(db)
    try:
        rows = con.execute("SELECT ts,dev_pct,ok,detail FROM reconcile_log "
                           "ORDER BY ts DESC LIMIT 24").fetchall()
    except sqlite3.OperationalError as e:
        return _r(False, None, TH["reconcile_dev_pct"], f"reconcile_log missing: {e}")
    finally:
        con.close()
    if not rows:
        return _r(False, None, TH["reconcile_dev_pct"], "no reconcile history")
    real, dry = [], 0
    for ts, dev, ok, d in rows:
        try:
            dj = json.loads(d) if d else {}
        except json.JSONDecodeError:
            dj = {}
        if dj.get("dry_run"):
            dry += 1
            continue
        real.append((ts, dev, ok))
    if not real:
        return _r(False, None, TH["reconcile_dev_pct"],
                  f"only dry_run entries ({dry}); need real venue reconcile")
    oks = [r for r in real if r[2]]
    if len(oks) < len(real) * 0.9:
        return _r(False, round(min(r[1] for r in real), 4),
                  TH["reconcile_dev_pct"], f"ok_rate={len(oks)}/{len(real)} <90%")
    w = max(r[1] for r in real)
    return _r(w <= TH["reconcile_dev_pct"], round(w, 4),
              TH["reconcile_dev_pct"], f"real_windows={len(real)} worst={w:.3f}%")


def check_funding_income_sanity(ev, cfg):
    per_day, nav = defaultdict(float), None
    for e in _iter(ev, "funding_credit"):
        day = datetime.fromtimestamp(_ts(e["ts"]), tz=timezone.utc).date().isoformat()
        per_day[day] += float(e["amount_usd"])
        nav = float(e.get("nav_usd", nav or 0.0))
    if not per_day or not nav:
        return _r(True, 0.0, TH["funding_max_pct_nav_per_day"], "no funding / no nav")
    wp = max(per_day.values()) / nav * 100
    return _r(wp <= TH["funding_max_pct_nav_per_day"], round(wp, 4),
              TH["funding_max_pct_nav_per_day"], f"worst_pct_nav={wp:.4f}%")


CHECKS = {
    "fees_match_schedule":     check_fees_match_schedule,
    "slippage_simulated":      check_slippage_simulated,
    "latency_recorded":        check_latency_recorded,
    "funding_cadence":         check_funding_cadence,
    "limit_fills_crossed":     check_limit_fills_crossed,
    "ts_monotonic":            check_ts_monotonic,
    "both_legs_executed":      check_both_legs_executed,
    "delta_within_target":     check_delta_within_target,
    "funding_reversal_closed": check_funding_reversal_closed,
    "no_conflicting_orders":   check_no_conflicting_orders,
    "reconcile_with_testnet":  check_reconcile_with_testnet,
    "funding_income_sanity":   check_funding_income_sanity,
}


def _telegram(msg):
    tok = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TG_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TG_CHAT_ID")
    if not tok or not chat:
        log.warning("telegram not configured; drop: %s", msg)
        return
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
            data=json.dumps({"chat_id": chat, "text": msg}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:
        log.error("telegram send failed: %s", e)


def _kill_event(level, check, value, cfg):
    path = cfg.get("kill_events_path", "state/kill_events.jsonl")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds")
             .replace("+00:00", "Z"),
           "level": level, "check": check, "value": value}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def _update_streak(cfg, results):
    sp = Path(cfg.get("state_path", "state/qa_state.json"))
    sp.parent.mkdir(parents=True, exist_ok=True)
    try:
        state = json.loads(sp.read_text())
    except Exception:
        state = {}
    for name, r in results.items():
        if r["passed"]:
            state.pop(name, None)
            continue
        state[name] = state.get(name, 0) + 1
        if state[name] >= TH["alert_streak"]:
            _telegram(f"⚠️ HONESTY FAIL: {name}")
            _kill_event("L1", name, r["value"], cfg)
            state[name] = 0
    sp.write_text(json.dumps(state, indent=2))


def run_checks(journal_path, sqlite_path, config=None):
    cfg = dict(config or {})
    cfg["sqlite_path"] = sqlite_path
    events = _load(journal_path)
    if not events:
        log.error("empty journal: %s", journal_path)
        return {n: _r(False, None, None, "empty journal") for n in CHECKS}
    results = {}
    for name, fn in CHECKS.items():
        try:
            r = fn(events, cfg)
        except Exception as e:
            log.exception("check %s crashed", name)
            r = _r(False, "exception", None, f"crash: {e}")
        results[name] = r
        if not r["passed"]:
            log.warning("FAIL %s: value=%s thr=%s msg=%s",
                        name, r["value"], r["threshold"], r["message"])
        else:
            log.info("ok   %s: value=%s", name, r["value"])
    if cfg.get("emit_alerts", True):
        _update_streak(cfg, results)
    return results


_NO_CREDS = ("no sqlite/reconcile log", "reconcile_log missing",
             "no reconcile history", "only dry_run entries")


def _is_expected_no_creds_fail(name, r):
    if name != "reconcile_with_testnet":
        return False
    return any(m in r.get("message", "") for m in _NO_CREDS)


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", default="journal/journal.jsonl")
    ap.add_argument("--db", default="state/state.db")
    ap.add_argument("--venue", default="binance_usdm")
    ap.add_argument("--no-alerts", action="store_true")
    ap.add_argument("--allow-no-creds", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    res = run_checks(a.journal, a.db,
                     {"venue": a.venue, "emit_alerts": not a.no_alerts})
    print(json.dumps(res, indent=2))
    hard = [k for k, r in res.items()
            if not r["passed"] and not _is_expected_no_creds_fail(k, r)]
    soft = [k for k, r in res.items()
            if not r["passed"] and _is_expected_no_creds_fail(k, r)]
    if hard:
        print(f"\nFATAL: {len(hard)} failed: {hard}", file=sys.stderr)
        sys.exit(1)
    if soft:
        if a.allow_no_creds:
            print(f"\nWARN: {soft} unverified (accepted).", file=sys.stderr)
            sys.exit(0)
        print(f"\nFAIL-CLOSED: {soft} unverified.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
