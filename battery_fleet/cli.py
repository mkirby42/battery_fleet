import argparse
from datetime import UTC, datetime
from pathlib import Path

from battery_fleet.checks import run_checks, scoreboard
from battery_fleet.clocks import SCHEMA_VERSION
from battery_fleet.index import rebuild_index
from battery_fleet.loop import simulate
from battery_fleet.scenario import load_scenario
from battery_fleet.store import (
    create_run_db,
    write_card,
    write_checks,
    write_events,
    write_intervals,
    write_scoreboard,
    write_ticks,
    write_world,
)
from battery_fleet.types import RunCard


def _make_run_id(world_seed: int, runs_dir: Path) -> str:
    base = datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + f"-{world_seed:04x}"[-4:]
    run_id = base
    suffix = 0
    while (runs_dir / run_id).exists():
        suffix += 1
        run_id = f"{base}{suffix:02x}"
    return run_id


def run_scenario(path: Path | str, runs_dir: Path | str) -> Path:
    path = Path(path)
    runs_dir = Path(runs_dir)
    world = load_scenario(path)

    run_id = _make_run_id(world.seed, runs_dir)
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True)
    db_path = run_dir / "run.db"
    create_run_db(db_path)
    write_world(db_path, world)

    card = RunCard(
        id=run_id,
        seed=world.seed,
        schema_version=SCHEMA_VERSION,
        status="running",
        error=None,
        local_policy_id=world.local_policy.id,
        hq_policy_id=world.hq_policy.id,
        market_event_id=world.event.id,
        started_s=0,
        finished_s=None,
    )
    write_card(db_path, card)

    try:
        ticks, events, intervals = simulate(world)
        checks = run_checks(
            ticks, world.units, world.local_policy, world.duration_s
        )
        write_ticks(db_path, ticks)
        write_events(db_path, events)
        write_intervals(db_path, intervals)
        write_checks(db_path, checks)

        failed = [c.name for c in checks if not c.passed]
        if failed:
            card = RunCard(
                id=run_id,
                seed=world.seed,
                schema_version=SCHEMA_VERSION,
                status="failed",
                error=",".join(failed),
                local_policy_id=world.local_policy.id,
                hq_policy_id=world.hq_policy.id,
                market_event_id=world.event.id,
                started_s=0,
                finished_s=world.duration_s,
            )
            write_card(db_path, card)
        else:
            sb = scoreboard(ticks, intervals, world.units, world.local_policy)
            write_scoreboard(db_path, sb)
            card = RunCard(
                id=run_id,
                seed=world.seed,
                schema_version=SCHEMA_VERSION,
                status="success",
                error=None,
                local_policy_id=world.local_policy.id,
                hq_policy_id=world.hq_policy.id,
                market_event_id=world.event.id,
                started_s=0,
                finished_s=world.duration_s,
            )
            write_card(db_path, card)
    except Exception as e:
        card = RunCard(
            id=run_id,
            seed=world.seed,
            schema_version=SCHEMA_VERSION,
            status="failed",
            error=str(e),
            local_policy_id=world.local_policy.id,
            hq_policy_id=world.hq_policy.id,
            market_event_id=world.event.id,
            started_s=0,
            finished_s=None,
        )
        write_card(db_path, card)
        rebuild_index(runs_dir)
        raise

    rebuild_index(runs_dir)
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(prog="battery_fleet")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run")
    run_parser.add_argument("scenario", type=Path)
    run_parser.add_argument("--runs-dir", type=Path, default=Path("runs"))

    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--host", type=str, default="127.0.0.1")

    args = parser.parse_args()
    if args.command == "run":
        run_dir = run_scenario(args.scenario, runs_dir=args.runs_dir)
        print(run_dir)
    elif args.command == "serve":
        from battery_fleet.serve import main as serve_main

        serve_main(host=args.host, port=args.port, runs_dir=args.runs_dir)

