import pytest

from battery_fleet import BatteryUnit, Installation
from battery_fleet.control import split_target
from battery_fleet.fleet import Fleet, build_fleet
from battery_fleet.loop import FleetTickInput, run_fleet

T0 = 1_700_000_000.0


def make_unit(
    unit_id: str,
    initial_state_of_charge_fraction: float = 0.50,
) -> BatteryUnit:
    return BatteryUnit(
        unit_id,
        "lot-a",
        10.0,
        10_000.0,
        10_000.0,
        T0,
        initial_state_of_charge_fraction=initial_state_of_charge_fraction,
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


def test_split_target_even_across_reachable_units():
    fleet = make_two_site_fleet()
    commands = split_target(fleet, 6_000.0)

    assert commands == {
        "u1": 2_000.0,
        "u2": 2_000.0,
        "u3": 2_000.0,
    }


def test_split_target_skips_unreachable_units():
    fleet = make_two_site_fleet()
    fleet.installations[0].batteries[0].go_offline()
    commands = split_target(fleet, 4_000.0)

    assert commands == {"u2": 2_000.0, "u3": 2_000.0}


def test_split_target_none_reachable_is_empty():
    fleet = make_two_site_fleet()
    for site in fleet.installations:
        for battery in site.batteries:
            battery.go_offline()

    assert split_target(fleet, 6_000.0) == {}


def test_splitter_then_run_hits_target_when_units_can():
    fleet = make_two_site_fleet()
    target = 6_000.0
    records = run_fleet(
        fleet,
        900.0,
        [
            FleetTickInput(
                {"i1": 0.0, "i2": 0.0},
                split_target(fleet, target),
                fleet_target_power_watts=target,
            )
        ],
    )

    record = records[0]
    assert record.fleet_target_power_watts == pytest.approx(target)
    assert record.fleet_actual_power_watts == pytest.approx(target)
    assert record.fleet_commanded_power_watts == pytest.approx(target)
    assert record.fleet_tracking_error_watts == pytest.approx(0.0)


def test_tracking_error_when_packs_are_full():
    fleet = Fleet(
        [
            Installation(
                "i1",
                30.0,
                -97.0,
                T0,
                [
                    make_unit("u1", initial_state_of_charge_fraction=1.0),
                    make_unit("u2", initial_state_of_charge_fraction=1.0),
                ],
            )
        ]
    )
    target = 4_000.0
    records = run_fleet(
        fleet,
        900.0,
        [
            FleetTickInput(
                {"i1": 0.0},
                split_target(fleet, target),
                fleet_target_power_watts=target,
            )
        ],
    )

    record = records[0]
    assert record.fleet_commanded_power_watts == pytest.approx(4_000.0)
    assert record.fleet_actual_power_watts == pytest.approx(0.0)
    assert record.fleet_tracking_error_watts == pytest.approx(4_000.0)


def test_split_100_units_to_100kw():
    fleet = build_fleet(80, 100, T0, seed=1)
    commands = split_target(fleet, 100_000.0)

    assert len(commands) == 100
    assert all(share == 1_000.0 for share in commands.values())
