import json
from dataclasses import FrozenInstanceError

import pytest

from battery_fleet.comparison import ComparisonRuns, generate_comparison


def test_generate_comparison_writes_matched_normalized_runs(tmp_path):
    result = generate_comparison(
        runs_dir=tmp_path,
        n_sites=2,
        n_units=3,
        seed=7,
        comparison_id="matched-pair",
    )
    assert isinstance(result, ComparisonRuns)
    assert result.comparison_id == "matched-pair"
    with pytest.raises(FrozenInstanceError):
        result.comparison_id = "changed"

    greedy = _read_json(result.greedy_dir / "run.json")
    lookahead = _read_json(result.lookahead_dir / "run.json")

    comparison_id = greedy["comparison_id"]
    assert lookahead["comparison_id"] == comparison_id
    assert greedy["id"] == f"{comparison_id}-greedy"
    assert lookahead["id"] == f"{comparison_id}-lookahead"
    assert greedy["controller"] == "greedy"
    assert lookahead["controller"] == "lookahead"
    assert greedy["fleet_seed"] == lookahead["fleet_seed"] == 7
    assert greedy["dt_seconds"] == lookahead["dt_seconds"]
    assert greedy["started_at_unix"] == lookahead["started_at_unix"]

    assert _tick_values(greedy, "time_unix") == _tick_values(
        lookahead, "time_unix"
    )
    assert _tick_values(greedy, "price_usd_per_mwh") == _tick_values(
        lookahead, "price_usd_per_mwh"
    )
    assert _tick_values(greedy, "load_w") == _tick_values(
        lookahead, "load_w"
    )
    greedy_outages = _tick_values(greedy, "n_unreachable")
    assert greedy_outages == _tick_values(lookahead, "n_unreachable")
    assert max(greedy_outages) == 3
    assert greedy["sites"] == lookahead["sites"]
    assert greedy["units"] == lookahead["units"]

    greedy_installations = _read_jsonl(
        result.greedy_dir / "installation_ticks.jsonl"
    )
    lookahead_installations = _read_jsonl(
        result.lookahead_dir / "installation_ticks.jsonl"
    )
    assert _installation_inputs(greedy_installations) == _installation_inputs(
        lookahead_installations
    )
    greedy_units = _read_jsonl(result.greedy_dir / "unit_ticks.jsonl")
    lookahead_units = _read_jsonl(result.lookahead_dir / "unit_ticks.jsonl")
    assert _unit_reachability(greedy_units) == _unit_reachability(
        lookahead_units
    )

    expected_files = {
        "run.json",
        "installation_ticks.jsonl",
        "unit_ticks.jsonl",
    }
    assert {path.name for path in result.greedy_dir.iterdir()} == expected_files
    assert {
        path.name for path in result.lookahead_dir.iterdir()
    } == expected_files


def test_unit_reachability_comparison_detects_installation_mutation():
    first = {
        "tick_index": 0,
        "install_id": "i001",
        "unit_id": "u001",
        "reachable": True,
    }
    moved = {**first, "install_id": "i002"}

    assert _unit_reachability([first]) != _unit_reachability([moved])


def _tick_values(summary, key):
    return [tick[key] for tick in summary["ticks"]]


def _read_json(path):
    return json.loads(path.read_text())


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def _installation_inputs(rows):
    return [
        (row["tick_index"], row["install_id"], row["load_w"])
        for row in rows
    ]


def _unit_reachability(rows):
    return [
        (
            row["tick_index"],
            row["install_id"],
            row["unit_id"],
            row["reachable"],
        )
        for row in rows
    ]
