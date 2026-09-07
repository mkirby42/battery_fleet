from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
from threading import Barrier

import pytest

from battery_fleet import store
from battery_fleet.store import write_run
from store_support import DT, make_records, make_two_site_fleet

NORMALIZED = {
    "comparison_id": "comparison-1",
    "controller": "greedy",
    "fleet_seed": 1,
}


def test_legacy_failure_leaves_no_run_and_retry_succeeds(
    tmp_path,
    monkeypatch,
):
    fleet = make_two_site_fleet()
    records = make_records(fleet)
    original_write = store._atomic_write_text

    def fail_write(_path, _text):
        raise OSError("injected write failure")

    monkeypatch.setattr(store, "_atomic_write_text", fail_write)
    with pytest.raises(OSError, match="injected write failure"):
        write_run("legacy", fleet, records, DT, runs_dir=tmp_path)

    assert not (tmp_path / "legacy").exists()
    monkeypatch.setattr(store, "_atomic_write_text", original_write)
    path = write_run("legacy", fleet, records, DT, runs_dir=tmp_path)
    assert path.is_file()


def test_normalized_failure_never_publishes_partial_run(
    tmp_path,
    monkeypatch,
):
    fleet = make_two_site_fleet()
    records = make_records(fleet, price=200.0)
    writes = 0

    def fail_second_detail_write(_path, _rows):
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError("injected write failure")

    monkeypatch.setattr(
        store,
        "_atomic_write_jsonl",
        fail_second_detail_write,
    )
    with pytest.raises(OSError, match="injected write failure"):
        write_run(
            "normalized",
            fleet,
            records,
            DT,
            runs_dir=tmp_path,
            **NORMALIZED,
        )

    assert not (tmp_path / "normalized").exists()
    assert not any(
        path.is_dir() and path.name.startswith(".normalized.")
        for path in tmp_path.iterdir()
    )


@pytest.mark.parametrize("normalized", [False, True])
def test_write_rejects_existing_empty_destination(tmp_path, normalized):
    (tmp_path / "existing").mkdir()
    fleet = make_two_site_fleet()
    records = make_records(fleet, price=200.0 if normalized else None)
    metadata = NORMALIZED if normalized else {}

    with pytest.raises(FileExistsError, match="already exists"):
        write_run(
            "existing",
            fleet,
            records,
            DT,
            runs_dir=tmp_path,
            **metadata,
        )

    assert list((tmp_path / "existing").iterdir()) == []


def test_normalized_write_preserves_existing_directory(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    marker = existing / "keep.txt"
    marker.write_text("original")
    fleet = make_two_site_fleet()

    with pytest.raises(FileExistsError, match="already exists"):
        write_run(
            "existing",
            fleet,
            make_records(fleet, price=200.0),
            DT,
            runs_dir=tmp_path,
            **NORMALIZED,
        )

    assert marker.read_text() == "original"
    assert [path.name for path in existing.iterdir()] == ["keep.txt"]


def test_concurrent_legacy_writers_publish_exactly_once(tmp_path):
    fleet = make_two_site_fleet()
    records = make_records(fleet)
    results = _concurrent_results(
        lambda value: write_run(
            "shared",
            fleet,
            records,
            value,
            runs_dir=tmp_path,
        ),
        (DT, DT * 2),
    )

    successes = [result for result in results if result[0] == "success"]
    assert len(successes) == 1
    assert json.loads(
        (tmp_path / "shared" / "run.json").read_text()
    )["dt_seconds"] == successes[0][1]


def test_concurrent_normalized_writers_do_not_mix_output(tmp_path):
    fleet = make_two_site_fleet()
    records = make_records(fleet, price=200.0)
    results = _concurrent_results(
        lambda controller: write_run(
            "shared",
            fleet,
            records,
            DT,
            runs_dir=tmp_path,
            comparison_id=f"comparison-{controller}",
            controller=controller,
            fleet_seed=1,
        ),
        ("greedy", "lookahead"),
    )

    successes = [result for result in results if result[0] == "success"]
    assert len(successes) == 1
    winner = successes[0][1]
    run_dir = tmp_path / "shared"
    summary = json.loads((run_dir / "run.json").read_text())
    installation_rows = _read_jsonl(run_dir / "installation_ticks.jsonl")
    unit_rows = _read_jsonl(run_dir / "unit_ticks.jsonl")
    assert summary["controller"] == winner
    assert {row["controller"] for row in installation_rows} == {winner}
    assert {row["controller"] for row in unit_rows} == {winner}


def test_process_exit_releases_advisory_lock(tmp_path):
    run_dir = tmp_path / "run"
    code = """
import os
from pathlib import Path
import sys
from battery_fleet.store import _exclusive_run_lock
with _exclusive_run_lock(Path(sys.argv[1])):
    os._exit(0)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(run_dir)],
        cwd=Path(__file__).parent.parent,
        check=False,
    )
    assert result.returncode == 0

    with store._exclusive_run_lock(run_dir):
        pass
    assert (tmp_path / ".run.lock").exists()


def _concurrent_results(operation, values):
    barrier = Barrier(2)

    def attempt(value):
        barrier.wait()
        try:
            operation(value)
            return ("success", value)
        except FileExistsError:
            return ("exists", value)

    with ThreadPoolExecutor(max_workers=2) as executor:
        return list(executor.map(attempt, values))


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]
