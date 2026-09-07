from concurrent.futures import ThreadPoolExecutor
import json
import re

import pytest

from battery_fleet import comparison
from battery_fleet.comparison import (
    ComparisonRuns,
    generate_comparison,
    list_completed_comparisons,
)


def test_repeated_default_generation_uses_unique_utc_ids(tmp_path):
    first = _generate(tmp_path)
    second = _generate(tmp_path)

    pattern = r"\d{8}T\d{6}\.\d{6}Z-[0-9a-f]+"
    assert re.fullmatch(pattern, first.comparison_id)
    assert re.fullmatch(pattern, second.comparison_id)
    assert first.comparison_id != second.comparison_id
    assert set(list_completed_comparisons(tmp_path)) == {first, second}


def test_concurrent_default_generation_does_not_collide(tmp_path):
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _value: _generate(tmp_path), range(4)))

    assert len({result.comparison_id for result in results}) == 4
    assert set(list_completed_comparisons(tmp_path)) == set(results)


def test_caller_supplied_id_collision_preserves_completed_pair(tmp_path):
    original = _generate(tmp_path, comparison_id="fixed-id")

    with pytest.raises(FileExistsError):
        _generate(tmp_path, comparison_id="fixed-id")

    assert list_completed_comparisons(tmp_path) == [original]
    assert original.greedy_dir.is_dir()
    assert original.lookahead_dir.is_dir()


@pytest.mark.parametrize("comparison_id", ["", "../escape", "nested/id"])
def test_caller_supplied_id_must_be_a_safe_file_name(
    tmp_path,
    comparison_id,
):
    with pytest.raises(ValueError, match="file name"):
        _generate(tmp_path, comparison_id=comparison_id)

    assert list_completed_comparisons(tmp_path) == []


def test_second_run_failure_removes_first_and_publishes_no_manifest(
    tmp_path,
    monkeypatch,
):
    original_write = comparison.write_run
    calls = 0

    def fail_second_write(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected second write failure")
        return original_write(*args, **kwargs)

    monkeypatch.setattr(comparison, "write_run", fail_second_write)

    with pytest.raises(OSError, match="injected second write failure"):
        _generate(tmp_path, comparison_id="second-fails")

    _assert_no_pair(tmp_path, "second-fails")


def test_manifest_failure_removes_both_runs(
    tmp_path,
    monkeypatch,
):
    def fail_manifest(*_args, **_kwargs):
        raise OSError("injected manifest failure")

    monkeypatch.setattr(comparison, "_publish_manifest", fail_manifest)

    with pytest.raises(OSError, match="injected manifest failure"):
        _generate(tmp_path, comparison_id="manifest-fails")

    _assert_no_pair(tmp_path, "manifest-fails")


def test_completed_discovery_ignores_orphans_and_incomplete_manifests(
    tmp_path,
):
    completed = _generate(tmp_path, comparison_id="complete")
    (tmp_path / "orphan-greedy").mkdir()
    manifests = tmp_path / "comparisons"
    (manifests / "incomplete.json").write_text(
        json.dumps(
            {
                "comparison_id": "incomplete",
                "greedy_dir": "missing-greedy",
                "lookahead_dir": "missing-lookahead",
            }
        )
    )
    (manifests / "invalid.json").write_text("{")

    assert list_completed_comparisons(tmp_path) == [completed]
    assert json.loads((manifests / "complete.json").read_text()) == {
        "comparison_id": "complete",
        "greedy_dir": "complete-greedy",
        "lookahead_dir": "complete-lookahead",
    }


def _generate(tmp_path, comparison_id=None):
    return generate_comparison(
        runs_dir=tmp_path,
        n_sites=2,
        n_units=3,
        seed=1,
        comparison_id=comparison_id,
    )


def _assert_no_pair(tmp_path, comparison_id):
    assert not (tmp_path / f"{comparison_id}-greedy").exists()
    assert not (tmp_path / f"{comparison_id}-lookahead").exists()
    assert not (tmp_path / "comparisons" / f"{comparison_id}.json").exists()
    assert list_completed_comparisons(tmp_path) == []
