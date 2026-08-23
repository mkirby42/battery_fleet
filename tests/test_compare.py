from pathlib import Path

from battery_fleet.cli import run_scenario
from battery_fleet.compare import Incomparable, compare_runs


def test_same_seed_tinies_are_comparable(tmp_path: Path):
    d1 = run_scenario(Path("scenarios/tiny.yaml"), runs_dir=tmp_path)
    d2 = run_scenario(Path("scenarios/tiny.yaml"), runs_dir=tmp_path)
    table = compare_runs(d1, d2)
    assert "revenue_usd" in table["a"]
    assert "revenue_usd" in table["b"]


def test_incomparable_seed(tmp_path: Path):
    p = tmp_path / "other.yaml"
    text = Path("scenarios/tiny.yaml").read_text().replace("seed: 1", "seed: 2")
    p.write_text(text)
    d1 = run_scenario(Path("scenarios/tiny.yaml"), runs_dir=tmp_path / "r")
    d2 = run_scenario(p, runs_dir=tmp_path / "r")
    try:
        compare_runs(d1, d2)
    except Incomparable:
        return
    raise AssertionError("expected Incomparable")
