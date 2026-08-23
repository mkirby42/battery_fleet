from pathlib import Path

from battery_fleet.cli import run_scenario
from battery_fleet.serve import run_payload, runs_payload


def test_api_lists_and_loads_a_success(tmp_path: Path):
    run_dir = run_scenario(Path("scenarios/tiny.yaml"), runs_dir=tmp_path)
    listing = runs_payload(tmp_path)
    assert listing[0]["status"] == "success"
    body = run_payload(tmp_path, run_dir.name)
    assert "locations" in body
    assert "ticks" in body
    assert "prices" in body
    assert "scoreboard" in body
