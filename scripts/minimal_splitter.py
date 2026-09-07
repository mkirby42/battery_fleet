from battery_fleet import (
    FleetTickInput,
    build_fleet,
    print_fleet_records,
    run_fleet,
)
from battery_fleet.control import split_target

t0 = 1_700_000_000.0
fleet = build_fleet(80, 100, t0, 1)
loads = {
    site.install_id: 1_500.0
    for site in fleet.installations
}

records = []
for target in (100_000.0, 100_000.0, -150_000.0):
    records.extend(
        run_fleet(
            fleet,
            900.0,
            [
                FleetTickInput(
                    loads,
                    split_target(fleet, target),
                    fleet_target_power_watts=target,
                )
            ],
        )
    )

print_fleet_records(records)
