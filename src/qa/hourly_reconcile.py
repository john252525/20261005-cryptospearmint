"""Hourly reconciliation of local position state vs venue (testnet)."""
from __future__ import annotations
import json, logging, os, sqlite3, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("qa.reconcile")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")

RECON_DEV_PCT = 0.5
INTERVAL_S = 3600
CCXT_TIMEOUT_MS = int(os.getenv("QA_CCXT_TIMEOUT_MS", "8000"))


def _load_dotenv():
    for cand in (Path.cwd() / ".env",
                 Path(__file__).resolve().parents[2] / ".env"):
        if not cand.is_file():
            continue
        for raw in cand.read_text().splitlines():
            ln = raw.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, _, v = ln.partition("=")
            if " #" in v:
                v = v.split(" #", 1)[0]
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)
        return


_load_dotenv()

DRY_RUN = os.getenv("QA_RECONCILE_DRY_RUN", "").lower() in ("1", "true", "yes")
DB_PATH = os.getenv("QA_DB_PATH", "state/state.db")
KILL_LOG = os.getenv("QA_KILL_LOG", "state/kill_events.jsonl")


class ConfigError(RuntimeError):
    pass


_PLACEHOLDER_PATTERNS = ("<", ">", "paste", "your_", "xxx", "todo", "fill_me")


def _looks_like_placeholder(v):
    lower = v.lower()
    for pat in _PLACEHOLDER_PATTERNS:
        if pat in lower:
            return f"contains placeholder token {pat!r}"
    if any(ord(c) > 127 for c in v):
        return "contains non-ASCII characters"
    if v != v.strip():
        return "leading/trailing whitespace"
    return None


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _require_secret(name, *aliases, expected_len=None):
    tried = (name, *aliases)
    v, used = None, None
    for n in tried:
        cand = os.getenv(n)
        if cand:
            v, used = cand, n
            break
    if not v:
        raise ConfigError(f"missing secret: set one of {' / '.join(tried)}")
    reason = _looks_like_placeholder(v)
    if reason:
        raise ConfigError(
            f"{used} {reason} (len={len(v)}, masked={v[:2]}***{v[-2:]}).")
    if expected_len is not None and len(v) != expected_len:
        raise ConfigError(f"{used} length={len(v)}, expected {expected_len}.")
    return v


def _telegram(msg):
    tok = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TG_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TG_CHAT_ID")
    if not tok or not chat:
        log.warning("telegram not configured: %s", msg)
        return
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            data=json.dumps({"chat_id": chat, "text": msg}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:
        log.error("telegram send failed: %s", e)


def trigger_kill_switch(level, reason):
    Path(KILL_LOG).parent.mkdir(parents=True, exist_ok=True)
    with open(KILL_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _now(), "level": level, "reason": reason}) + "\n")
    log.critical("KILL SWITCH %s armed: %s", level, reason)
    _telegram(f"🚨 KILL SWITCH {level}: {reason}")


def fetch_positions_binance_testnet():
    try:
        import ccxt
    except ModuleNotFoundError as e:
        raise ConfigError("ccxt not installed") from e
    ex = ccxt.binanceusdm({
        "apiKey": _require_secret("BINANCE_API_KEY", "BN_KEY", expected_len=64),
        "secret": _require_secret("BINANCE_API_SECRET", "BN_SECRET", expected_len=64),
        "options": {"defaultType": "future"},
        "enableRateLimit": True,
        "timeout": CCXT_TIMEOUT_MS,
        "adjustForTimeDifference": True,
    })
    if not hasattr(ex, "enableDemoTrading"):
        raise ConfigError("ccxt too old: no enableDemoTrading")
    try:
        ex.enableDemoTrading(True)
    except Exception as e:
        raise ConfigError(f"enableDemoTrading failed: {e}") from e
    out = {}
    for p in ex.fetch_positions():
        amt = float(p.get("contracts") or 0)
        if amt:
            out[p["symbol"]] = amt * (1 if p["side"] == "long" else -1)
    return out


def fetch_positions_bybit_testnet():
    try:
        import ccxt
    except ModuleNotFoundError as e:
        raise ConfigError("ccxt not installed") from e
    ex = ccxt.bybit({
        "apiKey": _require_secret("BYBIT_API_KEY", "BYBIT_KEY", expected_len=36),
        "secret": _require_secret("BYBIT_API_SECRET", "BYBIT_SECRET", expected_len=36),
        "options": {"defaultType": "linear"},
        "enableRateLimit": True,
        "timeout": CCXT_TIMEOUT_MS,
        "adjustForTimeDifference": True,
    })
    ex.set_sandbox_mode(True)
    out = {}
    for p in ex.fetch_positions():
        amt = float(p.get("contracts") or 0)
        if amt:
            out[p["symbol"]] = amt * (1 if p["side"] == "long" else -1)
    return out


def local_state(db_path):
    if not Path(db_path).exists():
        log.warning("local_state: db %s missing -> empty", db_path)
        return {}
    con = sqlite3.connect(db_path)
    try:
        have = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='positions'"
        ).fetchone()
        if not have:
            log.warning("local_state: no 'positions' table -> empty")
            return {}
        rows = con.execute(
            "SELECT symbol, SUM(CASE WHEN side='buy' THEN qty ELSE -qty END) "
            "FROM positions WHERE status='open' GROUP BY symbol").fetchall()
    finally:
        con.close()
    return {s: float(q) for s, q in rows if q}


def log_reconcile(db_path, dev_pct, ok, detail):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.execute("CREATE TABLE IF NOT EXISTS reconcile_log("
                    "ts TEXT PRIMARY KEY, dev_pct REAL, ok INTEGER, detail TEXT)")
        con.execute("INSERT OR REPLACE INTO reconcile_log VALUES (?,?,?,?)",
                    (_now(), dev_pct, int(ok), json.dumps(detail)))
        con.commit()
    finally:
        con.close()


def compare(local, remote):
    syms = set(local) | set(remote)
    worst, detail = 0.0, {}
    for s in syms:
        l, r = local.get(s, 0.0), remote.get(s, 0.0)
        denom = max(abs(r), abs(l), 1e-9)
        dev = abs(l - r) / denom * 100.0
        detail[s] = {"local": l, "remote": r, "dev_pct": round(dev, 4)}
        worst = max(worst, dev)
    return worst, detail


def tick():
    venue = os.getenv("QA_VENUE", "binance")
    if DRY_RUN:
        remote = {}
        log.warning("DRY-RUN mode: no venue query; entry rejected by QA")
    else:
        remote = (fetch_positions_binance_testnet()
                  if venue == "binance" else fetch_positions_bybit_testnet())
    local = local_state(DB_PATH)
    dev, detail = compare(local, remote)
    if DRY_RUN:
        detail["dry_run"] = True
        log_reconcile(DB_PATH, dev, False, detail)
        log.warning("DRY-RUN tick: dev=%.4f%% (kill switch NOT armed)", dev)
        return
    real_ok = dev <= RECON_DEV_PCT
    log_reconcile(DB_PATH, dev, real_ok, detail)
    if not real_ok:
        _telegram(f"⚠️ RECONCILE FAIL dev={dev:.3f}% > {RECON_DEV_PCT}%")
        trigger_kill_switch("L2", f"reconcile dev {dev:.3f}% > {RECON_DEV_PCT}%")
    else:
        log.info("reconcile ok, worst_dev=%.4f%%", dev)


def _preflight():
    import importlib.util
    if importlib.util.find_spec("ccxt") is None:
        raise ConfigError("ccxt not installed")
    venue = os.getenv("QA_VENUE", "binance")
    if venue == "binance":
        _require_secret("BINANCE_API_KEY", "BN_KEY", expected_len=64)
        _require_secret("BINANCE_API_SECRET", "BN_SECRET", expected_len=64)
    elif venue == "bybit":
        _require_secret("BYBIT_API_KEY", "BYBIT_KEY", expected_len=36)
        _require_secret("BYBIT_API_SECRET", "BYBIT_SECRET", expected_len=36)
    else:
        raise ConfigError(f"unknown venue: {venue}")
    log.info("preflight ok: venue=%s ccxt_module=found", venue)


def check_clock():
    import time as _t
    venue = os.getenv("QA_VENUE", "binance")
    try:
        import ccxt
    except ModuleNotFoundError as e:
        log.critical("ccxt missing: %s", e)
        return 2
    ex = ccxt.binanceusdm() if venue == "binance" else ccxt.bybit()
    if venue == "binance" and hasattr(ex, "enableDemoTrading"):
        ex.enableDemoTrading(True)
    if venue == "bybit":
        ex.set_sandbox_mode(True)
    ex.timeout = CCXT_TIMEOUT_MS
    try:
        srv_ms = ex.fetch_time()
    except Exception as e:
        log.error("fetch_time failed: %s", e)
        return 3
    local_ms = int(_t.time() * 1000)
    diff_ms = srv_ms - local_ms
    log.info("venue=%s local_ms=%d server_ms=%d diff_ms=%+d",
             venue, local_ms, srv_ms, diff_ms)
    if abs(diff_ms) > 1000:
        log.warning("CLOCK SKEW %+d ms", diff_ms)
        Path("state").mkdir(exist_ok=True)
        Path("state/clock_skew_ms").write_text(str(diff_ms))
        return 0
    log.info("clock ok, |diff| <= 1000ms")
    return 0


def verify_credentials():
    venue = os.getenv("QA_VENUE", "binance")
    try:
        if venue == "binance":
            try:
                import ccxt
            except ModuleNotFoundError as e:
                raise ConfigError("ccxt missing") from e
            ex = ccxt.binanceusdm({
                "apiKey": _require_secret("BINANCE_API_KEY", "BN_KEY", expected_len=64),
                "secret": _require_secret("BINANCE_API_SECRET", "BN_SECRET", expected_len=64),
                "options": {"defaultType": "future"},
                "enableRateLimit": True, "timeout": CCXT_TIMEOUT_MS,
            })
            if hasattr(ex, "enableDemoTrading"):
                ex.enableDemoTrading(True)
            probe = lambda: ex.fetch_balance()
        elif venue == "bybit":
            try:
                import ccxt
            except ModuleNotFoundError as e:
                raise ConfigError("ccxt missing") from e
            ex = ccxt.bybit({
                "apiKey": _require_secret("BYBIT_API_KEY", "BYBIT_KEY", expected_len=36),
                "secret": _require_secret("BYBIT_API_SECRET", "BYBIT_SECRET", expected_len=36),
                "options": {"defaultType": "linear"},
                "enableRateLimit": True, "timeout": CCXT_TIMEOUT_MS,
            })
            ex.set_sandbox_mode(True)
            probe = lambda: ex.fetch_balance()
        else:
            raise ConfigError(f"unknown venue: {venue}")
        key = ex.apiKey or ""
        api_url = (ex.urls["api"].get("fapiPrivate")
                   or ex.urls["api"].get("private")
                   or ex.urls["api"].get("spot")
                   or ex.urls["api"])
        if isinstance(api_url, dict):
            api_url = next(iter(api_url.values()))
        api_url = api_url.replace("{hostname}", ex.hostname or "")
        log.info("venue=%s key_len=%d api=%s", venue, len(key), api_url)
        bal = probe()
        total = {k: float(v) for k, v in (bal.get("total") or {}).items()
                 if v and float(v) > 0}
        log.info("AUTH OK. non-zero balances: %s", total or "{}")
        return 0
    except ConfigError as e:
        log.critical("config: %s", e)
        return 2
    except Exception as e:
        log.error("auth failed: %s: %s", type(e).__name__, e)
        return 3


def _run_forever():
    log.info("hourly reconciler start, venue=%s dry_run=%s",
             os.getenv("QA_VENUE", "binance"), DRY_RUN)
    while True:
        try:
            tick()
        except ConfigError:
            log.critical("reconcile config error — exiting")
            raise
        except Exception:
            log.exception("reconcile tick failed (transient, will retry)")
        time.sleep(INTERVAL_S)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--verify-credentials", action="store_true")
    ap.add_argument("--check-clock", action="store_true")
    a = ap.parse_args()
    if a.preflight:
        _preflight()
        return
    if a.check_clock:
        raise SystemExit(check_clock())
    if a.verify_credentials:
        raise SystemExit(verify_credentials())
    if a.once:
        venue = os.getenv("QA_VENUE", "binance")
        log.info("single reconcile tick, venue=%s dry_run=%s", venue, DRY_RUN)
        tick()
        log.info("tick done")
        return
    _run_forever()


if __name__ == "__main__":
    try:
        main()
    except ConfigError as e:
        log.critical("fatal: %s", e)
        raise SystemExit(2)
