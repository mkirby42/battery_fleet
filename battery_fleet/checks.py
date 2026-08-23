from battery_fleet.clocks import TICK_S
from battery_fleet.local_policy import floor_kwh
from battery_fleet.types import Check, Interval, LocalPolicy, Scoreboard, Tick, Unit


def run_checks(
    ticks: list[Tick],
    units: list[Unit],
    local: LocalPolicy,
    duration_s: int,
) -> list[Check]:
    capacity_by_unit = {u.id: u.capacity_kwh for u in units}
    floor_by_unit = {u.id: floor_kwh(u, local) for u in units}

    soc_ok = all(
        0.0 <= tick.energy_kwh <= capacity_by_unit[tick.unit_id]
        for tick in ticks
        if tick.unit_id in capacity_by_unit
    )
    soc = Check(
        "soc_in_range",
        soc_ok,
        "ok" if soc_ok else "energy outside [0, capacity]",
    )

    islanded_ok = not any(
        tick.islanded and tick.who_decided == "hq" for tick in ticks
    )
    islanded = Check(
        "islanded_no_market",
        islanded_ok,
        "ok" if islanded_ok else "islanded tick with hq decision",
    )

    if local.kind == "aggressive":
        reserve_ok = True
    else:
        reserve_ok = not any(
            tick.who_decided == "hq"
            and tick.power_kw > 0
            and tick.energy_kwh < floor_by_unit.get(tick.unit_id, 0.0) - 1e-9
            for tick in ticks
        )
    reserve = Check(
        "fixed_reserve_floor",
        reserve_ok,
        "ok" if reserve_ok else "hq discharge below floor",
    )

    align_ok = all(
        tick.t_s % TICK_S == 0 and 0 <= tick.t_s < duration_s for tick in ticks
    )
    align = Check(
        "ticks_align",
        align_ok,
        "ok" if align_ok else "tick times misaligned",
    )

    return [soc, islanded, reserve, align]


def scoreboard(
    ticks: list[Tick],
    intervals: list[Interval],
    units: list[Unit],
    local: LocalPolicy,
) -> Scoreboard:
    floor_by_unit = {u.id: floor_kwh(u, local) for u in units}
    dt_h = TICK_S / 3600.0

    revenue_usd = sum(iv.pnl_usd for iv in intervals)
    shortfall_kwh = sum(tick.shortfall_kwh for tick in ticks)
    served_islanded = sum(
        max(tick.power_kw, 0.0) * dt_h for tick in ticks if tick.islanded
    )
    coverage = 1.0 - shortfall_kwh / max(shortfall_kwh + served_islanded, 1e-9)
    locations_dark = len(
        {tick.unit_id for tick in ticks if tick.shortfall_kwh > 0}
    )
    time_at_floor_s = sum(
        TICK_S
        for tick in ticks
        if tick.energy_kwh <= floor_by_unit.get(tick.unit_id, 0.0) + 1e-6
    )

    return Scoreboard(
        revenue_usd=revenue_usd,
        shortfall_kwh=shortfall_kwh,
        coverage=coverage,
        locations_dark=locations_dark,
        time_at_floor_s=time_at_floor_s,
    )
