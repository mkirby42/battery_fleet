from dataclasses import replace
from pathlib import Path

from battery_fleet.loop import simulate, step_unit
from battery_fleet.scenario import load_scenario
from battery_fleet.types import (
    BatteryModel, HqPolicy, LocalPolicy, Location, Tick, Unit,
)

U = Unit("u1", 10.0, 5.0, 5.0)
LOC = Location("l1", 32.0, -97.0, "s1")
BM = BatteryModel("b", 1.0)
LP = LocalPolicy("lp", "fixed_reserve", 0.2)
HQ = HqPolicy("hq", 20.0, 80.0)


def test_hq_discharges_when_linked_and_pricey():
    prev = Tick(0, "u1", 8.0, 0.0, "hq", 0.0, 0.0, False, True)
    tick = step_unit(
        t_s=15, prev=prev, unit=U, location=LOC, battery=BM,
        local=LP, hq=HQ, spp=120.0, location_load_kw=1.0,
        islanded=False, link_up=True,
    )
    assert tick.who_decided == "hq"
    assert tick.hq_asked_kw == 5.0
    assert tick.power_kw > 0
    assert tick.islanded is False
    assert tick.link_up is True


def test_islanded_is_local_and_records_shortfall_if_empty():
    prev = Tick(0, "u1", 0.0, 0.0, "local", None, 0.0, True, True)
    tick = step_unit(
        t_s=15, prev=prev, unit=U, location=LOC, battery=BM,
        local=LP, hq=HQ, spp=120.0, location_load_kw=2.0,
        islanded=True, link_up=True,
    )
    assert tick.who_decided == "local"
    assert tick.hq_asked_kw is None
    assert tick.shortfall_kwh > 0


def test_silent_reverts_to_local_hold():
    prev = Tick(0, "u1", 8.0, 5.0, "hq", 5.0, 0.0, False, True)
    tick = step_unit(
        t_s=15, prev=prev, unit=U, location=LOC, battery=BM,
        local=LP, hq=HQ, spp=120.0, location_load_kw=1.0,
        islanded=False, link_up=False,
    )
    assert tick.who_decided == "local"
    assert tick.hq_asked_kw is None
    assert tick.power_kw == 0.0  # no last-setpoint


def test_simulate_seeds_start_soc_frac():
    tiny = Path(__file__).resolve().parents[1] / "scenarios" / "tiny.yaml"
    world = replace(load_scenario(tiny), start_soc_frac=0.25)
    ticks, _, _ = simulate(world)
    first = [t for t in ticks if t.t_s == 0]
    assert first
    assert all(abs(t.energy_kwh - 2.5) < 1e-9 for t in first)
