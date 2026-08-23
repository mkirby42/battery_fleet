from battery_fleet.clocks import INTERVAL_S, TICK_S
from battery_fleet.grid import link_up, location_islanded
from battery_fleet.hq_policy import hq_asked_kw
from battery_fleet.load import load_at
from battery_fleet.local_policy import floor_kwh, local_setpoint
from battery_fleet.market import price_at, settle_interval
from battery_fleet.physics import apply_setpoint
from battery_fleet.scenario import World
from battery_fleet.types import (
    BatteryModel,
    Event,
    HqPolicy,
    Interval,
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


def simulate(world: World) -> tuple[list[Tick], list[Event], list[Interval]]:
    units_by_id = {u.id: u for u in world.units}
    locations_by_id = {l.id: l for l in world.locations}

    last: dict[str, Tick] = {}
    all_ticks: list[Tick] = []
    events: list[Event] = []
    intervals: list[Interval] = []

    for t in range(0, world.duration_s, TICK_S):
        for install in world.installs:
            unit = units_by_id[install.unit_id]
            loc = locations_by_id[install.location_id]
            prev = last.get(unit.id) or Tick(
                t - TICK_S,
                unit.id,
                0.5 * unit.capacity_kwh,
                0.0,
                "local",
                None,
                0.0,
                False,
                True,
            )
            islanded = location_islanded(
                loc,
                world.outages,
                t,
                world.substations,
                world.cities,
                world.regions,
            )
            linked = link_up(loc.id, world.link_windows, t)
            load = load_at(world.loads, loc.id, t)
            price = price_at(world.prices, t)
            tick = step_unit(
                t,
                prev,
                unit,
                loc,
                world.battery_model,
                world.local_policy,
                world.hq_policy,
                price.spp,
                load,
                islanded,
                linked,
            )
            if unit.id in last:
                old = last[unit.id]
                if old.islanded != tick.islanded:
                    kind = "outage_start" if tick.islanded else "outage_end"
                    events.append(Event(t, kind, unit.id, loc.id, ""))
                if old.link_up != tick.link_up:
                    kind = "link_down" if not tick.link_up else "link_up"
                    events.append(Event(t, kind, unit.id, loc.id, ""))
            last[unit.id] = tick
            all_ticks.append(tick)
        if t > 0 and t % INTERVAL_S == 0:
            window = [x for x in all_ticks if t - INTERVAL_S <= x.t_s < t]
            intervals.append(
                settle_interval(
                    t - INTERVAL_S,
                    window,
                    price_at(world.prices, t - INTERVAL_S),
                )
            )

    last_start = (world.duration_s - 1) // INTERVAL_S * INTERVAL_S
    if not any(iv.t_s == last_start for iv in intervals):
        window = [
            x for x in all_ticks if last_start <= x.t_s < world.duration_s
        ]
        intervals.append(
            settle_interval(
                last_start,
                window,
                price_at(world.prices, last_start),
            )
        )

    return all_ticks, events, intervals
