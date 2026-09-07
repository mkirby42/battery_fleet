# Sim run dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **This repo:** work in the current workspace. No git worktree. **Do not commit** unless the user asks. Run tests with `.venv/bin/pytest`.

**Goal:** Persist a 24h fleet run as JSON, serve it locally, scrub it on a dark map with charts and a command log.

**Architecture:** `write_run` turns `Fleet` + `FleetTickRecord`s into `runs/<id>/run.json` (sites, units, ticks, derived command deltas). Stdlib HTTP exposes `/api/runs` and `/api/runs/<id>`. Vite React app proxies `/api` and plays the newest run.

**Tech Stack:** Python 3.11+, pytest, no new Python deps. React + Vite + TS, Leaflet, react-leaflet, lightweight-charts, IBM Plex.

**Spec:** `docs/superpowers/specs/2026-08-29-sim-run-dashboard-design.md`

---

## File map

| File | Responsibility |
| --- | --- |
| `battery_fleet/store.py` | write/read/list + derive commands / mean_soc / cumulative |
| `battery_fleet/prices.py` | 96 baked prices |
| `battery_fleet/serve.py` | HTTP handler |
| `battery_fleet/__main__.py` | `python -m battery_fleet serve` |
| `scripts/demo_market_day.py` | 80/100 × 96 dispatch + offline + write_run |
| `runs/.gitkeep` | keep empty runs dir |
| `tests/test_store.py` | store + command log |
| `tests/test_prices.py` | price series |
| `tests/test_serve.py` | HTTP |
| `dashboard/` | Vite app (see Task 4–5) |
| `docs/runbook.md` | how to run |

Existing code you call, do not rewrite: `build_fleet`, `run_fleet`, `solve_dispatch`, `FleetTickInput`, `BatteryUnit.go_offline` / `come_online`.

---

### Task 1: Store

**Files:**
- Create: `battery_fleet/store.py`
- Create: `runs/.gitkeep`
- Create: `tests/test_store.py`
- Modify: `battery_fleet/__init__.py` — export `write_run`, `read_run`, `list_runs` only if other tests import from the package root; prefer `from battery_fleet.store import ...` in tests.

TDD. Tiny fleet only (2 sites, 3 units). Use `tmp_path` as `runs_dir`.

- [ ] **Step 1: Write failing tests** in `tests/test_store.py`

Reuse the two-site helper pattern from `tests/test_dispatch.py` (`T0 = 1_700_000_000.0`, `DT = 900.0`).

Required tests:

1. `test_write_read_roundtrip` — one tick, all units charge 2000 W, load 1500. After `write_run` / `read_run`: same `id`, `dt_seconds`, site lat/lon, unit ids, tick `fleet_w`, per-unit `soc` / `actual_w` / `commanded_w` / `reachable`.
2. `test_mean_soc_and_cumulative_score` — two ticks with prices so `score` is not None. `mean_soc` is the mean of unit SOCs that tick. `cumulative_score_usd` on tick 1 equals tick 0 `score_usd` + tick 1 `score_usd`.
3. `test_command_log_deltas_only` — three ticks, same command map every tick (2000 W). Exactly one `setpoint` per unit (first tick, commanded ≠ 0). Not 3× units.
4. `test_target_logged_when_it_changes` — tick 0 target 1000, tick 1 target 2000. Two `target` events, watts 1000 then 2000.
5. `test_offline_then_online_logged` — after tick 0, `go_offline` one unit; tick 1; `come_online`; tick 2. Events include `offline` then `online` for that `unit_id`. No offline/online on tick 0.
6. `test_clip_when_commanded_ne_actual` — command a unit more than charge headroom (e.g. 1e9 W) so actual clips. One `clip` for that unit.
7. `test_list_runs_newest_first` — write `aaa` then `bbb`. `list_runs` returns `bbb` then `aaa`, each with `id`, `started_at_unix`, `n_ticks`.

- [ ] **Step 2: Run tests, confirm they fail** (import or assert)

```
.venv/bin/pytest tests/test_store.py -q
```

- [ ] **Step 3: Implement `store.py`**

```
write_run(run_id, fleet, records, dt_seconds, runs_dir=None) -> Path
read_run(run_id, runs_dir=None) -> dict
list_runs(runs_dir=None) -> list[dict]
```

Default `runs_dir`: repo-root `runs` (parent of `battery_fleet/`). Create `runs_dir / run_id / run.json`. JSON indent 2.

Build `sites` / `units` from the `Fleet` object (lat/lon live there). Build `ticks` from records. Derive commands per spec (epsilon `1e-6` for clip and float compare).

If `record.score` is None: `price_usd_per_mwh`, `score_usd`, `energy_pnl_usd` are JSON `null`. Cumulative adds 0.

- [ ] **Step 4: Tests pass**

```
.venv/bin/pytest tests/test_store.py -q
```

- [ ] **Step 5: Add `runs/.gitkeep`.** Do not commit.

---

### Task 2: Prices + demo script

**Files:**
- Create: `battery_fleet/prices.py`
- Create: `tests/test_prices.py`
- Create: `scripts/demo_market_day.py`

Depends on Task 1.

- [ ] **Step 1: Failing tests** `tests/test_prices.py`

```
from battery_fleet.prices import market_day_prices

def test_ninety_six_prices():
    assert len(market_day_prices()) == 96

def test_night_is_cheap():
    prices = market_day_prices()
    night = prices[0:24]  # hours 0–6
    assert all(10.0 <= p <= 40.0 for p in night)

def test_afternoon_spikes():
    prices = market_day_prices()
    afternoon = prices[56:68]  # hours 14–17
    assert max(afternoon) > 150.0
```

Also add `test_short_demo_writes_run` in the same file or `tests/test_demo_market_day.py`: a **3-tick** helper is fine — do **not** run 80×96 in pytest. Either extract `run_market_day(fleet, prices, offline_at, online_at, runs_dir)` into `battery_fleet/demo.py` and call it from the script with the full series, **or** keep the loop only in the script and test prices + store only. Prefer `battery_fleet/demo.py` with:

```
run_market_day(fleet, prices, dt_seconds, offline_unit_ids, offline_tick, online_tick, ancillary_revenue_usd=5.0) -> list[FleetTickRecord]
```

Then `test_run_market_day_marks_offline` uses a 3-site / 3-unit fleet, 3 prices, offline at tick 1, online at tick 2. Assert tick 1 `n_unreachable == 1` and the written command log has offline then online.

- [ ] **Step 2: Tests fail, then implement `prices.py` + `demo.py`**

`market_day_prices`: formula. Night ~20, afternoon peak >150.

`run_market_day`: each price → `solve_dispatch` → before the tick, if index == offline_tick call `go_offline` on those units; if index == online_tick call `come_online`; then `run_fleet` one `FleetTickInput` (loads 1500 every site, commands, target=sum, price, ancillary 5).

- [ ] **Step 3: `scripts/demo_market_day.py`**

```
t0 = 1_700_000_000.0
fleet = build_fleet(80, 100, t0, 1)
ids = first five unit ids in walk order
records = run_market_day(..., market_day_prices(), 900, ids, 40, 64)
run_id = time-based string
write_run(run_id, fleet, records, 900)
print run_id and path
```

- [ ] **Step 4: Pytest passes.** Do not run the 80×96 script unless asked. Do not commit.

---

### Task 3: Serve

**Files:**
- Create: `battery_fleet/serve.py`
- Create: `battery_fleet/__main__.py`
- Create: `tests/test_serve.py`

Depends on Task 1. Do not start a real listening server in tests if you can call the handler; `http.server` + `threading` + `urllib` against `127.0.0.1:0` (ephemeral port) is OK.

- [ ] **Step 1: Failing tests**

Write a tiny run into `tmp_path`. Start serve bound to that `runs_dir`.

1. `GET /api/runs` → 200, JSON list, includes the id.
2. `GET /api/runs/<id>` → 200, same `id` and tick count as `read_run`.
3. `GET /api/runs/nope` → 404.
4. Response has `Access-Control-Allow-Origin: *`.

- [ ] **Step 2: Implement**

`serve.main(host="127.0.0.1", port=8000, runs_dir=None)`.

`python -m battery_fleet serve` only. Other argv: print usage, exit 2.

- [ ] **Step 3: Tests pass.** Do not commit.

---

### Task 4: Dashboard scaffold

**Files:** `dashboard/` Vite React TS. Proxy `/api` → `http://127.0.0.1:8000`.

- [ ] **Step 1:** `npm create vite@latest` (react-ts) in `dashboard/` or write `package.json` + `vite.config.ts` + `index.html` + `src/main.tsx` by hand. Add `leaflet`, `react-leaflet`, `lightweight-charts`.

- [ ] **Step 2:** `src/types.ts` — types matching the spec JSON exactly (field names).

- [ ] **Step 3:** `src/api.ts` — `listRuns()`, `getRun(id)` using `fetch('/api/...')`.

- [ ] **Step 4:** `src/App.tsx` — load newest run. Empty/error copy exactly:

`Generate a run: .venv/bin/python scripts/demo_market_day.py then .venv/bin/python -m battery_fleet serve`

Placeholder main: run id + tick count if loaded.

- [ ] **Step 5:** `src/theme.css` — ink background, copper `#c47b3a`, teal `#3ecfc1`, fault `#e85d4c`. IBM Plex Sans + Plex Mono from Google Fonts in `index.html`.

- [ ] **Step 6:** `npx tsc --noEmit` clean. No file over 250 lines. Do not commit.

---

### Task 5: Map, charts, log, scrubber

**Files:**
- `src/playback.ts` — `tickIndex`, `playing`, step ~8/s (`125` ms), clamp 0..n-1
- `src/KpiBar.tsx`
- `src/MapPanel.tsx`
- `src/ChartsPanel.tsx`
- `src/CommandLog.tsx`
- `src/Scrubber.tsx`
- Wire into `App.tsx`

- [ ] **KPIs:** clock from `time_unix` (local or UTC, label which), price, fleet MW and target MW (W/1e6, 3 decimals), `error_w`, `n_unreachable`, `score_usd`.

- [ ] **Map:** `MapContainer` Carto Dark Matter (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`, attribution Carto/OSM). CircleMarkers. Colors per spec. Tooltip on hover with unit rows.

- [ ] **Charts:** two `lightweight-charts` panes, playhead at current `time_unix`. Series: fleet_w, target_w, price; mean_soc, cumulative_score_usd.

- [ ] **Log:** filter `time_unix <=` current, newest first.

- [ ] **Scrubber:** range input + play/pause. Layout: full-bleed map, overlay KPIs, right rail charts+log, bottom scrubber.

- [ ] `tsc --noEmit` clean. Do not commit.

---

### Task 6: Polish, runbook, first run, project log

- [ ] Visual pass: spacing, type scale, KPI overlay readable on the map, log rows tabular, playhead obvious. Stay on the copper/teal/ink language. No purple gradient.

- [ ] Append to `docs/runbook.md`:

```
## Dashboard

.venv/bin/python scripts/demo_market_day.py
.venv/bin/python -m battery_fleet serve
cd dashboard && npm install && npm run dev
```

- [ ] Run the demo script once (80/100 × 96). Confirm `runs/<id>/run.json` exists and is valid JSON.

- [ ] `.venv/bin/pytest -q` all green.

- [ ] Append `docs/project-log/2026-08-29.md` (project-log skill): what happened, the first run id, anything that broke. Not a file list.

- [ ] Do not commit. Do not deploy.

---

## Review gates (controller)

After each task: spec compliance against `2026-08-29-sim-run-dashboard-design.md`, then code quality. Fix before the next task.

Do not add SQLite, GitHub Pages, ERCOT clients, or extra APIs.
