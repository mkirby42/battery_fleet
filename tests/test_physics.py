import pytest

from battery_fleet import BatteryUnit, Installation

T0 = 1_700_000_000.0


def make_unit(**overrides) -> BatteryUnit:
    values = dict(
        unit_id="u1",
        manufacture_lot_id="lot-a",
        nominal_capacity_kilowatt_hours=10.0,
        nominal_max_charge_power_watts=10_000.0,
        nominal_max_discharge_power_watts=10_000.0,
        initial_time_unix=T0,
    )
    values.update(overrides)
    return BatteryUnit(**values)


def test_charge_stops_when_full():
    unit = make_unit(initial_state_of_charge_fraction=0.90)
    unit.command_power_watts(10_000.0)

    unit.step(3600.0)
    assert unit.state.state_of_charge_fraction == pytest.approx(1.0)

    unit.step(3600.0)
    assert unit.state.state_of_charge_fraction == pytest.approx(1.0)
    assert unit.state.actual_power_watts == pytest.approx(0.0)


def test_discharge_stops_at_reserve():
    unit = make_unit(
        initial_state_of_charge_fraction=0.30,
        reserve_state_of_charge_fraction=0.20,
    )
    unit.command_power_watts(-10_000.0)

    unit.step(3600.0)
    assert unit.state.state_of_charge_fraction == pytest.approx(0.20)

    unit.step(3600.0)
    assert unit.state.state_of_charge_fraction == pytest.approx(0.20)
    assert unit.state.actual_power_watts == pytest.approx(0.0)


def test_offline_ignores_new_command_keeps_last():
    unit = make_unit()
    unit.command_power_watts(3_000.0)
    unit.go_offline()
    unit.command_power_watts(-8_000.0)

    assert unit.state.commanded_power_watts == pytest.approx(3_000.0)

    unit.step(900.0)
    assert unit.state.actual_power_watts == pytest.approx(3_000.0)


def test_grid_power_is_load_plus_battery():
    unit = make_unit()
    unit.command_power_watts(2_000.0)
    site = Installation("i1", 30.27, -97.74, T0, [unit])
    site.set_user_load_power_watts(1_500.0)

    site.step(900.0)

    assert site.state.grid_power_watts == pytest.approx(
        1_500.0 + unit.state.actual_power_watts
    )
