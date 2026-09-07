from battery_fleet.battery import BatteryUnit
from battery_fleet.economics import planned_action_score_usd
from battery_fleet.fleet import Fleet


def split_target(
    fleet: Fleet,
    fleet_target_power_watts: float,
) -> dict[str, float]:
    """
    Even split of a fleet target across units that can
    receive a command. Unreachable units are omitted.
    Does not look at power or reserve headroom.
    """
    reachable = _reachable_units(fleet)
    if not reachable:
        return {}

    share_watts = fleet_target_power_watts / len(reachable)
    return {
        battery.unit_id: share_watts
        for battery in reachable
    }


def allocate_target(
    fleet: Fleet,
    fleet_target_power_watts: float,
    delta_t_seconds: float,
) -> dict[str, float]:
    """
    Split a fleet target across reachable units without
    asking any unit for more than it can do this step.
    If the target is larger than total headroom, every
    unit is filled to its limit.
    """
    return _allocate_units(
        _reachable_units(fleet),
        fleet_target_power_watts,
        delta_t_seconds,
    )


def _allocate_units(
    units: list[BatteryUnit],
    target_power_watts: float,
    delta_t_seconds: float,
) -> dict[str, float]:
    if delta_t_seconds <= 0:
        raise ValueError("delta_t_seconds must be positive.")
    if not units:
        return {}

    delta_t_hours = delta_t_seconds / 3600.0
    if target_power_watts >= 0:
        sign = 1.0
        headroom = {
            battery.unit_id: battery.charge_headroom_watts(delta_t_hours)
            for battery in units
        }
    else:
        sign = -1.0
        headroom = {
            battery.unit_id: battery.discharge_headroom_watts(delta_t_hours)
            for battery in units
        }

    remaining = abs(target_power_watts)
    allocated = {unit_id: 0.0 for unit_id in headroom}

    while remaining > 1e-6:
        active = [
            unit_id
            for unit_id, filled in allocated.items()
            if filled + 1e-9 < headroom[unit_id]
        ]
        if not active:
            break
        share = remaining / len(active)
        for unit_id in active:
            take = min(share, headroom[unit_id] - allocated[unit_id])
            allocated[unit_id] += take
            remaining -= take

    return {
        unit_id: sign * watts
        for unit_id, watts in allocated.items()
    }


def _reachable_units(fleet: Fleet) -> list[BatteryUnit]:
    return [
        battery
        for site in fleet.installations
        for battery in site.batteries
        if battery.state.network_reachable
    ]


def solve_dispatch(
    fleet: Fleet,
    price_usd_per_megawatt_hour: float,
    delta_t_seconds: float,
    ancillary_revenue_usd: float = 0.0,
    load_watts_by_install_id: dict[str, float] | None = None,
) -> dict[str, float]:
    """
    One-tick economic dispatch. For each house, pick charge,
    discharge, idle, or cover the load. Ancillary revenue is
    a placeholder added to the score later; it does not
    change the power choice.
    """
    del ancillary_revenue_usd

    if delta_t_seconds <= 0:
        raise ValueError("delta_t_seconds must be positive.")

    loads = load_watts_by_install_id or {}
    delta_t_hours = delta_t_seconds / 3600.0
    commands = {}
    for site in fleet.installations:
        units = [
            battery
            for battery in site.batteries
            if battery.state.network_reachable
        ]
        if not units:
            continue
        load_watts = loads.get(
            site.install_id,
            site.state.user_load_power_watts,
        )
        target = _best_site_power_watts(
            units,
            load_watts,
            price_usd_per_megawatt_hour,
            delta_t_seconds,
            delta_t_hours,
        )
        commands.update(
            _allocate_units(units, target, delta_t_seconds)
        )
    return commands


greedy = solve_dispatch


def _best_site_power_watts(
    units: list[BatteryUnit],
    load_power_watts: float,
    price_usd_per_megawatt_hour: float,
    delta_t_seconds: float,
    delta_t_hours: float,
) -> float:
    charge_watts = sum(
        battery.charge_headroom_watts(delta_t_hours)
        for battery in units
    )
    discharge_watts = sum(
        battery.discharge_headroom_watts(delta_t_hours)
        for battery in units
    )
    candidates = [0.0]
    if charge_watts > 0:
        candidates.append(charge_watts)
    if discharge_watts > 0:
        candidates.append(-discharge_watts)
    if load_power_watts > 1e-6 and load_power_watts <= discharge_watts + 1e-9:
        candidates.append(-load_power_watts)

    return max(
        candidates,
        key=lambda power_watts: planned_action_score_usd(
            power_watts,
            load_power_watts,
            price_usd_per_megawatt_hour,
            delta_t_seconds,
        ),
    )
