# Controller Comparison Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a matched greedy and locked look-ahead pair using the normalized run format.

**Architecture:** A small script builds two independent but identical fleets, runs both controllers under the same market and outage schedule, and gives both outputs one comparison ID. It delegates all serialization to `write_run()`.

**Tech Stack:** Python 3.11+, pytest.

---

### Task 1: Generate a matched pair

**Files:**
- Create: `scripts/compare_controllers.py`
- Create: `tests/test_compare_controllers.py`

- [ ] **Step 1: Write a failing paired-run test**

Import:

```python
from scripts.compare_controllers import generate_comparison
```

Call:

```python
greedy_path, lookahead_path = generate_comparison(
    runs_dir=tmp_path,
    n_sites=2,
    n_units=3,
    seed=1,
)
```

Assert both summaries share comparison ID, fleet seed, step length, timestamps, prices, loads, and outage counts. Assert controller names are `greedy` and `lookahead`.

- [ ] **Step 2: Verify the test fails**

Run:

```bash
.venv/bin/pytest tests/test_compare_controllers.py -q
```

Expected: import fails because the script does not exist.

- [ ] **Step 3: Implement paired generation**

Expose:

```python
def generate_comparison(
    runs_dir: Path | str | None = None,
    n_sites: int = 80,
    n_units: int = 100,
    seed: int = 1,
) -> tuple[Path, Path]:
```

Create two fleets with identical build arguments. Use `Market.from_formula()`. Choose the first five unit IDs, or all units if fewer than five, as the outage set. Take them offline at tick 60 and online at tick 68 in both runs.

Run greedy with `run_market_day()` and locked look-ahead with `run_lookahead_day()`. Pass `ancillary_revenue_usd=0.0`.

Use:

```python
comparison_id = time.strftime("%Y%m%d-%H%M%S")
greedy_id = f"{comparison_id}-greedy"
lookahead_id = f"{comparison_id}-lookahead"
```

Write both normalized runs with the same comparison ID and seed. Return both run directories.

- [ ] **Step 4: Add a command-line entry point**

When executed directly, generate the default 80-installation and 100-unit pair and print:

```text
comparison: <comparison-id>
greedy: <greedy-run-directory>
lookahead: <lookahead-run-directory>
```

- [ ] **Step 5: Verify the script**

Run:

```bash
.venv/bin/pytest tests/test_compare_controllers.py -q
.venv/bin/python scripts/compare_controllers.py
```

Expected: tests pass and both printed directories contain `run.json`, `installation_ticks.jsonl`, and `unit_ticks.jsonl`.

### Task 2: Verify the complete data slice

- [ ] **Step 1: Run all Python tests**

Run:

```bash
.venv/bin/pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Check diagnostics**

Read IDE diagnostics for `battery_fleet/run_details.py`, `battery_fleet/run_summary.py`, `battery_fleet/store.py`, `scripts/compare_controllers.py`, and their tests. Expected: no new errors.

No commits are included unless the user requests one.
