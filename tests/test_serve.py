from pathlib import Path

from battery_fleet.cli import run_scenario
from battery_fleet.serve import TICK_STRIDE_THRESHOLD, _stride_ticks, run_payload, runs_payload


def test_api_lists_and_loads_a_success(tmp_path: Path):
    run_dir = run_scenario(Path("scenarios/tiny.yaml"), runs_dir=tmp_path)
    listing = runs_payload(tmp_path)
    assert listing[0]["status"] == "success"
    body = run_payload(tmp_path, run_dir.name)
    assert "locations" in body
    assert "ticks" in body
    assert "prices" in body
    assert "scoreboard" in body
    assert body["last_tick_s"] == max(t["t_s"] for t in body["ticks"])
    assert body["card"]["local_policy_kind"] == "fixed_reserve"
    assert listing[0]["local_policy_kind"] == "fixed_reserve"
    assert body["loads"]
    assert {row["location_id"] for row in body["loads"]} == {loc["id"] for loc in body["locations"]}


def test_stride_ticks_below_threshold_keeps_all():
    rows = [(t, f"u{i}") for t in (0, 15, 30) for i in range(3)]
    kept, stride = _stride_ticks(rows, threshold=100)
    assert stride == 1
    assert kept == rows


def test_stride_ticks_keeps_every_unit_at_each_kept_time():
    n_units = 60
    times = list(range(0, 40 * 15, 15))
    rows = [(t, f"u{i:02d}") for t in times for i in range(n_units)]
    kept, stride = _stride_ticks(rows, threshold=200)
    assert stride == 4
    kept_times = sorted({r[0] for r in kept})
    assert kept_times == times[::4]
    all_units = {f"u{i:02d}" for i in range(n_units)}
    assert {r[1] for r in kept} == all_units
    for t in kept_times:
        assert {r[1] for r in kept if r[0] == t} == all_units


def test_stride_threshold_is_200k():
    assert TICK_STRIDE_THRESHOLD == 200_000
    rows = [(t, "u0") for t in range(0, 200_000 * 15, 15)]
    _, stride = _stride_ticks(rows)
    assert stride == 1
    rows.append((200_000 * 15, "u0"))
    _, stride = _stride_ticks(rows)
    assert stride == 4
