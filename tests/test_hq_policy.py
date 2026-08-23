from battery_fleet.hq_policy import hq_asked_kw
from battery_fleet.types import HqPolicy, Unit

U = Unit("u1", 10.0, 4.0, 5.0)
P = HqPolicy("hq", charge_below=20.0, discharge_above=80.0)


def test_discharge_when_spp_high():
    assert hq_asked_kw(U, P, spp=100.0, link_up=True, islanded=False) == 5.0


def test_charge_when_spp_low():
    assert hq_asked_kw(U, P, spp=10.0, link_up=True, islanded=False) == -4.0


def test_hold_in_band():
    assert hq_asked_kw(U, P, spp=50.0, link_up=True, islanded=False) == 0.0


def test_silent_or_islanded_asks_nothing():
    assert hq_asked_kw(U, P, spp=100.0, link_up=False, islanded=False) is None
    assert hq_asked_kw(U, P, spp=100.0, link_up=True, islanded=True) is None
