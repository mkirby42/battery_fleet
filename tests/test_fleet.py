import pytest

from battery_fleet.fleet import build_fleet

T0 = 1_700_000_000.0


def test_build_fleet_100_units_across_80_sites():
    fleet = build_fleet(
        n_sites=80,
        n_units=100,
        initial_time_unix=T0,
        seed=1,
    )

    assert len(fleet.installations) == 80
    sizes = [len(site.batteries) for site in fleet.installations]
    assert sum(sizes) == 100
    assert sizes.count(1) == 60
    assert sizes.count(2) == 20


def test_build_fleet_units_are_identical_10_kwh():
    fleet = build_fleet(2, 3, T0, seed=1)
    units = [
        battery
        for site in fleet.installations
        for battery in site.batteries
    ]

    assert len(units) == 3
    for unit in units:
        assert unit.nominal_capacity_kilowatt_hours == 10.0
        assert unit.nominal_max_charge_power_watts == 10_000.0
        assert unit.nominal_max_discharge_power_watts == 10_000.0
        assert unit.state.time_unix == T0


def test_build_fleet_places_sites_in_austin():
    fleet = build_fleet(80, 80, T0, seed=1)
    lats = [site.latitude_degrees for site in fleet.installations]
    lons = [site.longitude_degrees for site in fleet.installations]
    for site in fleet.installations:
        assert 30.19 <= site.latitude_degrees <= 30.41
        assert -97.88 <= site.longitude_degrees <= -97.66
    assert max(lats) - min(lats) > 0.10
    assert max(lons) - min(lons) > 0.10


def test_build_fleet_sites_are_separated():
    fleet = build_fleet(80, 80, T0, seed=1)
    coords = [
        (site.latitude_degrees, site.longitude_degrees)
        for site in fleet.installations
    ]
    gaps = [
        ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
        for i, a in enumerate(coords)
        for b in coords[i + 1 :]
    ]
    assert gaps
    assert min(gaps) >= 0.003


def test_build_fleet_same_seed_same_placement():
    a = build_fleet(80, 100, T0, seed=1)
    b = build_fleet(80, 100, T0, seed=1)

    assert [
        (site.install_id, site.latitude_degrees, site.longitude_degrees)
        for site in a.installations
    ] == [
        (site.install_id, site.latitude_degrees, site.longitude_degrees)
        for site in b.installations
    ]
    assert [
        [battery.unit_id for battery in site.batteries]
        for site in a.installations
    ] == [
        [battery.unit_id for battery in site.batteries]
        for site in b.installations
    ]


def test_build_fleet_ids_are_unique():
    fleet = build_fleet(80, 100, T0, seed=1)
    install_ids = [site.install_id for site in fleet.installations]
    unit_ids = [
        battery.unit_id
        for site in fleet.installations
        for battery in site.batteries
    ]

    assert len(install_ids) == len(set(install_ids))
    assert len(unit_ids) == len(set(unit_ids))


def test_build_fleet_rejects_fewer_units_than_sites():
    with pytest.raises(ValueError, match="at least one unit per site"):
        build_fleet(80, 79, T0, seed=1)
