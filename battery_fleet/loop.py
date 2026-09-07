from dataclasses import dataclass

from battery_fleet.battery import BatteryUnit
from battery_fleet.economics import FleetScore, add_scores, score_site_tick
from battery_fleet.fleet import Fleet
from battery_fleet.installation import Installation


@dataclass(frozen=True)
class TickInput:
    user_load_power_watts: float
    commanded_power_watts_by_unit_id: dict[str, float]


@dataclass(frozen=True)
class TickRecord:
    """
    One site after one step. Later a row per site, plus a row
    per unit from the dicts (command, actual, soc, reachable).
    """
    time_unix: float
    install_id: str
    user_load_power_watts: float
    grid_power_watts: float
    commanded_power_watts_by_unit_id: dict[str, float]
    actual_power_watts_by_unit_id: dict[str, float]
    state_of_charge_fraction_by_unit_id: dict[str, float]
    network_reachable_by_unit_id: dict[str, bool]


@dataclass(frozen=True)
class FleetTickInput:
    user_load_power_watts_by_install_id: dict[str, float]
    commanded_power_watts_by_unit_id: dict[str, float]
    fleet_target_power_watts: float | None = None
    price_usd_per_megawatt_hour: float | None = None
    ancillary_revenue_usd: float = 0.0


@dataclass(frozen=True)
class FleetTickRecord:
    """
    One fleet after one step. Totals are what a fleet_response
    event needs. site_records keep the per-house / per-unit
    detail. Tracking error is commanded minus actual.
    """
    time_unix: float
    fleet_target_power_watts: float | None
    fleet_actual_power_watts: float
    fleet_commanded_power_watts: float
    fleet_tracking_error_watts: float
    fleet_load_power_watts: float
    n_units: int
    n_unreachable: int
    score: FleetScore | None
    site_records: tuple[TickRecord, ...]


def snapshot_site(installation: Installation) -> TickRecord:
    return TickRecord(
        time_unix=installation.state.time_unix,
        install_id=installation.install_id,
        user_load_power_watts=installation.state.user_load_power_watts,
        grid_power_watts=installation.state.grid_power_watts,
        commanded_power_watts_by_unit_id={
            battery.unit_id: battery.state.commanded_power_watts
            for battery in installation.batteries
        },
        actual_power_watts_by_unit_id={
            battery.unit_id: battery.state.actual_power_watts
            for battery in installation.batteries
        },
        state_of_charge_fraction_by_unit_id={
            battery.unit_id: battery.state.state_of_charge_fraction
            for battery in installation.batteries
        },
        network_reachable_by_unit_id={
            battery.unit_id: battery.state.network_reachable
            for battery in installation.batteries
        },
    )


def run(
    installation: Installation,
    delta_t_seconds: float,
    ticks: list[TickInput],
) -> list[TickRecord]:
    """
    Advance one installation through a list of ticks.

    Each tick sets house load, delivers any new commands, then steps.
    A unit with no command this tick keeps its last command.
    """
    units_by_id = {
        battery.unit_id: battery
        for battery in installation.batteries
    }

    records = []
    for tick in ticks:
        installation.set_user_load_power_watts(
            tick.user_load_power_watts
        )
        _deliver_commands(
            units_by_id,
            tick.commanded_power_watts_by_unit_id,
        )
        installation.step(delta_t_seconds)
        records.append(snapshot_site(installation))

    return records


def run_fleet(
    fleet: Fleet,
    delta_t_seconds: float,
    ticks: list[FleetTickInput],
) -> list[FleetTickRecord]:
    """
    Advance every site. Each tick sets any new house loads,
    delivers any new unit commands, then steps every site.
    Omitted loads and commands keep their last value.
    """
    if not fleet.installations:
        raise ValueError("Fleet has no sites.")

    sites_by_id = {
        site.install_id: site
        for site in fleet.installations
    }
    units_by_id: dict[str, BatteryUnit] = {}
    for site in fleet.installations:
        for battery in site.batteries:
            if battery.unit_id in units_by_id:
                raise ValueError(
                    f"Duplicate unit_id: {battery.unit_id}"
                )
            units_by_id[battery.unit_id] = battery

    records = []
    for tick in ticks:
        for install_id, load_watts in (
            tick.user_load_power_watts_by_install_id.items()
        ):
            site = sites_by_id.get(install_id)
            if site is None:
                raise ValueError(
                    f"Unknown install_id: {install_id}"
                )
            site.set_user_load_power_watts(load_watts)

        _deliver_commands(
            units_by_id,
            tick.commanded_power_watts_by_unit_id,
        )

        for site in fleet.installations:
            site.step(delta_t_seconds)

        site_records = tuple(
            snapshot_site(site)
            for site in fleet.installations
        )
        records.append(
            _summarize_fleet(
                site_records,
                tick.fleet_target_power_watts,
                tick.price_usd_per_megawatt_hour,
                tick.ancillary_revenue_usd,
                delta_t_seconds,
            )
        )

    return records


def _deliver_commands(
    units_by_id: dict[str, BatteryUnit],
    commanded_power_watts_by_unit_id: dict[str, float],
) -> None:
    for unit_id, power_watts in commanded_power_watts_by_unit_id.items():
        battery = units_by_id.get(unit_id)
        if battery is None:
            raise ValueError(
                f"Unknown unit_id: {unit_id}"
            )
        battery.command_power_watts(power_watts)


def _summarize_fleet(
    site_records: tuple[TickRecord, ...],
    fleet_target_power_watts: float | None,
    price_usd_per_megawatt_hour: float | None,
    ancillary_revenue_usd: float,
    delta_t_seconds: float,
) -> FleetTickRecord:
    actual = sum(
        power
        for record in site_records
        for power in record.actual_power_watts_by_unit_id.values()
    )
    commanded = sum(
        power
        for record in site_records
        for power in record.commanded_power_watts_by_unit_id.values()
    )
    if price_usd_per_megawatt_hour is None:
        score = None
    else:
        site_scores = []
        for record in site_records:
            site_scores.append(
                score_site_tick(
                    record.user_load_power_watts,
                    record.actual_power_watts_by_unit_id,
                    record.commanded_power_watts_by_unit_id,
                    price_usd_per_megawatt_hour,
                    delta_t_seconds,
                )
            )
        score = add_scores(site_scores, ancillary_revenue_usd)
    return FleetTickRecord(
        time_unix=site_records[0].time_unix,
        fleet_target_power_watts=fleet_target_power_watts,
        fleet_actual_power_watts=actual,
        fleet_commanded_power_watts=commanded,
        fleet_tracking_error_watts=commanded - actual,
        fleet_load_power_watts=sum(
            record.user_load_power_watts
            for record in site_records
        ),
        n_units=sum(
            len(record.actual_power_watts_by_unit_id)
            for record in site_records
        ),
        n_unreachable=sum(
            1
            for record in site_records
            for reachable in record.network_reachable_by_unit_id.values()
            if not reachable
        ),
        score=score,
        site_records=site_records,
    )
