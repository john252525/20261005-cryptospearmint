"""Honesty checks for paper-trading journal (funding-carry)."""
from __future__ import annotations

import itertools
import json
import logging
import os
import sqlite3
import urllib.request
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("qa.honesty")

TH = {
    "fee_deviation_pct": 5.0,
    "min_slippage_bps": 0.5,
    "min_latency_ms": 80.0,
    "funding_hours_utc": {0, 8, 16},
    "funding_tolerance_min": 5,
    "limit_touch_atol_bps": 0.5,
    "leg_qty_mismatch_pct": 0.5,
    "delta_pct_nav": 2.0,
    "conflict_window_s": 1.0,
    "reconcile_dev_pct": 0.5,
    "funding_max_pct_nav_per_day": 0.3,
    "alert_streak": 2,
}

FEE_SCHEDULE_BPS: dict[str, dict[str, float]] = {
    "binance_usdm": {"taker": 5.0, "maker": 2.0},
    "binance_spot": {"taker": 10.0, "maker": 10.0},
    "bybit_linear": {"taker": 5.5, "maker": 2.0},
    "bybit_spot":   {"taker": 10.0, "maker": 10.0},
}


def _parse_ts(s) -> float:
    """Accept ISO-8601 (with Z) or numeric epoch (s or ms)."""
    if isinstance(s, (int, float)):
        return float(s) / (1.0 if abs(s) < 1e12 else 1e3)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).timestamp()


def _load_journal(path: str | Path) -> list[dict]:
    out: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                log.error("journal: bad line %d: %s", ln, e)
    return out


def _iter(events: Iterable[dict], *etypes: str):
    wanted = set(etypes)
    for ev in events:
        if ev.get("event_type") in wanted:
            yield ev


def _res(passed: bool, value: Any, threshold: Any, message: str) -> dict:
    return {"passed": bool(passed), "value": value,
            "threshold": threshold, "message": message}


def check_fees_match_schedule(events: list[dict], cfg: dict) -> dict:
    venue = cfg.get("venue", "binance_usdm")
    sched = FEE_SCHEDULE_BPS[venue]
    devs, bad = [], []
    for ev in _iter(events, "fill"):
        liq = ev.get("liquidity", "taker")
        exp = sched[liq]
        notional = abs(float(ev.get("qty", 0)) * float(ev.get("price", 0)))
        if notional < 10.0:
            continue
        act = abs(float(ev.get("fee", 0.0))) / notional * 1e4
        dev = abs(act - exp) / exp * 100.0
        devs.append(dev)
        if dev > TH["fee_deviation_pct"]:
            bad.append({"order_id": ev.get("order_id"), "actual_bps": act})
    if not devs:
        return _res(False, None, TH["fee_deviation_pct"], "no fills with notional>$10")
    worst = max(devs)
    return _res(worst <= TH["fee_deviation_pct"], round(worst, 3),
                TH["fee_deviation_pct"],
                f"worst_deviation={worst:.2f}% over {len(devs)} fills, bad={len(bad)}")


def check_slippage_simulated(events: list[dict], cfg: dict) -> dict:
    vals, bad = [], []
    for ev in _iter(events, "fill"):
        if ev.get("order_type") != "market":
            continue
        mid = float(ev["mid"])
        px = float(ev["price"])
        side = ev["side"]
        bps = abs(px - mid) / mid * 1e4
        adverse = (side == "buy" and px >= mid) or (side == "sell" and px <= mid)
        vals.append(bps)
        if bps < TH["min_slippage_bps"] or not adverse:
            bad.append({"order_id": ev.get("order_id"), "bps": bps, "adverse": adverse})
    if not vals:
        return _res(True, 0, TH["min_slippage_bps"], "no market fills (n/a)")
    worst = min(vals)
    return _res(worst >= TH["min_slippage_bps"] and not bad, round(worst, 4),
                TH["min_slippage_bps"],
                f"min_slippage_bps={worst:.3f}, violations={len(bad)}")


def check_latency_recorded(events: list[dict], cfg: dict) -> dict:
    submit_ts: dict[str, float] = {}
    for ev in _iter(events, "order_submit"):
        submit_ts[ev["order_id"]] = _parse_ts(ev["ts"])
    lat, bad = [], []
    for ev in _iter(events, "fill"):
        oid = ev.get("order_id")
        if oid not in submit_ts:
            continue
        ms = (_parse_ts(ev["ts"]) - submit_ts[oid]) * 1000.0
        lat.append(ms)
        if ms < TH["min_latency_ms"]:
            bad.append({"order_id": oid, "ms": ms})
    if not lat:
        return _res(False, None, TH["min_latency_ms"], "no submit/fill pairs")
    mn = min(lat)
    return _res(mn >= TH["min_latency_ms"], round(mn, 2), TH["min_latency_ms"],
                f"min_latency_ms={mn:.2f}, violations={len(bad)}")


def check_funding_cadence(events: list[dict], cfg: dict) -> dict:
    tol = TH["funding_tolerance_min"] * 60
    bad, n = [], 0
    for ev in _iter(events, "funding_credit"):
        n += 1
        dt = datetime.fromtimestamp(_parse_ts(ev["ts"]), tz=UTC)
        h = dt.hour
        secs_from = min(
            abs(((h - H) % 24) * 3600 + dt.minute * 60 + dt.second)
            for H in TH["funding_hours_utc"]
        )
        secs_from = min(secs_from, 24 * 3600 - secs_from)
        if secs_from > tol:
            bad.append({"ts": ev["ts"]})
    return _res(bool(n) and not bad, len(bad), 0,
                f"funding_events={n}, off_window={len(bad)}")


def check_limit_fills_crossed(events: list[dict], cfg: dict) -> dict:
    bad, n = [], 0
    for ev in _iter(events, "fill"):
        if ev.get("order_type") != "limit":
            continue
        n += 1
        touch = ev.get("market_touch")
        if touch is None:
            bad.append({"order_id": ev.get("order_id"), "reason": "no market_touch"})
            continue
        atol = ev["price"] * TH["limit_touch_atol_bps"] / 1e4
        if ev["side"] == "buy" and touch > ev["price"] + atol:
            bad.append({"order_id": ev.get("order_id"), "reason": "not crossed"})
        if ev["side"] == "sell" and touch < ev["price"] - atol:
            bad.append({"order_id": ev.get("order_id"), "reason": "not crossed"})
    return _res(not bad, len(bad), 0,
                f"limit_fills={n}, uncrossed={len(bad)}")


def check_ts_monotonic(events: list[dict], cfg: dict) -> dict:
    prev, bad = None, 0
    for i, ev in enumerate(events):
        ts = _parse_ts(ev["ts"])
        if prev is not None and ts < prev:
            bad += 1
            log.error("journal non-monotonic at line %d: %s < %s",
                      i, ev["ts"], datetime.fromtimestamp(prev, tz=UTC).isoformat())
        prev = ts
    return _res(bad == 0, bad, 0, f"non_monotonic_events={bad}")


def check_both_legs_executed(events: list[dict], cfg: dict) -> dict:
    opens: dict[str, dict] = {}
    for ev in _iter(events, "position_open"):
        opens[ev["position_id"]] = {"spot": None, "perp": None}
    for ev in _iter(events, "fill"):
        pid = ev.get("position_id")
        if pid in opens:
            leg = ev.get("leg")
            if leg in ("spot", "perp"):
                opens[pid][leg] = ev
    bad = []
    for pid, legs in opens.items():
        if not legs["spot"] or not legs["perp"]:
            bad.append({"position_id": pid, "reason": "missing_leg"})
            continue
        s_q = abs(float(legs["spot"]["qty"]))
        p_q = abs(float(legs["perp"]["qty"]))
        if abs(s_q - p_q) / max(s_q, 1e-12) * 100 > TH["leg_qty_mismatch_pct"]:
            bad.append({"position_id": pid, "reason": "qty_mismatch"})
    return _res(not bad and bool(opens), len(bad), 0,
                f"opens={len(opens)}, broken={len(bad)}")


def check_delta_within_target(events: list[dict], cfg: dict) -> dict:
    bad, n, worst = [], 0, 0.0
    for ev in _iter(events, "delta_snapshot"):
        n += 1
        nav = float(ev["nav_usd"])
        pct = abs(float(ev["delta_usd"])) / nav * 100.0 if nav else 0.0
        worst = max(worst, pct)
        if pct > TH["delta_pct_nav"]:
            bad.append({"ts": ev["ts"], "pct": pct})
    return _res(not bad, round(worst, 4), TH["delta_pct_nav"],
                f"snapshots={n}, breaches={len(bad)}")


def check_funding_reversal_closed(events: list[dict], cfg: dict) -> dict:
    by_sym: dict[str, list[dict]] = defaultdict(list)
    closes: dict[str, list[float]] = defaultdict(list)
    for ev in _iter(events, "funding_credit"):
        by_sym[ev["symbol"]].append(ev)
    for ev in _iter(events, "position_close"):
        closes[ev["symbol"]].append(_parse_ts(ev["ts"]))
    bad = []
    for sym, evs in by_sym.items():
        evs.sort(key=lambda e: _parse_ts(e["ts"]))
        for a, b in itertools.pairwise(evs):
            if a["funding_rate"] * b["funding_rate"] < 0:
                t_flip = _parse_ts(b["ts"])
                if not any(t > t_flip for t in closes.get(sym, [])):
                    bad.append({"symbol": sym, "flip_ts": b["ts"]})
    return _res(not bad, len(bad), 0, f"unclosed_flips={len(bad)}")


def check_no_conflicting_orders(events: list[dict], cfg: dict) -> dict:
    # Group by (symbol, market). spot/perp on the same symbol are two legs
    # of one hedge, NOT conflicting orders.
    by_key: dict[tuple[str, str], list[float]] = defaultdict(list)
    for ev in _iter(events, "order_submit"):
        market = ev.get("market") or ev.get("leg") or cfg.get("default_market", "perp")
        by_key[(ev["symbol"], market)].append(_parse_ts(ev["ts"]))
    bad, detail = 0, []
    for (sym, mkt), ts in by_key.items():
        ts.sort()
        for a, b in itertools.pairwise(ts):
            if b - a < TH["conflict_window_s"]:
                bad += 1
                detail.append({"symbol": sym, "market": mkt, "dt_s": round(b - a, 6)})
    return _res(bad == 0, bad, 0,
                f"conflicts={bad} groups={len(by_key)} {detail[:3]}")


def check_reconcile_with_testnet(events: list[dict], cfg: dict) -> dict:
    db = cfg.get("sqlite_path")
    if not db or not Path(db).exists():
        return _res(False, None, TH["reconcile_dev_pct"], "no sqlite/reconcile log")
    con = sqlite3.connect(db)
    try:
        rows = con.execute(
            "SELECT ts, dev_pct, ok, detail FROM reconcile_log "
            "ORDER BY ts DESC LIMIT 24"
        ).fetchall()
    except sqlite3.OperationalError as e:
        return _res(False, None, TH["reconcile_dev_pct"], f"reconcile_log missing: {e}")
    finally:
        con.close()
    if not rows:
        return _res(False, None, TH["reconcile_dev_pct"], "no reconcile history")

    real = []
    dry = 0
    for ts, dev, ok, detail in rows:
        try:
            d = json.loads(detail) if detail else {}
        except json.JSONDecodeError:
            d = {}
        if d.get("dry_run"):
            dry += 1
            continue
        real.append((ts, dev, ok))

    if not real:
        return _res(False, None, TH["reconcile_dev_pct"],
                    f"only dry_run entries ({dry}); need real venue reconcile")

    ok_rows = [r for r in real if r[2]]
    if len(ok_rows) < len(real) * 0.9:
        return _res(False, round(min(r[1] for r in real), 4),
                    TH["reconcile_dev_pct"],
                    f"ok_rate={len(ok_rows)}/{len(real)} (<90%)")

    worst = max(r[1] for r in real)
    return _res(worst <= TH["reconcile_dev_pct"], round(worst, 4),
                TH["reconcile_dev_pct"],
                f"real_windows={len(real)} (dry_run_skipped={dry}), worst_dev={worst:.3f}%")


def check_funding_income_sanity(events: list[dict], cfg: dict) -> dict:
    per_day: dict[str, float] = defaultdict(float)
    nav = None
    for ev in _iter(events, "funding_credit"):
        day = datetime.fromtimestamp(_parse_ts(ev["ts"]), tz=UTC).date().isoformat()
        per_day[day] += float(ev["amount_usd"])
        nav = float(ev.get("nav_usd", nav or 0.0))
    if not per_day or not nav:
        return _res(True, 0.0, TH["funding_max_pct_nav_per_day"], "no funding / no nav")
    worst_day, worst_pct = None, 0.0
    for day, amt in per_day.items():
        pct = amt / nav * 100.0
        if pct > worst_pct:
            worst_day, worst_pct = day, pct
    return _res(worst_pct <= TH["funding_max_pct_nav_per_day"], round(worst_pct, 4),
                TH["funding_max_pct_nav_per_day"],
                f"worst_day={worst_day} pct_nav={worst_pct:.4f}%")


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


def _telegram(msg: str) -> None:
    tok = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TG_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TG_CHAT_ID")
    if not tok or not chat:
        log.warning("telegram not configured; drop: %s", msg)
        return
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            data=json.dumps({"chat_id": chat, "text": msg}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:
        log.error("telegram send failed: %s", e)


def _kill_event(level: str, check: str, value: Any, cfg: dict) -> None:
    path = cfg.get("kill_events_path", "data/kill_events.jsonl")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
           "level": level, "check": check, "value": value}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def _update_streak(cfg: dict, results: dict) -> None:
    state_path = Path(cfg.get("state_path", "data/qa_state.json"))
    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        state = json.loads(state_path.read_text())
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
    state_path.write_text(json.dumps(state, indent=2))


def run_checks(journal_path: str, sqlite_path: str, config: dict | None = None) -> dict:
    cfg = dict(config or {})
    cfg["sqlite_path"] = sqlite_path
    events = _load_journal(journal_path)
    if not events:
        log.error("empty journal: %s", journal_path)
        return {name: _res(False, None, None, "empty journal") for name in CHECKS}

    results: dict[str, dict] = {}
    for name, fn in CHECKS.items():
        try:
            r = fn(events, cfg)
        except Exception as e:
            log.exception("check %s crashed", name)
            r = _res(False, "exception", None, f"crash: {e}")
        results[name] = r
        if not r["passed"]:
            log.warning("FAIL %s: value=%s thr=%s msg=%s",
                        name, r["value"], r["threshold"], r["message"])
        else:
            log.info("ok   %s: value=%s", name, r["value"])

    if cfg.get("emit_alerts", True):
        _update_streak(cfg, results)
    return results


# Expected when the process simply has no live venue credentials:
# reconcile_with_testnet is the ONLY allowed fail; any other fail is fatal.
_NO_CREDS_MARKERS = (
    "no sqlite/reconcile log",
    "reconcile_log missing",
    "no reconcile history",
    "only dry_run entries",
)


def _is_expected_no_creds_fail(name: str, r: dict) -> bool:
    if name != "reconcile_with_testnet":
        return False
    msg = r.get("message", "")
    return any(m in msg for m in _NO_CREDS_MARKERS)


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser(description="QA honesty checks")
    ap.add_argument("--journal", default="data/journal.jsonl")
    ap.add_argument("--db", default="data/state.db")
    ap.add_argument("--venue", default="binance_usdm")
    ap.add_argument("--no-alerts", action="store_true")
    ap.add_argument("--allow-no-creds", action="store_true",
                    help="exit 0 if reconcile_with_testnet is the ONLY fail "
                         "and its message says 'no creds / no reconcile log / dry_run'")
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
        print(f"\nFATAL: {len(hard)} meaningful check(s) failed: {hard}", file=sys.stderr)
        sys.exit(1)
    if soft:
        if a.allow_no_creds:
            print(f"\nWARN: no vendor credentials; {soft} unverified (accepted).",
                  file=sys.stderr)
            sys.exit(0)
        print(f"\nFAIL-CLOSED: {soft} unverified, no credentials supplied.",
              file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
