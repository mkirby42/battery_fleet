from battery_fleet import (
    FleetTickInput,
    build_fleet,
    print_fleet_records,
    run_fleet,
)
from battery_fleet.control import solve_dispatch

t0 = 1_700_000_000.0
dt = 900.0
fleet = build_fleet(80, 100, t0, 1)
loads = {
    site.install_id: 1_500.0
    for site in fleet.installations
}
ancillary_revenue_usd = 5.0

records = []
for price in (-80.0, 20.0, 200.0):
    commands = solve_dispatch(
        fleet,
        price,
        dt,
        ancillary_revenue_usd=ancillary_revenue_usd,
    )
    records.extend(
        run_fleet(
            fleet,
            dt,
            [
                FleetTickInput(
                    loads,
                    commands,
                    fleet_target_power_watts=sum(commands.values()),
                    price_usd_per_megawatt_hour=price,
                    ancillary_revenue_usd=ancillary_revenue_usd,
                )
            ],
        )
    )

print_fleet_records(records)
