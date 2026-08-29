# Sim backbone — design

Date: 2026-08-23  
Status: approved  
Replaces as the build spec: `2026-08-10-battery-fleet-reserve-design.md` (keep that file; it got the tick logic mostly right and over-scoped the rest)

This is the spec we build. Decisions and the author’s wording live in `notes/intent-log.md`. Things we named and are not building live in `notes/later.md`.

## Goal

A small, honest backbone for a Base-like residential battery fleet in an ERCOT-flavored toy world.

The old spec treated the data model as leftovers. That is the thing that makes a sim resilient. Each run is its own representation of reality. Realities reuse one data model.

First slice you can open:

- Two successful runs (`fixed_reserve` vs `aggressive`)
- A dashboard that plays **one** run: map + charts + time scrub
- A notebook that compares the two
- A generated index of runs
- A short card + automated checks on every run

## What this is not

Not a mini EMS. Not a live ERCOT feed. Not a customer app. Not a pile of unread docs.

## Four planes

Types are the law. Any picture of the planes is a view of the types, not a second schema.

1. **World pieces** — reusable parts a reality can point at.
2. **Reality** — one run. A card: which pieces, seed, schema version, pass/fail.
3. **Time** — what happened. Truth, plus who was allowed to decide.
4. **Judgment** — checks and a scoreboard. Uncertainty work is later.

### Authorities (not three metronomes)

Local is default. HQ is a privilege.

- **Local policy** always owns reserve and the house. Lives on the unit.
- **HQ policy** is a price-chase overlay. Only when the location’s radio is up and the location is not islanded.
- When the radio dies, the unit **reverts to local**. It does not hold the last HQ setpoint.
- **Market clock** (5 min) counts money from **truth** only.

Grid outage ≠ radio silence. Those are different drivers.

We do not store a second HQ-SOC movie. HQ’s view is “last tick where the location was linked.”

## Grain

| Thing | Grain |
|---|---|
| Location | One site. Lat/lon. Parent on the grid. Static. Not a battery. |
| Unit | One battery. kWh, kW. Can move across runs. |
| Install | Unit @ location. Fixed **inside** a run. |
| Grid stack | `location → substation → city → region`. No power flow. |
| Outage | Node × window (substation, city, or region). Hits every location under that node. |
| Load | Location × 5 min. From time of day, season, temperature. Snapshotted at spinup. |
| Price | One settlement point × 5 min, in **parts**. |
| Tick | Unit × 15 s |
| Money | Settlement point × 5 min, from unit truth |
| Link | At the **location**. Units there share it. |
| Island | At the **location**. |

Users later. First scenarios: one unit per location, all radios up. The columns still exist so we did not bake “always reachable” or “home = battery.”

### Price parts

`prices` is not one number. Each 5 min row:

- `energy`
- `scarcity` (ORDC-style adder)
- `congestion`
- `losses`
- `spp` — the sum, what we settle

A **market event** is a bundle of component schedules (scarcity window, congestion window) plus weather/load. It **writes** those series into the run. Physical outages stay a different object: outage = islanded, backup story; congestion = still on the grid, money story.

Ancillary services: later. Same shape, another series, not this build.

## How a reality is born

```
runs/
  index.json                  # generated only. never typed.
  2026-08-23T150412-a3f1/
    run.db                    # the whole reality
```

The run card is a table in `run.db`, not a sidecar file.

1. Read a scenario YAML (names the pieces).
2. Validate. Bad input dies **before** a folder exists.
3. Create the folder. Status `running`.
4. Copy the named pieces **into** `run.db`. Editing a scenario later cannot change this reality.
5. Step time. Write ticks, events, intervals.
6. Run checks. Write checks + scoreboard.
7. Status → `success` only if the loop finished **and** every check passed. Else `failed` + a reason.
8. Rebuild `index.json` by opening every `run.db`. Folders with no card are not successes.

Crash mid-run: leftover folder, not success. Dashboard skips it. Notebook can see it if you ask for failed.

If `index.json` and the folders disagree, the folders win and the file gets rewritten.

CLI:

```bash
python -m battery_fleet run scenarios/fixed_20.yaml
python -m battery_fleet run scenarios/aggressive.yaml
python -m battery_fleet serve
```

Do not `mkdir` a run. Do not edit the index. Two realities are comparable only if the cards share locations, units, installs, market event, outages, weather, seed, HQ policy — and differ by local policy.

## Tables in `run.db`

Same tables in every run.

**Places:** `regions`, `cities`, `substations`, `locations`, `units`, `installs`

**Drivers:** `market_event`, `prices` (parts above), `weather`, `load_model`, `loads`, `outages`, `link_plan` (first runs: empty)

**Models:** `battery_model`, `market_model`, `local_policy`, `hq_policy`

**Reality:** `run` — one row. Seed, schema version, status, error, names of the pieces, started/finished.

**Time**

- `ticks` — unit × 15 s: `energy_kWh`, `power_kW` (discharge +), `who_decided` (`local` | `hq`), `hq_asked_kW` (null if silent), `shortfall_kWh`. `islanded` and `link_up` copied from the location.
- `events` — outage, link, reserve bind, clamp.
- `intervals` — settlement point × 5 min: energy, $, plus the price parts for that interval.

**Judgment:** `checks`, `scoreboard` (revenue, shortfall, coverage, **locations** that went dark, time at floor).

Sign convention: discharge is positive power.

## One 15 s step

For each location, then each unit installed there:

1. Hold the current 5-min price parts and the current location load. Load does not get a new number this tick.
2. If an outage node covers this location → islanded. Units here must serve the location load or we add shortfall.
3. `link_up` from `link_plan` (first runs: always up).
4. Local: serve the house if islanded. Never market-discharge through the local floor.
5. HQ: only if linked and not islanded. Same price-chase both runs: discharge if SPP ≥ `hq_policy.discharge_above`, charge if SPP ≤ `hq_policy.charge_below`, clamped by local. Those two knobs live on the scenario. If silent: skip. Do not hold last HQ setpoint.
6. Physics: clamp by kW and energy. Apply efficiency. Write the tick.
7. If something started this tick, write an event.

On each 5-min boundary: sum fleet energy from ticks, settle → `intervals`. Export (discharge to grid) earns `spp × energy`. Import pays. `spp` is $/MWh; report run totals in $ and $/location.

End of run: checks, then scoreboard.

**v1 checks:** SOC in [0, capacity]; islanded location ⇒ no market kWh; `fixed_reserve` never market-discharges through the floor; ticks line up with 5-min prices; a failed run is never marked success.

## First two realities

Same locations, units, installs, market event (hot evening + scarcity spike, one settlement point), weather, outages (at least one substation or city window, preferably starting mid 5-min interval), load, battery model, market model, HQ policy, seed.

Different: local policy only — `fixed_reserve` (e.g. 20% floor) vs `aggressive` (floor ≈ 0).

Scale: about 50–200 locations, 24–48 hours, one unit per location, all links up.

Texas-ish fake lat/lon so the map looks like a fleet.

## Dashboard and notebook

Both read `run.db`. Neither invents data.

**Dashboard** (`python -m battery_fleet serve`): one run at a time from the generated index. Map of locations (color by SOC / islanded / silent). Scrub time. Price chart (SPP, optional stack of parts) with outage windows. Fleet SOC + shortfall. Metric strip from **that** scoreboard only. Missing or failed run: say so.

**Notebook:** two successful runs. Refuse the pair if the cards are not comparable. Scoreboard side by side. Interval series overlay. One or two extra plots if the story needs them. No compare UI in the dashboard.

## Repo

```
battery_fleet/     # types, loop, policies, sqlite io
scenarios/
runs/              # gitignore the dbs
dashboard/
analysis/          # one notebook
notes/             # intent-log + later
docs/project-log/  # daily habit, YYYY-MM-DD.md
docs/superpowers/specs/
.cursor/rules/
.cursor/skills/
```

Python 3. No live APIs. Dashboard is a small local web page. Notebook for compare.

Code: small files (split if a file goes over ~250 lines), obvious names, fail loud, no cleverness. Types at the boundary. Catch only where something outside can actually fail.

## Agents

**Rules (always on)**

- Plain English. Short questions. No technobabble.
- After a decision: quote the author into `notes/intent-log.md`.
- Types are law. Do not add a column the types don’t know. Do not mkdir a run or edit the index.
- After a session that ran something or decided something: write `docs/project-log/YYYY-MM-DD.md`.

**Skills (when the job comes up)**

- Run spinup
- Trust a run (card + checks)
- Project log entry

No extra docs. If it isn’t the spec, the intent log, later.md, the project log, or a type — don’t write it.

## Tests

- Unit: clamps (power, energy, reserve floor); 15 s tick maps to the right 5-min price; outage mid-interval; islanded ⇒ no market kWh; silent ⇒ `who_decided` is local.
- Policy: `fixed_reserve` never market-discharges through the floor; `aggressive` can.
- Grain: a tick is a unit; load and island are a location; SPP is the sum of parts.
- Integration: tiny fleet (3 locations, 1 hour, fixed seed) → valid `run.db`, index lists it, checks pass, metrics stable within tolerance.
- Compare: two run folders → notebook inputs have the expected columns; incomparable pair is refused.

Not in CI: full dashboard click-through; bit-identical floats across machines.

## Success

1. Two 24–48 h runs as above, both `success`.
2. Dual grain visible: 5-min price parts and 15 s ticks; at least one mid-interval outage start.
3. Dashboard plays each run. Notebook compares them.
4. Index matches the folders without anyone editing it.
5. Intent log and project log exist for the work that produced this.
6. `notes/later.md` still lists uncertainty, AS, and users — none of those got built.

## Later (do not build)

See `notes/later.md`. Also not this build: live ERCOT, power flow, feeders, DAM, delay/drop comms, mid-run unit moves, last-setpoint-forever, a compare app, agent-authored public post.
