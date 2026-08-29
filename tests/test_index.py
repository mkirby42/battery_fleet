import sqlite3
from pathlib import Path

from battery_fleet.index import default_runs_dir, load_index, rebuild_index


def test_default_runs_dir_is_repo_runs():
    d = default_runs_dir()
    assert d.is_absolute()
    assert d.name == "runs"
    assert (d.parent / "battery_fleet").is_dir()


def test_load_index_missing_dir_returns_empty(tmp_path: Path):
    missing = tmp_path / "nope"
    assert load_index(missing) == []


def test_rebuild_index_includes_local_policy_kind(tmp_path: Path):
    run_dir = tmp_path / "r1"
    run_dir.mkdir()
    con = sqlite3.connect(run_dir / "run.db")
    con.executescript(
        """
        CREATE TABLE local_policy (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            floor_frac REAL NOT NULL
        );
        CREATE TABLE run (
            id TEXT PRIMARY KEY,
            seed INTEGER,
            schema_version INTEGER,
            status TEXT,
            error TEXT,
            local_policy_id TEXT,
            hq_policy_id TEXT,
            market_event_id TEXT
        );
        INSERT INTO local_policy VALUES ('lp', 'aggressive', 0.0);
        INSERT INTO run VALUES ('r1', 1, 1, 'success', NULL, 'lp', 'hq', 'me');
        """
    )
    con.close()
    entries = rebuild_index(tmp_path)
    assert entries[0]["local_policy_kind"] == "aggressive"
    assert load_index(tmp_path)[0]["local_policy_kind"] == "aggressive"
