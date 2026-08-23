from pathlib import Path
from battery_fleet.scenario import load_scenario


def test_demo_scenarios_load():
    for name in ("fixed_20.yaml", "aggressive.yaml"):
        w = load_scenario(Path("scenarios") / name)
        assert len(w.locations) == 60
        assert any(s.id == "s0" for s in w.substations)
