import sqlite3
from pathlib import Path

from battery_fleet.schema import DDL


def create_run_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(DDL)
    con.commit()
    con.close()
