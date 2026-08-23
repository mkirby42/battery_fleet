from battery_fleet.local_policy import floor_kwh, local_setpoint
from battery_fleet.types import LocalPolicy, Unit


def test_fixed_reserve_floor():
    u = Unit("u1", capacity_kwh=10.0, max_charge_kw=5.0, max_discharge_kw=5.0)
    p = LocalPolicy("lp", "fixed_reserve", 0.2)
    assert floor_kwh(u, p) == 2.0


def test_aggressive_floor_is_zero():
    u = Unit("u1", 10.0, 5.0, 5.0)
    p = LocalPolicy("lp", "aggressive", 0.0)
    assert floor_kwh(u, p) == 0.0


def test_islanded_serves_load():
    kw = local_setpoint(islanded=True, location_load_kw=2.0, hq_asked_kw=8.0)
    assert kw == 2.0


def test_grid_tied_local_does_not_invent_setpoint():
    kw = local_setpoint(islanded=False, location_load_kw=2.0, hq_asked_kw=8.0)
    assert kw is None
