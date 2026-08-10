# Battery fleet reserve vs revenue — design

Date: 2026-08-10  
Status: approved for implementation planning  
Audience: personal portfolio / Base Power interview showcase

## Goal

Explore how a Base-like residential battery fleet trades **market / grid revenue** against **outage reserve** under an ERCOT-flavored toy world. The stress is temporal and physical: prices settle on a 5-minute market clock while the fleet can telemeter and re-dispatch much faster; outages can start mid-interval; reserve policy decides whether energy is still there when backup is needed.

Deliverables for the first milestone (same shape as `consensus`):

- Scenario-driven simulation runs with immutable artifacts
- Web playbacks for representative runs
- Analysis tables and figures comparing policies
- Plain-language notes the author can turn into a short public post (the post itself is written by the author, not by agents)
- A daily project log of pushes, issue investigations, and experiments

v1 compares two reserve policies under the same fleet, price series, outages, and seed:

1. `fixed_reserve` — never discharge below a SOC floor (e.g. 20%)
2. `aggressive` — thin / no floor; chase price subject to power limits

## Future questions (not v1 code)

Document in `notes/` as they come up; do not build unless a later milestone explicitly promotes them:

- Degraded telemetry / control (links drop, lag, sites offline mid-event)
- Local grid constraints (feeder / transformer limits vs aggregate VPP targets)
- Member fairness / SLA during storms while still supporting the grid
- Risk-aware reserve (raise floor when outage probability rises)
- Uneven central allocation of reserve across homes

## Approach

**Thin tick-loop experiment pipeline** (not a mini EMS platform, not a single ad-hoc script):

1. A scenario file describes the fleet, market curve, outages, load, and reserve policy.
2. A runner steps a shared tick loop: world (price + outages + load) ↔ battery fleet ↔ reserve policy.
3. Each run writes an immutable folder of traces and metrics.
4. A web player and analysis scripts consume those folders.

Two clocks are first-class:

| Clock | Cadence | Role |
|-------|---------|------|
| Market | 5 minutes | ERCOT RT-flavored settlement / price updates; price held constant within an interval |
| Fleet | 15 seconds | Telemetry and dispatch decisions; SOC, power, islanding, shortfall update every tick |

## Architecture

```
scenario YAML
    → runner (15s tick loop)
        price/outage/load world ↔ battery fleet ↔ reserve policy
    → runs/<id>/
        config · trace · events · metrics · status
    → web player | analysis tables/figures
```

### Repository layout

| Path | Role |
|------|------|
| `engines/` | World (price + outage + load), battery physics, policy plugins |
| `scenarios/` | Fleet + market + outage + policy knobs (YAML) |
| `runs/` | Immutable experiment outputs |
| `playback/` | Local web player over a chosen run |
| `analysis/` | Batch metrics → tables and figures |
| `notes/` | Plain-language strategy / concern writeups for the author’s post |
| `docs/project-log/` | Daily lab notebook (`YYYY-MM-DD.md`) |
| `docs/superpowers/specs/` | Design specs |

## Components

### World engine (ERCOT-flavored, synthetic)

No live market APIs in v1. Generate:

- **Price series:** synthetic RT SPP-like curve on **5-minute** boundaries — overnight trough, evening peak, short sharp spikes (one to a few intervals). Price is constant within an interval; changes only on interval boundaries.
- **Outages:** scenario-scheduled bursts `{start, end, home_ids|region}`. May begin **mid-interval** so reserve + fast dispatch matter while price is flat.
- **Home load:** simple per-home kW while islanded (and optionally light grid-connected load) so backup shortfall is measurable.

### Battery / home model

Each site: capacity (kWh), max charge/discharge (kW), SOC, simple constant efficiency, online/islanded flag.

Each 15s tick: apply policy setpoint → clamp by power, SOC, and reserve rules → update SOC → if islanded, serve load or record shortfall (kWh).

Sign convention: **discharge to grid or home is positive power (kW)**; charging from grid is negative. SOC is fraction in `[0, 1]` or kWh — pick one at implementation and keep it consistent at boundaries (prefer kWh in the engine, percent only in scenario knobs / UI).

When islanded: no market import/export; battery serves home load only (subject to power/SOC). Market setpoints apply only while grid-connected.

v1 scale: about **50–200 homes**, scenario duration **24–48 hours**.

### Reserve policies (plugins, same interface)

Shared price-chase heuristic when grid-connected (same for both): discharge into high-price intervals, charge in low-price intervals, subject to power and energy limits. Exact thresholds live in the scenario (e.g. discharge above $/MWh X, charge below Y).

1. **`fixed_reserve`** — SOC floor (e.g. 20% of capacity); market discharge only while above the floor; charge still allowed below floor when grid-connected.
2. **`aggressive`** — floor ≈ 0 (or a tiny operational buffer); same price-chase subject to power and energy limits only.

Both see the same world and may re-dispatch every 15s. The only intentional difference is the reserve constraint.

### Runner

Load scenario → validate → construct world + fleet + policy → step until duration complete → write `runs/<id>/`. Fail fast on bad config. Never mark a failed or partial run as successful.

### Playback

Local web page that loads a run folder:

- Fleet SOC overview (strip / simple spatial scatter)
- Price timeline on 5-minute steps
- Outage markers
- Scrubber over the 15s trace
- Metric strip (revenue, shortfall, fleet SOC)

### Analysis

Read many `metrics.json` files → comparison tables and a small set of figures covering revenue, backup performance, and reserve binding.

### Notes and project log

- `notes/`: material for the author’s post; agents do not write the public post.
- Daily project log under `docs/project-log/` (same habit as `consensus`).

## Data flow and artifacts

### Scenario YAML (conceptual fields)

- `duration`, `tick_s` (15), `seed`
- `fleet`: N homes, capacity/power archetype or light distributions, initial SOC
- `market`: price series id or inline 5-minute curve parameters (peak, spike schedule)
- `outages`: list of `{start, end, home_ids|region}`
- `policy`: `fixed_reserve` | `aggressive` plus knobs (floor fraction)
- `load`: per-home outage load (kW)

### Run folder: `runs/<timestamp>-<short-hash>/`

| File | Purpose |
|------|---------|
| `scenario.snapshot.yaml` | Exact knobs used |
| `trace.jsonl` | Per-tick per-home: SOC, power, islanded, shortfall |
| `events.jsonl` | Interval price changes, outage start/end, reserve binds, power clamps |
| `metrics.json` | Final scoreboard |
| `status.json` | `{ "state": "success" \| "failed", "error": null \| string }` |

At ~100 homes × 48h × 15s ≈ 1.15M lean rows — acceptable for v1 if records stay tight. Optional playback downsample later if needed; metrics always use full fidelity aggregates.

### Scoreboard (v1)

- **Revenue:** settlement-interval P&L using the 5-minute price and interval energy (export earns price × energy; import pays price × energy). Units: scenario uses $/MWh; report run totals in $ and $/home.
- **Backup:** shortfall_kWh, outage coverage fraction, homes that went dark
- **Reserve behavior:** time-at-floor, energy left above floor during high-price intervals (fixed_reserve opportunity cost), SOC at outage start (fleet mean / p10)
- **Timing (required in v1 analysis):** per-interval energy and P&L so 5-minute structure is visible alongside 15s playback; include at least one figure that overlays price, fleet SOC, and outage window

### CLI shape

```bash
python -m battery_fleet run scenarios/.../fixed_20.yaml --runs-dir runs
python -m battery_fleet serve
analysis/compare_runs.py --runs-dir runs --out analysis/output
```

## First case and experiment grid

### v1 demo day

One ERCOT-flavored synthetic day (extendable to 48h):

- Clear overnight trough and evening peak
- At least one short high-price spike cluster
- One outage burst that overlaps a period when aggressive policy is likely depleted and fixed_reserve still has floor energy — preferably starting mid 5-minute interval

### v1 run matrix

Minimum:

- Policies: `fixed_reserve` (e.g. 20%) × `aggressive`
- Same fleet, price curve, outages, seed

Optional second seed or second outage timing only if variance obscures the story. Risk-aware and other policies are later milestones.

## Failure modes and testing

### In-simulation (expected)

Outages, reserve binds, and power clamps are experimental inputs/outputs. Log them in `events.jsonl`. They are not engineering failures.

### Engineering

- Invalid scenario → clear error **before** creating a successful run; validate first, then create the run directory
- Invariant break (SOC NaN, tick misaligned with market boundaries in a way that breaks indexing) → abort, `status: failed`, non-zero exit
- Partial output → analysis skips unless explicitly included
- Playback missing artifacts → clear UI error; do not invent data

### Tests

- Unit: battery clamp (power, SOC, reserve floor); price interval indexing (15s tick → correct 5-minute price); outage mid-interval start
- Policy: `fixed_reserve` never commands market discharge through the floor; `aggressive` can
- Integration: tiny fleet (e.g. 3 homes, 1h) under fixed seed → valid run folder and stable metrics within tolerance
- Analysis: two run folders → comparison rows with expected columns

Non-goals for v1 tests: full playback e2e in CI; bit-identical floats across platforms beyond seed-stable metrics within tolerance.

Reproducibility: every run stores scenario snapshot and seed.

## Tech stack

- Python 3
- YAML scenarios
- Static HTML/JS web player
- Matplotlib (or similar) for figures
- Git; daily project log

No SUMO, no live ERCOT API, no production EMS stack in v1.

## Code quality

This project must stay readable for the author. Prefer clear Python over clever or “production hardened” noise.

Rules:

- **Obvious data shapes.** Types, dataclasses, or small typed dicts at boundaries. Do not guess what a function returns—name it and document the fields once at the boundary.
- **Fail loud on bad input.** Validate scenario files and plugin names up front. No silent defaults that paper over misconfiguration.
- **Minimal defensive clutter.** No broad `try/except`, null-checking everything, or fallback chains “just in case.” Catch only where a real external failure is expected, then exit with a clear message.
- **Small modules, one job each.** A reader should understand a file without hunting through helpers.
- **Boring structure.** Plain functions and classes; avoid deep inheritance, metaprogramming, and framework-shaped abstractions until a second use case forces them.
- **Names over comments.** Comment only non-obvious *why* (e.g. settlement vs tick alignment).
- **Tests as examples.** Unit tests should show how to call price indexing and policy plugins with real-looking inputs and outputs.

Jank is a bug. If a shortcut is temporary, note it in the project log and replace it before calling the milestone done.

## Out of scope for v1

- Live ERCOT / ISO market feeds
- Full power-flow or feeder constraint model
- Degradation, warranty, or thermal models beyond simple efficiency
- Ancillary services co-optimization (may appear later as notes or plugins)
- Multi-feeder topology and transformer limits (future question)
- Comms degradation model (future question)
- Agent-authored public blog post
- Production dispatch controller or customer-facing app

## Success criteria

v1 is done when:

1. A 24–48h ERCOT-flavored scenario runs for both `fixed_reserve` and `aggressive` on the same fleet/price/outages/seed
2. Dual clocks are visible: 5-minute price steps and 15s dispatch/trace, including at least one mid-interval outage start
3. Web playbacks exist for those runs
4. Tables and figures compare revenue, backup shortfall/coverage, and reserve binding
5. `notes/` has enough plain-language material for the author to write the post
6. Project log entries exist for the major pushes and experiments that produced the above
