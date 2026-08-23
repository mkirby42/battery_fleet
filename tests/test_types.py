from battery_fleet.types import PriceRow


def test_spp_is_sum_of_parts():
    row = PriceRow(t_s=0, energy=30.0, scarcity=100.0, congestion=5.0, losses=1.0)
    assert row.spp == 136.0
