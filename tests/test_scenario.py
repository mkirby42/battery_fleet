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
