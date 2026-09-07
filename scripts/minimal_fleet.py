from battery_fleet import build_fleet

fleet = build_fleet(80, 100, 1_700_000_000.0, 1)

print(len(fleet.installations), "sites")
print(
    sum(len(site.batteries) for site in fleet.installations),
    "units",
)

for site in fleet.installations:
    unit_ids = " ".join(
        battery.unit_id for battery in site.batteries
    )
    print(
        site.install_id,
        f"{site.latitude_degrees:.3f}",
        f"{site.longitude_degrees:.3f}",
        unit_ids,
    )
