import math
from dataclasses import dataclass

N_TICKS = 96
DEFAULT_DT_SECONDS = 900.0


@dataclass(frozen=True)
class Market:
    """
    Wholesale prices for a run. The home rate is not here.
    """
    prices: tuple[float, ...]
    dt_seconds: float

    def __len__(self) -> int:
        return len(self.prices)

    def price_at(self, index: int) -> float:
        return self.prices[index]

    @classmethod
    def from_formula(cls, dt_seconds: float = DEFAULT_DT_SECONDS) -> "Market":
        return cls(tuple(market_day_prices()), dt_seconds)

    @classmethod
    def from_prices(
        cls,
        prices: list[float],
        dt_seconds: float,
    ) -> "Market":
        if dt_seconds <= 0:
            raise ValueError("dt_seconds must be positive.")
        if not prices:
            raise ValueError("prices must not be empty.")
        return cls(tuple(prices), dt_seconds)


def market_day_prices() -> list[float]:
    """
    96 quarter-hour prices. Cheap night, afternoon spike,
    evening settle. ERCOT-summer-ish, formula not a file.
    """
    return [_price_at_tick(i) for i in range(N_TICKS)]


def _price_at_tick(index: int) -> float:
    hour = index / 4.0
    return (
        15.0
        - 105.0 * math.exp(-((hour - 3.0) / 5.0) ** 2)
        + 155.0 * math.exp(-((hour - 16.0) / 1.5) ** 2)
    )
