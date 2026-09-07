import json

import pytest

from battery_fleet.loop import FleetTickInput, run_fleet
from battery_fleet.store import read_run, write_run
from store_support import (
    CHARGE,
    COMMANDS,
    DT,
    LOADS,
    make_records,
    make_two_site_fleet,
)


def test_normalized_run_writes_three_reconciled_files(tmp_path):
    fleet = make_two_site_fleet()
    priced = FleetTickInput(
        LOADS,
        COMMANDS,
        fleet_target_power_watts=6_000.0,
        price_usd_per_megawatt_hour=200.0,
    )
    records = run_fleet(fleet, DT, [priced, priced])

    path = write_run(
        "greedy-1",
        fleet,
        records,
        DT,
        runs_dir=tmp_path,
        comparison_id="comparison-1",
        controller="greedy",
        fleet_seed=1,
    )

    run_dir = path.parent
    assert {child.name for child in run_dir.iterdir()} == {
        "run.json",
        "installation_ticks.jsonl",
        "unit_ticks.jsonl",
    }
    summary = json.loads(path.read_text())
    installation_rows = _read_jsonl(
        run_dir / "installation_ticks.jsonl"
    )
    unit_rows = _read_jsonl(run_dir / "unit_ticks.jsonl")
    assert summary["comparison_id"] == "comparison-1"
    assert summary["controller"] == "greedy"
    assert summary["fleet_seed"] == 1
    assert summary["detail_files"] == {
        "installations": "installation_ticks.jsonl",
        "units": "unit_ticks.jsonl",
    }
    assert "units" not in summary["ticks"][0]
    assert len(installation_rows) == 4
    assert len(unit_rows) == 6
    for tick_index, tick in enumerate(summary["ticks"]):
        tick_sites = [
            row
            for row in installation_rows
            if row["tick_index"] == tick_index
        ]
        assert sum(
            row["customer_bill_usd"] for row in tick_sites
        ) == pytest.approx(tick["customer_bill_usd"])
        assert sum(
            row["wholesale_pnl_usd"] for row in tick_sites
        ) == pytest.approx(tick["wholesale_pnl_usd"])
        assert sum(
            row["company_profit_usd"] for row in tick_sites
        ) == pytest.approx(tick["score_usd"])


def test_read_run_hydrates_normalized_unit_ticks(tmp_path):
    fleet = make_two_site_fleet()
    records = make_records(fleet, price=200.0)
    write_run(
        "greedy-1",
        fleet,
        records,
        DT,
        runs_dir=tmp_path,
        comparison_id="comparison-1",
        controller="greedy",
        fleet_seed=1,
    )

    data = read_run("greedy-1", runs_dir=tmp_path)

    assert set(data["ticks"][0]["units"]) == {"u1", "u2", "u3"}
    assert data["ticks"][0]["units"]["u1"] == {
        "soc": pytest.approx(
            records[0]
            .site_records[0]
            .state_of_charge_fraction_by_unit_id["u1"]
        ),
        "actual_w": pytest.approx(
            records[0].site_records[0].actual_power_watts_by_unit_id["u1"]
        ),
        "commanded_w": pytest.approx(CHARGE),
        "reachable": True,
    }
    assert "installation_ticks" not in data


@pytest.mark.parametrize(
    "metadata",
    [
        {"comparison_id": "comparison-1"},
        {"controller": "greedy", "fleet_seed": 1},
        {"comparison_id": "comparison-1", "fleet_seed": 1},
    ],
)
def test_write_run_rejects_partial_normalized_metadata(tmp_path, metadata):
    fleet = make_two_site_fleet()
    records = make_records(fleet)

    with pytest.raises(ValueError, match="all three"):
        write_run(
            "bad",
            fleet,
            records,
            DT,
            runs_dir=tmp_path,
            **metadata,
        )


def test_normalized_write_rejects_ancillary_revenue(tmp_path):
    fleet = make_two_site_fleet()
    records = make_records(fleet, price=200.0, ancillary=5.0)

    with pytest.raises(ValueError, match="ancillary revenue"):
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

    legacy_path = write_run(
        "legacy",
        fleet,
        records,
        DT,
        runs_dir=tmp_path,
    )
    assert json.loads(legacy_path.read_text())["ticks"][0][
        "score_usd"
    ] == pytest.approx(records[0].score.score_usd)


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]
