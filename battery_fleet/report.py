from battery_fleet.loop import FleetTickRecord, TickRecord


def format_records(records: list[TickRecord]) -> str:
    if not records:
        return ""

    unit_ids = sorted(
        {
            unit_id
            for record in records
            for unit_id in record.actual_power_watts_by_unit_id
        }
    )

    headers = ["time", "install", "load_W", "grid_W"]
    for unit_id in unit_ids:
        headers.append(f"{unit_id}_W")
        headers.append(f"{unit_id}_soc")

    rows = [headers]
    for record in records:
        row = [
            f"{record.time_unix:.0f}",
            record.install_id,
            f"{record.user_load_power_watts:.1f}",
            f"{record.grid_power_watts:.1f}",
        ]
        for unit_id in unit_ids:
            row.append(
                f"{record.actual_power_watts_by_unit_id[unit_id]:.1f}"
            )
            row.append(
                f"{record.state_of_charge_fraction_by_unit_id[unit_id]:.3f}"
            )
        rows.append(row)

    return _align(rows)


def format_fleet_records(records: list[FleetTickRecord]) -> str:
    if not records:
        return ""

    headers = [
        "time",
        "price",
        "target_W",
        "fleet_W",
        "error_W",
        "as_$",
        "score_$",
        "n_unreach",
    ]
    rows = [headers]
    for record in records:
        if record.fleet_target_power_watts is None:
            target = "-"
        else:
            target = f"{record.fleet_target_power_watts:.1f}"
        if record.score is None:
            price = "-"
            as_usd = "-"
            score_usd = "-"
        else:
            price = f"{record.score.price_usd_per_megawatt_hour:.1f}"
            as_usd = f"{record.score.ancillary_revenue_usd:.2f}"
            score_usd = f"{record.score.score_usd:.2f}"
        rows.append(
            [
                f"{record.time_unix:.0f}",
                price,
                target,
                f"{record.fleet_actual_power_watts:.1f}",
                f"{record.fleet_tracking_error_watts:.1f}",
                as_usd,
                score_usd,
                str(record.n_unreachable),
            ]
        )
    return _align(rows)


def print_records(records: list[TickRecord]) -> None:
    text = format_records(records)
    if text:
        print(text)


def print_fleet_records(records: list[FleetTickRecord]) -> None:
    text = format_fleet_records(records)
    if text:
        print(text)


def _align(rows: list[list[str]]) -> str:
    widths = [
        max(len(row[column]) for row in rows)
        for column in range(len(rows[0]))
    ]
    lines = [
        "  ".join(
            row[column].rjust(widths[column])
            for column in range(len(rows[0]))
        )
        for row in rows
    ]
    return "\n".join(lines)
