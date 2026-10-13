"""Risk engine tests: limits, kill-switch, portfolio."""
import pytest

from risk.kill_switch import KillSwitch, flatten_all
from risk.limits import Limits
from risk.structures import Order, Portfolio, Position, Side


def big(**over):
    base = dict(max_position_size=1e9, max_gross_exposure=1e9,
                max_net_exposure=1e9, max_daily_loss=1e9,
                max_drawdown_pct=1e9, max_single_symbol_pct=1e9,
                max_orders_per_minute=1000)
    base.update(over)
    return Limits(**base)


def test_approve_small():
    r = big().check_order(Order("1", "AAPL", Side.BUY, 10, 100.0),
                          Portfolio(cash=1_000_000))
    assert r.approved and r.reason == "OK"


def test_reject_position_size():
    lim = big(max_position_size=1_000, max_single_symbol_pct=100)
    r = lim.check_order(Order("1", "AAPL", Side.BUY, 100, 100.0),
                        Portfolio(cash=1_000_000))
    assert not r.approved and "position size" in r.reason


def test_reject_gross():
    lim = big(max_gross_exposure=5_000, max_single_symbol_pct=100)
    r = lim.check_order(Order("1", "AAPL", Side.BUY, 100, 100.0),
                        Portfolio(cash=1_000_000))
    assert not r.approved and "gross" in r.reason


def test_reject_symbol_pct():
    lim = big(max_single_symbol_pct=5.0)
    r = lim.check_order(Order("1", "AAPL", Side.BUY, 1_000, 100.0),
                        Portfolio(cash=1_000_000))
    assert not r.approved and "AAPL" in r.reason


def test_rate_limit():
    lim = big(max_orders_per_minute=1)
    p = Portfolio(cash=1_000_000)
    o = Order("1", "AAPL", Side.BUY, 1, 100.0)
    assert lim.check_order(o, p).approved
    assert not lim.check_order(o, p).approved


def test_kill_l1():
    p = Portfolio(cash=100_000)
    p.nav_start_of_day = 100_000
    p.peak_nav = 99_000
    p.cash = 98_500
    ks = KillSwitch({"daily_loss_l1": 1_000.0})
    ks.auto_check(p)
    assert ks.level == 1


def test_kill_l2():
    p = Portfolio(cash=100_000)
    p.cash = 95_500
    ks = KillSwitch()
    ks.auto_check(p)
    assert ks.level == 2


def test_kill_l3():
    p = Portfolio(cash=100_000)
    p.cash = 93_000
    ks = KillSwitch()
    ks.auto_check(p)
    assert ks.level == 3


def test_kill_l4():
    p = Portfolio(cash=100_000)
    p.cash = 91_000
    ks = KillSwitch()
    ks.auto_check(p)
    assert ks.level == 4


def test_kill_monotonic():
    ks = KillSwitch()
    ks.trigger(3, "x")
    ks.trigger(1, "y")
    assert ks.level == 3 and len(ks.events) == 1


def test_kill_reset():
    ks = KillSwitch()
    ks.trigger(2, "x")
    ks.reset()
    assert ks.level == 0
    assert any(e.reason.startswith("RESET") for e in ks.events)


def test_drawdown():
    p = Portfolio(cash=100_000)
    assert p.drawdown_pct == 0.0
    p.cash = 92_000
    assert p.drawdown_pct == pytest.approx(8.0)


def test_daily_loss():
    p = Portfolio(cash=100_000, nav_start_of_day=100_000)
    p.cash = 97_500
    assert p.daily_loss == pytest.approx(2_500.0)


def test_apply_fill_realized():
    p = Portfolio(cash=10_000)
    p.apply_fill(Order("1", "AAPL", Side.BUY, 10, 100.0))
    p.apply_fill(Order("2", "AAPL", Side.SELL, 10, 110.0))
    assert "AAPL" not in p.positions
    assert p.realized_pnl == pytest.approx(100.0)


def test_position_unrealized():
    pos = Position("AAPL", 10, 100.0, 110.0)
    assert pos.unrealized_pnl == pytest.approx(100.0)
    assert pos.notional == pytest.approx(1_100.0)


def test_flatten_plan():
    positions = [Position("AAPL", 10, 100.0, 110.0),
                 Position("TSLA", -5, 200.0, 195.0)]
    plan = flatten_all(positions)
    assert plan[0] == {"symbol": "AAPL", "side": "SELL", "qty": 10,
                       "type": "MARKET", "current_px": 110.0}
    assert plan[1]["side"] == "BUY" and plan[1]["qty"] == 5
