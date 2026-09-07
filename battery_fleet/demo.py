from battery_fleet.battery import BatteryUnit
from battery_fleet.control import greedy
from battery_fleet.fleet import Fleet
from battery_fleet.lookahead import commands_for_targets, plan_fleet
from battery_fleet.loop import FleetTickInput, FleetTickRecord, run_fleet
from battery_fleet.prices import Market

LOAD_WATTS = 1_500.0


def run_market_day(
    fleet: Fleet,
    market: Market,
    offline_unit_ids: list[str],
    offline_tick: int,
    online_tick: int,
    ancillary_revenue_usd: float = 5.0,
) -> list[FleetTickRecord]:
    """
    One price, one dispatch, one fleet tick. Take named
    units offline / online at the given tick indices.
    """
    units_by_id = {
        battery.unit_id: battery
        for site in fleet.installations
        for battery in site.batteries
    }
    loads = {
        site.install_id: LOAD_WATTS
        for site in fleet.installations
    }

    records = []
    for index in range(len(market)):
        price = market.price_at(index)
        if index == offline_tick:
            _set_reachability(units_by_id, offline_unit_ids, False)
        if index == online_tick:
            _set_reachability(units_by_id, offline_unit_ids, True)

        commands = greedy(
            fleet,
            price,
            market.dt_seconds,
            ancillary_revenue_usd=ancillary_revenue_usd,
            load_watts_by_install_id=loads,
        )
        tick_ancillary = (
            ancillary_revenue_usd
            if abs(sum(commands.values())) > 1e-6
            else 0.0
        )
        records.extend(
            run_fleet(
                fleet,
                market.dt_seconds,
                [
                    FleetTickInput(
                        loads,
                        commands,
                        fleet_target_power_watts=sum(commands.values()),
                        price_usd_per_megawatt_hour=price,
                        ancillary_revenue_usd=tick_ancillary,
                    )
                ],
            )
        )
    return records


def run_lookahead_day(
    fleet: Fleet,
    market: Market,
    offline_unit_ids: list[str],
    offline_tick: int,
    online_tick: int,
    ancillary_revenue_usd: float = 5.0,
) -> list[FleetTickRecord]:
    """
    Lock a perfect-price plan before the first tick, then
    execute each house target against current fleet state.
    """
    units_by_id = {
        battery.unit_id: battery
        for site in fleet.installations
        for battery in site.batteries
    }
    loads = {
        site.install_id: LOAD_WATTS
        for site in fleet.installations
    }
    targets_by_tick = plan_fleet(fleet, market, loads)

    records = []
    for index, house_targets in enumerate(targets_by_tick):
        if index == offline_tick:
            _set_reachability(units_by_id, offline_unit_ids, False)
        if index == online_tick:
            _set_reachability(units_by_id, offline_unit_ids, True)

        commands = commands_for_targets(
            fleet,
            house_targets,
            market.dt_seconds,
        )
        tick_ancillary = (
            ancillary_revenue_usd
            if abs(sum(commands.values())) > 1e-6
            else 0.0
        )
        records.extend(
            run_fleet(
                fleet,
                market.dt_seconds,
                [
                    FleetTickInput(
                        loads,
                        commands,
                        fleet_target_power_watts=sum(house_targets.values()),
                        price_usd_per_megawatt_hour=market.price_at(index),
                        ancillary_revenue_usd=tick_ancillary,
                    )
                ],
            )
        )
    return records


def _set_reachability(
    units_by_id: dict[str, BatteryUnit],
    unit_ids: list[str],
    online: bool,
) -> None:
    for unit_id in unit_ids:
        battery = units_by_id.get(unit_id)
        if battery is None:
            raise ValueError(f"Unknown unit_id: {unit_id}")
        if online:
            battery.come_online()
        else:
            battery.go_offline()
