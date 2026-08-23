from battery_fleet.checks import run_checks, scoreboard
from battery_fleet.types import Interval, LocalPolicy, Tick, Unit

U = Unit("u1", 10.0, 5.0, 5.0)
LP = LocalPolicy("lp", "fixed_reserve", 0.2)


def test_soc_out_of_range_fails():
    ticks = [Tick(0, "u1", 99.0, 0.0, "local", None, 0.0, False, True)]
    checks = run_checks(ticks, [U], LP, duration_s=15)
    soc = next(c for c in checks if c.name == "soc_in_range")
    assert soc.passed is False


def test_islanded_market_kwh_fails():
    ticks = [Tick(0, "u1", 5.0, 3.0, "hq", 3.0, 0.0, True, True)]
    checks = run_checks(ticks, [U], LP, duration_s=15)
    row = next(c for c in checks if c.name == "islanded_no_market")
    assert row.passed is False


def test_fixed_reserve_through_floor_fails():
    ticks = [Tick(0, "u1", 1.9, 1.0, "hq", 1.0, 0.0, False, True)]
    checks = run_checks(ticks, [U], LP, duration_s=15)
    row = next(c for c in checks if c.name == "fixed_reserve_floor")
    assert row.passed is False


def test_clean_ticks_all_pass():
    ticks = [Tick(0, "u1", 5.0, 0.0, "local", None, 0.0, False, True)]
    checks = run_checks(ticks, [U], LP, duration_s=15)
    assert len(checks) == 4
    assert all(c.passed for c in checks)


def test_scoreboard_sums_revenue():
    intervals = [Interval(0, 0.1, 4.0, 40.0, 0.0, 0.0, 0.0, 40.0)]
    ticks = [Tick(0, "u1", 5.0, 0.0, "local", None, 0.0, False, True)]
    sb = scoreboard(ticks, intervals, [U], LP)
    assert sb.revenue_usd == 4.0
