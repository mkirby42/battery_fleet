import pytest

from battery_fleet.economics import (
    HOME_RATE_USD_PER_KILOWATT_HOUR,
    score_tick,
)

DT = 900.0
HOURS = DT / 3600.0
LOAD = 1_500.0
PRICE = 200.0


def test_idle_customer_pays_home_rate_on_load():
    score = score_tick(
        load_power_watts=LOAD,
        actual_battery_power_watts=0.0,
        commanded_battery_power_watts=0.0,
        price_usd_per_megawatt_hour=PRICE,
        delta_t_seconds=DT,
    )

    expected_bill = HOME_RATE_USD_PER_KILOWATT_HOUR * (LOAD / 1000.0) * HOURS
    assert score.customer_bill_usd == pytest.approx(expected_bill)
    assert score.no_battery_customer_bill_usd == pytest.approx(expected_bill)


def test_charging_does_not_raise_customer_bill():
    idle = score_tick(LOAD, 0.0, 0.0, PRICE, DT)
    charge = score_tick(LOAD, 2_000.0, 2_000.0, PRICE, DT)

    assert charge.customer_bill_usd == pytest.approx(idle.customer_bill_usd)
    assert charge.customer_bill_usd == pytest.approx(
        charge.no_battery_customer_bill_usd
    )


def test_covering_the_house_lowers_the_customer_bill():
    idle = score_tick(LOAD, 0.0, 0.0, PRICE, DT)
    cover = score_tick(LOAD, -LOAD, -LOAD, PRICE, DT)

    assert cover.customer_bill_usd == pytest.approx(0.0)
    assert cover.customer_bill_usd < idle.customer_bill_usd


def test_export_does_not_credit_the_customer_bill():
    dump = score_tick(LOAD, -10_000.0, -10_000.0, PRICE, DT)
    assert dump.customer_bill_usd == pytest.approx(0.0)


def test_wholesale_is_on_the_meter_not_the_battery():
    charge = score_tick(LOAD, 2_000.0, 2_000.0, PRICE, DT)
    meter_mwh = (LOAD + 2_000.0) / 1_000_000.0 * HOURS
    assert charge.wholesale_pnl_usd == pytest.approx(-PRICE * meter_mwh)


def test_company_profit_is_customer_plus_wholesale_minus_wear():
    score = score_tick(LOAD, 2_000.0, 2_000.0, PRICE, DT, ancillary_revenue_usd=5.0)
    assert score.score_usd == pytest.approx(
        score.customer_bill_usd
        + score.wholesale_pnl_usd
        + 5.0
        - score.degradation_cost_usd
        - score.tracking_penalty_usd
    )
