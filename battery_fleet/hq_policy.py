from battery_fleet.types import HqPolicy, Unit


def hq_asked_kw(
    unit: Unit,
    policy: HqPolicy,
    spp: float,
    link_up: bool,
    islanded: bool,
) -> float | None:
    if not link_up or islanded:
        return None
    if spp >= policy.discharge_above:
        return unit.max_discharge_kw
    if spp <= policy.charge_below:
        return -unit.max_charge_kw
    return 0.0
