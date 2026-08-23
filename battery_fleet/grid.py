from battery_fleet.types import City, LinkWindow, Location, Outage, Region, Substation


def location_islanded(
    loc: Location,
    outages: list[Outage],
    t_s: int,
    substations: list[Substation],
    cities: list[City],
    regions: list[Region],
) -> bool:
    sub = next(s for s in substations if s.id == loc.substation_id)
    city = next(c for c in cities if c.id == sub.city_id)
    for o in outages:
        if not (o.start_s <= t_s < o.end_s):
            continue
        if o.node_kind == "substation" and o.node_id == sub.id:
            return True
        if o.node_kind == "city" and o.node_id == city.id:
            return True
        if o.node_kind == "region" and o.node_id == city.region_id:
            return True
    return False


def link_up(location_id: str, windows: list[LinkWindow], t_s: int) -> bool:
    for w in windows:
        if w.location_id == location_id and w.start_s <= t_s < w.end_s:
            return False
    return True
