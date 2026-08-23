import json
import sqlite3
from pathlib import Path


def rebuild_index(runs_dir: Path) -> list[dict]:
    runs_dir = Path(runs_dir)
    entries: list[dict] = []
    for db_path in sorted(runs_dir.glob("*/run.db")):
        con = sqlite3.connect(db_path)
        row = con.execute(
            "SELECT id, status, seed, error, local_policy_id, hq_policy_id, market_event_id FROM run"
        ).fetchone()
        con.close()
        if row is None:
            continue
        entries.append(
            {
                "id": row[0],
                "status": row[1],
                "seed": row[2],
                "error": row[3],
                "local_policy_id": row[4],
                "hq_policy_id": row[5],
                "market_event_id": row[6],
            }
        )
    index_path = runs_dir / "index.json"
    index_path.write_text(json.dumps(entries))
    return entries


def load_index(runs_dir: Path) -> list[dict]:
    runs_dir = Path(runs_dir)
    index_path = runs_dir / "index.json"
    if not index_path.exists():
        rebuild_index(runs_dir)
    return json.loads(index_path.read_text())
