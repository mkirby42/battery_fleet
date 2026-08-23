from battery_fleet.clocks import INTERVAL_S, TICK_S, interval_start
from battery_fleet.types import Interval, MarketEvent, PriceRow, Tick


def write_prices(
    event: MarketEvent,
    duration_s: int,
    base_energy: float,
    losses: float,
) -> list[PriceRow]:
    rows: list[PriceRow] = []
    for t in range(0, duration_s, INTERVAL_S):
        if event.scarcity_start_s <= t < event.scarcity_end_s:
            scarcity = event.scarcity_adder
        else:
            scarcity = 0.0
        if event.congestion_end_s != 0 and event.congestion_start_s <= t < event.congestion_end_s:
            congestion = event.congestion_adder
        else:
            congestion = 0.0
        rows.append(
            PriceRow(
                t_s=t,
                energy=base_energy,
                scarcity=scarcity,
                congestion=congestion,
                losses=losses,
            )
        )
    return rows


def price_at(prices: list[PriceRow], t_s: int) -> PriceRow:
    start = interval_start(t_s)
    for row in prices:
        if row.t_s == start:
            return row
    raise KeyError(f"no price row at t_s={start}")


def settle_interval(t_s: int, ticks: list[Tick], price: PriceRow) -> Interval:
    energy_mwh = sum(
        tick.power_kw * TICK_S / 3600 / 1000
        for tick in ticks
        if not tick.islanded
    )
    pnl_usd = energy_mwh * price.spp
    return Interval(
        t_s=t_s,
        energy_mwh=energy_mwh,
        pnl_usd=pnl_usd,
        energy=price.energy,
        scarcity=price.scarcity,
        congestion=price.congestion,
        losses=price.losses,
        spp=price.spp,
    )
