import json

import pytest

from battery_fleet.loop import FleetTickInput, run_fleet
from battery_fleet.store import list_runs, read_run, write_run
from store_support import (
    COMMANDS,
    DT,
    LOADS,
    make_records,
    make_two_site_fleet,
)


def test_write_read_roundtrip(tmp_path):
    fleet = make_two_site_fleet()
    records = make_records(fleet)
    path = write_run("r1", fleet, records, DT, runs_dir=tmp_path)
    data = read_run("r1", runs_dir=tmp_path)

    assert path == tmp_path / "r1" / "run.json"
    assert data["id"] == "r1"
    assert data["dt_seconds"] == DT
    sites = {site["id"]: site for site in data["sites"]}
    assert sites["i1"]["lat"] == 30.0
    assert sites["i1"]["lon"] == -97.0
    assert sites["i2"]["lat"] == 31.0
    assert sites["i2"]["lon"] == -98.0
    assert {unit["id"] for unit in data["units"]} == {"u1", "u2", "u3"}

    record = records[0]
    tick = data["ticks"][0]
    assert tick["fleet_w"] == pytest.approx(record.fleet_actual_power_watts)
    for site_record in record.site_records:
        for unit_id, actual_w in (
            site_record.actual_power_watts_by_unit_id.items()
        ):
            unit_tick = tick["units"][unit_id]
            assert unit_tick["soc"] == pytest.approx(
                site_record.state_of_charge_fraction_by_unit_id[unit_id]
            )
            assert unit_tick["actual_w"] == pytest.approx(actual_w)
            assert unit_tick["commanded_w"] == pytest.approx(
                site_record.commanded_power_watts_by_unit_id[unit_id]
            )
            assert (
                unit_tick["reachable"]
                is site_record.network_reachable_by_unit_id[unit_id]
            )


def test_mean_soc_and_cumulative_score(tmp_path):
    fleet = make_two_site_fleet()
    priced = FleetTickInput(
        LOADS,
        COMMANDS,
        fleet_target_power_watts=6_000.0,
        price_usd_per_megawatt_hour=200.0,
        ancillary_revenue_usd=5.0,
    )
    records = run_fleet(fleet, DT, [priced, priced])
    write_run("r1", fleet, records, DT, runs_dir=tmp_path)
    data = read_run("r1", runs_dir=tmp_path)

    for index, record in enumerate(records):
        socs = [
            soc
            for site in record.site_records
            for soc in site.state_of_charge_fraction_by_unit_id.values()
        ]
        assert data["ticks"][index]["mean_soc"] == pytest.approx(
            sum(socs) / len(socs)
        )
    tick0, tick1 = data["ticks"]
    assert tick1["cumulative_score_usd"] == pytest.approx(
        tick0["score_usd"] + tick1["score_usd"]
    )
    assert tick1["cumulative_customer_bill_usd"] == pytest.approx(
        tick0["customer_bill_usd"] + tick1["customer_bill_usd"]
    )
    assert tick0["customer_bill_usd"] == pytest.approx(
        records[0].score.customer_bill_usd
    )


def test_command_log_deltas_only(tmp_path):
    fleet = make_two_site_fleet()
    records = run_fleet(
        fleet,
        DT,
        [FleetTickInput(LOADS, COMMANDS)] * 3,
    )
    write_run("r1", fleet, records, DT, runs_dir=tmp_path)
    data = read_run("r1", runs_dir=tmp_path)

    setpoints = [
        event for event in data["commands"] if event["kind"] == "setpoint"
    ]
    assert len(setpoints) == 3
    assert {event["unit_id"] for event in setpoints} == {"u1", "u2", "u3"}


def test_target_logged_when_it_changes(tmp_path):
    fleet = make_two_site_fleet()
    records = run_fleet(
        fleet,
        DT,
        [
            FleetTickInput(LOADS, {}, fleet_target_power_watts=1_000.0),
            FleetTickInput(LOADS, {}, fleet_target_power_watts=2_000.0),
        ],
    )
    write_run("r1", fleet, records, DT, runs_dir=tmp_path)
    data = read_run("r1", runs_dir=tmp_path)

    targets = [
        event for event in data["commands"] if event["kind"] == "target"
    ]
    assert len(targets) == 2
    assert targets[0]["watts"] == pytest.approx(1_000.0)
    assert targets[1]["watts"] == pytest.approx(2_000.0)
    assert all(event["unit_id"] is None for event in targets)
    assert all(event["site_id"] is None for event in targets)


def test_offline_then_online_logged(tmp_path):
    fleet = make_two_site_fleet()
    records = list(make_records(fleet))
    fleet.installations[0].batteries[0].go_offline()
    records.extend(make_records(fleet))
    fleet.installations[0].batteries[0].come_online()
    records.extend(make_records(fleet))
    write_run("r1", fleet, records, DT, runs_dir=tmp_path)
    data = read_run("r1", runs_dir=tmp_path)

    flips = [
        event
        for event in data["commands"]
        if event["kind"] in ("offline", "online")
    ]
    assert [(event["kind"], event["unit_id"]) for event in flips] == [
        ("offline", "u1"),
        ("online", "u1"),
    ]
    tick0_time = data["ticks"][0]["time_unix"]
    assert all(event["time_unix"] != tick0_time for event in flips)


def test_clip_when_commanded_ne_actual(tmp_path):
    fleet = make_two_site_fleet()
    records = run_fleet(
        fleet,
        DT,
        [FleetTickInput(LOADS, {"u1": 1e9})],
    )
    write_run("r1", fleet, records, DT, runs_dir=tmp_path)
    data = read_run("r1", runs_dir=tmp_path)

    clips = [
        event for event in data["commands"] if event["kind"] == "clip"
    ]
    assert len(clips) == 1
    assert clips[0]["unit_id"] == "u1"


def test_list_runs_newest_first(tmp_path):
    fleet = make_two_site_fleet()
    records = make_records(fleet)
    write_run("aaa", fleet, records, DT, runs_dir=tmp_path)
    write_run("bbb", fleet, records, DT, runs_dir=tmp_path)

    listed = list_runs(runs_dir=tmp_path)
    assert [item["id"] for item in listed] == ["bbb", "aaa"]
    for item in listed:
        assert item["started_at_unix"] == records[0].time_unix
        assert item["n_ticks"] == 1


def test_old_format_writes_only_run_json(tmp_path):
    fleet = make_two_site_fleet()
    records = make_records(fleet)

    path = write_run("old", fleet, records, DT, runs_dir=tmp_path)
    raw = json.loads(path.read_text())
    loaded = read_run("old", runs_dir=tmp_path)

    assert [child.name for child in path.parent.iterdir()] == ["run.json"]
    assert "detail_files" not in raw
    assert raw == loaded
    assert set(loaded["ticks"][0]["units"]) == {"u1", "u2", "u3"}
