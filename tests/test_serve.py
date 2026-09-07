import json
import subprocess
import sys
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from battery_fleet import BatteryUnit, Installation
from battery_fleet.fleet import Fleet
from battery_fleet.loop import FleetTickInput, run_fleet
from battery_fleet.store import read_run, write_run
from battery_fleet import serve
from battery_fleet.__main__ import run as module_run

T0 = 1_700_000_000.0
DT = 900.0
CHARGE = 2_000.0
LOAD = 1_500.0
COMMANDS = {"u1": CHARGE, "u2": CHARGE, "u3": CHARGE}
LOADS = {"i1": LOAD, "i2": LOAD}


def make_unit(unit_id: str) -> BatteryUnit:
    return BatteryUnit(
        unit_id,
        "lot-a",
        10.0,
        10_000.0,
        10_000.0,
        T0,
    )


def make_two_site_fleet() -> Fleet:
    return Fleet(
        [
            Installation("i1", 30.0, -97.0, T0, [make_unit("u1")]),
            Installation(
                "i2",
                31.0,
                -98.0,
                T0,
                [make_unit("u2"), make_unit("u3")],
            ),
        ]
    )


def write_tiny_run(runs_dir, run_id="r1") -> str:
    fleet = make_two_site_fleet()
    records = run_fleet(fleet, DT, [FleetTickInput(LOADS, COMMANDS)])
    write_run(run_id, fleet, records, DT, runs_dir=runs_dir)
    return run_id


def start_server(runs_dir):
    httpd = serve.make_server("127.0.0.1", 0, runs_dir)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


def stop_server(httpd, thread):
    httpd.shutdown()
    thread.join(timeout=2)
    httpd.server_close()


def get(httpd, path):
    url = f"http://127.0.0.1:{httpd.server_port}{path}"
    request = Request(url, method="GET")
    with urlopen(request, timeout=2) as response:
        body = response.read()
        headers = dict(response.headers)
        return response.status, json.loads(body), headers


def test_list_runs_includes_written_id(tmp_path):
    run_id = write_tiny_run(tmp_path)
    httpd, thread = start_server(tmp_path)
    try:
        status, payload, headers = get(httpd, "/api/runs")
        assert status == 200
        assert any(item["id"] == run_id for item in payload)
        assert headers.get("Access-Control-Allow-Origin") == "*"
    finally:
        stop_server(httpd, thread)


def test_get_run_matches_read_run(tmp_path):
    run_id = write_tiny_run(tmp_path)
    expected = read_run(run_id, runs_dir=tmp_path)
    httpd, thread = start_server(tmp_path)
    try:
        status, payload, headers = get(httpd, f"/api/runs/{run_id}")
        assert status == 200
        assert payload["id"] == expected["id"]
        assert len(payload["ticks"]) == len(expected["ticks"])
        assert headers.get("Access-Control-Allow-Origin") == "*"
    finally:
        stop_server(httpd, thread)


def test_get_normalized_run_preserves_dashboard_unit_shape(tmp_path):
    fleet = make_two_site_fleet()
    records = run_fleet(
        fleet,
        DT,
        [
            FleetTickInput(
                LOADS,
                COMMANDS,
                price_usd_per_megawatt_hour=200.0,
            )
        ],
    )
    write_run(
        "normalized",
        fleet,
        records,
        DT,
        runs_dir=tmp_path,
        comparison_id="comparison-1",
        controller="greedy",
        fleet_seed=1,
    )
    httpd, thread = start_server(tmp_path)
    try:
        status, payload, _headers = get(httpd, "/api/runs/normalized")
        assert status == 200
        assert set(payload["ticks"][0]["units"]) == {"u1", "u2", "u3"}
        assert set(payload["ticks"][0]["units"]["u1"]) == {
            "soc",
            "actual_w",
            "commanded_w",
            "reachable",
        }
    finally:
        stop_server(httpd, thread)


def test_missing_run_is_404(tmp_path):
    write_tiny_run(tmp_path)
    httpd, thread = start_server(tmp_path)
    try:
        url = f"http://127.0.0.1:{httpd.server_port}/api/runs/nope"
        try:
            urlopen(url, timeout=2)
            raise AssertionError("expected 404")
        except HTTPError as error:
            assert error.code == 404
            assert error.headers.get("Access-Control-Allow-Origin") == "*"
    finally:
        stop_server(httpd, thread)


def test_unknown_path_is_404(tmp_path):
    write_tiny_run(tmp_path)
    httpd, thread = start_server(tmp_path)
    try:
        url = f"http://127.0.0.1:{httpd.server_port}/nope"
        try:
            urlopen(url, timeout=2)
            raise AssertionError("expected 404")
        except HTTPError as error:
            assert error.code == 404
    finally:
        stop_server(httpd, thread)


def test_unknown_argv_exits_2():
    result = subprocess.run(
        [sys.executable, "-m", "battery_fleet", "nope"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 2
    assert "usage" in (result.stderr + result.stdout).lower()


def test_serve_argv_dispatches_to_main(monkeypatch):
    called = []
    monkeypatch.setattr("battery_fleet.serve.main", lambda **_kw: called.append(True))
    module_run(["serve"])
    assert called
