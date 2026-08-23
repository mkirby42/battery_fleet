from battery_fleet.clocks import TICK_S
from battery_fleet.physics import apply_setpoint


def test_discharge_reduces_energy():
    energy, power = apply_setpoint(
        energy_kwh=10.0, setpoint_kw=4.0, capacity_kwh=20.0,
        max_charge_kw=5.0, max_discharge_kw=5.0, floor_kwh=0.0,
        efficiency=1.0, dt_s=TICK_S,
    )
    assert power == 4.0
    assert energy == 10.0 - 4.0 * (15 / 3600)


def test_floor_blocks_market_discharge():
    energy, power = apply_setpoint(
        energy_kwh=2.0, setpoint_kw=10.0, capacity_kwh=10.0,
        max_charge_kw=5.0, max_discharge_kw=5.0, floor_kwh=2.0,
        efficiency=1.0, dt_s=TICK_S,
    )
    assert power == 0.0
    assert energy == 2.0


def test_charge_is_negative_power():
    energy, power = apply_setpoint(
        energy_kwh=1.0, setpoint_kw=-3.0, capacity_kwh=10.0,
        max_charge_kw=5.0, max_discharge_kw=5.0, floor_kwh=0.0,
        efficiency=1.0, dt_s=TICK_S,
    )
    assert power == -3.0
    assert energy == 1.0 + 3.0 * (15 / 3600)
