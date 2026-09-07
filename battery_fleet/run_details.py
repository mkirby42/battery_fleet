from battery_fleet.economics import (
    battery_costs_usd,
    score_site_tick,
)
from battery_fleet.loop import FleetTickRecord, TickRecord


def detail_rows(
    run_id: str,
    comparison_id: str,
    controller: str,
    records: list[FleetTickRecord],
    dt_seconds: float,
) -> tuple[list[dict], list[dict]]:
    installation_rows = []
    unit_rows = []
    for tick_index, record in enumerate(records):
        if record.score is None:
            raise ValueError("Normalized runs require a price for every tick.")
        price = record.score.price_usd_per_megawatt_hour
        for site in record.site_records:
            installation, units = _site_rows(
                run_id,
                comparison_id,
                controller,
                tick_index,
                site,
                price,
                dt_seconds,
            )
            installation_rows.append(installation)
            unit_rows.extend(units)
    return installation_rows, unit_rows


def _site_rows(
    run_id: str,
    comparison_id: str,
    controller: str,
    tick_index: int,
    site: TickRecord,
    price: float,
    dt_seconds: float,
) -> tuple[dict, list[dict]]:
    actual_w = sum(site.actual_power_watts_by_unit_id.values())
    commanded_w = sum(site.commanded_power_watts_by_unit_id.values())
    score = score_site_tick(
        site.user_load_power_watts,
        site.actual_power_watts_by_unit_id,
        site.commanded_power_watts_by_unit_id,
        price,
        dt_seconds,
    )
    dt_hours = dt_seconds / 3600.0
    load_mwh = site.user_load_power_watts / 1_000_000.0 * dt_hours
    no_battery_profit = (
        score.no_battery_customer_bill_usd - price * load_mwh
    )
    installation = {
        "run_id": run_id,
        "comparison_id": comparison_id,
        "controller": controller,
        "tick_index": tick_index,
        "time_unix": site.time_unix,
        "install_id": site.install_id,
        "load_w": site.user_load_power_watts,
        "battery_w": actual_w,
        "grid_w": site.grid_power_watts,
        "customer_bill_usd": score.customer_bill_usd,
        "no_battery_customer_bill_usd": (
            score.no_battery_customer_bill_usd
        ),
        "wholesale_pnl_usd": score.wholesale_pnl_usd,
        "degradation_cost_usd": score.degradation_cost_usd,
        "tracking_penalty_usd": score.tracking_penalty_usd,
        "company_profit_usd": score.score_usd,
        "no_battery_company_profit_usd": no_battery_profit,
    }
    payment_change = (
        score.customer_bill_usd - score.no_battery_customer_bill_usd
    )
    discharging_w = sum(
        abs(power)
        for power in site.actual_power_watts_by_unit_id.values()
        if power < 0
    )
    units = [
        _unit_row(
            run_id,
            comparison_id,
            controller,
            tick_index,
            site,
            unit_id,
            price,
            dt_seconds,
            payment_change,
            discharging_w,
        )
        for unit_id in site.actual_power_watts_by_unit_id
    ]
    return installation, units


def _unit_row(
    run_id: str,
    comparison_id: str,
    controller: str,
    tick_index: int,
    site: TickRecord,
    unit_id: str,
    price: float,
    dt_seconds: float,
    site_payment_change: float,
    discharging_w: float,
) -> dict:
    actual_w = site.actual_power_watts_by_unit_id[unit_id]
    commanded_w = site.commanded_power_watts_by_unit_id[unit_id]
    dt_hours = dt_seconds / 3600.0
    unit_mwh = actual_w / 1_000_000.0 * dt_hours
    wholesale = -price * unit_mwh
    degradation, tracking = battery_costs_usd(
        actual_w,
        commanded_w,
        dt_seconds,
    )
    if site_payment_change < 0 and actual_w < 0:
        payment_change = site_payment_change * abs(actual_w) / discharging_w
    else:
        payment_change = 0.0
    return {
        "run_id": run_id,
        "comparison_id": comparison_id,
        "controller": controller,
        "tick_index": tick_index,
        "time_unix": site.time_unix,
        "install_id": site.install_id,
        "unit_id": unit_id,
        "soc": site.state_of_charge_fraction_by_unit_id[unit_id],
        "actual_w": actual_w,
        "commanded_w": commanded_w,
        "reachable": site.network_reachable_by_unit_id[unit_id],
        "wholesale_contribution_usd": wholesale,
        "customer_payment_change_usd": payment_change,
        "degradation_cost_usd": degradation,
        "tracking_penalty_usd": tracking,
        "profit_contribution_usd": (
            wholesale + payment_change - degradation - tracking
        ),
    }
