import sqlite3
from pathlib import Path


class Incomparable(Exception):
    pass


def _db_path(run_dir: Path) -> Path:
    return Path(run_dir) / "run.db"


def _read_card(con: sqlite3.Connection) -> dict:
    row = con.execute(
        "SELECT id, seed, schema_version, local_policy_id, hq_policy_id, market_event_id, status FROM run"
    ).fetchone()
    if row is None:
        raise Incomparable("run card missing")
    return {
        "id": row[0],
        "seed": row[1],
        "schema_version": row[2],
        "local_policy_id": row[3],
        "hq_policy_id": row[4],
        "market_event_id": row[5],
        "status": row[6],
    }


def _count(con: sqlite3.Connection, table: str) -> int:
    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _read_scoreboard(con: sqlite3.Connection) -> dict:
    row = con.execute(
        "SELECT revenue_usd, shortfall_kwh, coverage, locations_dark, time_at_floor_s FROM scoreboard"
    ).fetchone()
    if row is None:
        raise Incomparable("scoreboard missing")
    return {
        "revenue_usd": row[0],
        "shortfall_kwh": row[1],
        "coverage": row[2],
        "locations_dark": row[3],
        "time_at_floor_s": row[4],
    }


def _read_intervals(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute(
        "SELECT t_s, pnl_usd, spp FROM intervals ORDER BY t_s"
    ).fetchall()
    return [{"t_s": r[0], "pnl_usd": r[1], "spp": r[2]} for r in rows]


def _assert_comparable(card_a: dict, card_b: dict, con_a: sqlite3.Connection, con_b: sqlite3.Connection) -> None:
    for field in ("seed", "market_event_id", "hq_policy_id", "schema_version"):
        if card_a[field] != card_b[field]:
            raise Incomparable(f"{field} mismatch: {card_a[field]!r} vs {card_b[field]!r}")
    for table in ("locations", "units"):
        count_a = _count(con_a, table)
        count_b = _count(con_b, table)
        if count_a != count_b:
            raise Incomparable(f"{table} count mismatch: {count_a} vs {count_b}")


def compare_runs(dir_a: Path | str, dir_b: Path | str) -> dict:
    path_a = _db_path(Path(dir_a))
    path_b = _db_path(Path(dir_b))
    con_a = sqlite3.connect(path_a)
    con_b = sqlite3.connect(path_b)
    try:
        card_a = _read_card(con_a)
        card_b = _read_card(con_b)
        _assert_comparable(card_a, card_b, con_a, con_b)
        return {
            "a": _read_scoreboard(con_a),
            "b": _read_scoreboard(con_b),
            "intervals": {
                "a": _read_intervals(con_a),
                "b": _read_intervals(con_b),
            },
        }
    finally:
        con_a.close()
        con_b.close()
