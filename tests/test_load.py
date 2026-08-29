from battery_fleet.load import load_at, write_loads
from battery_fleet.types import Location, WeatherRow


def _wx(temp_c: float, t_s: int = 0) -> list[WeatherRow]:
    return [WeatherRow(t_s=t_s, city_id="c1", temp_c=temp_c)]


def test_hot_afternoon_higher_than_cool_night():
    loc = Location("l1", 32.0, -97.0, "s1")
    weather = [
        WeatherRow(t_s=0, city_id="c1", temp_c=15.0),
        WeatherRow(t_s=3600 * 15, city_id="c1", temp_c=38.0),
    ]
    loads = write_loads([loc], weather, duration_s=3600 * 16, seed=1, city_of={"l1": "c1"})
    night = load_at(loads, "l1", 0)
    hot = load_at(loads, "l1", 3600 * 15)
    assert hot > night
    assert night > 0


def test_houses_differ_at_the_same_hour():
    a = Location("l1", 30.27, -97.74, "s1")
    b = Location("l2", 30.28, -97.73, "s1")
    city_of = {"l1": "c1", "l2": "c1"}
    loads = write_loads([a, b], _wx(28.0), duration_s=300, seed=7, city_of=city_of)
    assert load_at(loads, "l1", 0) != load_at(loads, "l2", 0)


def test_same_seed_replays_the_same_house():
    loc = Location("l1", 30.27, -97.74, "s1")
    a = write_loads([loc], _wx(28.0), duration_s=300, seed=7, city_of={"l1": "c1"})
    b = write_loads([loc], _wx(28.0), duration_s=300, seed=7, city_of={"l1": "c1"})
    assert load_at(a, "l1", 0) == load_at(b, "l1", 0)


def test_seed_changes_the_house_scale():
    loc = Location("l1", 30.27, -97.74, "s1")
    a = write_loads([loc], _wx(28.0), duration_s=300, seed=7, city_of={"l1": "c1"})
    b = write_loads([loc], _wx(28.0), duration_s=300, seed=99, city_of={"l1": "c1"})
    assert load_at(a, "l1", 0) != load_at(b, "l1", 0)
