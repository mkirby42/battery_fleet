# Controller Analysis Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Save installation and unit histories separately while keeping old runs and the dashboard API compatible.

**Architecture:** Keep file input and output in `store.py`. Move payload construction out of that already-large file. Build installation and unit rows from `FleetTickRecord`, write them as JSON Lines, and hydrate unit rows when a normalized run is read.

**Tech Stack:** Python 3.11+, standard-library JSON, pytest.

---

### Task 1: Calculate installation and unit rows

**Files:**
- Create: `battery_fleet/run_details.py`
- Create: `tests/test_run_details.py`

- [ ] **Step 1: Write failing row tests**

Build one installation record with two units discharging 1,000 W and 500 W for 15 minutes at $200/MWh. Call:

```python
installation_rows, unit_rows = detail_rows(
    run_id="greedy-1",
    comparison_id="comparison-1",
    controller="greedy",
    records=records,
    dt_seconds=900.0,
)
```

Assert:

```python
site = installation_rows[0]
assert len(unit_rows) == 2
assert site["battery_w"] == -1_500.0
assert site["grid_w"] == 0.0
assert sum(row["customer_payment_change_usd"] for row in unit_rows) == pytest.approx(
    site["customer_bill_usd"] - site["no_battery_customer_bill_usd"]
)
assert sum(row["profit_contribution_usd"] for row in unit_rows) == pytest.approx(
    site["company_profit_usd"] - site["no_battery_company_profit_usd"]
)
```

- [ ] **Step 2: Verify the tests fail**

Run:

```bash
.venv/bin/pytest tests/test_run_details.py -q
```

Expected: collection fails because `battery_fleet.run_details` does not exist.

- [ ] **Step 3: Implement `detail_rows()`**

Create:

```python
def detail_rows(
    run_id: str,
    comparison_id: str,
    controller: str,
    records: list[FleetTickRecord],
    dt_seconds: float,
) -> tuple[list[dict], list[dict]]:
```

For each installation, call `score_tick()` with its load, actual battery power, commanded battery power, price, and step length. Use zero ancillary revenue.

Calculate:

```python
load_mwh = load_w / 1_000_000 * dt_hours
no_battery_company_profit_usd = (
    site_score.no_battery_customer_bill_usd
    - price_usd_per_mwh * load_mwh
)
wholesale_contribution_usd = -price_usd_per_mwh * unit_mwh
degradation_cost_usd = abs(actual_w) / 1000 * dt_hours * 0.05
tracking_penalty_usd = (
    abs(commanded_w - actual_w) / 1000 * dt_hours * 0.20
)
```

Customer payment change equals actual customer bill minus no-battery bill. Divide a negative change among units with `actual_w < 0` in proportion to `abs(actual_w)`. Otherwise assign zero.

Set unit profit contribution to wholesale contribution plus customer payment change minus wear and missed-delivery penalty.

- [ ] **Step 4: Add conservation and edge-case tests**

Test charging, idle units, different discharge amounts, and an unreachable unit retaining an old command. At every installation and step, assert that assigned customer payment changes and unit profit contributions reconcile with installation values.

- [ ] **Step 5: Verify the focused tests pass**

Run:

```bash
.venv/bin/pytest tests/test_run_details.py -q
```

Expected: all tests pass.

### Task 2: Write normalized run files

**Files:**
- Create: `battery_fleet/run_summary.py`
- Modify: `battery_fleet/store.py`
- Modify: `tests/test_store.py`

- [ ] **Step 1: Write failing storage tests**

Call:

```python
path = write_run(
    "greedy-1",
    fleet,
    records,
    900.0,
    runs_dir=tmp_path,
    comparison_id="comparison-1",
    controller="greedy",
    fleet_seed=1,
)
```

Assert all three files exist. Assert detail row counts equal steps multiplied by installations or units. Assert:

```python
assert summary["comparison_id"] == "comparison-1"
assert summary["controller"] == "greedy"
assert summary["fleet_seed"] == 1
assert summary["detail_files"] == {
    "installations": "installation_ticks.jsonl",
    "units": "unit_ticks.jsonl",
}
assert "units" not in summary["ticks"][0]
```

- [ ] **Step 2: Verify the storage tests fail**

Run:

```bash
.venv/bin/pytest tests/test_store.py -q
```

Expected: `write_run()` rejects the new metadata arguments.

- [ ] **Step 3: Split summary construction out of `store.py`**

Move static site and unit construction, fleet tick construction, command-event construction, and mean charge calculation into `run_summary.py`. Add a builder option that omits nested unit histories for normalized runs.

Keep `store.py` responsible for paths, file input and output, run listing, and calling builders.

- [ ] **Step 4: Extend `write_run()`**

Add keyword-only metadata:

```python
def write_run(
    run_id: str,
    fleet: Fleet,
    records: list[FleetTickRecord],
    dt_seconds: float,
    runs_dir: Path | str | None = None,
    *,
    comparison_id: str | None = None,
    controller: str | None = None,
    fleet_seed: int | None = None,
) -> Path:
```

Require either all three metadata values or none. With all three, write normalized files. With none, preserve old single-file behavior.

Write each complete file to a temporary sibling and replace the final file so readers never observe partial output.

- [ ] **Step 5: Hydrate normalized runs**

When `detail_files.units` exists, read unit rows and rebuild:

```python
tick["units"][unit_id] = {
    "soc": row["soc"],
    "actual_w": row["actual_w"],
    "commanded_w": row["commanded_w"],
    "reachable": row["reachable"],
}
```

Return the existing dashboard shape. Do not add installation details to the API response.

- [ ] **Step 6: Verify old and normalized formats**

Test that an old run still writes and reads nested units. Test that a normalized run stores separate details but reads back with nested units.

Run:

```bash
.venv/bin/pytest tests/test_store.py tests/test_serve.py -q
```

Expected: all tests pass.

No commits are included unless the user requests one.
