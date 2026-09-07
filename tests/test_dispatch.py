import pytest

from battery_fleet import BatteryUnit, Installation
from battery_fleet.control import greedy, solve_dispatch
from battery_fleet.economics import HOME_RATE_USD_PER_KILOWATT_HOUR
from battery_fleet.fleet import Fleet, build_fleet
from battery_fleet.loop import FleetTickInput, run_fleet

T0 = 1_700_000_000.0
DT = 900.0


def make_unit(unit_id: str) -> BatteryUnit:
    return BatteryUnit(
        unit_id,
        "lot-a",
        10.0,
        10_000.0,
        10_000.0,
        T0,
    )


def make_two_site_fleet() -> Fleet:
    return Fleet(
        [
            Installation("i1", 30.0, -97.0, T0, [make_unit("u1")]),
            Installation(
                "i2",
                31.0,
                -98.0,
                T0,
                [make_unit("u2"), make_unit("u3")],
            ),
        ]
    )


def test_greedy_is_solve_dispatch():
    fleet = make_two_site_fleet()
    assert greedy(fleet, -80.0, DT) == solve_dispatch(fleet, -80.0, DT)


def test_negative_price_charges_at_headroom():
    fleet = make_two_site_fleet()
    commands = solve_dispatch(fleet, -80.0, DT)

    assert commands == {
        "u1": 10_000.0,
        "u2": 10_000.0,
        "u3": 10_000.0,
    }


def test_high_price_discharges_at_headroom():
    fleet = make_two_site_fleet()
    commands = solve_dispatch(fleet, 200.0, DT)

    assert commands == {
        "u1": -10_000.0,
        "u2": -10_000.0,
        "u3": -10_000.0,
    }


def test_low_positive_price_stays_idle():
    fleet = make_two_site_fleet()
    commands = solve_dispatch(fleet, 20.0, DT)

    assert commands == {"u1": 0.0, "u2": 0.0, "u3": 0.0}


def test_ancillary_placeholder_does_not_change_commands():
    fleet = make_two_site_fleet()
    without = solve_dispatch(fleet, 200.0, DT, ancillary_revenue_usd=0.0)
    with_as = solve_dispatch(fleet, 200.0, DT, ancillary_revenue_usd=99.0)
    assert without == with_as


def test_dispatch_skips_unreachable():
    fleet = make_two_site_fleet()
    fleet.installations[0].batteries[0].go_offline()
    commands = solve_dispatch(fleet, 200.0, DT)
    assert "u1" not in commands
    assert commands["u2"] == -10_000.0


def test_run_records_score_with_placeholder_ancillary():
    fleet = make_two_site_fleet()
    price = 200.0
    ancillary = 5.0
    commands = solve_dispatch(
        fleet,
        price,
        DT,
        ancillary_revenue_usd=ancillary,
    )
    records = run_fleet(
        fleet,
        DT,
        [
            FleetTickInput(
                {"i1": 0.0, "i2": 0.0},
                commands,
                fleet_target_power_watts=sum(commands.values()),
                price_usd_per_megawatt_hour=price,
                ancillary_revenue_usd=ancillary,
            )
        ],
    )

    record = records[0]
    assert record.score is not None
    assert record.score.ancillary_revenue_usd == pytest.approx(5.0)
    assert record.score.score_usd == pytest.approx(
        record.score.customer_bill_usd
        + record.score.wholesale_pnl_usd
        + 5.0
        - record.score.degradation_cost_usd
        - record.score.tracking_penalty_usd
    )
    assert record.fleet_actual_power_watts == pytest.approx(-30_000.0)
    assert record.fleet_tracking_error_watts == pytest.approx(0.0)


def test_customer_bills_do_not_net_across_houses():
    fleet = make_two_site_fleet()
    records = run_fleet(
        fleet,
        DT,
        [
            FleetTickInput(
                {"i1": 1_500.0, "i2": 1_500.0},
                {"u1": 2_000.0, "u2": -2_000.0, "u3": 0.0},
                price_usd_per_megawatt_hour=200.0,
            )
        ],
    )
    score = records[0].score
    assert score is not None
    idle_one_house = HOME_RATE_USD_PER_KILOWATT_HOUR * 1.5 * (DT / 3600.0)
    assert score.customer_bill_usd == pytest.approx(idle_one_house)
    assert score.no_battery_customer_bill_usd == pytest.approx(2 * idle_one_house)


def test_two_units_at_one_house_share_one_target():
    fleet = Fleet(
        [
            Installation(
                "i1",
                30.0,
                -97.0,
                T0,
                [make_unit("u1"), make_unit("u2")],
            ),
        ]
    )
    commands = solve_dispatch(
        fleet,
        200.0,
        DT,
        load_watts_by_install_id={"i1": 1_500.0},
    )
    assert commands["u1"] + commands["u2"] == pytest.approx(-20_000.0)


def test_solve_100_units_high_price():
    fleet = build_fleet(80, 100, T0, seed=1)
    commands = solve_dispatch(fleet, 200.0, DT)
    assert len(commands) == 100
    assert all(power == -10_000.0 for power in commands.values())
