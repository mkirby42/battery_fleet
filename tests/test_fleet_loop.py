import pytest

from battery_fleet import BatteryUnit, Installation
from battery_fleet.fleet import Fleet, build_fleet
from battery_fleet.loop import FleetTickInput, run_fleet

T0 = 1_700_000_000.0


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
    a = Installation("i1", 30.0, -97.0, T0, [make_unit("u1")])
    b = Installation(
        "i2",
        31.0,
        -98.0,
        T0,
        [make_unit("u2"), make_unit("u3")],
    )
    return Fleet([a, b])


def test_run_fleet_sums_actual_and_keeps_site_rows():
    fleet = make_two_site_fleet()
    records = run_fleet(
        fleet,
        900.0,
        [
            FleetTickInput(
                {"i1": 1_000.0, "i2": 2_000.0},
                {"u1": 2_000.0, "u2": 2_000.0, "u3": 2_000.0},
            )
        ],
    )

    record = records[0]
    assert record.time_unix == T0 + 900.0
    assert record.fleet_actual_power_watts == pytest.approx(6_000.0)
    assert record.fleet_commanded_power_watts == pytest.approx(6_000.0)
    assert record.fleet_load_power_watts == pytest.approx(3_000.0)
    assert record.n_units == 3
    assert record.n_unreachable == 0
    assert [site.install_id for site in record.site_records] == ["i1", "i2"]
    assert record.site_records[0].actual_power_watts_by_unit_id["u1"] == (
        pytest.approx(2_000.0)
    )


def test_run_fleet_holds_last_command_when_tick_omits_it():
    fleet = make_two_site_fleet()
    records = run_fleet(
        fleet,
        900.0,
        [
            FleetTickInput({"i1": 0.0, "i2": 0.0}, {"u1": 3_000.0}),
            FleetTickInput({}, {}),
        ],
    )

    assert records[1].site_records[0].actual_power_watts_by_unit_id[
        "u1"
    ] == pytest.approx(3_000.0)


def test_run_fleet_counts_unreachable_and_keeps_last_command():
    fleet = make_two_site_fleet()
    fleet.installations[0].batteries[0].command_power_watts(2_000.0)
    fleet.installations[0].batteries[0].go_offline()

    records = run_fleet(
        fleet,
        900.0,
        [
            FleetTickInput(
                {"i1": 0.0},
                {"u1": -8_000.0},
            )
        ],
    )

    assert records[0].n_unreachable == 1
    assert records[0].site_records[0].commanded_power_watts_by_unit_id[
        "u1"
    ] == pytest.approx(2_000.0)
    assert records[0].site_records[0].network_reachable_by_unit_id["u1"] is False


def test_run_fleet_unknown_ids_raise():
    fleet = make_two_site_fleet()

    with pytest.raises(ValueError, match="Unknown install_id"):
        run_fleet(
            fleet,
            900.0,
            [FleetTickInput({"missing": 1.0}, {})],
        )

    with pytest.raises(ValueError, match="Unknown unit_id"):
        run_fleet(
            fleet,
            900.0,
            [FleetTickInput({}, {"missing": 1.0})],
        )


def test_run_fleet_80_by_100_charges_together():
    fleet = build_fleet(80, 100, T0, seed=1)
    unit_ids = [
        battery.unit_id
        for site in fleet.installations
        for battery in site.batteries
    ]
    loads = {
        site.install_id: 1_500.0
        for site in fleet.installations
    }
    commands = {unit_id: 2_000.0 for unit_id in unit_ids}

    records = run_fleet(
        fleet,
        900.0,
        [FleetTickInput(loads, commands)],
    )

    assert records[0].n_units == 100
    assert records[0].fleet_actual_power_watts == pytest.approx(200_000.0)
    assert records[0].fleet_load_power_watts == pytest.approx(120_000.0)
    assert len(records[0].site_records) == 80


def test_fleet_score_sums_mixed_sign_unit_wear_and_tracking():
    fleet = Fleet(
        [
            Installation(
                "i1",
                30.0,
                -97.0,
                T0,
                [make_unit("u1"), make_unit("u2")],
            )
        ]
    )
    record = run_fleet(
        fleet,
        900.0,
        [
            FleetTickInput(
                {"i1": 1_500.0},
                {"u1": 20_000.0, "u2": -20_000.0},
                price_usd_per_megawatt_hour=200.0,
            )
        ],
    )[0]

    assert record.score.degradation_cost_usd == pytest.approx(0.25)
    assert record.score.tracking_penalty_usd == pytest.approx(1.0)
    assert record.score.score_usd == pytest.approx(
        record.score.customer_bill_usd
        + record.score.wholesale_pnl_usd
        - record.score.degradation_cost_usd
        - record.score.tracking_penalty_usd
    )
