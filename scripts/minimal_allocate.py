from battery_fleet import (
    FleetTickInput,
    build_fleet,
    print_fleet_records,
    run_fleet,
)
from battery_fleet.control import allocate_target

t0 = 1_700_000_000.0
dt = 900.0
fleet = build_fleet(80, 100, t0, 1)
loads = {
    site.install_id: 1_500.0
    for site in fleet.installations
}

records = []
for target in (100_000.0, 2_000_000.0, -150_000.0):
    commands = allocate_target(fleet, target, dt)
    records.extend(
        run_fleet(
            fleet,
            dt,
            [
                FleetTickInput(
                    loads,
                    commands,
                    fleet_target_power_watts=target,
                )
            ],
        )
    )

print_fleet_records(records)
