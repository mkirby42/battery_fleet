from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Iterator

from battery_fleet.fleet import Fleet
from battery_fleet.loop import FleetTickRecord
from battery_fleet.run_details import detail_rows
from battery_fleet.run_summary import build_run_payload


def write_run(
    run_id: str,
    fleet: Fleet,
    records: list[FleetTickRecord],
    dt_seconds: float,
    runs_dir: Path | str | None = None,
    *,
    comparison_id: str | None = None,
    controller: str | None = None,
    fleet_seed: int | None = None,
) -> Path:
    metadata = (comparison_id, controller, fleet_seed)
    provided = [value is not None for value in metadata]
    if any(provided) and not all(provided):
        raise ValueError(
            "comparison_id, controller, and fleet_seed must provide all three."
        )

    normalized_metadata: tuple[str, str, int] | None = None
    if all(provided):
        normalized_metadata = (
            comparison_id,
            controller,
            fleet_seed,
        )

    path = _run_json_path(run_id, runs_dir)
    run_dir = path.parent
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive_run_lock(run_dir):
        if run_dir.exists():
            raise FileExistsError(f"Run directory already exists: {run_dir}")
        if normalized_metadata is not None:
            return _write_normalized_run(
                run_id,
                fleet,
                records,
                dt_seconds,
                runs_dir,
                normalized_metadata,
            )

        payload = build_run_payload(
            run_id,
            fleet,
            records,
            dt_seconds,
        )
        with TemporaryDirectory(
            dir=run_dir.parent,
            prefix=f".{run_dir.name}.",
        ) as temporary:
            temporary_dir = Path(temporary)
            _atomic_write_text(
                temporary_dir / "run.json",
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            )
            temporary_dir.rename(run_dir)
    return path


def _write_normalized_run(
    run_id: str,
    fleet: Fleet,
    records: list[FleetTickRecord],
    dt_seconds: float,
    runs_dir: Path | str | None,
    metadata: tuple[str, str, int],
) -> Path:
    comparison_id, controller, _fleet_seed = metadata
    final_path = _run_json_path(run_id, runs_dir)
    final_dir = final_path.parent
    for record in records:
        if (
            record.score is not None
            and record.score.ancillary_revenue_usd != 0.0
        ):
            raise ValueError(
                "Normalized runs require zero ancillary revenue."
            )

    payload = build_run_payload(
        run_id,
        fleet,
        records,
        dt_seconds,
        normalized_metadata=metadata,
    )
    installations, units = detail_rows(
        run_id,
        comparison_id,
        controller,
        records,
        dt_seconds,
    )
    with TemporaryDirectory(
        dir=final_dir.parent,
        prefix=f".{final_dir.name}.",
    ) as temporary:
        temporary_dir = Path(temporary)
        _atomic_write_jsonl(
            temporary_dir / payload["detail_files"]["installations"],
            installations,
        )
        _atomic_write_jsonl(
            temporary_dir / payload["detail_files"]["units"],
            units,
        )
        _atomic_write_text(
            temporary_dir / "run.json",
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        )
        temporary_dir.rename(final_dir)
    return final_path


@contextmanager
def _exclusive_run_lock(run_dir: Path) -> Iterator[None]:
    lock_path = run_dir.with_name(f".{run_dir.name}.lock")
    lock_file = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()


def read_run(
    run_id: str,
    runs_dir: Path | str | None = None,
) -> dict:
    path = _run_json_path(run_id, runs_dir)
    payload = json.loads(path.read_text(encoding="utf-8"))
    detail_files = payload.get("detail_files")
    if detail_files and detail_files.get("units"):
        _hydrate_units(payload, path.parent / detail_files["units"])
    return payload


def list_runs(runs_dir: Path | str | None = None) -> list[dict]:
    root = _resolve_runs_dir(runs_dir)
    if not root.is_dir():
        return []

    items = []
    for child in root.iterdir():
        path = child / "run.json"
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append((
                path.stat().st_mtime,
                {
                    "id": data["id"],
                    "started_at_unix": data["started_at_unix"],
                    "n_ticks": len(data["ticks"]),
                },
            ))
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            continue

    items.sort(key=lambda item: (item[0], item[1]["id"]), reverse=True)
    return [item[1] for item in items]


def _resolve_runs_dir(runs_dir: Path | str | None) -> Path:
    if runs_dir is None:
        return Path(__file__).resolve().parent.parent / "runs"
    return Path(runs_dir)


def _run_json_path(run_id: str, runs_dir: Path | str | None) -> Path:
    return _resolve_runs_dir(runs_dir) / run_id / "run.json"


def _atomic_write_jsonl(path: Path, rows: list[dict]) -> None:
    text = "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in rows
    )
    _atomic_write_text(path, text)


def _atomic_write_text(path: Path, text: str) -> None:
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(text)
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _hydrate_units(payload: dict, path: Path) -> None:
    for tick in payload["ticks"]:
        tick["units"] = {}
    with path.open(encoding="utf-8") as rows:
        for line in rows:
            row = json.loads(line)
            payload["ticks"][row["tick_index"]]["units"][row["unit_id"]] = {
                "soc": row["soc"],
                "actual_w": row["actual_w"],
                "commanded_w": row["commanded_w"],
                "reachable": row["reachable"],
            }
