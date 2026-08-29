"""Mermaid view of battery_fleet.types. Fields come from the dataclasses."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Union, get_args, get_origin, get_type_hints

from battery_fleet import types as T

ENTITIES = [
    T.Region, T.City, T.Substation, T.Location, T.Unit, T.Install,
    T.BatteryModel, T.MarketModel, T.LocalPolicy, T.HqPolicy,
    T.MarketEvent, T.WeatherRow, T.LoadRow, T.Outage, T.LinkWindow,
    T.PriceRow, T.Tick, T.Event, T.Interval, T.Check, T.Scoreboard, T.RunCard,
]

PLANES = {
    "World pieces": [
        "Region", "City", "Substation", "Location", "Unit", "Install",
        "BatteryModel", "MarketModel", "LocalPolicy", "HqPolicy",
        "MarketEvent", "WeatherRow", "Outage", "LinkWindow",
    ],
    "Reality": ["RunCard"],
    "Time": ["PriceRow", "LoadRow", "Tick", "Event", "Interval"],
    "Judgment": ["Check", "Scoreboard"],
}

# (from, to, label) — FKs implied by *_id fields on the types
EDGES = [
    ("Region", "City", "region_id"),
    ("City", "Substation", "city_id"),
    ("Substation", "Location", "substation_id"),
    ("Unit", "Install", "unit_id"),
    ("Location", "Install", "location_id"),
    ("City", "WeatherRow", "city_id"),
    ("Location", "LoadRow", "location_id"),
    ("Location", "LinkWindow", "location_id"),
    ("Unit", "Tick", "unit_id"),
    ("Unit", "Event", "unit_id"),
    ("Location", "Event", "location_id"),
    ("LocalPolicy", "RunCard", "local_policy_id"),
    ("HqPolicy", "RunCard", "hq_policy_id"),
    ("MarketEvent", "RunCard", "market_event_id"),
]

DATA_MODEL_MD = Path(__file__).with_name("data-model.md")


def _simple_type(hint: object) -> str:
    origin = get_origin(hint)
    if origin is Union:
        args = [a for a in get_args(hint) if a is not type(None)]
        return _simple_type(args[0]) if args else "any"
    if origin is not None:
        return "any"
    if hint is str:
        return "string"
    if hint is int:
        return "int"
    if hint is float:
        return "float"
    if hint is bool:
        return "bool"
    return "string"


def _field_rows(cls: type) -> list[str]:
    hints = get_type_hints(cls)
    rows = []
    for f in fields(cls):
        rows.append(f"    {_simple_type(hints.get(f.name, str))} {f.name}")
    return rows


def mermaid_er() -> str:
    lines = ["erDiagram"]
    for cls in ENTITIES:
        lines.append(f"  {cls.__name__} {{")
        lines.extend(_field_rows(cls))
        lines.append("  }")
    for src, dst, label in EDGES:
        lines.append(f"  {src} ||--o{{ {dst} : {label}")
    return "\n".join(lines) + "\n"


def mermaid_planes() -> str:
    lines = ["flowchart TB"]
    for i, (plane, names) in enumerate(PLANES.items(), start=1):
        sid = f"p{i}"
        lines.append(f'  subgraph {sid}["{plane}"]')
        for name in names:
            lines.append(f"    {name}")
        lines.append("  end")
    for src, dst, label in EDGES:
        lines.append(f"  {src} -->|{label}| {dst}")
    return "\n".join(lines) + "\n"


def render_markdown() -> str:
    return (
        "# Data model\n\n"
        "Generated from `battery_fleet.types`. Do not edit by hand. "
        "Regenerate: `python -m battery_fleet diagram`.\n\n"
        "## Four planes\n\n"
        "```mermaid\n"
        f"{mermaid_planes().rstrip()}\n"
        "```\n\n"
        "## Entities and fields\n\n"
        "```mermaid\n"
        f"{mermaid_er().rstrip()}\n"
        "```\n"
    )


def write_markdown(path: Path | None = None) -> Path:
    path = path or DATA_MODEL_MD
    path.write_text(render_markdown())
    return path
