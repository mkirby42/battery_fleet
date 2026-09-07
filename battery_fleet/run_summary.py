from battery_fleet.fleet import Fleet
from battery_fleet.loop import FleetTickRecord

EPSILON = 1e-6


def build_run_payload(
    run_id: str,
    fleet: Fleet,
    records: list[FleetTickRecord],
    dt_seconds: float,
    *,
    normalized_metadata: tuple[str, str, int] | None = None,
) -> dict:
    sites, units, site_id_by_unit = static_sites_and_units(fleet)
    ticks, commands = fleet_ticks_and_commands(
        records,
        site_id_by_unit,
        include_units=normalized_metadata is None,
    )
    if records:
        started_at_unix = records[0].time_unix
    elif fleet.installations:
        started_at_unix = fleet.installations[0].state.time_unix
    else:
        started_at_unix = 0.0
    payload = {
        "id": run_id,
        "dt_seconds": dt_seconds,
        "started_at_unix": started_at_unix,
        "sites": sites,
        "units": units,
        "ticks": ticks,
        "commands": commands,
    }
    if normalized_metadata is not None:
        comparison_id, controller, fleet_seed = normalized_metadata
        payload.update(
            {
                "comparison_id": comparison_id,
                "controller": controller,
                "fleet_seed": fleet_seed,
                "detail_files": {
                    "installations": "installation_ticks.jsonl",
                    "units": "unit_ticks.jsonl",
                },
            }
        )
    return payload


def static_sites_and_units(
    fleet: Fleet,
) -> tuple[list[dict], list[dict], dict[str, str]]:
    sites = []
    units = []
    site_id_by_unit = {}
    for site in fleet.installations:
        unit_ids = [battery.unit_id for battery in site.batteries]
        sites.append(
            {
                "id": site.install_id,
                "lat": site.latitude_degrees,
                "lon": site.longitude_degrees,
                "unit_ids": unit_ids,
            }
        )
        for battery in site.batteries:
            units.append(
                {
                    "id": battery.unit_id,
                    "site_id": site.install_id,
                    "capacity_kwh": (
                        battery.nominal_capacity_kilowatt_hours
                    ),
                }
            )
            site_id_by_unit[battery.unit_id] = site.install_id
    return sites, units, site_id_by_unit


def fleet_ticks_and_commands(
    records: list[FleetTickRecord],
    site_id_by_unit: dict[str, str],
    *,
    include_units: bool,
) -> tuple[list[dict], list[dict]]:
    ticks = []
    commands = []
    cumulative_score_usd = 0.0
    cumulative_customer_bill_usd = 0.0
    previous_target = None
    previous_units = None

    for record in records:
        units = fleet_tick_units(record)
        if record.score is None:
            score_usd = wholesale_pnl_usd = customer_bill_usd = None
            no_battery_bill_usd = price = None
        else:
            score_usd = record.score.score_usd
            wholesale_pnl_usd = record.score.wholesale_pnl_usd
            customer_bill_usd = record.score.customer_bill_usd
            no_battery_bill_usd = record.score.no_battery_customer_bill_usd
            price = record.score.price_usd_per_megawatt_hour
            cumulative_score_usd += score_usd
            cumulative_customer_bill_usd += customer_bill_usd

        tick = {
            "time_unix": record.time_unix,
            "price_usd_per_mwh": price,
            "target_w": record.fleet_target_power_watts,
            "fleet_w": record.fleet_actual_power_watts,
            "commanded_w": record.fleet_commanded_power_watts,
            "error_w": record.fleet_tracking_error_watts,
            "load_w": record.fleet_load_power_watts,
            "score_usd": score_usd,
            "wholesale_pnl_usd": wholesale_pnl_usd,
            "customer_bill_usd": customer_bill_usd,
            "no_battery_customer_bill_usd": no_battery_bill_usd,
            "n_unreachable": record.n_unreachable,
            "mean_soc": mean_soc(units),
            "cumulative_score_usd": cumulative_score_usd,
            "cumulative_customer_bill_usd": cumulative_customer_bill_usd,
        }
        if include_units:
            tick["units"] = units
        ticks.append(tick)
        commands.extend(
            command_events(
                record.time_unix,
                record.fleet_target_power_watts,
                previous_target,
                units,
                previous_units,
                site_id_by_unit,
            )
        )
        previous_target = record.fleet_target_power_watts
        previous_units = units

    return ticks, commands


def fleet_tick_units(record: FleetTickRecord) -> dict[str, dict]:
    units = {}
    for site in record.site_records:
        for unit_id, soc in (
            site.state_of_charge_fraction_by_unit_id.items()
        ):
            units[unit_id] = {
                "soc": soc,
                "actual_w": site.actual_power_watts_by_unit_id[unit_id],
                "commanded_w": (
                    site.commanded_power_watts_by_unit_id[unit_id]
                ),
                "reachable": (
                    site.network_reachable_by_unit_id[unit_id]
                ),
            }
    return units


def mean_soc(units: dict[str, dict]) -> float:
    socs = [unit["soc"] for unit in units.values()]
    return sum(socs) / len(socs) if socs else 0.0


def command_events(
    time_unix: float,
    target_w: float | None,
    previous_target: float | None,
    units: dict[str, dict],
    previous_units: dict[str, dict] | None,
    site_id_by_unit: dict[str, str],
) -> list[dict]:
    events = []
    if target_w is not None and _changed(previous_target, target_w):
        events.append(_event(time_unix, "target", None, None, target_w))

    for unit_id, unit in units.items():
        site_id = site_id_by_unit[unit_id]
        commanded_w = unit["commanded_w"]
        if previous_units is None:
            if commanded_w != 0:
                events.append(
                    _event(
                        time_unix,
                        "setpoint",
                        unit_id,
                        site_id,
                        commanded_w,
                    )
                )
        else:
            previous = previous_units[unit_id]
            if _changed(previous["commanded_w"], commanded_w):
                events.append(
                    _event(
                        time_unix,
                        "setpoint",
                        unit_id,
                        site_id,
                        commanded_w,
                    )
                )
            if unit["reachable"] != previous["reachable"]:
                kind = "online" if unit["reachable"] else "offline"
                events.append(
                    _event(time_unix, kind, unit_id, site_id, None)
                )

        if abs(commanded_w - unit["actual_w"]) > EPSILON:
            events.append(
                _event(time_unix, "clip", unit_id, site_id, commanded_w)
            )

    return events


def _event(
    time_unix: float,
    kind: str,
    unit_id: str | None,
    site_id: str | None,
    watts: float | None,
) -> dict:
    return {
        "time_unix": time_unix,
        "kind": kind,
        "unit_id": unit_id,
        "site_id": site_id,
        "watts": watts,
        "note": "",
    }


def _changed(previous: float | None, current: float | None) -> bool:
    if previous is None and current is None:
        return False
    if previous is None or current is None:
        return True
    return abs(previous - current) > EPSILON
