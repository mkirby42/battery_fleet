# Sim Backbone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the sim backbone in the 2026-08-23 spec: types → `run.db` → two comparable runs → one-run dashboard → compare notebook.

**Architecture:** One Python package. Types are the law. A run is a folder with one SQLite file. The runner snapshots world pieces in, steps 15 s ticks, settles 5-min SPP parts, writes checks, and rebuilds `runs/index.json` by scanning folders. Dashboard reads one `run.db`. Notebook compares two.

**Tech Stack:** Python 3.11+, stdlib sqlite3, PyYAML, pytest. Dashboard: small local HTTP server + static HTML/JS. Notebook: thin wrapper around `battery_fleet.compare`.

**Spec:** `docs/superpowers/specs/2026-08-23-sim-backbone-design.md`

---

## File map

| Path | Job |
|---|---|
| `pyproject.toml` | Package + pytest |
| `.gitignore` | `runs/*`, venv, pyc |
| `battery_fleet/__init__.py` | Empty |
| `battery_fleet/__main__.py` | `cli.main()` |
| `battery_fleet/clocks.py` | 15 s ↔ 5 min |
| `battery_fleet/types.py` | Dataclasses |
| `battery_fleet/schema.py` | `CREATE TABLE` |
| `battery_fleet/grid.py` | Outage covers location? |
| `battery_fleet/physics.py` | Clamp + efficiency |
| `battery_fleet/local_policy.py` | Floor + islanded house |
| `battery_fleet/hq_policy.py` | Price chase |
| `battery_fleet/market.py` | Event → price parts; settle |
| `battery_fleet/load.py` | Weather + TOD → 5-min kW |
| `battery_fleet/loop.py` | One tick; run to completion in memory |
| `battery_fleet/checks.py` | v1 checklist + scoreboard |
| `battery_fleet/store.py` | Open/write `run.db` |
| `battery_fleet/index.py` | Scan folders → `index.json` |
| `battery_fleet/scenario.py` | YAML → world pieces |
| `battery_fleet/cli.py` | `run`, `serve` |
| `battery_fleet/serve.py` | HTTP + JSON for dashboard |
| `scenarios/tiny.yaml` | 3 locations, 1 hour (tests + smoke) |
| `scenarios/fixed_20.yaml` | Demo A |
| `scenarios/aggressive.yaml` | Demo B (same world, different floor) |
| `dashboard/index.html` | Map + charts + scrub |
| `dashboard/app.js` | Reads `/api/...` |
| `dashboard/style.css` | Look |
| `analysis/compare.py` | Comparable pair → tables |
| `analysis/compare.ipynb` | Calls `compare.py` |
| `tests/` | pytest |

Constants used everywhere: `TICK_S = 15`, `INTERVAL_S = 300`, `SCHEMA_VERSION = 1`. Discharge power is positive.

If any file crosses ~250 lines, split it before the next task.

---

### Task 1: Package, clocks

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `battery_fleet/__init__.py`
- Create: `battery_fleet/clocks.py`
- Test: `tests/test_clocks.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_clocks.py
from battery_fleet.clocks import INTERVAL_S, TICK_S, interval_start, ticks_in_interval


def test_constants():
    assert TICK_S == 15
    assert INTERVAL_S == 300


def test_interval_start_aligns_down():
    assert interval_start(0) == 0
    assert interval_start(14) == 0
    assert interval_start(300) == 300
    assert interval_start(314) == 300


def test_ticks_in_interval():
    assert ticks_in_interval(300) == 20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_clocks.py -v`  
Expected: FAIL — `battery_fleet` not installed / module missing.

- [ ] **Step 3: Write minimal implementation**

```toml
# pyproject.toml
[project]
name = "battery-fleet"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["pyyaml"]

[project.optional-dependencies]
dev = ["pytest"]

[project.scripts]
battery-fleet = "battery_fleet.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["battery_fleet*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```
# .gitignore
.venv/
__pycache__/
*.pyc
*.egg-info/
runs/*
!runs/.gitkeep
.pytest_cache/
```

`battery_fleet/__init__.py` empty.

```python
# battery_fleet/clocks.py
TICK_S = 15
INTERVAL_S = 300
SCHEMA_VERSION = 1


def interval_start(t_s: int) -> int:
    return (t_s // INTERVAL_S) * INTERVAL_S


def ticks_in_interval(interval_s: int = INTERVAL_S) -> int:
    return interval_s // TICK_S
```

Also create `runs/.gitkeep`.

Run: `pip install -e ".[dev]"`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_clocks.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore battery_fleet/__init__.py battery_fleet/clocks.py tests/test_clocks.py runs/.gitkeep
git commit -m "Add package skeleton and 15s / 5min clocks."
```

---

### Task 2: Types

**Files:**
- Create: `battery_fleet/types.py`
- Test: `tests/test_types.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_types.py
from battery_fleet.types import PriceRow


def test_spp_is_sum_of_parts():
    row = PriceRow(t_s=0, energy=30.0, scarcity=100.0, congestion=5.0, losses=1.0)
    assert row.spp == 136.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_types.py -v`  
Expected: FAIL — `types` missing.

- [ ] **Step 3: Write minimal implementation**

Put these dataclasses in `battery_fleet/types.py` (stdlib `dataclasses` + `Literal` only):

- `Region(id, name)`
- `City(id, name, region_id)`
- `Substation(id, name, city_id)`
- `Location(id, lat, lon, substation_id)`
- `Unit(id, capacity_kwh, max_charge_kw, max_discharge_kw)`
- `Install(unit_id, location_id)`
- `BatteryModel(id, efficiency)`  # one-way, 0–1
- `MarketModel(id)`
- `LocalPolicy(id, kind: Literal["fixed_reserve","aggressive"], floor_frac)`
- `HqPolicy(id, charge_below, discharge_above)`  # $/MWh
- `PriceRow(t_s, energy, scarcity, congestion, losses)` with `@property spp`
- `MarketEvent(id, settlement_point, kind, scarcity_start_s, scarcity_end_s, scarcity_adder, congestion_start_s, congestion_end_s, congestion_adder)`
- `WeatherRow(t_s, city_id, temp_c)`
- `LoadRow(location_id, t_s, kw)`
- `Outage(start_s, end_s, node_kind: Literal["substation","city","region"], node_id)`
- `LinkWindow(start_s, end_s, location_id)`
- `Tick(t_s, unit_id, energy_kwh, power_kw, who_decided: Literal["local","hq"], hq_asked_kw: float | None, shortfall_kwh, islanded, link_up)`
- `Event(t_s, kind, unit_id: str | None, location_id: str | None, detail)`
- `Interval(t_s, energy_mwh, pnl_usd, energy, scarcity, congestion, losses, spp)`
- `Check(name, passed, detail)`
- `Scoreboard(revenue_usd, shortfall_kwh, coverage, locations_dark, time_at_floor_s)`
- `RunCard(id, seed, schema_version, status: Literal["running","success","failed"], error: str | None, local_policy_id, hq_policy_id, market_event_id, started_s: int | None, finished_s: int | None)`

All frozen dataclasses.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_types.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/types.py tests/test_types.py
git commit -m "Add frozen types; SPP is the sum of price parts."
```

---

### Task 3: Schema and empty store

**Files:**
- Create: `battery_fleet/schema.py`
- Create: `battery_fleet/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store.py
import sqlite3
from pathlib import Path

from battery_fleet.store import create_run_db


def test_create_run_db_has_run_table(tmp_path: Path):
    path = tmp_path / "run.db"
    create_run_db(path)
    con = sqlite3.connect(path)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()
    for needed in (
        "regions", "cities", "substations", "locations", "units", "installs",
        "market_event", "prices", "weather", "load_model", "loads", "outages",
        "link_plan", "battery_model", "market_model", "local_policy", "hq_policy",
        "run", "ticks", "events", "intervals", "checks", "scoreboard",
    ):
        assert needed in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_store.py -v`  
Expected: FAIL — `store` missing.

- [ ] **Step 3: Write minimal implementation**

`schema.py`: one string `DDL` with `CREATE TABLE` for every name in the test. Columns match `types.py` field names (snake_case). `prices` has energy, scarcity, congestion, losses (no stored spp). `run` has the `RunCard` fields. `ticks` includes `islanded` and `link_up` as integers 0/1.

`store.py`:

```python
import sqlite3
from pathlib import Path
from battery_fleet.schema import DDL


def create_run_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(DDL)
    con.commit()
    con.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_store.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/schema.py battery_fleet/store.py tests/test_store.py
git commit -m "Add run.db schema and empty-db create."
```

---

### Task 4: Grid containment

**Files:**
- Create: `battery_fleet/grid.py`
- Test: `tests/test_grid.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_grid.py
from battery_fleet.grid import location_islanded
from battery_fleet.types import City, Location, Outage, Region, Substation

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


def test_other_substation_misses():
    out = Outage(0, 10, "substation", "other")
    assert location_islanded(LOC, [out], 5, [SUB], [CITY], [REG]) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_grid.py -v`  
Expected: FAIL — `grid` missing.

- [ ] **Step 3: Write minimal implementation**

```python
# battery_fleet/grid.py
from battery_fleet.types import City, Location, Outage, Region, Substation


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
```

Also add `link_up(location_id, windows, t_s) -> bool`: True if no window covers this location at `t_s` (first runs: empty plan ⇒ always up). Cover with a 4-line test in the same file: empty plan True; covering window False.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_grid.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/grid.py tests/test_grid.py
git commit -m "Add outage containment and location link_up."
```

---

### Task 5: Physics

**Files:**
- Create: `battery_fleet/physics.py`
- Test: `tests/test_physics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_physics.py
from battery_fleet.clocks import TICK_S
from battery_fleet.physics import apply_setpoint


def test_discharge_reduces_energy():
    energy, power = apply_setpoint(
        energy_kwh=10.0, setpoint_kw=4.0, capacity_kwh=20.0,
        max_charge_kw=5.0, max_discharge_kw=5.0, floor_kwh=0.0,
        efficiency=1.0, dt_s=TICK_S,
    )
    assert power == 4.0
    assert energy == 10.0 - 4.0 * (15 / 3600)


def test_floor_blocks_market_discharge():
    energy, power = apply_setpoint(
        energy_kwh=2.0, setpoint_kw=10.0, capacity_kwh=10.0,
        max_charge_kw=5.0, max_discharge_kw=5.0, floor_kwh=2.0,
        efficiency=1.0, dt_s=TICK_S,
    )
    assert power == 0.0
    assert energy == 2.0


def test_charge_is_negative_power():
    energy, power = apply_setpoint(
        energy_kwh=1.0, setpoint_kw=-3.0, capacity_kwh=10.0,
        max_charge_kw=5.0, max_discharge_kw=5.0, floor_kwh=0.0,
        efficiency=1.0, dt_s=TICK_S,
    )
    assert power == -3.0
    assert energy == 1.0 + 3.0 * (15 / 3600)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_physics.py -v`  
Expected: FAIL — `physics` missing.

- [ ] **Step 3: Write minimal implementation**

`apply_setpoint(...)` → `(energy_kwh, power_kw)`:

- Clamp setpoint to `[-max_charge_kw, max_discharge_kw]`.
- Discharge (`>0`): cannot go below `floor_kwh`. Energy out = power * dt_h / efficiency? Use: energy delta for discharge = `-power * dt_h / efficiency` so inefficiency burns extra energy. Charge: `energy += -power * dt_h * efficiency` (power is negative). If `efficiency == 1`, the tests above hold. Implement so eta=1 matches tests; eta≠1 still conserves the sign.
- Clamp energy to `[floor_kwh, capacity_kwh]` for discharge-to-floor and charge-to-full; reduce `power` to match the energy that actually moved.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_physics.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/physics.py tests/test_physics.py
git commit -m "Add battery clamp: power, energy, reserve floor."
```

---

### Task 6: Local policy

**Files:**
- Create: `battery_fleet/local_policy.py`
- Test: `tests/test_local_policy.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_local_policy.py
from battery_fleet.local_policy import floor_kwh, local_setpoint
from battery_fleet.types import LocalPolicy, Unit


def test_fixed_reserve_floor():
    u = Unit("u1", capacity_kwh=10.0, max_charge_kw=5.0, max_discharge_kw=5.0)
    p = LocalPolicy("lp", "fixed_reserve", 0.2)
    assert floor_kwh(u, p) == 2.0


def test_aggressive_floor_is_zero():
    u = Unit("u1", 10.0, 5.0, 5.0)
    p = LocalPolicy("lp", "aggressive", 0.0)
    assert floor_kwh(u, p) == 0.0


def test_islanded_serves_load():
    # house wants 2 kW; battery must discharge 2 (local), not chase price
    kw = local_setpoint(islanded=True, location_load_kw=2.0, hq_asked_kw=8.0)
    assert kw == 2.0


def test_grid_tied_local_does_not_invent_setpoint():
    kw = local_setpoint(islanded=False, location_load_kw=2.0, hq_asked_kw=8.0)
    assert kw is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_local_policy.py -v`  
Expected: FAIL — missing module.

- [ ] **Step 3: Write minimal implementation**

```python
def floor_kwh(unit, policy) -> float:
    return unit.capacity_kwh * policy.floor_frac


def local_setpoint(islanded: bool, location_load_kw: float, hq_asked_kw: float | None) -> float | None:
    if islanded:
        return location_load_kw
    return None
```

When islanded, HQ is ignored. Floor is applied later in physics, not here. First scenarios: one unit per location, so the unit takes the whole location load.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_local_policy.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/local_policy.py tests/test_local_policy.py
git commit -m "Add local floor and islanded house setpoint."
```

---

### Task 7: HQ policy

**Files:**
- Create: `battery_fleet/hq_policy.py`
- Test: `tests/test_hq_policy.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hq_policy.py
from battery_fleet.hq_policy import hq_asked_kw
from battery_fleet.types import HqPolicy, Unit

U = Unit("u1", 10.0, 4.0, 5.0)
P = HqPolicy("hq", charge_below=20.0, discharge_above=80.0)


def test_discharge_when_spp_high():
    assert hq_asked_kw(U, P, spp=100.0, link_up=True, islanded=False) == 5.0


def test_charge_when_spp_low():
    assert hq_asked_kw(U, P, spp=10.0, link_up=True, islanded=False) == -4.0


def test_hold_in_band():
    assert hq_asked_kw(U, P, spp=50.0, link_up=True, islanded=False) == 0.0


def test_silent_or_islanded_asks_nothing():
    assert hq_asked_kw(U, P, spp=100.0, link_up=False, islanded=False) is None
    assert hq_asked_kw(U, P, spp=100.0, link_up=True, islanded=True) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hq_policy.py -v`  
Expected: FAIL — missing module.

- [ ] **Step 3: Write minimal implementation**

```python
def hq_asked_kw(unit, policy, spp, link_up, islanded) -> float | None:
    if not link_up or islanded:
        return None
    if spp >= policy.discharge_above:
        return unit.max_discharge_kw
    if spp <= policy.charge_below:
        return -unit.max_charge_kw
    return 0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_hq_policy.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/hq_policy.py tests/test_hq_policy.py
git commit -m "Add HQ price-chase; None when silent or islanded."
```

---

### Task 8: Market event and settlement

**Files:**
- Create: `battery_fleet/market.py`
- Test: `tests/test_market.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_market.py
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
    # 5 kW discharge for 300 s = 5 * 300/3600 = 0.41666 kWh = 0.00041666 MWh
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
```

Add `import pytest` at the top.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_market.py -v`  
Expected: FAIL — missing module.

- [ ] **Step 3: Write minimal implementation**

`write_prices(event, duration_s, base_energy, losses) -> list[PriceRow]`: one row per 300 s from 0 inclusive to `duration_s` exclusive. `energy = base_energy` (constant for v1; diurnal can wait). `scarcity = adder` if `scarcity_start_s <= t < scarcity_end_s` else 0. Same for congestion. `congestion_end_s == 0` means no window.

`settle_interval(t_s, ticks, price) -> Interval`: sum `power_kw * TICK_S/3600 / 1000` for ticks with `not islanded`. `pnl_usd = energy_mwh * price.spp`. Copy price parts onto the Interval.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_market.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/market.py tests/test_market.py
git commit -m "Add market event price parts and interval settlement."
```

---

### Task 9: Load series

**Files:**
- Create: `battery_fleet/load.py`
- Test: `tests/test_load.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_load.py
from battery_fleet.load import load_at, write_loads
from battery_fleet.types import Location, WeatherRow


def test_hot_afternoon_higher_than_cool_night():
    loc = Location("l1", 32.0, -97.0, "s1")
    weather = [
        WeatherRow(t_s=0, city_id="c1", temp_c=15.0),
        WeatherRow(t_s=3600 * 15, city_id="c1", temp_c=38.0),
    ]
    loads = write_loads([loc], weather, duration_s=3600 * 16, seed=1, city_of={"l1": "c1"})
    night = load_at(loads, "l1", 0)
    hot = load_at(loads, "l1", 3600 * 15)
    assert hot > night
    assert night > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_load.py -v`  
Expected: FAIL — missing module.

- [ ] **Step 3: Write minimal implementation**

5-min grain. For each location and each `t` in `0..duration_s step 300`:

```
hour = (t % 86400) / 3600
tod = 0.6 + 0.4 * max(0, 1 - abs(hour - 18) / 6)   # evening-ish
temp = weather row for that city at latest t_s <= t (or 20 C)
ac = 0.15 * max(0, temp - 22)
kw = 1.2 * (tod + ac)   # ~1–3 kW house
```

`load_at(loads, location_id, t_s)`: hold the 5-min row whose `t_s == interval_start(t_s)`.

`seed` is accepted and unused beyond a comment (reproducible formula, no RNG). Keep the argument so scenario seed is plumbed.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_load.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/load.py tests/test_load.py
git commit -m "Add 5-min location load from time of day and temperature."
```

---

### Task 10: One tick and a short loop

**Files:**
- Create: `battery_fleet/loop.py`
- Test: `tests/test_loop.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_loop.py
from battery_fleet.loop import step_unit
from battery_fleet.types import (
    BatteryModel, HqPolicy, LocalPolicy, Location, Tick, Unit,
)

U = Unit("u1", 10.0, 5.0, 5.0)
LOC = Location("l1", 32.0, -97.0, "s1")
BM = BatteryModel("b", 1.0)
LP = LocalPolicy("lp", "fixed_reserve", 0.2)
HQ = HqPolicy("hq", 20.0, 80.0)


def test_hq_discharges_when_linked_and_pricey():
    prev = Tick(0, "u1", 8.0, 0.0, "hq", 0.0, 0.0, False, True)
    tick = step_unit(
        t_s=15, prev=prev, unit=U, location=LOC, battery=BM,
        local=LP, hq=HQ, spp=120.0, location_load_kw=1.0,
        islanded=False, link_up=True,
    )
    assert tick.who_decided == "hq"
    assert tick.hq_asked_kw == 5.0
    assert tick.power_kw > 0
    assert tick.islanded is False
    assert tick.link_up is True


def test_islanded_is_local_and_records_shortfall_if_empty():
    prev = Tick(0, "u1", 0.0, 0.0, "local", None, 0.0, True, True)
    tick = step_unit(
        t_s=15, prev=prev, unit=U, location=LOC, battery=BM,
        local=LP, hq=HQ, spp=120.0, location_load_kw=2.0,
        islanded=True, link_up=True,
    )
    assert tick.who_decided == "local"
    assert tick.hq_asked_kw is None
    assert tick.shortfall_kwh > 0


def test_silent_reverts_to_local_hold():
    prev = Tick(0, "u1", 8.0, 5.0, "hq", 5.0, 0.0, False, True)
    tick = step_unit(
        t_s=15, prev=prev, unit=U, location=LOC, battery=BM,
        local=LP, hq=HQ, spp=120.0, location_load_kw=1.0,
        islanded=False, link_up=False,
    )
    assert tick.who_decided == "local"
    assert tick.hq_asked_kw is None
    assert tick.power_kw == 0.0  # no last-setpoint
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_loop.py -v`  
Expected: FAIL — missing module.

- [ ] **Step 3: Write minimal implementation**

`step_unit(...)` → `Tick`:

1. `asked = hq_asked_kw(...)`  # None if silent/islanded
2. `local_kw = local_setpoint(islanded, location_load_kw, asked)`
3. If `local_kw is not None`: setpoint = local_kw, who = `"local"`
   Else: setpoint = asked or 0.0, who = `"hq"`
4. `floor = floor_kwh(unit, local)` — always applied in physics
5. `energy, power = apply_setpoint(prev.energy_kwh, setpoint, ...)`
6. If islanded: desired_kwh = location_load_kw * dt_h; served = max(power, 0) * dt_h; shortfall = max(0, desired - served). If not islanded: shortfall = 0. Market setpoint is never used while islanded (already local).
7. Return Tick.

Do **not** hold `prev.power_kw` when silent.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_loop.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/loop.py tests/test_loop.py
git commit -m "Add one-unit tick: local default, HQ privilege, no last setpoint."
```

---

### Task 11: Checks and scoreboard

**Files:**
- Create: `battery_fleet/checks.py`
- Test: `tests/test_checks.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_checks.py
from battery_fleet.checks import run_checks
from battery_fleet.types import LocalPolicy, Tick, Unit

U = Unit("u1", 10.0, 5.0, 5.0)
LP = LocalPolicy("lp", "fixed_reserve", 0.2)


def test_soc_out_of_range_fails():
    ticks = [Tick(0, "u1", 99.0, 0.0, "local", None, 0.0, False, True)]
    checks = run_checks(ticks, [U], LP, duration_s=15)
    soc = next(c for c in checks if c.name == "soc_in_range")
    assert soc.passed is False


def test_islanded_market_kwh_fails():
    ticks = [Tick(0, "u1", 5.0, 3.0, "hq", 3.0, 0.0, True, True)]
    checks = run_checks(ticks, [U], LP, duration_s=15)
    row = next(c for c in checks if c.name == "islanded_no_market")
    assert row.passed is False


def test_fixed_reserve_through_floor_fails():
    # energy 2.0 is the floor; market discharge
    ticks = [Tick(0, "u1", 1.9, 1.0, "hq", 1.0, 0.0, False, True)]
    checks = run_checks(ticks, [U], LP, duration_s=15)
    row = next(c for c in checks if c.name == "fixed_reserve_floor")
    assert row.passed is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_checks.py -v`  
Expected: FAIL — missing module.

- [ ] **Step 3: Write minimal implementation**

`run_checks(ticks, units, local, duration_s) -> list[Check]` with exactly these names:

- `soc_in_range` — every tick energy in `[0, capacity]`
- `islanded_no_market` — no tick with `islanded and power_kw != 0` used as *market*. Islanded discharge to the house is allowed (`who_decided == "local"`). Fail only if `islanded and who_decided == "hq"`.
- `fixed_reserve_floor` — if kind is `fixed_reserve`, no tick with `who_decided == "hq"` and `power_kw > 0` and `energy_kwh < floor` (use energy **before** or after? Use tick.energy_kwh after step: fail if after-energy < floor - 1e-9 and power>0 and who hq). Aggressive: this check passes.
- `ticks_align` — every tick `t_s % 15 == 0` and `0 <= t_s < duration_s`

Also `scoreboard(ticks, intervals, units, local) -> Scoreboard`:

- `revenue_usd` = sum of interval.pnl_usd
- `shortfall_kwh` = sum of tick.shortfall_kwh
- `coverage` = 1 - shortfall / max(shortfall + served_islanded, 1e-9) where served_islanded = sum of `max(power,0)*dt_h` for islanded ticks
- `locations_dark` = count of distinct units (v1: 1:1 with locations) that had any shortfall
- `time_at_floor_s` = ticks where energy <= floor + 1e-6, times 15

Add one passing-path test that a clean tick list yields all `passed is True`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_checks.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/checks.py tests/test_checks.py
git commit -m "Add v1 run checks and scoreboard."
```

---

### Task 12: Scenario YAML → world

**Files:**
- Create: `battery_fleet/scenario.py`
- Create: `scenarios/tiny.yaml`
- Test: `tests/test_scenario.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scenario.py
from pathlib import Path
from battery_fleet.scenario import load_scenario

TINY = Path(__file__).resolve().parents[1] / "scenarios" / "tiny.yaml"


def test_tiny_has_three_locations_and_units():
    world = load_scenario(TINY)
    assert len(world.locations) == 3
    assert len(world.units) == 3
    assert len(world.installs) == 3
    assert world.local_policy.kind == "fixed_reserve"
    assert world.duration_s == 3600
    assert world.seed == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scenario.py -v`  
Expected: FAIL — missing module or yaml.

- [ ] **Step 3: Write minimal implementation**

`scenarios/tiny.yaml`:

```yaml
seed: 1
duration_s: 3600
n_locations: 3
local_policy: {kind: fixed_reserve, floor_frac: 0.2}
hq_policy: {charge_below: 25, discharge_above: 80}
battery: {efficiency: 1.0}
market_event:
  kind: hot_evening_scarcity
  settlement_point: HB_NORTH
  scarcity_start_s: 900
  scarcity_end_s: 1200
  scarcity_adder: 1500
  congestion_start_s: 0
  congestion_end_s: 0
  congestion_adder: 0
  base_energy: 35
  losses: 1
outages:
  - {start_s: 915, end_s: 1500, node_kind: substation, node_id: s0}
```

`load_scenario(path) -> World` where `World` is a dataclass in `scenario.py` holding: regions, cities, substations, locations, units, installs, policies, models, event, outages, link_windows=[], duration_s, seed, weather (one city, 5-min temps 18–30), plus `prices` and `loads` already generated via `write_prices` / `write_loads`.

Place 3 locations in Texas box (lat 32.6–33.0, lon -97.0–-96.6), one substation `s0`, one city, one region. Unit i installed at location i. Deterministic from `n_locations` + seed.

Raise `ValueError` with a clear message if required keys are missing (fail before any folder exists — this function does not create folders).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scenario.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/scenario.py scenarios/tiny.yaml tests/test_scenario.py
git commit -m "Add scenario YAML loader and tiny 3-location world."
```

---

### Task 13: Spinup, persist, index, CLI

**Files:**
- Create: `battery_fleet/index.py`
- Create: `battery_fleet/cli.py`
- Create: `battery_fleet/__main__.py`
- Modify: `battery_fleet/store.py` (write all tables + ticks)
- Modify: `battery_fleet/loop.py` (add `simulate(world) -> ticks, events, intervals`)
- Test: `tests/test_spinup.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spinup.py
from pathlib import Path
from battery_fleet.cli import run_scenario
from battery_fleet.index import load_index


def test_tiny_run_is_success_and_indexed(tmp_path: Path):
    scenario = Path("scenarios/tiny.yaml")
    run_dir = run_scenario(scenario, runs_dir=tmp_path)
    assert (run_dir / "run.db").exists()
    idx = load_index(tmp_path)
    assert len(idx) == 1
    assert idx[0]["status"] == "success"
    assert idx[0]["id"] == run_dir.name


def test_bad_yaml_does_not_create_folder(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("seed: 1\n")  # missing the rest
    try:
        run_scenario(bad, runs_dir=tmp_path / "runs")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
    runs = tmp_path / "runs"
    if runs.exists():
        assert list(runs.glob("*/run.db")) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_spinup.py -v`  
Expected: FAIL — CLI missing.

- [ ] **Step 3: Write minimal implementation**

`loop.simulate(world)`: for `t` in `0..duration_s step 15`, for each install, `step_unit` with islanded/link from `grid`, load from `load_at`, price from `price_at`. Seed unit energy at `0.5 * capacity`. Collect ticks. On each new interval boundary (when `t>0` and `t % 300 == 0`), `settle_interval` for `[t-300, t)`. After the last tick, settle the final incomplete-or-full interval. Emit events when islanded or link flips vs previous tick.

`store.write_world` / `write_ticks` / `write_checks` / `write_scoreboard` / `write_card` — simple INSERT helpers. Snapshot every world piece into the db.

`run_scenario(path, runs_dir)`:

1. `world = load_scenario(path)`  # may raise, no folder yet
2. `run_id = utc_compact_timestamp + "-" + 4 hex from seed`
3. mkdir `runs_dir / run_id`, `create_run_db`, write card status=`running`
4. try: simulate; checks; if any check failed: status=failed, error=joined names; else scoreboard + success
5. except: status=failed, error=str(exc)
6. `rebuild_index(runs_dir)`
7. return run_dir  
   If status is failed, still return the dir (tests for success use tiny.yaml which should pass).

`index.rebuild_index` / `load_index`: glob `*/run.db`, SELECT the `run` row, write `index.json` list of dicts. Skip folders with no `run` row.

`cli.main`: argparse `run <scenario> --runs-dir runs` and `serve` (serve implemented in Task 15; for now `serve` can raise SystemExit("not yet") — **do not wire serve until Task 15**). Only implement `run` here.

`__main__.py`: `from battery_fleet.cli import main; main()`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_spinup.py tests/test_loop.py -v`  
Expected: PASS. Tiny run must get `success` — if a check fails, fix the check or the tiny world (mid-interval outage at t=915 is intentional; islanded house load must be serveable from 50% SOC for 1 hour).

If tiny fails `soc` or `fixed_reserve`, loosen tiny duration/load or start SOC until checks pass for honest physics — do not delete the check.

- [ ] **Step 5: Commit**

```bash
git add battery_fleet tests/test_spinup.py
git commit -m "Add run spinup, persist, generated index, and CLI run."
```

---

### Task 14: Demo scenarios (two realities)

**Files:**
- Create: `scenarios/fixed_20.yaml`
- Create: `scenarios/aggressive.yaml`
- Test: `tests/test_compare_ready.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_compare_ready.py
from pathlib import Path
import yaml


def test_demo_pair_differs_only_by_local_policy():
    a = yaml.safe_load(Path("scenarios/fixed_20.yaml").read_text())
    b = yaml.safe_load(Path("scenarios/aggressive.yaml").read_text())
    assert a["local_policy"]["kind"] == "fixed_reserve"
    assert b["local_policy"]["kind"] == "aggressive"
    skip = {"local_policy"}
    for k in a:
        if k in skip:
            continue
        assert a[k] == b[k], k
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_compare_ready.py -v`  
Expected: FAIL — files missing.

- [ ] **Step 3: Write the two YAML files**

Same as each other except local policy. Knobs:

- `seed: 7`
- `duration_s: 86400`
- `n_locations: 60`
- HQ `charge_below: 25`, `discharge_above: 80`
- battery `efficiency: 0.95`
- market event: scarcity `start_s: 64800` (18:00), `end_s: 65400` (18:10), adder `2500`, `base_energy: 32`, `losses: 1`, optional congestion `start_s: 65000`, `end_s: 65600`, adder `80`
- outage: `start_s: 64915` (mid-interval after 18:00), `end_s: 66700`, `node_kind: substation`, `node_id: s0` (scenario builder must name the first substation `s0`)
- `fixed_20`: `floor_frac: 0.2`
- `aggressive`: `kind: aggressive`, `floor_frac: 0.0`

Extend `load_scenario` if `n_locations > 3` needs more substations: e.g. 4 substations `s0..s3` cycled, 2 cities. Keep `s0` as a real id so the outage hits a cluster, not everyone.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_compare_ready.py -v`  
Expected: PASS

Also run (not committed as a unit test if too slow — if 60×24h is >30s, add `tests/test_demo_smoke.py` that loads both YAMLs via `load_scenario` only, no full sim):

`python -m pytest tests/test_compare_ready.py tests/test_scenario.py -v`

- [ ] **Step 5: Commit**

```bash
git add scenarios/fixed_20.yaml scenarios/aggressive.yaml tests/test_compare_ready.py battery_fleet/scenario.py
git commit -m "Add paired demo scenarios that differ only by local floor."
```

---

### Task 15: Compare helper (notebook brain)

**Files:**
- Create: `analysis/compare.py`
- Test: `tests/test_compare.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_compare.py
from pathlib import Path
from battery_fleet.cli import run_scenario
from battery_fleet.compare import Incomparable, compare_runs


def test_refuses_different_seeds(tmp_path: Path, monkeypatch):
    # two tinies are the same seed — should be comparable
    d1 = run_scenario(Path("scenarios/tiny.yaml"), runs_dir=tmp_path)
    d2 = run_scenario(Path("scenarios/tiny.yaml"), runs_dir=tmp_path)
    table = compare_runs(d1, d2)
    assert "revenue_usd" in table["a"]
    assert "revenue_usd" in table["b"]


def test_incomparable_seed(tmp_path: Path):
    # write a second tiny-like yaml with seed 2
    p = tmp_path / "other.yaml"
    text = Path("scenarios/tiny.yaml").read_text().replace("seed: 1", "seed: 2")
    p.write_text(text)
    d1 = run_scenario(Path("scenarios/tiny.yaml"), runs_dir=tmp_path / "r")
    d2 = run_scenario(p, runs_dir=tmp_path / "r")
    try:
        compare_runs(d1, d2)
    except Incomparable:
        return
    raise AssertionError("expected Incomparable")
```

If `analysis` is not a package, make `compare_runs` live at `battery_fleet/compare.py` and have `analysis/compare.py` import it. Prefer `battery_fleet/compare.py` so tests don’t fight the path. Then `analysis/compare.py` is a 5-line wrapper.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_compare.py -v`  
Expected: FAIL — missing compare.

- [ ] **Step 3: Write minimal implementation**

`battery_fleet/compare.py`:

- Read both `run` cards from sqlite.
- Comparable iff seed, market_event_id, hq_policy_id, schema_version match and `local_policy_id` may differ. Also require same counts of locations/units (SELECT COUNT).
- Raise `Incomparable(reason)` otherwise.
- Return `{"a": scoreboard_dict, "b": scoreboard_dict, "intervals": [...]}` with both interval series.

`analysis/compare.py`:

```python
from battery_fleet.compare import Incomparable, compare_runs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_compare.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/compare.py analysis/compare.py tests/test_compare.py
git commit -m "Add compare helper that refuses incomparable realities."
```

---

### Task 16: Serve + dashboard

**Files:**
- Create: `battery_fleet/serve.py`
- Modify: `battery_fleet/cli.py` (wire `serve`)
- Create: `dashboard/index.html`
- Create: `dashboard/app.js`
- Create: `dashboard/style.css`
- Test: `tests/test_serve.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_serve.py
from pathlib import Path
from fastapi.testclient import TestClient  # only if you pick FastAPI
```

Do **not** add FastAPI. Use stdlib `http.server`. Test with `urllib` against a thread, or test the handler functions directly:

```python
# tests/test_serve.py
from pathlib import Path
from battery_fleet.cli import run_scenario
from battery_fleet.serve import run_payload, runs_payload


def test_api_lists_and_loads_a_success(tmp_path: Path):
    run_dir = run_scenario(Path("scenarios/tiny.yaml"), runs_dir=tmp_path)
    listing = runs_payload(tmp_path)
    assert listing[0]["status"] == "success"
    body = run_payload(tmp_path, run_dir.name)
    assert "locations" in body
    assert "ticks" in body
    assert "prices" in body
    assert "scoreboard" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_serve.py -v`  
Expected: FAIL — serve missing.

- [ ] **Step 3: Write minimal implementation**

`runs_payload(runs_dir)` = `load_index` filtered to `success` by default.

`run_payload(runs_dir, run_id)`: open that `run.db`, return JSON-able dict: card, locations (id, lat, lon), units/installs, ticks (may downsample to every 4th tick if > 200k rows — if you downsample, also include `trace_stride`), prices, outages, events, intervals, scoreboard. Do not invent rows. Missing id → raise `FileNotFoundError`.

`serve.py` `main(host, port, runs_dir)`: stdlib server.

- `GET /api/runs` → `runs_payload`
- `GET /api/runs/<id>` → `run_payload`
- `GET /` and static files from `dashboard/`

`cli serve --runs-dir runs --port 8765`

**Dashboard (must look finished, not a wireframe):** dark page, full-width Texas-ish scatter (plot lat/lon, no map tiles), time range input, color dots by SOC (energy/capacity), red ring if islanded. Charts: SPP line (and stacked parts if easy), fleet mean SOC, shortfall. Metric strip from scoreboard. Run picker from `/api/runs`. If the payload errors, show the error string, no fake dots.

Keep `app.js` + `style.css` under 250 lines each; split if not.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_serve.py -v`  
Expected: PASS

Manual: `python -m battery_fleet run scenarios/tiny.yaml && python -m battery_fleet serve` — open the page, scrub, confirm dots move.

- [ ] **Step 5: Commit**

```bash
git add battery_fleet/serve.py battery_fleet/cli.py dashboard tests/test_serve.py
git commit -m "Add one-run dashboard over run.db."
```

---

### Task 17: Notebook + demo runs in the log

**Files:**
- Create: `analysis/compare.ipynb`
- Modify: `docs/project-log/YYYY-MM-DD.md` (today)

- [ ] **Step 1: Write a failing smoke**

```python
# tests/test_notebook_exists.py
from pathlib import Path

def test_notebook_present():
    text = Path("analysis/compare.ipynb").read_text()
    assert "compare_runs" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_notebook_exists.py -v`  
Expected: FAIL — missing notebook.

- [ ] **Step 3: Write the notebook**

Three cells:

1. Markdown: “Two realities. Same world, different local floor.”
2. Code: find the two latest successful runs whose cards differ only by local policy (or take paths as variables `A` and `B`). Call `compare_runs`. Print scoreboards.
3. Code: plot interval `spp` (shared) and `pnl_usd` for A vs B. matplotlib.

No extra narrative.

Then run both demo scenarios (this can take a few minutes):

```bash
python -m battery_fleet run scenarios/fixed_20.yaml
python -m battery_fleet run scenarios/aggressive.yaml
```

If a 60×24h run is too slow or fails a check, cut `n_locations` to 40 or `duration_s` to 43200 **in both YAML files together** and update `test_compare_ready`. Do not drop the mid-interval outage or the scarcity window.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_notebook_exists.py -v`  
Expected: PASS

Run: `python -m pytest tests/ -v`  
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add analysis/compare.ipynb scenarios docs/project-log
git commit -m "Add compare notebook and record the demo pair."
```

Append the project log: what ran, how long, scoreboard headline, anything that broke.

---

## Self-review (plan vs spec)

| Spec piece | Task |
|---|---|
| Four planes / types as law | 2, 3 |
| Location ≠ unit, install, grid stack | 2, 4, 12 |
| Price parts + SPP sum | 2, 8 |
| Market event writes series | 8, 12 |
| Load location × 5 min | 9 |
| Local default, HQ privilege, no last setpoint | 6, 7, 10 |
| Folder + run.db + generated index | 3, 13 |
| Validate before folder | 13 |
| v1 checks + scoreboard | 11 |
| Two demo realities, mid-interval outage | 14, 17 |
| Dashboard one run | 16 |
| Notebook compare, refuse incomparable | 15, 17 |
| CLI `run` / `serve` | 13, 16 |
| AS / UQ / users not built | no task — leave `notes/later.md` alone |

No FastAPI, no second SOC table, no AS series, no mkdir-by-hand. Dashboard does not compare.
