from battery_fleet import BatteryUnit, Installation, TickInput, run
from battery_fleet.report import print_records

t0 = 1_700_000_000.0
unit = BatteryUnit("u1", "lot-a", 10.0, 10_000, 10_000, t0)
site = Installation("i1", 30.27, -97.74, t0, [unit])

records = run(
    site,
    900.0,
    [
        TickInput(1_500.0, {"u1": 2_000.0}),
        TickInput(1_500.0, {}),
        TickInput(1_500.0, {"u1": -3_000.0}),
    ],
)

print_records(records)
