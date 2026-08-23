from battery_fleet.grid import link_up, location_islanded
from battery_fleet.types import City, LinkWindow, Location, Outage, Region, Substation

REG = Region("r1", "north")
CITY = City("c1", "Dallas", "r1")
SUB = Substation("s1", "oak", "c1")
LOC = Location("l1", 32.8, -96.8, "s1")


def test_substation_outage_hits_child():
    out = Outage(100, 200, "substation", "s1")
    assert location_islanded(LOC, [out], 150, [SUB], [CITY], [REG]) is True
    assert location_islanded(LOC, [out], 50, [SUB], [CITY], [REG]) is False


def test_city_outage_hits_nested_substation():
    out = Outage(0, 10, "city", "c1")
    assert location_islanded(LOC, [out], 5, [SUB], [CITY], [REG]) is True


def test_region_outage_hits_nested_location():
    out = Outage(0, 10, "region", "r1")
    assert location_islanded(LOC, [out], 5, [SUB], [CITY], [REG]) is True
    assert location_islanded(LOC, [out], 10, [SUB], [CITY], [REG]) is False


def test_other_substation_misses():
    out = Outage(0, 10, "substation", "other")
    assert location_islanded(LOC, [out], 5, [SUB], [CITY], [REG]) is False


def test_link_up_empty_plan():
    assert link_up("l1", [], 100) is True


def test_link_up_covering_window():
    window = LinkWindow(50, 150, "l1")
    assert link_up("l1", [window], 100) is False
    assert link_up("l1", [window], 50) is False
    assert link_up("l1", [window], 149) is False
    assert link_up("l1", [window], 150) is True
