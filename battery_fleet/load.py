from battery_fleet.clocks import INTERVAL_S, interval_start
from battery_fleet.types import LoadRow, Location, WeatherRow


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


def _kw_at(t_s: int, temp_c: float) -> float:
    hour = (t_s % 86400) / 3600
    tod = 0.6 + 0.4 * max(0, 1 - abs(hour - 18) / 6)
    ac = 0.15 * max(0, temp_c - 22)
    return 1.2 * (tod + ac)


def write_loads(
    locations: list[Location],
    weather: list[WeatherRow],
    duration_s: int,
    seed: int,
    city_of: dict[str, str],
) -> list[LoadRow]:
    del seed  # reproducible formula, no RNG
    weather_by_city = _index_weather(weather)
    loads: list[LoadRow] = []
    for loc in locations:
        city_id = city_of[loc.id]
        for t in range(0, duration_s, INTERVAL_S):
            temp = _temp_at(weather_by_city, city_id, t)
            loads.append(LoadRow(location_id=loc.id, t_s=t, kw=_kw_at(t, temp)))
    return loads


def load_at(loads: list[LoadRow], location_id: str, t_s: int) -> float:
    start = interval_start(t_s)
    for row in loads:
        if row.location_id == location_id and row.t_s == start:
            return row.kw
    raise KeyError(f"no load row for {location_id=} at t_s={start}")
