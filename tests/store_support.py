from battery_fleet import BatteryUnit, Installation
from battery_fleet.fleet import Fleet
from battery_fleet.loop import FleetTickInput, FleetTickRecord, run_fleet

T0 = 1_700_000_000.0
DT = 900.0
CHARGE = 2_000.0
LOAD = 1_500.0
COMMANDS = {"u1": CHARGE, "u2": CHARGE, "u3": CHARGE}
LOADS = {"i1": LOAD, "i2": LOAD}


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


def make_records(
    fleet: Fleet,
    *,
    price: float | None = None,
    ancillary: float = 0.0,
    ticks: int = 1,
) -> list[FleetTickRecord]:
    tick = FleetTickInput(
        LOADS,
        COMMANDS,
        price_usd_per_megawatt_hour=price,
        ancillary_revenue_usd=ancillary,
    )
    return run_fleet(fleet, DT, [tick] * ticks)
