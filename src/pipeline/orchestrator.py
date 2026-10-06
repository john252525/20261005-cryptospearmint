"""Argparse CLI. Без typer (не в pyproject).

  python -m src.pipeline.orchestrator fetch    --symbol BTCUSDT --interval 1m --days 7
  python -m src.pipeline.orchestrator audit
  python -m src.pipeline.orchestrator backtest --config configs/example.yaml
  python -m src.pipeline.orchestrator qa       --allow-no-creds
  python -m src.pipeline.orchestrator report   --kind daily
  python -m src.pipeline.orchestrator snapshot --tag pre_promotion
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY   = sys.executable
REP  = ROOT / "docs" / "reports"
LOG  = ROOT / "logs"
REP.mkdir(parents=True, exist_ok=True)
LOG.mkdir(exist_ok=True)
JOURNAL = ROOT / "data" / "journal.jsonl"
STATE   = ROOT / "data" / "state.db"


def _run(cmd: list[str], *, fail_stage: str) -> int:
    print("$ " + " ".join(cmd))
    rc = subprocess.call(cmd, cwd=ROOT)
    if rc:
        try:
            from src.pipeline.notify import pipeline_fail
            pipeline_fail(fail_stage, rc)
        except Exception:
            pass
        return rc
    return 0


def cmd_fetch(a) -> int:
    return _run([PY, "-m", "src.data.fetch_crypto",
                 "--symbol", a.symbol, "--interval", a.interval,
                 "--days", str(a.days)], fail_stage="fetch")


def cmd_audit(a) -> int:
    return _run([PY, "scripts/data_audit.py"], fail_stage="audit")


def cmd_backtest(a) -> int:
    return _run([PY, "-m", "src.research.backtest_sma", "--config", a.config],
                fail_stage="backtest")


def cmd_qa(a) -> int:
    cmd = [PY, "-m", "qa.honesty_checks",
           "--journal", a.journal, "--db", a.db]
    if a.allow_no_creds:
        cmd.append("--allow-no-creds")
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (LOG / "qa_last.log").write_text(p.stdout + "\n---\n" + p.stderr)
    (REP / "qa_latest.md").write_text(
        "# QA report\n\n```\n" + p.stdout + "\n" + p.stderr + "\n```\n")
    sys.stdout.write(p.stdout)
    sys.stderr.write(p.stderr)
    return p.returncode


def cmd_report(a) -> int:
    if a.kind == "daily":
        from src.pipeline.daily_report import build_daily
        print(build_daily(a.out))
    else:
        from src.pipeline.daily_report import build_qa
        print(build_qa(a.out))
    return 0


def cmd_snapshot(a) -> int:
    from scripts.rollback import snapshot
    print(snapshot(a.tag))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="orchestrator",
                                description="Trading pipeline orchestrator")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch")
    f.add_argument("--symbol",   default="BTCUSDT")
    f.add_argument("--interval", default="1m")
    f.add_argument("--days",     type=int, default=7)
    f.set_defaults(func=cmd_fetch)

    sub.add_parser("audit").set_defaults(func=cmd_audit)

    b = sub.add_parser("backtest")
    b.add_argument("--config", default="configs/example.yaml")
    b.set_defaults(func=cmd_backtest)

    q = sub.add_parser("qa")
    q.add_argument("--journal", default=str(JOURNAL))
    q.add_argument("--db",      default=str(STATE))
    q.add_argument("--allow-no-creds", action="store_true")
    q.set_defaults(func=cmd_qa)

    r = sub.add_parser("report")
    r.add_argument("--kind", choices=["daily", "qa"], default="daily")
    r.add_argument("--out", default=None)
    r.set_defaults(func=cmd_report)

    s = sub.add_parser("snapshot")
    s.add_argument("--tag", default=None)
    s.set_defaults(func=cmd_snapshot)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
