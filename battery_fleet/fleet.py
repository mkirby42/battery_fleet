from dataclasses import dataclass
from random import Random

from battery_fleet.battery import BatteryUnit
from battery_fleet.installation import Installation

NOMINAL_CAPACITY_KILOWATT_HOURS = 10.0
NOMINAL_MAX_POWER_WATTS = 10_000.0
# City-of-Austin neighborhoods only. Suburbs pull the map frame too wide.
AUSTIN_NEIGHBORHOODS = (
    (30.2672, -97.7431),  # downtown
    (30.3060, -97.7300),  # hyde park
    (30.2570, -97.7220),  # east cesar chavez
    (30.2960, -97.7030),  # mueller
    (30.2450, -97.7500),  # south congress
    (30.2660, -97.7730),  # zilker
    (30.2560, -97.7840),  # barton hills
    (30.2480, -97.8520),  # oak hill east
    (30.2810, -97.8070),  # westlake
    (30.2970, -97.7670),  # tarrytown
    (30.3420, -97.7260),  # crestview
    (30.2840, -97.7150),  # cherrywood
    (30.3120, -97.6900),  # windsor park
    (30.2300, -97.6900),  # montopolis
    (30.2440, -97.7390),  # travis heights
    (30.2470, -97.7550),  # bouldin
    (30.2790, -97.7600),  # clarksville
    (30.3400, -97.7450),  # allandale
    (30.3310, -97.7350),  # brentwood
    (30.3920, -97.7260),  # domain
    (30.2280, -97.8150),  # sunset valley
    (30.2100, -97.7390),  # dove springs
    (30.3190, -97.7240),  # north loop
    (30.3120, -97.7470),  # rosedale
)
AUSTIN_LATITUDE_DEGREES = (30.19, 30.41)
AUSTIN_LONGITUDE_DEGREES = (-97.88, -97.66)
NEIGHBORHOOD_JITTER_DEGREES = 0.012
MIN_SITE_SEPARATION_DEGREES = 0.003
MAX_PLACEMENT_RETRIES = 80


@dataclass
class Fleet:
    installations: list[Installation]


def build_fleet(
    n_sites: int,
    n_units: int,
    initial_time_unix: float,
    seed: int,
) -> Fleet:
    if n_sites <= 0:
        raise ValueError("n_sites must be positive.")
    if n_units < n_sites:
        raise ValueError(
            "Need at least one unit per site."
        )

    rng = Random(seed)
    units_per_site = _units_per_site(n_sites, n_units, rng)

    installations = []
    placed: list[tuple[float, float]] = []
    next_unit = 1
    for site_number, unit_count in enumerate(units_per_site, start=1):
        latitude, longitude = _draw_site(rng, placed)
        placed.append((latitude, longitude))
        batteries = []
        for _ in range(unit_count):
            batteries.append(
                BatteryUnit(
                    f"u{next_unit:03d}",
                    "lot-a",
                    NOMINAL_CAPACITY_KILOWATT_HOURS,
                    NOMINAL_MAX_POWER_WATTS,
                    NOMINAL_MAX_POWER_WATTS,
                    initial_time_unix,
                )
            )
            next_unit += 1

        installations.append(
            Installation(
                f"i{site_number:03d}",
                latitude,
                longitude,
                initial_time_unix,
                batteries,
            )
        )

    return Fleet(installations)


def _draw_site(
    rng: Random,
    placed: list[tuple[float, float]],
) -> tuple[float, float]:
    latitude = 0.0
    longitude = 0.0
    for _ in range(MAX_PLACEMENT_RETRIES):
        lat0, lon0 = rng.choice(AUSTIN_NEIGHBORHOODS)
        latitude = lat0 + rng.uniform(
            -NEIGHBORHOOD_JITTER_DEGREES,
            NEIGHBORHOOD_JITTER_DEGREES,
        )
        longitude = lon0 + rng.uniform(
            -NEIGHBORHOOD_JITTER_DEGREES,
            NEIGHBORHOOD_JITTER_DEGREES,
        )
        latitude = min(
            AUSTIN_LATITUDE_DEGREES[1],
            max(AUSTIN_LATITUDE_DEGREES[0], latitude),
        )
        longitude = min(
            AUSTIN_LONGITUDE_DEGREES[1],
            max(AUSTIN_LONGITUDE_DEGREES[0], longitude),
        )
        if not _too_close(latitude, longitude, placed):
            break
    return latitude, longitude


def _too_close(
    latitude: float,
    longitude: float,
    placed: list[tuple[float, float]],
) -> bool:
    for other_lat, other_lon in placed:
        gap = (
            (latitude - other_lat) ** 2 + (longitude - other_lon) ** 2
        ) ** 0.5
        if gap < MIN_SITE_SEPARATION_DEGREES:
            return True
    return False


def _units_per_site(
    n_sites: int,
    n_units: int,
    rng: Random,
) -> list[int]:
    counts = [1] * n_sites
    remaining = n_units - n_sites
    while remaining > 0:
        order = list(range(n_sites))
        rng.shuffle(order)
        for site_index in order:
            if remaining == 0:
                break
            counts[site_index] += 1
            remaining -= 1
    return counts
