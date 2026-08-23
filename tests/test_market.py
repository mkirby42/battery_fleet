# tests/test_market.py
import pytest
from battery_fleet.market import price_at, settle_interval, write_prices
from battery_fleet.types import Interval, MarketEvent, PriceRow, Tick

EV = MarketEvent(
    id="e1", settlement_point="HB_NORTH", kind="hot_evening_scarcity",
    scarcity_start_s=300, scarcity_end_s=600, scarcity_adder=2000.0,
    congestion_start_s=0, congestion_end_s=0, congestion_adder=0.0,
)


def test_scarcity_window_adds():
    rows = write_prices(EV, duration_s=900, base_energy=30.0, losses=1.0)
    by_t = {r.t_s: r for r in rows}
    assert by_t[0].scarcity == 0.0
    assert by_t[0].spp == 31.0
    assert by_t[300].scarcity == 2000.0
    assert by_t[300].spp == 2031.0


def test_settle_export_earns():
    ticks = [
        Tick(t_s=t, unit_id="u1", energy_kwh=10.0, power_kw=5.0, who_decided="hq",
             hq_asked_kw=5.0, shortfall_kwh=0.0, islanded=False, link_up=True)
        for t in range(0, 300, 15)
    ]
    price = PriceRow(0, energy=40.0, scarcity=0.0, congestion=0.0, losses=0.0)
    iv = settle_interval(0, ticks, price)
    assert iv.energy_mwh == pytest.approx(5.0 * 300 / 3600 / 1000)
    assert iv.pnl_usd == pytest.approx(iv.energy_mwh * 40.0)
    assert iv.spp == 40.0


def test_islanded_ticks_do_not_settle():
    ticks = [
        Tick(0, "u1", 10.0, 5.0, "local", None, 0.0, True, True)
    ]
    price = PriceRow(0, 40.0, 0.0, 0.0, 0.0)
    iv = settle_interval(0, ticks, price)
    assert iv.energy_mwh == 0.0
    assert iv.pnl_usd == 0.0
