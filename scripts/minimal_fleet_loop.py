from battery_fleet import (
    FleetTickInput,
    build_fleet,
    print_fleet_records,
    run_fleet,
)

t0 = 1_700_000_000.0
fleet = build_fleet(80, 100, t0, 1)

loads = {
    site.install_id: 1_500.0
    for site in fleet.installations
}
unit_ids = [
    battery.unit_id
    for site in fleet.installations
    for battery in site.batteries
]

records = run_fleet(
    fleet,
    900.0,
    [
        FleetTickInput(loads, {unit_id: 2_000.0 for unit_id in unit_ids}),
        FleetTickInput(loads, {}),
        FleetTickInput(loads, {unit_id: -3_000.0 for unit_id in unit_ids}),
    ],
)

print_fleet_records(records)
