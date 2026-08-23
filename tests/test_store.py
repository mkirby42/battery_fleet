import sqlite3
from pathlib import Path

from battery_fleet.store import create_run_db


def test_create_run_db_has_run_table(tmp_path: Path):
    path = tmp_path / "run.db"
    create_run_db(path)
    con = sqlite3.connect(path)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()
    for needed in (
        "regions", "cities", "substations", "locations", "units", "installs",
        "market_event", "prices", "weather", "load_model", "loads", "outages",
        "link_plan", "battery_model", "market_model", "local_policy", "hq_policy",
        "run", "ticks", "events", "intervals", "checks", "scoreboard",
    ):
        assert needed in names
