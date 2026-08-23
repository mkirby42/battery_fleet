from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Region:
    id: str
    name: str


@dataclass(frozen=True)
class City:
    id: str
    name: str
    region_id: str


@dataclass(frozen=True)
class Substation:
    id: str
    name: str
    city_id: str


@dataclass(frozen=True)
class Location:
    id: str
    lat: float
    lon: float
    substation_id: str


@dataclass(frozen=True)
class Unit:
    id: str
    capacity_kwh: float
    max_charge_kw: float
    max_discharge_kw: float


@dataclass(frozen=True)
class Install:
    unit_id: str
    location_id: str


@dataclass(frozen=True)
class BatteryModel:
    id: str
    efficiency: float


@dataclass(frozen=True)
class MarketModel:
    id: str


@dataclass(frozen=True)
class LocalPolicy:
    id: str
    kind: Literal["fixed_reserve", "aggressive"]
    floor_frac: float


@dataclass(frozen=True)
class HqPolicy:
    id: str
    charge_below: float
    discharge_above: float


@dataclass(frozen=True)
class PriceRow:
    t_s: int
    energy: float
    scarcity: float
    congestion: float
    losses: float

    @property
    def spp(self) -> float:
        return self.energy + self.scarcity + self.congestion + self.losses


@dataclass(frozen=True)
class MarketEvent:
    id: str
    settlement_point: str
    kind: str
    scarcity_start_s: int
    scarcity_end_s: int
    scarcity_adder: float
    congestion_start_s: int
    congestion_end_s: int
    congestion_adder: float


@dataclass(frozen=True)
class WeatherRow:
    t_s: int
    city_id: str
    temp_c: float


@dataclass(frozen=True)
class LoadRow:
    location_id: str
    t_s: int
    kw: float


@dataclass(frozen=True)
class Outage:
    start_s: int
    end_s: int
    node_kind: Literal["substation", "city", "region"]
    node_id: str


@dataclass(frozen=True)
class LinkWindow:
    start_s: int
    end_s: int
    location_id: str


@dataclass(frozen=True)
class Tick:
    t_s: int
    unit_id: str
    energy_kwh: float
    power_kw: float
    who_decided: Literal["local", "hq"]
    hq_asked_kw: float | None
    shortfall_kwh: float
    islanded: bool
    link_up: bool


@dataclass(frozen=True)
class Event:
    t_s: int
    kind: str
    unit_id: str | None
    location_id: str | None
    detail: str


@dataclass(frozen=True)
class Interval:
    t_s: int
    energy_mwh: float
    pnl_usd: float
    energy: float
    scarcity: float
    congestion: float
    losses: float
    spp: float


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class Scoreboard:
    revenue_usd: float
    shortfall_kwh: float
    coverage: float
    locations_dark: int
    time_at_floor_s: int


@dataclass(frozen=True)
class RunCard:
    id: str
    seed: int
    schema_version: int
    status: Literal["running", "success", "failed"]
    error: str | None
    local_policy_id: str
    hq_policy_id: str
    market_event_id: str
    started_s: int | None
    finished_s: int | None
