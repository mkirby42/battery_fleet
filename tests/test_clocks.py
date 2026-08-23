from battery_fleet.clocks import INTERVAL_S, TICK_S, interval_start, ticks_in_interval


def test_constants():
    assert TICK_S == 15
    assert INTERVAL_S == 300


def test_interval_start_aligns_down():
    assert interval_start(0) == 0
    assert interval_start(14) == 0
    assert interval_start(300) == 300
    assert interval_start(314) == 300


def test_ticks_in_interval():
    assert ticks_in_interval(300) == 20
