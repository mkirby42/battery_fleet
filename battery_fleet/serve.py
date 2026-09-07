import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from battery_fleet.store import list_runs, read_run


def make_server(host: str, port: int, runs_dir: Path | str | None = None):
    return ThreadingHTTPServer((host, port), _handler_for(runs_dir))


def main(host: str = "127.0.0.1", port: int = 8000, runs_dir=None) -> None:
    httpd = make_server(host, port, runs_dir)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()


def _handler_for(runs_dir: Path | str | None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = unquote(urlparse(self.path).path)
            if path == "/api/runs":
                self._json(200, list_runs(runs_dir=runs_dir))
                return
            prefix = "/api/runs/"
            if path.startswith(prefix):
                run_id = path[len(prefix) :]
                if run_id and "/" not in run_id and run_id not in {".", ".."}:
                    try:
                        self._json(200, read_run(run_id, runs_dir=runs_dir))
                        return
                    except (FileNotFoundError, OSError, json.JSONDecodeError, KeyError):
                        pass
            self._not_found()

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, format: str, *args) -> None:
            return

        def _cors(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def _json(self, status: int, payload) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _not_found(self) -> None:
            self.send_response(404)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

    return Handler
