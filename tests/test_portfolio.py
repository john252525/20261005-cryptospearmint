import pytest

from src.paper.portfolio import DeltaNeutralPortfolio
from src.strategies.funding_carry.config import FundingCarrySettings


@pytest.fixture()
def pf(tmp_path):
    s = FundingCarrySettings(
        max_pos_per_symbol_usd=1000.0,
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    )
    p = DeltaNeutralPortfolio(str(tmp_path / "state.db"), s)
    yield p
    p.close()


def test_funding_income_sign():
    assert DeltaNeutralPortfolio.funding_income(
        "long_spot_short_perp", 0.0001, 1000.0) == pytest.approx(0.1)
    assert DeltaNeutralPortfolio.funding_income(
        "short_spot_long_perp", 0.0001, 1000.0) == pytest.approx(-0.1)
    assert DeltaNeutralPortfolio.funding_income(
        "flat", 0.0001, 1000.0) == 0.0


def test_position_recovery_from_sqlite(tmp_path):
    s = FundingCarrySettings(max_pos_per_symbol_usd=1000.0)
    db = str(tmp_path / "state.db")
    p1 = DeltaNeutralPortfolio(db, s)
    pid = p1.open_position(
        symbol="BTCUSDT", exchange="binance", direction="long_spot_short_perp",
        spot_qty=1.0 / 60.0, perp_qty=-1.0 / 60.0,
        spot_entry=60000.0, perp_entry=60060.0,
        entry_funding_bps=2.0, notional_usd=1000.0,
    )
    p1.close()

    p2 = DeltaNeutralPortfolio(db, s)
    open_pos = p2.recover()
    assert len(open_pos) == 1
    assert open_pos[0]["id"] == pid
    assert open_pos[0]["symbol"] == "BTCUSDT"
    assert p2.has_open("BTCUSDT", "binance") is True
    assert p2.has_open("ETHUSDT", "binance") is False
    p2.close()


def test_mark_to_market_delta_neutral(tmp_path):
    s = FundingCarrySettings(max_pos_per_symbol_usd=1000.0)
    p = DeltaNeutralPortfolio(str(tmp_path / "state.db"), s)
    qty = 1000.0 / 60000.0
    p.open_position(
        symbol="BTCUSDT", exchange="binance",
        direction="long_spot_short_perp",
        spot_qty=qty, perp_qty=-qty,
        spot_entry=60000.0, perp_entry=60000.0,
        entry_funding_bps=2.0, notional_usd=1000.0,
    )
    m = p.mark_to_market({"BTCUSDT": {"spot": 60000.0, "perp": 60000.0}})
    assert m["delta_usd"] == pytest.approx(0.0, abs=1e-6)
    assert m["delta_bps_nav"] == pytest.approx(0.0, abs=1e-6)
    assert m["nav"] == pytest.approx(3000.0, abs=1e-6)
    p.close()


def test_profitable_after_basis_convergence(tmp_path):
    s = FundingCarrySettings(max_pos_per_symbol_usd=1000.0)
    p = DeltaNeutralPortfolio(str(tmp_path / "state.db"), s)
    qty = 1000.0 / 60000.0
    pid = p.open_position(
        symbol="BTCUSDT", exchange="binance",
        direction="long_spot_short_perp",
        spot_qty=qty, perp_qty=-qty,
        spot_entry=60000.0, perp_entry=60060.0,
        entry_funding_bps=2.0, notional_usd=1000.0,
    )
    pnl = p.close_position(pid, spot_exit=60000.0, perp_exit=60000.0)
    assert pnl > 0
    assert p.realized_pnl == pytest.approx(pnl)
    p.close()


def test_funding_accrual_accumulates(tmp_path):
    s = FundingCarrySettings(max_pos_per_symbol_usd=1000.0)
    p = DeltaNeutralPortfolio(str(tmp_path / "state.db"), s)
    qty = 1000.0 / 60000.0
    p.open_position(
        symbol="BTCUSDT", exchange="binance",
        direction="long_spot_short_perp",
        spot_qty=qty, perp_qty=-qty,
        spot_entry=60000.0, perp_entry=60060.0,
        entry_funding_bps=2.0, notional_usd=1000.0,
    )
    for _ in range(3):
        p.accrue_funding("BTCUSDT", funding_rate=0.0001, notional_usd=1000.0)
    assert p.funding_accrued == pytest.approx(0.3)
    m = p.mark_to_market({"BTCUSDT": {"spot": 60000.0, "perp": 60060.0}})
    assert m["nav"] == pytest.approx(3000.0 + 0.3, abs=1e-6)
    p.close()


def test_snapshot_persisted(tmp_path):
    s = FundingCarrySettings(max_pos_per_symbol_usd=1000.0)
    p = DeltaNeutralPortfolio(str(tmp_path / "state.db"), s)
    p.snapshot({"BTCUSDT": {"spot": 60000.0, "perp": 60000.0}})
    rows = p._conn.execute(
        "SELECT COUNT(*) AS n FROM pnl_snapshots").fetchone()
    assert rows["n"] == 1
    p.close()
