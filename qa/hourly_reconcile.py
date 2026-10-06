"""Hourly reconciliation: local sqlite vs Binance/Bybit testnet positions."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("qa.reconcile")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

RECON_DEV_PCT = 0.5
INTERVAL_S = 3600
def _load_dotenv() -> None:
    """Load .env into os.environ WITHOUT overwriting existing vars.
    Minimal parser: KEY=VALUE, # comments, blank lines, optional quotes."""
    for cand in (Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"):
        if not cand.is_file():
            continue
        for raw in cand.read_text().splitlines():
            ln = raw.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, _, v = ln.partition("=")
            # strip inline `# comment`, then quotes/surrounding space
            if " #" in v:
                v = v.split(" #", 1)[0]
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)
        return


_load_dotenv()

DRY_RUN = os.getenv("QA_RECONCILE_DRY_RUN", "").lower() in ("1", "true", "yes")
CCXT_TIMEOUT_MS = int(os.getenv("QA_CCXT_TIMEOUT_MS", "8000"))  # hard cap on any HTTP call


class ConfigError(RuntimeError):
    """Fatal misconfiguration: do NOT retry, kill the process."""
DB_PATH = os.getenv("QA_DB_PATH", "data/state.db")
KILL_LOG = os.getenv("QA_KILL_LOG", "data/kill_events.jsonl")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _telegram(msg: str) -> None:
    tok = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TG_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TG_CHAT_ID")
    if not tok or not chat:
        log.warning("telegram not configured: %s", msg)
        return
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            data=json.dumps({"chat_id": chat, "text": msg}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:  # noqa: BLE001
        log.error("telegram send failed: %s", e)


def trigger_kill_switch(level: str, reason: str) -> None:
    Path(KILL_LOG).parent.mkdir(parents=True, exist_ok=True)
    with open(KILL_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _now(), "level": level, "reason": reason}) + "\n")
    log.critical("KILL SWITCH %s armed: %s", level, reason)
    _telegram(f"🚨 KILL SWITCH {level}: {reason}")


_PLACEHOLDER_PATTERNS = ("<", ">", "paste", "your_", "xxx", "todo", "fill_me")


def _looks_like_placeholder(v: str) -> str | None:
    """Return a reason string if v is clearly a placeholder, else None."""
    lower = v.lower()
    for pat in _PLACEHOLDER_PATTERNS:
        if pat in lower:
            return f"contains placeholder token {pat!r}"
    if any(ord(c) > 127 for c in v):
        return "contains non-ASCII characters"
    if v != v.strip():
        return "leading/trailing whitespace"
    return None


def _require_secret(name: str, *aliases: str, expected_len: int | None = None) -> str:
    """Read a secret. First name wins; aliases are tried in order.
    Rejects empty, placeholder-looking, or wrong-length values."""
    tried = (name, *aliases)
    v = None
    used = None
    for n in tried:
        cand = os.getenv(n)
        if cand:
            v, used = cand, n
            break
    if not v:
        raise ConfigError(
            f"missing secret: set one of {' / '.join(tried)} "
            f"(project convention: {' / '.join(tried[:1])})"
        )
    reason = _looks_like_placeholder(v)
    if reason:
        raise ConfigError(
            f"{used} {reason} (len={len(v)}, masked={v[:2]}***{v[-2:]}). "
            f"Put the real value in .env, not a placeholder."
        )
    if expected_len is not None and len(v) != expected_len:
        raise ConfigError(
            f"{used} length={len(v)}, expected {expected_len}. "
            f"Likely wrong venue (mainnet vs testnet) or wrong exchange."
        )
    return v


def _require(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise ConfigError(f"missing env var {name}")
    return v


def fetch_positions_binance_testnet() -> dict[str, float]:
    try:
        import ccxt  # type: ignore
    except ModuleNotFoundError as e:
        raise ConfigError("ccxt not installed: `uv add ccxt`") from e

    ex = ccxt.binanceusdm({
        "apiKey": _require_secret("BINANCE_API_KEY", "BN_KEY", expected_len=64),
        "secret": _require_secret("BINANCE_API_SECRET", "BN_SECRET", expected_len=64),
        "options": {"defaultType": "future"},
        "enableRateLimit": True,
        "timeout": CCXT_TIMEOUT_MS,
        "adjustForTimeDifference": True,   # ccxt will sync once via public /time
    })
    # Binance RETIRED futures testnet (ccxt sandbox mode raises NotSupported).
    # Replacement per ccxt announcement: demo trading.
    # Fallback path if the local ccxt lacks enableDemoTrading: refuse loudly,
    # never silently fall through to prod or to a no-op.
    if not hasattr(ex, "enableDemoTrading"):
        raise ConfigError(
            "ccxt too old: no enableDemoTrading. "
            "Either `uv add ccxt --upgrade` or switch to QA_VENUE=bybit "
            "(Bybit testnet is still live)."
        )
    try:
        ex.enableDemoTrading(True)
    except Exception as e:  # noqa: BLE001
        raise ConfigError(f"enableDemoTrading failed: {e}") from e
    out: dict[str, float] = {}
    for p in ex.fetch_positions():
        amt = float(p.get("contracts") or 0)
        if amt:
            out[p["symbol"]] = amt * (1 if p["side"] == "long" else -1)
    return out


def fetch_positions_bybit_testnet() -> dict[str, float]:
    try:
        import ccxt  # type: ignore
    except ModuleNotFoundError as e:
        raise ConfigError("ccxt not installed: `uv add ccxt`") from e
    ex = ccxt.bybit({
        "apiKey": _require_secret("BYBIT_API_KEY", "BYBIT_KEY", expected_len=36),
        "secret": _require_secret("BYBIT_API_SECRET", "BYBIT_SECRET", expected_len=36),
        "options": {"defaultType": "linear"},
        "enableRateLimit": True,
        "timeout": CCXT_TIMEOUT_MS,
        "adjustForTimeDifference": True,
    })
    ex.set_sandbox_mode(True)
    out: dict[str, float] = {}
    for p in ex.fetch_positions():
        amt = float(p.get("contracts") or 0)
        if amt:
            out[p["symbol"]] = amt * (1 if p["side"] == "long" else -1)
    return out


def local_state(db_path: str) -> dict[str, float]:
    """Empty state if DB or table absent — no crash.
    A missing DB means 'no open positions as far as we know', which is a
    legitimate zero; reconcile will still flag remote != {} if the venue has any."""
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
            "FROM positions WHERE status='open' GROUP BY symbol"
        ).fetchall()
    finally:
        con.close()
    return {s: float(q) for s, q in rows if q}


def log_reconcile(db_path: str, dev_pct: float, ok: bool, detail: dict) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute("CREATE TABLE IF NOT EXISTS reconcile_log("
                    "ts TEXT PRIMARY KEY, dev_pct REAL, ok INTEGER, detail TEXT)")
        con.execute("INSERT OR REPLACE INTO reconcile_log VALUES (?,?,?,?)",
                    (_now(), dev_pct, int(ok), json.dumps(detail)))
        con.commit()
    finally:
        con.close()


def compare(local: dict[str, float], remote: dict[str, float]) -> tuple[float, dict]:
    syms = set(local) | set(remote)
    worst, detail = 0.0, {}
    for s in syms:
        l, r = local.get(s, 0.0), remote.get(s, 0.0)
        denom = max(abs(r), abs(l), 1e-9)
        dev = abs(l - r) / denom * 100.0
        detail[s] = {"local": l, "remote": r, "dev_pct": round(dev, 4)}
        worst = max(worst, dev)
    return worst, detail


def tick() -> None:
    venue = os.getenv("QA_VENUE", "binance")
    if DRY_RUN:
        # offline dev mode: NO remote fetch, reconcile_log entry is TAGGED.
        # check_reconcile_with_testnet() rejects entries with detail.dry_run=true,
        # so a dry-run can never make the QA suite go green.
        remote: dict[str, float] = {}
        log.warning("DRY-RUN mode: no venue query; entry will be rejected by QA")
    else:
        remote = (fetch_positions_binance_testnet()
                  if venue == "binance" else fetch_positions_bybit_testnet())
    local = local_state(DB_PATH)
    dev, detail = compare(local, remote)

    # DRY-RUN: write an entry the QA check will REJECT (ok=0 + dry_run tag),
    # but DO NOT trip the kill switch. Distinct concepts:
    #   - "is this entry honest?"      -> False for dry-run
    #   - "is the venue diverging?"    -> only meaningful on a real query
    if DRY_RUN:
        detail["dry_run"] = True
        log_reconcile(DB_PATH, dev, False, detail)
        log.warning("DRY-RUN tick: dev=%.4f%% (kill switch NOT armed)", dev)
        return

    real_ok = dev <= RECON_DEV_PCT
    log_reconcile(DB_PATH, dev, real_ok, detail)
    if not real_ok:
        _telegram(f"⚠️ RECONCILE FAIL dev={dev:.3f}% > {RECON_DEV_PCT}% "
                  f"details={json.dumps(detail)[:350]}")
        trigger_kill_switch("L2", f"reconcile dev {dev:.3f}% > {RECON_DEV_PCT}%")
    else:
        log.info("reconcile ok, worst_dev=%.4f%%", dev)


def _run_forever() -> None:
    log.info("hourly reconciler start, venue=%s dry_run=%s",
             os.getenv("QA_VENUE", "binance"), DRY_RUN)
    while True:
        try:
            tick()
        except ConfigError:
            log.critical("reconcile config error — exiting, fix env and restart")
            raise
        except Exception:  # noqa: BLE001 transient: retry next hour
            log.exception("reconcile tick failed (transient, will retry)")
        time.sleep(INTERVAL_S)


def _preflight() -> None:
    """Check env + ccxt import. No network. Raises ConfigError on problem."""
    try:
        import ccxt  # type: ignore
    except ModuleNotFoundError as e:
        raise ConfigError("ccxt not installed: `uv add ccxt`") from e
    venue = os.getenv("QA_VENUE", "binance")
    if venue == "binance":
        _require_secret("BINANCE_API_KEY", "BN_KEY",         expected_len=64)
        _require_secret("BINANCE_API_SECRET", "BN_SECRET",   expected_len=64)
    elif venue == "bybit":
        _require_secret("BYBIT_API_KEY", "BYBIT_KEY",        expected_len=36)
        _require_secret("BYBIT_API_SECRET", "BYBIT_SECRET",  expected_len=36)
    else:
        raise ConfigError(f"unknown venue: {venue}")
    log.info("preflight ok: venue=%s ccxt=%s timeout=%dms",
             venue, ccxt.__version__, CCXT_TIMEOUT_MS)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true",
                    help="single tick then exit (used by tests/CI)")
    ap.add_argument("--preflight", action="store_true",
                    help="check config only, no network call")
    ap.add_argument("--verify-credentials", action="store_true",
                    help="auth-only probe against venue (no DB write)")
    ap.add_argument("--check-clock", action="store_true",
                    help="compare local vs venue server time, no auth")
    ap.add_argument("--monitor-clock", action="store_true",
                    help="loop: check clock every hour (optional)")
    a = ap.parse_args()
    if a.preflight:
        _preflight()
        return
    if a.check_clock:
        raise SystemExit(check_clock())
    if a.monitor_clock:
        monitor_loop(); return
    if a.verify_credentials:
        raise SystemExit(verify_credentials())
    if a.once:
        venue = os.getenv("QA_VENUE", "binance")
        log.info("single reconcile tick, venue=%s dry_run=%s", venue, DRY_RUN)
        tick()
        log.info("tick done")
        return
    _run_forever()


def verify_credentials() -> int:
    """Auth-only check: fetch one read-only endpoint, no DB writes, no kill switch.
    Returns process exit code (0 ok, 2 auth error, 3 other)."""
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
        # resolve the template URL as ccxt would at request time
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
        log.info("AUTH OK. non-zero balances: %s", total or "{} (empty account)")
        return 0
    except ConfigError as e:
        log.critical("config: %s", e); return 2
    except Exception as e:  # noqa: BLE001
        log.error("auth failed: %s: %s", type(e).__name__, e)
        return 3


def check_clock() -> int:
    """Compare local time with venue server time. Exit 0 if within tolerance.
    No auth, no DB writes."""
    import time as _t
    venue = os.getenv("QA_VENUE", "binance")
    try:
        import ccxt  # type: ignore
    except ModuleNotFoundError as e:
        log.critical("ccxt missing: %s", e); return 2

    ex = ccxt.binanceusdm() if venue == "binance" else ccxt.bybit()
    if venue == "binance" and hasattr(ex, "enableDemoTrading"):
        ex.enableDemoTrading(True)
    if venue == "bybit":
        ex.set_sandbox_mode(True)
    ex.timeout = CCXT_TIMEOUT_MS

    try:
        srv_ms = ex.fetch_time()
    except Exception as e:  # noqa: BLE001
        log.error("fetch_time failed: %s", e); return 3

    local_ms = int(_t.time() * 1000)
    diff_ms = srv_ms - local_ms
    log.info("venue=%s local_ms=%d server_ms=%d diff_ms=%+d",
             venue, local_ms, srv_ms, diff_ms)

    if abs(diff_ms) > 1000:
        log.warning(
            "CLOCK SKEW %+d ms. ccxt will now auto-correct via "
            "adjustForTimeDifference, but any independent signer "
            "(curl, custom code, other process) WILL get -1021.",
            diff_ms,
        )
        # Record diff so fetch_* can offset.
        Path("data/clock_skew_ms").write_text(str(diff_ms))
        return 0  # not fatal, just noisy — ccxt can compensate
    log.info("clock ok, |diff| <= 1000ms")
    return 0


def monitor_loop() -> None:
    """Optional: refresh skew file every hour (used by systemd, not by default)."""
    while True:
        try:
            check_clock()
        except Exception:  # noqa: BLE001
            log.exception("clock check failed")
        import time as _t
        _t.sleep(3600)


if __name__ == "__main__":
    try:
        main()
    except ConfigError as e:
        log.critical("fatal: %s", e)
        raise SystemExit(2)
