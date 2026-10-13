"""Unified CLI over trading-desk modules.

  python -m src.pipeline.orchestrator fetch --symbol BTCUSDT --interval 1h --days 7
  python -m src.pipeline.orchestrator audit
  python -m src.pipeline.orchestrator backtest --strategy funding_carry --since 90d
  python -m src.pipeline.orchestrator qa --allow-no-creds
  python -m src.pipeline.orchestrator report --kind daily
  python -m src.pipeline.orchestrator snapshot --tag pre_promotion
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, help="Trading-desk pipeline orchestrator")

ROOT    = Path(__file__).resolve().parents[2]
REP     = ROOT / "docs" / "reports"
LOG     = ROOT / "logs"
JOURNAL = ROOT / "data" / "journal.jsonl"
STATE   = ROOT / "data" / "state.db"


def _resolve(candidates: list[str]) -> str:
    for m in candidates:
        try:
            if importlib.util.find_spec(m) is not None:
                return m
        except (ImportError, ValueError):
            continue
    raise typer.BadParameter("none of these modules found: " + ", ".join(candidates))


def _run_module(module: str, args: list[str], *, stage: str) -> int:
    cmd = [sys.executable, "-m", module, *args]
    typer.echo("$ " + " ".join(cmd))
    rc = subprocess.call(cmd, cwd=ROOT)
    if rc:
        try:
            from src.pipeline.notify import pipeline_fail
            pipeline_fail(stage=stage, code=rc)
        except Exception:
            pass
        raise typer.Exit(rc)
    return rc


@app.command()
def fetch(symbol: str = typer.Option("BTCUSDT"),
          interval: str = typer.Option("1h"),
          days: int = typer.Option(30)) -> None:
    m = _resolve(["src.data.fetch_crypto", "data.fetch_crypto"])
    _run_module(m, ["--symbol", symbol, "--interval", interval, "--days", str(days)],
                stage="fetch")


@app.command()
def audit() -> None:
    _run_module("scripts.data_audit", [], stage="audit")


@app.command()
def backtest(strategy: str = typer.Option("funding_carry"),
             since: str = typer.Option("90d")) -> None:
    if strategy == "funding_carry":
        m = _resolve(["src.strategies.funding_carry.backtest",
                      "strategies.funding_carry.backtest"])
        _run_module(m, ["--since", since], stage="backtest.funding_carry")
    elif strategy == "sma":
        m = _resolve(["src.research.backtest_sma", "research.backtest_sma"])
        _run_module(m, ["--since", since], stage="backtest.sma")
    else:
        raise typer.BadParameter(f"unknown strategy: {strategy}")


@app.command()
def qa(journal: Path = typer.Option(JOURNAL),
       db: Path = typer.Option(STATE),
       allow_no_creds: bool = typer.Option(False, "--allow-no-creds")) -> None:
    m = _resolve(["src.qa.honesty_checks", "qa.honesty_checks"])
    args = ["--journal", str(journal), "--db", str(db)]
    if allow_no_creds:
        args.append("--allow-no-creds")
    cmd = [sys.executable, "-m", m, *args]
    typer.echo("$ " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    LOG.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    (LOG / "qa_last.log").write_text(p.stdout + "\n---\n" + p.stderr)
    (REP / "qa_latest.md").write_text(
        "# QA report\n\n```\n" + p.stdout + "\n" + p.stderr + "\n```\n")
    sys.stdout.write(p.stdout)
    sys.stderr.write(p.stderr)
    raise typer.Exit(p.returncode)


@app.command()
def report(kind: str = typer.Option("daily")) -> None:
    if kind == "daily":
        from src.pipeline.daily_report import build_daily
        typer.echo(str(build_daily()))
    elif kind == "qa":
        from src.pipeline.daily_report import build_qa
        typer.echo(str(build_qa()))
    else:
        raise typer.BadParameter(f"unknown kind: {kind}")


@app.command()
def snapshot(tag: str = typer.Option("")) -> None:
    from scripts.rollback import snapshot as _snap
    typer.echo(str(_snap(tag or None)))


if __name__ == "__main__":
    app()
