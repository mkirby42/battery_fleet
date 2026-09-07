## Minimal loop

```
.venv/bin/python scripts/minimal_loop.py
```

Three ticks of 900 seconds. First tick charges at 2000 W. Second tick sends no command, so that charge holds. Third tick discharges at 3000 W. The table columns are time, house load, grid power, battery power, and state of charge.

## Fleet

```
.venv/bin/python scripts/minimal_fleet.py
```

Builds 80 sites and 100 identical 10 kWh units with seed 1. Houses sit in city-of-Austin neighborhoods (downtown through Domain / Oak Hill), not the suburbs. Prints site count, unit count, then one line per site: id, lat, lon, and the unit ids at that house.

## Fleet loop

```
.venv/bin/python scripts/minimal_fleet_loop.py
```

Same 80/100 fleet. Three ticks of 900 seconds. Every house load is 1500 W. First tick charges every unit at 2000 W. Second tick sends no command, so that charge holds. Third tick discharges every unit at 3000 W. The table is fleet totals: time, actual fleet power, commanded fleet power, house load, unit count, unreachable count. Per-site rows live on each record as `site_records` if you need them.

## Splitter

```
.venv/bin/python scripts/minimal_splitter.py
```

Same 80/100 fleet. Each tick a target is split evenly across units that can receive a command, then `run_fleet` delivers that map. Targets are 100000 W, 100000 W, then -150000 W. The table adds target and tracking error (commanded minus actual).

## Allocate

```
.venv/bin/python scripts/minimal_allocate.py
```

Same 80/100 fleet. Each tick `allocate_target` splits a fleet target without asking any unit for more than it can do this step. Targets are 100000 W (fits), 2000000 W (clips at 1 MW, every unit at 10 kW), then -150000 W. Tracking error should stay near zero. The leftover versus a huge target is the target miss, not a physics miss.

## Dispatch

```
.venv/bin/python scripts/minimal_dispatch.py
```

Same 80/100 fleet. Each tick `greedy` picks charge, idle, cover-the-house, or full discharge from a fake wholesale price. Prices are -80, 20, then 200 dollars per megawatt-hour. It picks per house using company profit. The score keeps company profit, customer bill, wholesale settlement, wear, and missed delivery. `solve_dispatch` remains as the old name for the same function.

## Locked look-ahead

`Market.from_formula()` creates the made-up 96-step wholesale day. `plan_fleet(fleet, market, loads)` sees the whole day and returns one locked house-target map per step. It plans one-battery and two-battery houses separately. `commands_for_targets` splits the target for the current step across batteries that are reachable and physically able to act.

`run_lookahead_day` plans once before the first step, then runs the complete day. It does not re-plan after an outage. Tests compare it with greedy:

```
.venv/bin/pytest tests/test_lookahead.py -q
```

## Controller comparison

```
.venv/bin/python scripts/compare_controllers.py
```

Builds independent greedy and locked look-ahead fleets from the same seed, then runs both against the same 96-step market and outage schedule. It prints the shared comparison id and both run directories.

The generated layout is:

```
runs/
  comparisons/<comparison-id>.json
  <comparison-id>-greedy/
    run.json
    installation_ticks.jsonl
    unit_ticks.jsonl
  <comparison-id>-lookahead/
    run.json
    installation_ticks.jsonl
    unit_ticks.jsonl
```

Each `run.json` holds metadata, static fleet data, fleet-level ticks, and command events. The JSONL files hold one row per installation per tick and one row per unit per tick.

The file under `runs/comparisons/` is the completion manifest. It appears atomically only after both run directories are complete. `list_completed_comparisons()` reads these manifests, verifies both runs, and ignores orphan run directories, malformed manifests, and manifests whose runs are missing.

## Controller analysis notebook

Generate a fresh matched comparison:

```
.venv/bin/python scripts/compare_controllers.py
```

Install the optional notebook environment:

```
.venv/bin/pip install -e ".[analysis]"
```

Launch JupyterLab:

```
.venv/bin/jupyter lab analysis/controller_analysis.ipynb
```

Execute the notebook in place and retain its outputs:

```
.venv/bin/jupyter nbconvert --to notebook --execute --inplace analysis/controller_analysis.ipynb --ExecutePreprocessor.timeout=300
```

The notebook selects the newest completed comparison by default. Set `COMPARISON_ID` in its configuration cell to use a specific completion manifest.

## Dashboard

```
.venv/bin/python scripts/demo_market_day.py
.venv/bin/python -m battery_fleet serve
cd dashboard && npm install && npm run dev
```

`demo_market_day.py` writes `runs/<id>/run.json` (gitignored). Serve is `:8000`. Vite proxies `/api` to that port.

## Tests

From the repo root, with the existing venv:

```
.venv/bin/pytest
```

`testpaths` is already `tests`, so you do not need to pass a folder.

```
.venv/bin/pytest -q
```

`-q` prints one line per test instead of the full header.

```
.venv/bin/pytest tests/test_physics.py
```

Run one file.

```
.venv/bin/pytest -k charge
```

`-k` keeps tests whose names match the expression. Here that is `test_charge_stops_when_full`.

```
.venv/bin/pytest -x
```

`-x` stops on the first failure.

```
.venv/bin/pytest -vv
```

`-vv` prints the full assert values when something fails.
