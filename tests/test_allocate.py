import pytest

from battery_fleet import BatteryUnit, Installation
from battery_fleet.control import allocate_target
from battery_fleet.fleet import Fleet, build_fleet
from battery_fleet.loop import FleetTickInput, run_fleet

T0 = 1_700_000_000.0
DT = 900.0


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


def make_fleet(*units: BatteryUnit) -> Fleet:
    return Fleet(
        [Installation("i1", 30.0, -97.0, T0, list(units))]
    )


def test_allocate_even_when_all_units_have_room():
    fleet = make_fleet(make_unit("u1"), make_unit("u2"), make_unit("u3"))
    commands = allocate_target(fleet, 6_000.0, DT)
    assert commands == {"u1": 2_000.0, "u2": 2_000.0, "u3": 2_000.0}


def test_allocate_skips_full_pack_and_gives_the_rest_to_others():
    fleet = make_fleet(
        make_unit("full", initial_state_of_charge_fraction=1.0),
        make_unit("ok"),
    )
    commands = allocate_target(fleet, 4_000.0, DT)
    assert commands["full"] == pytest.approx(0.0)
    assert commands["ok"] == pytest.approx(4_000.0)


def test_allocate_clips_to_total_headroom():
    fleet = make_fleet(make_unit("u1"), make_unit("u2"))
    commands = allocate_target(fleet, 1_000_000.0, DT)
    assert commands["u1"] == pytest.approx(10_000.0)
    assert commands["u2"] == pytest.approx(10_000.0)


def test_allocate_discharge_respects_reserve():
    fleet = make_fleet(
        make_unit("low", initial_state_of_charge_fraction=0.25),
        make_unit("low2", initial_state_of_charge_fraction=0.25),
    )
    commands = allocate_target(fleet, -5_000.0, DT)
    # 0.05 SOC * 10 kWh * 0.95 / 0.25 h * 1000 = 1900 W each
    assert commands["low"] == pytest.approx(-1_900.0)
    assert commands["low2"] == pytest.approx(-1_900.0)


def test_allocate_skips_unreachable():
    fleet = make_fleet(make_unit("u1"), make_unit("u2"))
    fleet.installations[0].batteries[0].go_offline()
    commands = allocate_target(fleet, 4_000.0, DT)
    assert "u1" not in commands
    assert commands["u2"] == pytest.approx(4_000.0)


def test_allocate_then_run_actual_matches_command():
    fleet = make_fleet(
        make_unit("full", initial_state_of_charge_fraction=1.0),
        make_unit("ok"),
    )
    target = 4_000.0
    commands = allocate_target(fleet, target, DT)
    records = run_fleet(
        fleet,
        DT,
        [
            FleetTickInput(
                {"i1": 0.0},
                commands,
                fleet_target_power_watts=target,
            )
        ],
    )
    record = records[0]
    assert record.fleet_commanded_power_watts == pytest.approx(4_000.0)
    assert record.fleet_actual_power_watts == pytest.approx(4_000.0)
    assert record.fleet_tracking_error_watts == pytest.approx(0.0)


def test_allocate_100_units_clips_at_one_megawatt():
    fleet = build_fleet(80, 100, T0, seed=1)
    commands = allocate_target(fleet, 2_000_000.0, DT)
    assert sum(commands.values()) == pytest.approx(1_000_000.0)
    assert all(power == 10_000.0 for power in commands.values())
