import json
import mimetypes
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from battery_fleet.index import load_index

DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "dashboard"
TICK_STRIDE_THRESHOLD = 200_000


def runs_payload(runs_dir: Path | str) -> list[dict]:
    return [r for r in load_index(Path(runs_dir)) if r["status"] == "success"]


def _rows_to_dicts(cursor: sqlite3.Cursor, rows: list) -> list[dict]:
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


def _read_card(con: sqlite3.Connection) -> dict:
    row = con.execute(
        "SELECT id, seed, schema_version, status, error, local_policy_id, "
        "hq_policy_id, market_event_id, started_s, finished_s FROM run"
    ).fetchone()
    if row is None:
        raise ValueError("run card missing")
    cols = [
        "id", "seed", "schema_version", "status", "error", "local_policy_id",
        "hq_policy_id", "market_event_id", "started_s", "finished_s",
    ]
    return dict(zip(cols, row))


def _read_ticks(con: sqlite3.Connection) -> tuple[list[dict], int]:
    cur = con.execute(
        "SELECT t.t_s, t.unit_id, t.energy_kwh, t.power_kw, t.shortfall_kwh, "
        "t.islanded, t.link_up, u.capacity_kwh "
        "FROM ticks t JOIN units u ON t.unit_id = u.id ORDER BY t.t_s, t.unit_id"
    )
    rows = cur.fetchall()
    stride = 1
    if len(rows) > TICK_STRIDE_THRESHOLD:
        rows = rows[::4]
        stride = 4
    ticks = [
        {
            "t_s": r[0],
            "unit_id": r[1],
            "energy_kwh": r[2],
            "power_kw": r[3],
            "shortfall_kwh": r[4],
            "islanded": bool(r[5]),
            "link_up": bool(r[6]),
            "capacity_kwh": r[7],
        }
        for r in rows
    ]
    return ticks, stride


def run_payload(runs_dir: Path | str, run_id: str) -> dict:
    db_path = Path(runs_dir) / run_id / "run.db"
    if not db_path.exists():
        raise FileNotFoundError(f"run not found: {run_id}")

    con = sqlite3.connect(db_path)
    try:
        card = _read_card(con)

        cur = con.execute("SELECT id, lat, lon FROM locations ORDER BY id")
        locations = _rows_to_dicts(cur, cur.fetchall())

        cur = con.execute(
            "SELECT id, capacity_kwh, max_charge_kw, max_discharge_kw FROM units ORDER BY id"
        )
        units = _rows_to_dicts(cur, cur.fetchall())

        cur = con.execute(
            "SELECT unit_id, location_id FROM installs ORDER BY unit_id"
        )
        installs = _rows_to_dicts(cur, cur.fetchall())

        ticks, trace_stride = _read_ticks(con)

        cur = con.execute(
            "SELECT t_s, energy, scarcity, congestion, losses FROM prices ORDER BY t_s"
        )
        prices = _rows_to_dicts(cur, cur.fetchall())

        cur = con.execute(
            "SELECT start_s, end_s, node_kind, node_id FROM outages ORDER BY start_s"
        )
        outages = _rows_to_dicts(cur, cur.fetchall())

        cur = con.execute(
            "SELECT t_s, kind, unit_id, location_id, detail FROM events ORDER BY t_s"
        )
        events = _rows_to_dicts(cur, cur.fetchall())

        cur = con.execute(
            "SELECT t_s, energy_mwh, pnl_usd, energy, scarcity, congestion, losses, spp "
            "FROM intervals ORDER BY t_s"
        )
        intervals = _rows_to_dicts(cur, cur.fetchall())

        cur = con.execute(
            "SELECT revenue_usd, shortfall_kwh, coverage, locations_dark, time_at_floor_s "
            "FROM scoreboard"
        )
        sb_row = cur.fetchone()
        scoreboard = None
        if sb_row is not None:
            scoreboard = {
                "revenue_usd": sb_row[0],
                "shortfall_kwh": sb_row[1],
                "coverage": sb_row[2],
                "locations_dark": sb_row[3],
                "time_at_floor_s": sb_row[4],
            }

        return {
            "card": card,
            "locations": locations,
            "units": units,
            "installs": installs,
            "ticks": ticks,
            "trace_stride": trace_stride,
            "prices": prices,
            "outages": outages,
            "events": events,
            "intervals": intervals,
            "scoreboard": scoreboard,
        }
    finally:
        con.close()


def _json_response(handler: BaseHTTPRequestHandler, status: int, body: object) -> None:
    data = json.dumps(body).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _file_response(handler: BaseHTTPRequestHandler, path: Path) -> None:
    content = path.read_bytes()
    mime, _ = mimetypes.guess_type(str(path))
    handler.send_response(200)
    handler.send_header("Content-Type", mime or "application/octet-stream")
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)


def _make_handler(runs_dir: Path, dashboard_dir: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            pass

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = unquote(parsed.path)

            if path == "/api/runs":
                _json_response(self, 200, runs_payload(runs_dir))
                return

            if path.startswith("/api/runs/"):
                run_id = path[len("/api/runs/"):]
                if not run_id:
                    _json_response(self, 404, {"error": "missing run id"})
                    return
                try:
                    body = run_payload(runs_dir, run_id)
                except FileNotFoundError:
                    _json_response(self, 404, {"error": f"run not found: {run_id}"})
                    return
                _json_response(self, 200, body)
                return

            rel = "index.html" if path in ("/", "") else path.lstrip("/")
            file_path = (dashboard_dir / rel).resolve()
            if not str(file_path).startswith(str(dashboard_dir.resolve())):
                self.send_error(403)
                return
            if not file_path.is_file():
                self.send_error(404)
                return
            _file_response(self, file_path)

    return Handler


def main(host: str = "127.0.0.1", port: int = 8765, runs_dir: Path | str = "runs") -> None:
    runs_dir = Path(runs_dir)
    handler = _make_handler(runs_dir, DASHBOARD_DIR)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving dashboard at http://{host}:{port}/  (runs: {runs_dir.resolve()})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
