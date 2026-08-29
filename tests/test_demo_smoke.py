from pathlib import Path

from battery_fleet.scenario import load_scenario


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy)


def test_demo_scenarios_load():
    for name in ("fixed_20.yaml", "aggressive.yaml"):
        w = load_scenario(Path("scenarios") / name)
        assert len(w.locations) == 60
        assert any(s.id == "s0" for s in w.substations)


def test_demo_sites_are_two_clusters_not_a_line():
    w = load_scenario(Path("scenarios") / "fixed_20.yaml")
    lats = [loc.lat for loc in w.locations]
    lons = [loc.lon for loc in w.locations]
    for i, loc in enumerate(w.locations):
        assert 30.13 <= loc.lat <= 30.50
        assert -97.90 <= loc.lon <= -97.52
        assert loc.substation_id == f"s{i % 4}"
    assert len(set(lats)) > 2
    assert len(set(lons)) > 2
    assert abs(_pearson(lats, lons)) < 0.95

    c0 = [loc for loc in w.locations if w.city_of[loc.id] == "c0"]
    c1 = [loc for loc in w.locations if w.city_of[loc.id] == "c1"]
    assert c0 and c1
    mean0 = (
        sum(loc.lat for loc in c0) / len(c0),
        sum(loc.lon for loc in c0) / len(c0),
    )
    mean1 = (
        sum(loc.lat for loc in c1) / len(c1),
        sum(loc.lon for loc in c1) / len(c1),
    )
    dist = ((mean0[0] - mean1[0]) ** 2 + (mean0[1] - mean1[1]) ** 2) ** 0.5
    assert dist > 0.15


def test_demo_is_three_days_with_day2_event():
    w = load_scenario(Path("scenarios") / "fixed_20.yaml")
    assert w.duration_s == 3 * 86400
    assert 86400 <= w.event.scarcity_start_s < 2 * 86400
    kws = [row.kw for row in w.loads if row.t_s == 0]
    assert len(set(round(k, 6) for k in kws)) > 10


def test_demo_start_soc_lets_floor_bind():
    for name in ("fixed_20.yaml", "aggressive.yaml"):
        w = load_scenario(Path("scenarios") / name)
        assert w.start_soc_frac == 0.25
        assert all(u.capacity_kwh == 10.0 for u in w.units)
        assert all(u.max_discharge_kw == 5.0 for u in w.units)
        scarcity_s = w.event.scarcity_end_s - w.event.scarcity_start_s
        assert scarcity_s == 600
        leftover = 0.25 * 10.0 - 5.0 * (scarcity_s / 3600.0)
        if w.local_policy.kind == "fixed_reserve":
            assert leftover < 0.2 * 10.0
        else:
            assert leftover > 0.0
