import math

from battery_fleet.clocks import INTERVAL_S, interval_start
from battery_fleet.types import LoadRow, Location, WeatherRow


def _unit01(seed: int, i: int, salt: int) -> float:
    x = (seed + 1) * 0x9E3779B9 + i * 0x85EBCA6B + salt * 0xC2B2AE35
    x &= 0xFFFFFFFF
    x ^= x >> 16
    x = (x * 0x45D9F3B) & 0xFFFFFFFF
    x ^= x >> 16
    x = (x * 0x45D9F3B) & 0xFFFFFFFF
    x ^= x >> 16
    return x / 0x100000000


def house_scale(seed: int, loc_i: int) -> float:
    u = min(1.0 - 1e-12, max(1e-12, _unit01(seed, loc_i, 11)))
    v = min(1.0 - 1e-12, max(1e-12, _unit01(seed, loc_i, 12)))
    z = math.sqrt(-2.0 * math.log(u)) * math.cos(2.0 * math.pi * v)
    return math.exp(0.45 * z)


def write_weather(
    duration_s: int, city_ids: list[str], day_of_year: int = 227
) -> list[WeatherRow]:
    season = 0.5 + 0.5 * math.sin((day_of_year - 80) / 365.0 * 2.0 * math.pi)
    mean = 20.0 + 10.0 * season
    amp = 5.0 + 3.0 * season
    rows: list[WeatherRow] = []
    for t in range(0, duration_s, INTERVAL_S):
        hour = (t % 86400) / 3600.0
        temp_c = mean + amp * math.cos((hour - 16.0) * 2.0 * math.pi / 24.0)
        for city_id in city_ids:
            rows.append(WeatherRow(t_s=t, city_id=city_id, temp_c=temp_c))
    return rows


def _index_weather(weather: list[WeatherRow]) -> dict[str, list[WeatherRow]]:
    by_city: dict[str, list[WeatherRow]] = {}
    for row in weather:
        by_city.setdefault(row.city_id, []).append(row)
    for rows in by_city.values():
        rows.sort(key=lambda r: r.t_s)
    return by_city


def _temp_at(weather_by_city: dict[str, list[WeatherRow]], city_id: str, t_s: int) -> float:
    temp = 20.0
    for row in weather_by_city.get(city_id, []):
        if row.t_s <= t_s:
            temp = row.temp_c
        else:
            break
    return temp


def _tod(t_s: int) -> float:
    hour = (t_s % 86400) / 3600.0
    morning = max(0.0, 1.0 - abs(hour - 8.0) / 2.5)
    evening = max(0.0, 1.0 - abs(hour - 18.5) / 4.0)
    return 0.55 + 0.30 * morning + 0.55 * evening


def _hvac(temp_c: float) -> float:
    return 0.12 * max(0.0, temp_c - 22.0) + 0.10 * max(0.0, 16.0 - temp_c)


def _kw_at(t_s: int, temp_c: float, scale: float) -> float:
    return scale * (_tod(t_s) + _hvac(temp_c))


def write_loads(
    locations: list[Location],
    weather: list[WeatherRow],
    duration_s: int,
    seed: int,
    city_of: dict[str, str],
) -> list[LoadRow]:
    weather_by_city = _index_weather(weather)
    loads: list[LoadRow] = []
    for i, loc in enumerate(locations):
        scale = house_scale(seed, i)
        city_id = city_of[loc.id]
        for t in range(0, duration_s, INTERVAL_S):
            temp = _temp_at(weather_by_city, city_id, t)
            loads.append(LoadRow(location_id=loc.id, t_s=t, kw=_kw_at(t, temp, scale)))
    return loads


def index_loads(loads: list[LoadRow]) -> dict[tuple[str, int], float]:
    return {(row.location_id, row.t_s): row.kw for row in loads}


def load_at(loads: list[LoadRow], location_id: str, t_s: int) -> float:
    start = interval_start(t_s)
    for row in loads:
        if row.location_id == location_id and row.t_s == start:
            return row.kw
    raise KeyError(f"no load row for {location_id=} at t_s={start}")
