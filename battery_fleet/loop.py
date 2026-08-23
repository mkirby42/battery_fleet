from battery_fleet.clocks import TICK_S
from battery_fleet.hq_policy import hq_asked_kw
from battery_fleet.local_policy import floor_kwh, local_setpoint
from battery_fleet.physics import apply_setpoint
from battery_fleet.types import (
    BatteryModel,
    HqPolicy,
    LocalPolicy,
    Location,
    Tick,
    Unit,
)


def step_unit(
    t_s: int,
    prev: Tick,
    unit: Unit,
    location: Location,
    battery: BatteryModel,
    local: LocalPolicy,
    hq: HqPolicy,
    spp: float,
    location_load_kw: float,
    islanded: bool,
    link_up: bool,
) -> Tick:
    asked = hq_asked_kw(unit, hq, spp, link_up, islanded)
    local_kw = local_setpoint(islanded, location_load_kw, asked)

    if islanded:
        who_decided = "local"
        setpoint = local_kw
    elif not link_up:
        who_decided = "local"
        setpoint = 0.0
    else:
        who_decided = "hq"
        setpoint = asked if asked is not None else 0.0

    floor = floor_kwh(unit, local)
    energy, power = apply_setpoint(
        prev.energy_kwh,
        setpoint,
        unit.capacity_kwh,
        unit.max_charge_kw,
        unit.max_discharge_kw,
        floor,
        battery.efficiency,
        TICK_S,
    )

    if islanded:
        dt_h = TICK_S / 3600.0
        desired_kwh = location_load_kw * dt_h
        served = max(power, 0) * dt_h
        shortfall = max(0.0, desired_kwh - served)
    else:
        shortfall = 0.0

    return Tick(
        t_s,
        unit.id,
        energy,
        power,
        who_decided,
        asked,
        shortfall,
        islanded,
        link_up,
    )
