from battery_fleet.types import LocalPolicy, Unit


def floor_kwh(unit: Unit, policy: LocalPolicy) -> float:
    return unit.capacity_kwh * policy.floor_frac


def local_setpoint(
    islanded: bool,
    location_load_kw: float,
    hq_asked_kw: float | None,
) -> float | None:
    if islanded:
        return location_load_kw
    return None
