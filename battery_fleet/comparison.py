from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile
from uuid import uuid4

from battery_fleet.demo import run_lookahead_day, run_market_day
from battery_fleet.fleet import build_fleet
from battery_fleet.prices import Market
from battery_fleet.store import _resolve_runs_dir, write_run

START_TIME_UNIX = datetime(2024, 8, 15, tzinfo=timezone.utc).timestamp()
OFFLINE_TICK = 60
ONLINE_TICK = 68
MANIFESTS_DIRNAME = "comparisons"


@dataclass(frozen=True)
class ComparisonRuns:
    comparison_id: str
    greedy_dir: Path
    lookahead_dir: Path


def generate_comparison(
    runs_dir: Path | str | None = None,
    n_sites: int = 80,
    n_units: int = 100,
    seed: int = 1,
    comparison_id: str | None = None,
) -> ComparisonRuns:
    root = _resolve_runs_dir(runs_dir)
    resolved_id = (
        _new_comparison_id() if comparison_id is None else comparison_id
    )
    _validate_comparison_id(resolved_id)
    result = ComparisonRuns(
        resolved_id,
        root / f"{resolved_id}-greedy",
        root / f"{resolved_id}-lookahead",
    )
    manifest_path = _manifest_path(root, resolved_id)
    _ensure_available(result, manifest_path)

    greedy_fleet = build_fleet(n_sites, n_units, START_TIME_UNIX, seed)
    lookahead_fleet = build_fleet(n_sites, n_units, START_TIME_UNIX, seed)
    market = Market.from_formula()
    outage_ids = [
        battery.unit_id
        for site in greedy_fleet.installations
        for battery in site.batteries
    ][:5]

    greedy_records = run_market_day(
        greedy_fleet,
        market,
        outage_ids,
        OFFLINE_TICK,
        ONLINE_TICK,
        ancillary_revenue_usd=0.0,
    )
    lookahead_records = run_lookahead_day(
        lookahead_fleet,
        market,
        outage_ids,
        OFFLINE_TICK,
        ONLINE_TICK,
        ancillary_revenue_usd=0.0,
    )

    created_dirs = []
    try:
        greedy_path = write_run(
            result.greedy_dir.name,
            greedy_fleet,
            greedy_records,
            market.dt_seconds,
            runs_dir=root,
            comparison_id=resolved_id,
            controller="greedy",
            fleet_seed=seed,
        )
        created_dirs.append(greedy_path.parent)
        lookahead_path = write_run(
            result.lookahead_dir.name,
            lookahead_fleet,
            lookahead_records,
            market.dt_seconds,
            runs_dir=root,
            comparison_id=resolved_id,
            controller="lookahead",
            fleet_seed=seed,
        )
        created_dirs.append(lookahead_path.parent)
        _publish_manifest(manifest_path, result)
    except BaseException:
        for created_dir in reversed(created_dirs):
            shutil.rmtree(created_dir)
        raise
    return result


def list_completed_comparisons(
    runs_dir: Path | str | None = None,
) -> list[ComparisonRuns]:
    root = _resolve_runs_dir(runs_dir)
    manifests_dir = root / MANIFESTS_DIRNAME
    if not manifests_dir.is_dir():
        return []

    completed = []
    for manifest_path in manifests_dir.glob("*.json"):
        result = _read_completed_manifest(root, manifest_path)
        if result is not None:
            completed.append((manifest_path.stat().st_mtime, result))
    completed.sort(key=lambda item: (item[0], item[1].comparison_id), reverse=True)
    return [item[1] for item in completed]


def _new_comparison_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return f"{timestamp}-{uuid4().hex}"


def _validate_comparison_id(comparison_id: str) -> None:
    if (
        not comparison_id
        or comparison_id in {".", ".."}
        or Path(comparison_id).name != comparison_id
    ):
        raise ValueError("comparison_id must be a non-empty file name.")


def _manifest_path(root: Path, comparison_id: str) -> Path:
    return root / MANIFESTS_DIRNAME / f"{comparison_id}.json"


def _ensure_available(
    result: ComparisonRuns,
    manifest_path: Path,
) -> None:
    occupied = (
        result.greedy_dir,
        result.lookahead_dir,
        manifest_path,
    )
    if any(path.exists() for path in occupied):
        raise FileExistsError(
            f"Comparison already exists: {result.comparison_id}"
        )


def _publish_manifest(
    manifest_path: Path,
    result: ComparisonRuns,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "comparison_id": result.comparison_id,
        "greedy_dir": result.greedy_dir.name,
        "lookahead_dir": result.lookahead_dir.name,
    }
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=manifest_path.parent,
            prefix=f".{manifest_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            json.dump(payload, temporary, indent=2)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.link(temporary_path, manifest_path)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _read_completed_manifest(
    root: Path,
    manifest_path: Path,
) -> ComparisonRuns | None:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        comparison_id = payload["comparison_id"]
        greedy_name = payload["greedy_dir"]
        lookahead_name = payload["lookahead_dir"]
        if not all(
            isinstance(value, str)
            and value
            and Path(value).name == value
            for value in (comparison_id, greedy_name, lookahead_name)
        ):
            return None
        result = ComparisonRuns(
            comparison_id,
            root / greedy_name,
            root / lookahead_name,
        )
        if manifest_path.name != f"{comparison_id}.json":
            return None
        if not _run_matches(result.greedy_dir, comparison_id, "greedy"):
            return None
        if not _run_matches(result.lookahead_dir, comparison_id, "lookahead"):
            return None
        return result
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None


def _run_matches(
    run_dir: Path,
    comparison_id: str,
    controller: str,
) -> bool:
    try:
        summary = json.loads(
            (run_dir / "run.json").read_text(encoding="utf-8")
        )
        return (
            summary["comparison_id"] == comparison_id
            and summary["controller"] == controller
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return False
