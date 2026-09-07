import pytest

from battery_fleet import BatteryUnit, Installation
from battery_fleet.loop import TickInput, run

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


def make_site(unit: BatteryUnit) -> Installation:
    return Installation("i1", 30.27, -97.74, T0, [unit])


def test_loop_advances_time_once_per_tick():
    unit = make_unit()
    site = make_site(unit)
    records = run(
        site,
        900.0,
        [
            TickInput(0.0, {}),
            TickInput(0.0, {}),
        ],
    )

    assert [record.time_unix for record in records] == [
        T0 + 900.0,
        T0 + 1800.0,
    ]
    assert site.state.time_unix == T0 + 1800.0
    assert unit.state.time_unix == T0 + 1800.0


def test_loop_grid_is_load_plus_battery():
    unit = make_unit()
    site = make_site(unit)
    records = run(
        site,
        900.0,
        [TickInput(1_500.0, {"u1": 2_000.0})],
    )

    assert records[0].grid_power_watts == pytest.approx(
        1_500.0 + records[0].actual_power_watts_by_unit_id["u1"]
    )
    assert records[0].actual_power_watts_by_unit_id["u1"] == pytest.approx(2_000.0)
    assert records[0].install_id == "i1"
    assert records[0].commanded_power_watts_by_unit_id["u1"] == pytest.approx(
        2_000.0
    )
    assert records[0].network_reachable_by_unit_id["u1"] is True


def test_loop_holds_last_command_when_tick_omits_it():
    unit = make_unit()
    site = make_site(unit)
    records = run(
        site,
        900.0,
        [
            TickInput(0.0, {"u1": 3_000.0}),
            TickInput(0.0, {}),
        ],
    )

    assert records[1].actual_power_watts_by_unit_id["u1"] == pytest.approx(3_000.0)


def test_loop_unknown_unit_id_raises():
    unit = make_unit()
    site = make_site(unit)

    with pytest.raises(ValueError, match="Unknown unit_id"):
        run(site, 900.0, [TickInput(0.0, {"missing": 1_000.0})])
