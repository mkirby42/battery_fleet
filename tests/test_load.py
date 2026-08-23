from battery_fleet.load import load_at, write_loads
from battery_fleet.types import Location, WeatherRow


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
