from battery_fleet import BatteryUnit, Installation
from battery_fleet.demo import run_market_day
from battery_fleet.fleet import Fleet
from battery_fleet.prices import Market, market_day_prices
from battery_fleet.store import read_run, write_run

T0 = 1_700_000_000.0
DT = 900.0


def make_unit(unit_id: str) -> BatteryUnit:
    return BatteryUnit(
        unit_id,
        "lot-a",
        10.0,
        10_000.0,
        10_000.0,
        T0,
    )


def make_two_site_fleet() -> Fleet:
    return Fleet(
        [
            Installation("i1", 30.0, -97.0, T0, [make_unit("u1")]),
            Installation(
                "i2",
                31.0,
                -98.0,
                T0,
                [make_unit("u2"), make_unit("u3")],
            ),
        ]
    )


def test_ninety_six_prices():
    assert len(market_day_prices()) == 96


def test_night_is_cheap():
    prices = market_day_prices()
    night = prices[0:24]
    assert all(price < -50.0 for price in night)


def test_afternoon_spikes():
    prices = market_day_prices()
    afternoon = prices[56:68]
    assert max(afternoon) > 150.0


def test_market_from_formula_has_the_curve_and_step_length():
    market = Market.from_formula()
    prices = market_day_prices()
    assert len(market) == 96
    assert market.dt_seconds == 900.0
    assert market.price_at(0) == prices[0]
    assert market.price_at(64) == prices[64]


def test_market_from_prices_keeps_the_list():
    market = Market.from_prices([-80.0, 20.0, 200.0], 900.0)
    assert len(market) == 3
    assert market.price_at(1) == 20.0
    assert market.dt_seconds == 900.0


def test_run_market_day_accepts_a_market():
    fleet = make_two_site_fleet()
    market = Market.from_prices([-80.0, 20.0, 200.0], DT)
    records = run_market_day(fleet, market, [], 99, 99)
    assert len(records) == 3
    assert records[0].score is not None
    assert records[0].score.price_usd_per_megawatt_hour == -80.0


def test_idle_tick_has_no_ancillary():
    fleet = make_two_site_fleet()
    market = Market.from_prices([-80.0, 20.0, 200.0], DT)
    records = run_market_day(
        fleet,
        market,
        [],
        99,
        99,
    )

    idle = records[1]
    assert idle.score is not None
    assert idle.score.ancillary_revenue_usd == 0.0


def test_run_market_day_marks_offline(tmp_path):
    fleet = make_two_site_fleet()
    market = Market.from_prices([20.0, 200.0, 20.0], DT)
    records = run_market_day(
        fleet,
        market,
        ["u1"],
        1,
        2,
    )

    assert records[1].n_unreachable == 1

    write_run("r1", fleet, records, DT, runs_dir=tmp_path)
    data = read_run("r1", runs_dir=tmp_path)
    flips = [
        event
        for event in data["commands"]
        if event["kind"] in ("offline", "online")
    ]
    assert [(event["kind"], event["unit_id"]) for event in flips] == [
        ("offline", "u1"),
        ("online", "u1"),
    ]
