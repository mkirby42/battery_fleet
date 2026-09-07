from dataclasses import dataclass

DEGRADATION_USD_PER_KILOWATT_HOUR = 0.05
TRACKING_PENALTY_USD_PER_KILOWATT_HOUR = 0.20
HOME_RATE_USD_PER_KILOWATT_HOUR = 0.14


@dataclass(frozen=True)
class FleetScore:
    price_usd_per_megawatt_hour: float
    customer_bill_usd: float
    no_battery_customer_bill_usd: float
    wholesale_pnl_usd: float
    ancillary_revenue_usd: float
    degradation_cost_usd: float
    tracking_penalty_usd: float
    score_usd: float


def customer_billable_watts(
    load_power_watts: float,
    battery_power_watts: float,
) -> float:
    """
    House energy that still came from the grid.

    Charging is not passed through to the customer.
    Export does not credit the customer.
    """
    meter_watts = load_power_watts + battery_power_watts
    return max(0.0, min(meter_watts, load_power_watts))


def planned_action_score_usd(
    battery_power_watts: float,
    load_power_watts: float,
    price_usd_per_megawatt_hour: float,
    delta_t_seconds: float,
) -> float:
    """
    Company profit for one planned battery power, before
    ancillary and miss. Used by greedy.
    """
    return score_tick(
        load_power_watts,
        battery_power_watts,
        battery_power_watts,
        price_usd_per_megawatt_hour,
        delta_t_seconds,
    ).score_usd


def score_tick(
    load_power_watts: float,
    actual_battery_power_watts: float,
    commanded_battery_power_watts: float,
    price_usd_per_megawatt_hour: float,
    delta_t_seconds: float,
    ancillary_revenue_usd: float = 0.0,
) -> FleetScore:
    degradation, tracking = battery_costs_usd(
        actual_battery_power_watts,
        commanded_battery_power_watts,
        delta_t_seconds,
    )
    return _score_tick_with_costs(
        load_power_watts,
        actual_battery_power_watts,
        price_usd_per_megawatt_hour,
        delta_t_seconds,
        ancillary_revenue_usd,
        degradation,
        tracking,
    )


def score_site_tick(
    load_power_watts: float,
    actual_power_watts_by_unit_id: dict[str, float],
    commanded_power_watts_by_unit_id: dict[str, float],
    price_usd_per_megawatt_hour: float,
    delta_t_seconds: float,
) -> FleetScore:
    if actual_power_watts_by_unit_id.keys() != (
        commanded_power_watts_by_unit_id.keys()
    ):
        raise ValueError("Actual and commanded unit IDs must match.")
    costs = [
        battery_costs_usd(
            actual_power_watts,
            commanded_power_watts_by_unit_id[unit_id],
            delta_t_seconds,
        )
        for unit_id, actual_power_watts in (
            actual_power_watts_by_unit_id.items()
        )
    ]
    return _score_tick_with_costs(
        load_power_watts,
        sum(actual_power_watts_by_unit_id.values()),
        price_usd_per_megawatt_hour,
        delta_t_seconds,
        0.0,
        sum(cost[0] for cost in costs),
        sum(cost[1] for cost in costs),
    )


def battery_costs_usd(
    actual_power_watts: float,
    commanded_power_watts: float,
    delta_t_seconds: float,
) -> tuple[float, float]:
    if delta_t_seconds <= 0:
        raise ValueError("delta_t_seconds must be positive.")

    delta_t_hours = delta_t_seconds / 3600.0
    degradation = (
        abs(actual_power_watts)
        / 1000.0
        * delta_t_hours
        * DEGRADATION_USD_PER_KILOWATT_HOUR
    )
    tracking = (
        abs(commanded_power_watts - actual_power_watts)
        / 1000.0
        * delta_t_hours
        * TRACKING_PENALTY_USD_PER_KILOWATT_HOUR
    )
    return degradation, tracking


def _score_tick_with_costs(
    load_power_watts: float,
    actual_battery_power_watts: float,
    price_usd_per_megawatt_hour: float,
    delta_t_seconds: float,
    ancillary_revenue_usd: float,
    degradation_cost_usd: float,
    tracking_penalty_usd: float,
) -> FleetScore:
    if delta_t_seconds <= 0:
        raise ValueError("delta_t_seconds must be positive.")

    delta_t_hours = delta_t_seconds / 3600.0
    billed_watts = customer_billable_watts(
        load_power_watts,
        actual_battery_power_watts,
    )
    customer_kwh = billed_watts / 1000.0 * delta_t_hours
    no_battery_kwh = max(load_power_watts, 0.0) / 1000.0 * delta_t_hours
    customer_bill_usd = (
        customer_kwh * HOME_RATE_USD_PER_KILOWATT_HOUR
    )
    no_battery_customer_bill_usd = (
        no_battery_kwh * HOME_RATE_USD_PER_KILOWATT_HOUR
    )

    meter_watts = load_power_watts + actual_battery_power_watts
    meter_mwh = meter_watts / 1_000_000.0 * delta_t_hours
    wholesale_pnl_usd = -price_usd_per_megawatt_hour * meter_mwh
    score_usd = (
        customer_bill_usd
        + wholesale_pnl_usd
        + ancillary_revenue_usd
        - degradation_cost_usd
        - tracking_penalty_usd
    )
    return FleetScore(
        price_usd_per_megawatt_hour=price_usd_per_megawatt_hour,
        customer_bill_usd=customer_bill_usd,
        no_battery_customer_bill_usd=no_battery_customer_bill_usd,
        wholesale_pnl_usd=wholesale_pnl_usd,
        ancillary_revenue_usd=ancillary_revenue_usd,
        degradation_cost_usd=degradation_cost_usd,
        tracking_penalty_usd=tracking_penalty_usd,
        score_usd=score_usd,
    )


def add_scores(
    scores: list[FleetScore],
    ancillary_revenue_usd: float = 0.0,
) -> FleetScore | None:
    if not scores:
        return None
    price = scores[0].price_usd_per_megawatt_hour
    customer = sum(score.customer_bill_usd for score in scores)
    no_battery = sum(
        score.no_battery_customer_bill_usd for score in scores
    )
    wholesale = sum(score.wholesale_pnl_usd for score in scores)
    wear = sum(score.degradation_cost_usd for score in scores)
    miss = sum(score.tracking_penalty_usd for score in scores)
    profit = customer + wholesale + ancillary_revenue_usd - wear - miss
    return FleetScore(
        price_usd_per_megawatt_hour=price,
        customer_bill_usd=customer,
        no_battery_customer_bill_usd=no_battery,
        wholesale_pnl_usd=wholesale,
        ancillary_revenue_usd=ancillary_revenue_usd,
        degradation_cost_usd=wear,
        tracking_penalty_usd=miss,
        score_usd=profit,
    )
