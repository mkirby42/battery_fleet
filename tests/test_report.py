from battery_fleet.loop import FleetTickRecord, TickRecord
from battery_fleet.report import format_fleet_records, format_records


def _site(
    time_unix: float,
    grid_watts: float,
    actual_by_unit: dict[str, float],
    soc_by_unit: dict[str, float],
    load_watts: float = 1_500.0,
    install_id: str = "i1",
) -> TickRecord:
    return TickRecord(
        time_unix=time_unix,
        install_id=install_id,
        user_load_power_watts=load_watts,
        grid_power_watts=grid_watts,
        commanded_power_watts_by_unit_id=dict(actual_by_unit),
        actual_power_watts_by_unit_id=actual_by_unit,
        state_of_charge_fraction_by_unit_id=soc_by_unit,
        network_reachable_by_unit_id={
            unit_id: True for unit_id in actual_by_unit
        },
    )


def test_format_records_empty():
    assert format_records([]) == ""


def test_format_records_is_aligned_table():
    records = [
        _site(
            1_700_000_900.0,
            3_500.0,
            {"u1": 2_000.0},
            {"u1": 0.5475},
        ),
        _site(
            1_700_002_700.0,
            -1_500.0,
            {"u1": -3_000.0},
            {"u1": 0.5160526315789473},
        ),
    ]

    text = format_records(records)
    lines = text.splitlines()

    assert lines[0].split() == [
        "time",
        "install",
        "load_W",
        "grid_W",
        "u1_W",
        "u1_soc",
    ]
    assert "1700000900" in lines[1]
    assert "i1" in lines[1]
    assert "2000.0" in lines[1]
    assert "0.547" in lines[1]
    assert "-3000.0" in lines[2]
    assert "-1500.0" in lines[2]
    assert len({len(line) for line in lines}) == 1


def test_format_records_adds_a_column_per_unit():
    record = _site(
        1_700_000_900.0,
        500.0,
        {"u2": -200.0, "u1": 700.0},
        {"u2": 0.4, "u1": 0.6},
        load_watts=1_000.0,
    )

    header = format_records([record]).splitlines()[0].split()
    assert header == [
        "time",
        "install",
        "load_W",
        "grid_W",
        "u1_W",
        "u1_soc",
        "u2_W",
        "u2_soc",
    ]


def test_format_fleet_records_is_aligned_table():
    site = _site(
        1_700_000_900.0,
        3_500.0,
        {"u1": 2_000.0},
        {"u1": 0.55},
    )
    records = [
        FleetTickRecord(
            time_unix=1_700_000_900.0,
            fleet_target_power_watts=200_000.0,
            fleet_actual_power_watts=200_000.0,
            fleet_commanded_power_watts=200_000.0,
            fleet_tracking_error_watts=0.0,
            fleet_load_power_watts=120_000.0,
            n_units=100,
            n_unreachable=0,
            score=None,
            site_records=(site,),
        )
    ]

    text = format_fleet_records(records)
    lines = text.splitlines()
    assert lines[0].split() == [
        "time",
        "price",
        "target_W",
        "fleet_W",
        "error_W",
        "as_$",
        "score_$",
        "n_unreach",
    ]
    assert "200000.0" in lines[1]
    assert len({len(line) for line in lines}) == 1
