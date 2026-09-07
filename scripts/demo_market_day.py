import time
from datetime import datetime, timezone

from battery_fleet.demo import run_market_day
from battery_fleet.fleet import build_fleet
from battery_fleet.prices import Market
from battery_fleet.store import write_run

t0 = datetime(2024, 8, 15, tzinfo=timezone.utc).timestamp()
fleet = build_fleet(80, 100, t0, 1)
ids = [
    battery.unit_id
    for site in fleet.installations
    for battery in site.batteries
][:5]
records = run_market_day(
    fleet,
    Market.from_formula(),
    ids,
    60,
    68,
)
run_id = time.strftime("%Y%m%d-%H%M%S")
path = write_run(run_id, fleet, records, 900)
print(run_id)
print(path)
