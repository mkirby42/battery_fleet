import pytest

from battery_fleet import BatteryUnit, Installation
from battery_fleet.demo import run_lookahead_day, run_market_day
from battery_fleet.fleet import Fleet
from battery_fleet.lookahead import commands_for_targets, plan_fleet, plan_house
from battery_fleet.prices import Market

T0 = 1_700_000_000.0
LOAD = 1_500.0


def make_unit(unit_id: str) -> BatteryUnit:
    return BatteryUnit(
        unit_id,
        "lot-a",
        10.0,
        10_000.0,
        10_000.0,
        T0,
    )


def test_lookahead_charges_the_cheapest_hours():
    market = Market.from_formula()
    plan = plan_house(1, market, LOAD)
    charge = [index for index, watts in enumerate(plan) if watts > 1.0]
    assert charge
    charge_prices = [market.price_at(index) for index in charge]
    cheapest = sorted(market.prices)[: len(charge)]
    assert sorted(charge_prices) == pytest.approx(cheapest)


def test_lookahead_discharges_at_the_peak():
    market = Market.from_formula()
    plan = plan_house(1, market, LOAD)
    peak = max(range(len(market)), key=market.price_at)
    dump = [index for index, watts in enumerate(plan) if watts < -1.0]
    assert peak in dump
    assert min(dump) >= peak - 2


def test_two_battery_house_dumps_twice_the_power_at_the_peak():
    market = Market.from_formula()
    one = plan_house(1, market, LOAD)
    two = plan_house(2, market, LOAD)
    peak = max(range(len(market)), key=market.price_at)
    assert two[peak] == pytest.approx(2 * one[peak])


def test_plan_fleet_uses_house_types():
    fleet = Fleet(
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
    market = Market.from_formula()
    loads = {"i1": LOAD, "i2": LOAD}
    schedules = plan_fleet(fleet, market, loads)
    peak = max(range(len(market)), key=market.price_at)
    assert len(schedules) == 96
    assert schedules[peak]["i1"] == pytest.approx(-10_000.0)
    assert schedules[peak]["i2"] == pytest.approx(-20_000.0)


def test_commands_split_targets_using_current_reachability():
    fleet = Fleet(
        [
            Installation(
                "i1",
                30.0,
                -97.0,
                T0,
                [make_unit("u1"), make_unit("u2")],
            ),
        ]
    )
    fleet.installations[0].batteries[0].go_offline()

    commands = commands_for_targets(fleet, {"i1": -20_000.0}, 900.0)

    assert "u1" not in commands
    assert commands["u2"] == pytest.approx(-10_000.0)


def test_lookahead_day_locks_targets_before_a_unit_goes_offline():
    fleet = Fleet(
        [
            Installation(
                "i1",
                30.0,
                -97.0,
                T0,
                [make_unit("u1"), make_unit("u2")],
            ),
        ]
    )
    market = Market.from_prices([20.0, 200.0], 900.0)

    records = run_lookahead_day(
        fleet,
        market,
        ["u1"],
        offline_tick=1,
        online_tick=99,
    )

    assert len(records) == 2
    assert records[1].n_unreachable == 1
    assert records[1].fleet_target_power_watts == pytest.approx(-20_000.0)
    assert records[1].fleet_actual_power_watts == pytest.approx(-10_000.0)


def test_lookahead_beats_greedy_on_the_formula_day():
    market = Market.from_formula()
    greedy_fleet = Fleet(
        [Installation("i1", 30.0, -97.0, T0, [make_unit("g1")])]
    )
    lookahead_fleet = Fleet(
        [Installation("i1", 30.0, -97.0, T0, [make_unit("l1")])]
    )

    greedy_records = run_market_day(
        greedy_fleet,
        market,
        [],
        999,
        999,
        ancillary_revenue_usd=0.0,
    )
    lookahead_records = run_lookahead_day(
        lookahead_fleet,
        market,
        [],
        999,
        999,
        ancillary_revenue_usd=0.0,
    )

    greedy_profit = sum(record.score.score_usd for record in greedy_records)
    lookahead_profit = sum(
        record.score.score_usd for record in lookahead_records
    )
    assert lookahead_profit > greedy_profit
