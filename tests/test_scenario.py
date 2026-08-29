from pathlib import Path

from battery_fleet.scenario import load_scenario

TINY = Path(__file__).resolve().parents[1] / "scenarios" / "tiny.yaml"


def test_tiny_has_three_locations_and_units():
    world = load_scenario(TINY)
    assert len(world.locations) == 3
    assert len(world.units) == 3
    assert len(world.installs) == 3
    assert world.local_policy.kind == "fixed_reserve"
    assert world.duration_s == 3600
    assert world.seed == 1


def test_tiny_locations_are_a_cluster_not_a_line():
    world = load_scenario(TINY)
    locs = world.locations
    for loc in locs:
        assert 30.13 <= loc.lat <= 30.50
        assert -97.90 <= loc.lon <= -97.52
    lats = [loc.lat for loc in locs]
    lons = [loc.lon for loc in locs]
    assert max(lats) - min(lats) < 0.15
    assert max(lons) - min(lons) < 0.15
    a, b, c = locs
    area = (
        a.lat * (b.lon - c.lon)
        + b.lat * (c.lon - a.lon)
        + c.lat * (a.lon - b.lon)
    )
    assert abs(area) > 1e-9


def test_tiny_defaults_start_soc_frac_to_half():
    world = load_scenario(TINY)
    assert world.start_soc_frac == 0.5
