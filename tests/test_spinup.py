from pathlib import Path

from battery_fleet.cli import run_scenario
from battery_fleet.index import load_index


def test_tiny_run_is_success_and_indexed(tmp_path: Path):
    scenario = Path("scenarios/tiny.yaml")
    run_dir = run_scenario(scenario, runs_dir=tmp_path)
    assert (run_dir / "run.db").exists()
    idx = load_index(tmp_path)
    assert len(idx) == 1
    assert idx[0]["status"] == "success"
    assert idx[0]["id"] == run_dir.name


def test_bad_yaml_does_not_create_folder(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("seed: 1\n")
    try:
        run_scenario(bad, runs_dir=tmp_path / "runs")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
    runs = tmp_path / "runs"
    if runs.exists():
        assert list(runs.glob("*/run.db")) == []
