# Sim run dashboard — design

Local ops-console for one persisted fleet run. Scrub a 24h dispatch. See every site move.

Not a deploy. Not Grafana. Not live ERCOT.

## Why

The sim already has per-tick fleet totals and per-unit command / actual / SOC / reachable, plus site lat/lon. Nothing persists. Nothing draws. This is the first observability surface: write a run, serve it, play it back.

## Who

You, locally. Portfolio screenshots later. No public host in this cut.

## Locked decisions

- Persist `runs/<id>/run.json`. Gitignored except `runs/.gitkeep`.
- Serve with stdlib HTTP on port 8000. No extra Python deps.
- UI is React + Vite + TypeScript + Leaflet. Charts: TradingView `lightweight-charts`.
- Demo world: `build_fleet(80, 100, t0, seed)`, 96 × 15-min ticks, baked ERCOT-shaped prices, `solve_dispatch`, a few units offline around the spike then back.
- One map marker per site. Two units at one house share a pin.
- Extra series: mean SOC, cumulative score $.
- Command log is derived at write time. No event bus.
- Dark ops-console. IBM Plex Sans + Plex Mono. Copper / teal / fault on ink.

## Out of scope

GitHub Pages, `demo.json`, SQLite, real ERCOT fetch, MPC, 10k units, Grafana, live streaming, auth.

---

## Data flow

```
scripts/demo_market_day.py
        ↓
  runs/<id>/run.json
        ↓
python -m battery_fleet serve     :8000
        ↓  GET /api/runs
        ↓  GET /api/runs/<id>
dashboard (Vite :5173, proxies /api)
```

Two processes: generate once, then serve + `npm run dev`.

---

## Run JSON

Writer joins `FleetTickRecord` with `Installation` lat/lon. Tick records do not carry coordinates.

### Root

| field | type | notes |
| --- | --- | --- |
| `id` | string | directory name, unique |
| `dt_seconds` | number | 900 for the demo |
| `started_at_unix` | number | first tick time, or fleet initial time if no ticks |
| `sites` | array | once |
| `units` | array | once |
| `ticks` | array | chronological |
| `commands` | array | derived, chronological |

### Site

`id`, `lat`, `lon`, `unit_ids` (string array, order as on the installation).

### Unit

`id`, `site_id`, `capacity_kwh`.

### Tick

| field | type |
| --- | --- |
| `time_unix` | number |
| `price_usd_per_mwh` | number or null |
| `target_w` | number or null |
| `fleet_w` | number |
| `commanded_w` | number |
| `error_w` | number |
| `load_w` | number |
| `score_usd` | number or null |
| `energy_pnl_usd` | number or null |
| `n_unreachable` | int |
| `mean_soc` | number (0–1, mean over all units this tick) |
| `cumulative_score_usd` | number (running sum of `score_usd`; null scores add 0) |
| `units` | object keyed by unit id |

Per-unit tick: `soc`, `actual_w`, `commanded_w`, `reachable`.

### Command event

| field | type |
| --- | --- |
| `time_unix` | number |
| `kind` | `target` \| `setpoint` \| `offline` \| `online` \| `clip` |
| `unit_id` | string or null (`target` is fleet-level) |
| `site_id` | string or null |
| `watts` | number or null |
| `note` | string |

**Deltas only**

- `target`: `fleet_target_power_watts` changed vs previous tick (including first non-null).
- `setpoint`: that unit’s `commanded_w` changed vs previous tick. First tick logs a setpoint if commanded ≠ 0. Do not log 100 identical setpoints every later tick.
- `offline` / `online`: `reachable` flipped vs previous tick. Not on the first tick unless you need it — first tick is baseline, no flip.
- `clip`: `|commanded_w − actual_w| > 1e-6` this tick. Physics rejected part of the command.

---

## Store API

`battery_fleet/store.py`

```
write_run(run_id, fleet, records, dt_seconds, runs_dir=None) -> Path
read_run(run_id, runs_dir=None) -> dict
list_runs(runs_dir=None) -> list[dict]   # {id, started_at_unix, n_ticks} newest first
```

Default `runs_dir` is `<repo>/runs`. Create the run directory. Write `run.json` (pretty-printed, UTF-8). `list_runs` skips missing/invalid files.

Derive `commands`, `mean_soc`, `cumulative_score_usd` inside `write_run`. Do not require the caller to precompute them.

---

## Prices

`battery_fleet/prices.py`

`market_day_prices() -> list[float]`

Exactly 96 values. Formula, not a CSV.

- Night hours 0–6: about $20 (band 10–40).
- Afternoon peak (hours 14–17): at least one value > $150.
- Shape is ERCOT-summer-ish: cheap night, spike afternoon, settle evening.

---

## Demo script

`scripts/demo_market_day.py`

1. `build_fleet(80, 100, t0, seed)` — seed 1, `t0 = 1_700_000_000.0`.
2. House load 1500 W every site every tick.
3. For each of 96 prices: `solve_dispatch(fleet, price, 900, ancillary_revenue_usd=5.0)`, then `run_fleet` one tick with that command map, `fleet_target_power_watts=sum(commands)`, that price, $5 ancillary.
4. Offline: at tick index 40, `go_offline()` on 5 units. At tick index 64, `come_online()` on those same units. Pick stable ids (first five in fleet walk order).
5. `write_run` with a timestamp id. Print the run id and path.

Do not print the ASCII table.

---

## HTTP

`python -m battery_fleet serve` → `battery_fleet/__main__.py` dispatches to `serve.main()`.

Port 8000. Stdlib only.

| method | path | body |
| --- | --- | --- |
| GET | `/api/runs` | JSON list from `list_runs` |
| GET | `/api/runs/<id>` | full `run.json` or 404 |

CORS: allow `*` origin, `GET`, `Content-Type`. Vite on 5173 must be able to call this.

Unknown paths: 404. No static file serving in this cut (Vite owns the UI).

---

## Dashboard

`dashboard/` Vite + React + TS.

Dev proxy: `/api` → `http://127.0.0.1:8000`.

Every source file under 250 lines.

### Load

On mount: `GET /api/runs`. If empty or network fail, show one line:

`Generate a run: .venv/bin/python scripts/demo_market_day.py then .venv/bin/python -m battery_fleet serve`

If list is non-empty, load the newest run (`GET /api/runs/<id>`).

### Layout

Dark full-bleed map. Overlay KPI strip. Right rail: charts then command log. Bottom: scrubber.

### KPIs (current tick)

Clock (from `time_unix`), RT price, fleet MW vs target MW, tracking error W, unreachable count, tick `score_usd`.

### Map

- Carto Dark Matter tiles.
- Fit Texas box (the fleet bbox, ~26–36 N, 94–106 W).
- One circle per site.
- Color from **site net battery power** (sum of unit `actual_w`): copper if charging (> +1 W), teal if discharging (< −1 W), muted idle.
- If any unit at the site is unreachable: red ring, dim the fill.
- Hover: site id; each unit’s kW, SOC %, reachable, last commanded W.

### Charts

`lightweight-charts`, two panes:

1. Fleet power W and target W; price $/MWh on a second scale or dedicated pane — whichever stays readable.
2. Mean SOC (0–1) and cumulative score $.

Vertical playhead at the current tick. All series share the 96 timestamps.

### Command log

Events with `time_unix <=` current tick. Newest at top. Columns: time, kind, unit/site, watts, note.

### Scrubber

Play / pause. Discrete steps (one tick at a time). ~8 ticks/sec so a day is ~12 s. Drag or click the bar to jump.

### Look

Ink background. Copper charge, teal discharge, fault red. IBM Plex Sans + IBM Plex Mono (Google Fonts). Not Inter, not purple gradients, not a generic SaaS card grid.

---

## Tests (must exist)

- Store: write/read roundtrip on a tiny fleet (2–3 units, a few ticks). Command log is deltas-only. `mean_soc` and `cumulative_score_usd` correct. Offline flip emits `offline` then `online`. Clip when commanded ≠ actual.
- Prices: length 96; night band; afternoon max > 150.
- Serve: `/api/runs` lists a written run; `/api/runs/<id>` returns the same JSON; unknown id is 404.
- Demo: either a focused test that runs a **short** fixture (not full 80/100×96 in the default suite) *or* the demo script is covered by store+dispatch tests plus a smoke that `market_day_prices` + a 3-site loop writes a run. Do **not** put an 80×96 run in pytest.

---

## How you run it

```
.venv/bin/python scripts/demo_market_day.py
.venv/bin/python -m battery_fleet serve
cd dashboard && npm install && npm run dev
```
