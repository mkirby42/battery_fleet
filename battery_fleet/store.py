import sqlite3
from pathlib import Path

from battery_fleet.schema import DDL
from battery_fleet.scenario import World
from battery_fleet.types import (
    Check,
    Event,
    Interval,
    RunCard,
    Scoreboard,
    Tick,
)


def create_run_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(DDL)
    con.commit()
    con.close()


def write_world(path: Path, world: World) -> None:
    con = sqlite3.connect(path)
    for r in world.regions:
        con.execute(
            "INSERT INTO regions (id, name) VALUES (?, ?)",
            (r.id, r.name),
        )
    for c in world.cities:
        con.execute(
            "INSERT INTO cities (id, name, region_id) VALUES (?, ?, ?)",
            (c.id, c.name, c.region_id),
        )
    for s in world.substations:
        con.execute(
            "INSERT INTO substations (id, name, city_id) VALUES (?, ?, ?)",
            (s.id, s.name, s.city_id),
        )
    for loc in world.locations:
        con.execute(
            "INSERT INTO locations (id, lat, lon, substation_id) VALUES (?, ?, ?, ?)",
            (loc.id, loc.lat, loc.lon, loc.substation_id),
        )
    for u in world.units:
        con.execute(
            "INSERT INTO units (id, capacity_kwh, max_charge_kw, max_discharge_kw) VALUES (?, ?, ?, ?)",
            (u.id, u.capacity_kwh, u.max_charge_kw, u.max_discharge_kw),
        )
    for inst in world.installs:
        con.execute(
            "INSERT INTO installs (unit_id, location_id) VALUES (?, ?)",
            (inst.unit_id, inst.location_id),
        )
    ev = world.event
    con.execute(
        "INSERT INTO market_event (id, settlement_point, kind, scarcity_start_s, scarcity_end_s, scarcity_adder, congestion_start_s, congestion_end_s, congestion_adder) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ev.id,
            ev.settlement_point,
            ev.kind,
            ev.scarcity_start_s,
            ev.scarcity_end_s,
            ev.scarcity_adder,
            ev.congestion_start_s,
            ev.congestion_end_s,
            ev.congestion_adder,
        ),
    )
    for row in world.prices:
        con.execute(
            "INSERT INTO prices (t_s, energy, scarcity, congestion, losses) VALUES (?, ?, ?, ?, ?)",
            (row.t_s, row.energy, row.scarcity, row.congestion, row.losses),
        )
    for row in world.weather:
        con.execute(
            "INSERT INTO weather (t_s, city_id, temp_c) VALUES (?, ?, ?)",
            (row.t_s, row.city_id, row.temp_c),
        )
    con.execute(
        "INSERT INTO load_model (id, formula) VALUES (?, ?)",
        ("lm", "scale*(tod+hvac)"),
    )
    for row in world.loads:
        con.execute(
            "INSERT INTO loads (location_id, t_s, kw) VALUES (?, ?, ?)",
            (row.location_id, row.t_s, row.kw),
        )
    for o in world.outages:
        con.execute(
            "INSERT INTO outages (start_s, end_s, node_kind, node_id) VALUES (?, ?, ?, ?)",
            (o.start_s, o.end_s, o.node_kind, o.node_id),
        )
    for w in world.link_windows:
        con.execute(
            "INSERT INTO link_plan (start_s, end_s, location_id) VALUES (?, ?, ?)",
            (w.start_s, w.end_s, w.location_id),
        )
    bm = world.battery_model
    con.execute(
        "INSERT INTO battery_model (id, efficiency) VALUES (?, ?)",
        (bm.id, bm.efficiency),
    )
    mm = world.market_model
    con.execute(
        "INSERT INTO market_model (id) VALUES (?)",
        (mm.id,),
    )
    lp = world.local_policy
    con.execute(
        "INSERT INTO local_policy (id, kind, floor_frac) VALUES (?, ?, ?)",
        (lp.id, lp.kind, lp.floor_frac),
    )
    hq = world.hq_policy
    con.execute(
        "INSERT INTO hq_policy (id, charge_below, discharge_above) VALUES (?, ?, ?)",
        (hq.id, hq.charge_below, hq.discharge_above),
    )
    con.commit()
    con.close()


def write_card(path: Path, card: RunCard) -> None:
    con = sqlite3.connect(path)
    con.execute(
        "INSERT OR REPLACE INTO run (id, seed, schema_version, status, error, local_policy_id, hq_policy_id, market_event_id, started_s, finished_s) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            card.id,
            card.seed,
            card.schema_version,
            card.status,
            card.error,
            card.local_policy_id,
            card.hq_policy_id,
            card.market_event_id,
            card.started_s,
            card.finished_s,
        ),
    )
    con.commit()
    con.close()


def write_ticks(path: Path, ticks: list[Tick]) -> None:
    con = sqlite3.connect(path)
    con.executemany(
        "INSERT INTO ticks (t_s, unit_id, energy_kwh, power_kw, who_decided, hq_asked_kw, shortfall_kwh, islanded, link_up) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                t.t_s,
                t.unit_id,
                t.energy_kwh,
                t.power_kw,
                t.who_decided,
                t.hq_asked_kw,
                t.shortfall_kwh,
                int(t.islanded),
                int(t.link_up),
            )
            for t in ticks
        ],
    )
    con.commit()
    con.close()


def write_events(path: Path, events: list[Event]) -> None:
    con = sqlite3.connect(path)
    con.executemany(
        "INSERT INTO events (t_s, kind, unit_id, location_id, detail) VALUES (?, ?, ?, ?, ?)",
        [
            (e.t_s, e.kind, e.unit_id, e.location_id, e.detail)
            for e in events
        ],
    )
    con.commit()
    con.close()


def write_intervals(path: Path, intervals: list[Interval]) -> None:
    con = sqlite3.connect(path)
    con.executemany(
        "INSERT INTO intervals (t_s, energy_mwh, pnl_usd, energy, scarcity, congestion, losses, spp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                iv.t_s,
                iv.energy_mwh,
                iv.pnl_usd,
                iv.energy,
                iv.scarcity,
                iv.congestion,
                iv.losses,
                iv.spp,
            )
            for iv in intervals
        ],
    )
    con.commit()
    con.close()


def write_checks(path: Path, checks: list[Check]) -> None:
    con = sqlite3.connect(path)
    con.executemany(
        "INSERT INTO checks (name, passed, detail) VALUES (?, ?, ?)",
        [(c.name, int(c.passed), c.detail) for c in checks],
    )
    con.commit()
    con.close()


def write_scoreboard(path: Path, sb: Scoreboard) -> None:
    con = sqlite3.connect(path)
    con.execute(
        "INSERT INTO scoreboard (revenue_usd, shortfall_kwh, coverage, locations_dark, time_at_floor_s) VALUES (?, ?, ?, ?, ?)",
        (
            sb.revenue_usd,
            sb.shortfall_kwh,
            sb.coverage,
            sb.locations_dark,
            sb.time_at_floor_s,
        ),
    )
    con.commit()
    con.close()
