from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from battery_fleet.load import write_loads, write_weather
from battery_fleet.market import write_prices
from battery_fleet.types import (
    BatteryModel,
    City,
    HqPolicy,
    Install,
    LinkWindow,
    LoadRow,
    LocalPolicy,
    Location,
    MarketEvent,
    MarketModel,
    Outage,
    PriceRow,
    Region,
    Substation,
    Unit,
    WeatherRow,
)

REQUIRED_KEYS = (
    "seed",
    "duration_s",
    "n_locations",
    "local_policy",
    "hq_policy",
    "battery",
    "market_event",
)


@dataclass(frozen=True)
class World:
    regions: list[Region]
    cities: list[City]
    substations: list[Substation]
    locations: list[Location]
    units: list[Unit]
    installs: list[Install]
    local_policy: LocalPolicy
    hq_policy: HqPolicy
    battery_model: BatteryModel
    market_model: MarketModel
    event: MarketEvent
    outages: list[Outage]
    link_windows: list[LinkWindow]
    duration_s: int
    seed: int
    start_soc_frac: float
    weather: list[WeatherRow]
    prices: list[PriceRow]
    loads: list[LoadRow]
    city_of: dict[str, str]


def _require(data: dict, key: str):
    if key not in data:
        raise ValueError(f"missing key: {key}")
    return data[key]


def _unit01(seed: int, i: int, salt: int) -> float:
    x = (seed + 1) * 0x9E3779B9 + i * 0x85EBCA6B + salt * 0xC2B2AE35
    x &= 0xFFFFFFFF
    x ^= x >> 16
    x = (x * 0x45D9F3B) & 0xFFFFFFFF
    x ^= x >> 16
    x = (x * 0x45D9F3B) & 0xFFFFFFFF
    x ^= x >> 16
    return x / 0x100000000


def _place(n_locations: int, seed: int, i: int, city_id: str) -> tuple[float, float]:
    u = _unit01(seed, i, 1)
    v = _unit01(seed, i, 2)
    if n_locations > 3:
        if city_id == "c0":
            lat0, lon0 = 30.27, -97.74  # Austin
        else:
            lat0, lon0 = 30.44, -97.62  # Pflugerville
        span = 0.10
    else:
        lat0, lon0 = 30.27, -97.74
        span = 0.05
    lat = min(30.50, max(30.13, lat0 + (u - 0.5) * span))
    lon = min(-97.52, max(-97.90, lon0 + (v - 0.5) * span))
    return lat, lon


def load_scenario(path: Path | str) -> World:
    path = Path(path)
    with path.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("scenario must be a mapping")

    for key in REQUIRED_KEYS:
        _require(data, key)

    seed = data["seed"]
    duration_s = data["duration_s"]
    n_locations = data["n_locations"]
    start_soc_frac = float(data.get("start_soc_frac", 0.5))
    local_cfg = data["local_policy"]
    hq_cfg = data["hq_policy"]
    battery_cfg = data["battery"]
    event_cfg = data["market_event"]

    regions = [Region(id="r0", name="Travis")]

    if n_locations > 3:
        cities = [
            City(id="c0", name="Austin", region_id="r0"),
            City(id="c1", name="Pflugerville", region_id="r0"),
        ]
        substations = [
            Substation(id="s0", name="s0", city_id="c0"),
            Substation(id="s1", name="s1", city_id="c0"),
            Substation(id="s2", name="s2", city_id="c1"),
            Substation(id="s3", name="s3", city_id="c1"),
        ]
        substation_city = {"s0": "c0", "s1": "c0", "s2": "c1", "s3": "c1"}
    else:
        cities = [City(id="c0", name="Austin", region_id="r0")]
        substations = [Substation(id="s0", name="s0", city_id="c0")]
        substation_city = {"s0": "c0"}

    locations: list[Location] = []
    units: list[Unit] = []
    installs: list[Install] = []
    city_of: dict[str, str] = {}

    for i in range(n_locations):
        loc_id = f"l{i}"
        unit_id = f"u{i}"
        if n_locations > 3:
            substation_id = f"s{i % 4}"
        else:
            substation_id = "s0"
        city_id = substation_city[substation_id]
        lat, lon = _place(n_locations, seed, i, city_id)
        locations.append(
            Location(id=loc_id, lat=lat, lon=lon, substation_id=substation_id)
        )
        units.append(
            Unit(id=unit_id, capacity_kwh=10.0, max_charge_kw=5.0, max_discharge_kw=5.0)
        )
        installs.append(Install(unit_id=unit_id, location_id=loc_id))
        city_of[loc_id] = city_id

    local_policy = LocalPolicy(
        id="lp", kind=local_cfg["kind"], floor_frac=local_cfg["floor_frac"]
    )
    hq_policy = HqPolicy(
        id="hq",
        charge_below=hq_cfg["charge_below"],
        discharge_above=hq_cfg["discharge_above"],
    )
    battery_model = BatteryModel(id="b", efficiency=battery_cfg["efficiency"])
    market_model = MarketModel(id="m")

    event = MarketEvent(
        id="evt",
        settlement_point=event_cfg["settlement_point"],
        kind=event_cfg["kind"],
        scarcity_start_s=event_cfg["scarcity_start_s"],
        scarcity_end_s=event_cfg["scarcity_end_s"],
        scarcity_adder=event_cfg["scarcity_adder"],
        congestion_start_s=event_cfg["congestion_start_s"],
        congestion_end_s=event_cfg["congestion_end_s"],
        congestion_adder=event_cfg["congestion_adder"],
    )

    outages = [
        Outage(
            start_s=o["start_s"],
            end_s=o["end_s"],
            node_kind=o["node_kind"],
            node_id=o["node_id"],
        )
        for o in data.get("outages", [])
    ]

    day_of_year = int(data.get("day_of_year", 227))
    weather = write_weather(duration_s, [c.id for c in cities], day_of_year)
    prices = write_prices(
        event,
        duration_s,
        base_energy=event_cfg["base_energy"],
        losses=event_cfg["losses"],
    )
    loads = write_loads(locations, weather, duration_s, seed, city_of)

    return World(
        regions=regions,
        cities=cities,
        substations=substations,
        locations=locations,
        units=units,
        installs=installs,
        local_policy=local_policy,
        hq_policy=hq_policy,
        battery_model=battery_model,
        market_model=market_model,
        event=event,
        outages=outages,
        link_windows=[],
        duration_s=duration_s,
        seed=seed,
        start_soc_frac=start_soc_frac,
        weather=weather,
        prices=prices,
        loads=loads,
        city_of=city_of,
    )
