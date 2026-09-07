import pytest

from battery_fleet.economics import add_scores, score_site_tick
from battery_fleet.loop import FleetTickRecord, TickRecord
from battery_fleet.run_details import detail_rows

T0 = 1_700_000_900.0
DT = 900.0
PRICE = 200.0


def make_record(
    *,
    load_w: float,
    actual_w: dict[str, float],
    commanded_w: dict[str, float] | None = None,
    reachable: dict[str, bool] | None = None,
) -> FleetTickRecord:
    commanded_w = commanded_w or actual_w
    reachable = reachable or {unit_id: True for unit_id in actual_w}
    site = TickRecord(
        time_unix=T0,
        install_id="i1",
        user_load_power_watts=load_w,
        grid_power_watts=load_w + sum(actual_w.values()),
        commanded_power_watts_by_unit_id=commanded_w,
        actual_power_watts_by_unit_id=actual_w,
        state_of_charge_fraction_by_unit_id={
            unit_id: 0.5 for unit_id in actual_w
        },
        network_reachable_by_unit_id=reachable,
    )
    site_score = score_site_tick(
        load_w,
        actual_w,
        commanded_w,
        PRICE,
        DT,
    )
    return FleetTickRecord(
        time_unix=T0,
        fleet_target_power_watts=None,
        fleet_actual_power_watts=sum(actual_w.values()),
        fleet_commanded_power_watts=sum(commanded_w.values()),
        fleet_tracking_error_watts=(
            sum(commanded_w.values()) - sum(actual_w.values())
        ),
        fleet_load_power_watts=load_w,
        n_units=len(actual_w),
        n_unreachable=sum(not value for value in reachable.values()),
        score=add_scores([site_score]),
        site_records=(site,),
    )


def rows_for(record: FleetTickRecord) -> tuple[list[dict], list[dict]]:
    return detail_rows(
        run_id="greedy-1",
        comparison_id="comparison-1",
        controller="greedy",
        records=[record],
        dt_seconds=DT,
    )


def assert_reconciles(site: dict, units: list[dict]) -> None:
    assert sum(
        row["customer_payment_change_usd"] for row in units
    ) == pytest.approx(
        site["customer_bill_usd"]
        - site["no_battery_customer_bill_usd"]
    )
    assert sum(
        row["profit_contribution_usd"] for row in units
    ) == pytest.approx(
        site["company_profit_usd"]
        - site["no_battery_company_profit_usd"]
    )


def test_unequal_discharge_allocates_customer_change_proportionally():
    installation_rows, unit_rows = rows_for(
        make_record(load_w=1_500.0, actual_w={"u1": -1_000.0, "u2": -500.0})
    )

    site = installation_rows[0]
    units = {row["unit_id"]: row for row in unit_rows}
    assert site["battery_w"] == -1_500.0
    assert site["grid_w"] == 0.0
    assert units["u1"]["customer_payment_change_usd"] == pytest.approx(
        2 * units["u2"]["customer_payment_change_usd"]
    )
    assert_reconciles(site, unit_rows)


@pytest.mark.parametrize(
    ("actual_w", "commanded_w", "reachable"),
    [
        ({"u1": 1_000.0, "u2": 0.0}, None, None),
        (
            {"u1": 0.0, "u2": -400.0},
            {"u1": -1_000.0, "u2": -1_000.0},
            {"u1": False, "u2": True},
        ),
        (
            {"u1": -250.0, "u2": 0.0},
            {"u1": -1_000.0, "u2": 0.0},
            None,
        ),
    ],
)
def test_charging_idle_stale_and_clipped_rows_reconcile(
    actual_w,
    commanded_w,
    reachable,
):
    installation_rows, unit_rows = rows_for(
        make_record(
            load_w=1_500.0,
            actual_w=actual_w,
            commanded_w=commanded_w,
            reachable=reachable,
        )
    )

    site = installation_rows[0]
    assert_reconciles(site, unit_rows)
    assert sum(
        row["degradation_cost_usd"] for row in unit_rows
    ) == pytest.approx(site["degradation_cost_usd"])
    assert sum(
        row["tracking_penalty_usd"] for row in unit_rows
    ) == pytest.approx(site["tracking_penalty_usd"])
    if sum(actual_w.values()) >= 0:
        assert all(
            row["customer_payment_change_usd"] == 0.0 for row in unit_rows
        )


def test_mixed_sign_wear_and_tracking_reconcile():
    record = make_record(
        load_w=1_500.0,
        actual_w={"u1": 1_000.0, "u2": -1_000.0},
        commanded_w={"u1": 2_000.0, "u2": -2_000.0},
    )
    installation_rows, unit_rows = rows_for(record)

    site = installation_rows[0]
    assert site["degradation_cost_usd"] == pytest.approx(
        sum(row["degradation_cost_usd"] for row in unit_rows)
    )
    assert site["tracking_penalty_usd"] == pytest.approx(
        sum(row["tracking_penalty_usd"] for row in unit_rows)
    )
    assert record.score.degradation_cost_usd == pytest.approx(
        site["degradation_cost_usd"]
    )
    assert record.score.tracking_penalty_usd == pytest.approx(
        site["tracking_penalty_usd"]
    )
    assert record.score.score_usd == pytest.approx(
        site["company_profit_usd"]
    )
    assert_reconciles(site, unit_rows)
