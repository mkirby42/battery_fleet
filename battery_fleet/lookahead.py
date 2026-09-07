from battery_fleet.control import _allocate_units
from battery_fleet.economics import planned_action_score_usd
from battery_fleet.fleet import Fleet
from battery_fleet.prices import Market

CAPACITY_KWH_PER_UNIT = 10.0
MAX_POWER_WATTS_PER_UNIT = 10_000.0
CHARGE_EFFICIENCY = 0.95
DISCHARGE_EFFICIENCY = 0.95
RESERVE_SOC = 0.20
INITIAL_SOC = 0.50
SOC_STEP = 0.005


def plan_house(
    n_units: int,
    market: Market,
    load_watts: float,
) -> list[float]:
    """
    House battery power for every tick, locked at the
    start of the day. Positive is charge.
    """
    if n_units <= 0:
        return [0.0] * len(market)
    if load_watts < 0:
        raise ValueError("load_watts must be non-negative.")

    capacity_kwh = n_units * CAPACITY_KWH_PER_UNIT
    max_power_watts = n_units * MAX_POWER_WATTS_PER_UNIT
    n_ticks = len(market)
    n_levels = int(round(1.0 / SOC_STEP)) + 1
    dt_seconds = market.dt_seconds
    dt_hours = dt_seconds / 3600.0

    value_next = [0.0] * n_levels
    policy = [[0.0] * n_levels for _ in range(n_ticks)]

    for tick in range(n_ticks - 1, -1, -1):
        price = market.price_at(tick)
        value_now = [0.0] * n_levels
        for level in range(n_levels):
            soc = level * SOC_STEP
            best = None
            best_power = 0.0
            for power in _candidates(
                soc,
                load_watts,
                capacity_kwh,
                max_power_watts,
                dt_hours,
            ):
                score = planned_action_score_usd(
                    power,
                    load_watts,
                    price,
                    dt_seconds,
                )
                next_soc = _next_soc(
                    soc,
                    power,
                    capacity_kwh,
                    dt_hours,
                )
                next_level = _level_of(next_soc)
                total = score + value_next[next_level]
                if best is None or total > best:
                    best = total
                    best_power = power
            value_now[level] = best if best is not None else 0.0
            policy[tick][level] = best_power
        value_next = value_now

    level = _level_of(INITIAL_SOC)
    plan = []
    for tick in range(n_ticks):
        power = policy[tick][level]
        plan.append(power)
        soc = _next_soc(
            level * SOC_STEP,
            power,
            capacity_kwh,
            dt_hours,
        )
        level = _level_of(soc)
    return plan


def plan_fleet(
    fleet: Fleet,
    market: Market,
    load_watts_by_install_id: dict[str, float],
) -> list[dict[str, float]]:
    """
    One house-target map per tick. Houses of the same
    size and load share one locked plan.
    """
    cache: dict[tuple[int, float], list[float]] = {}
    sites = []
    for site in fleet.installations:
        units = [
            battery
            for battery in site.batteries
            if battery.state.network_reachable
        ]
        load_watts = load_watts_by_install_id.get(
            site.install_id,
            site.state.user_load_power_watts,
        )
        key = (len(units), load_watts)
        if key not in cache:
            cache[key] = plan_house(len(units), market, load_watts)
        sites.append((site.install_id, cache[key]))

    schedules = []
    for tick in range(len(market)):
        schedules.append({
            install_id: house_plan[tick]
            for install_id, house_plan in sites
        })
    return schedules


def commands_for_targets(
    fleet: Fleet,
    target_watts_by_install_id: dict[str, float],
    dt_seconds: float,
) -> dict[str, float]:
    """
    Split locked house targets using the batteries that
    are reachable and physically able to act right now.
    """
    commands = {}
    for site in fleet.installations:
        target_watts = target_watts_by_install_id.get(site.install_id)
        if target_watts is None:
            continue
        reachable = [
            battery
            for battery in site.batteries
            if battery.state.network_reachable
        ]
        commands.update(_allocate_units(reachable, target_watts, dt_seconds))
    return commands


def _candidates(
    soc: float,
    load_watts: float,
    capacity_kwh: float,
    max_power_watts: float,
    dt_hours: float,
) -> list[float]:
    charge_watts = _charge_headroom(
        soc,
        capacity_kwh,
        max_power_watts,
        dt_hours,
    )
    discharge_watts = _discharge_headroom(
        soc,
        capacity_kwh,
        max_power_watts,
        dt_hours,
    )
    choices = [0.0]
    if charge_watts > 0:
        choices.append(charge_watts)
    if discharge_watts > 0:
        choices.append(-discharge_watts)
    if load_watts > 1e-6 and load_watts <= discharge_watts + 1e-9:
        choices.append(-load_watts)
    return choices


def _charge_headroom(
    soc: float,
    capacity_kwh: float,
    max_power_watts: float,
    dt_hours: float,
) -> float:
    available_storage_kwh = (1.0 - soc) * capacity_kwh
    if available_storage_kwh <= 1e-12:
        return 0.0
    max_grid_kwh = available_storage_kwh / CHARGE_EFFICIENCY
    return min(max_power_watts, max_grid_kwh / dt_hours * 1000.0)


def _discharge_headroom(
    soc: float,
    capacity_kwh: float,
    max_power_watts: float,
    dt_hours: float,
) -> float:
    dispatchable_soc = max(0.0, soc - RESERVE_SOC)
    stored_kwh = dispatchable_soc * capacity_kwh
    deliverable_kwh = stored_kwh * DISCHARGE_EFFICIENCY
    if deliverable_kwh <= 1e-12:
        return 0.0
    return min(max_power_watts, deliverable_kwh / dt_hours * 1000.0)


def _next_soc(
    soc: float,
    power_watts: float,
    capacity_kwh: float,
    dt_hours: float,
) -> float:
    power_kw = power_watts / 1000.0
    charge_kw = max(power_kw, 0.0)
    discharge_kw = max(-power_kw, 0.0)
    stored_change_kwh = (
        CHARGE_EFFICIENCY * charge_kw
        - discharge_kw / DISCHARGE_EFFICIENCY
    ) * dt_hours
    return max(0.0, min(1.0, soc + stored_change_kwh / capacity_kwh))


def _level_of(soc: float) -> int:
    snapped = max(0.0, min(1.0, soc))
    return int(round(snapped / SOC_STEP))
