# Controller Analysis Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and execute a notebook that compares matched greedy and locked look-ahead runs using every installation and unit.

**Architecture:** The notebook reads saved JSON and JSON Lines files only. Small helper functions validate the pair and prepare reusable tables. Each requested chart gets a separate section and uses shared axis limits when plans are compared.

**Tech Stack:** JupyterLab, pandas, NumPy, Matplotlib.

---

### Task 1: Add a reproducible analysis environment

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore` or create: `analysis/.gitignore`

- [ ] **Step 1: Add optional analysis dependencies**

Add:

```toml
[project.optional-dependencies]
dev = ["pytest"]
analysis = ["jupyterlab", "matplotlib", "numpy", "pandas"]
```

Ignore `.ipynb_checkpoints/`.

- [ ] **Step 2: Install the analysis environment**

Run:

```bash
.venv/bin/pip install -e ".[analysis]"
```

Expected: installation completes without dependency errors.

### Task 2: Create notebook loading and validation cells

**Files:**
- Create: `analysis/controller_analysis.ipynb`

- [ ] **Step 1: Create the notebook with the notebook editor**

Create a title cell explaining that the notebook compares company and customer outcomes for matched greedy and locked look-ahead runs.

Create a configuration cell:

```python
from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RUNS_DIR = Path("../runs")
COMPARISON_ID = None
```

When `COMPARISON_ID` is `None`, select the newest comparison ID that has both controllers.

- [ ] **Step 2: Load both run directories**

Implement notebook-local helpers:

```python
def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def load_jsonl(path: Path) -> pd.DataFrame:
    return pd.read_json(path, lines=True)


def load_run(path: Path) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    summary = load_json(path / "run.json")
    installations = load_jsonl(path / summary["detail_files"]["installations"])
    units = load_jsonl(path / summary["detail_files"]["units"])
    return summary, installations, units
```

Locate summaries with matching comparison IDs and controller names.

- [ ] **Step 3: Validate that the comparison is fair**

Assert matching:

- comparison ID
- fleet seed
- step length
- step timestamps
- prices
- total loads
- unreachable counts
- static installation IDs
- static unit IDs

Display the selected run IDs and controller names.

### Task 3: Build summary tables and histograms

**Files:**
- Modify: `analysis/controller_analysis.ipynb`

- [ ] **Step 1: Calculate daily unit and installation totals**

Create:

```python
unit_daily = (
    units.groupby(["controller", "unit_id"], as_index=False)
    .agg(profit_usd=("profit_contribution_usd", "sum"))
)

installation_daily = (
    installations.groupby(["controller", "install_id"], as_index=False)
    .agg(
        customer_bill_usd=("customer_bill_usd", "sum"),
        no_battery_bill_usd=("no_battery_customer_bill_usd", "sum"),
    )
)
```

- [ ] **Step 2: Plot unit-profit histograms**

Calculate common bin edges from both controllers with `np.histogram_bin_edges(..., bins="auto")`. Create one subplot per controller. Use the same bins and x limits. Add mean and zero reference lines.

- [ ] **Step 3: Plot customer-bill histograms**

Use common bins and x limits. Create one subplot per controller. Add a dashed no-battery reference line. Label every axis with dollars and installation count.

### Task 4: Plot unit charge levels

**Files:**
- Modify: `analysis/controller_analysis.ipynb`

- [ ] **Step 1: Prepare charge-level tables**

For each controller, pivot unit data with time as rows, unit ID as columns, and `soc` as values. Calculate row mean and population standard deviation.

- [ ] **Step 2: Plot every unit and the fleet band**

Create one subplot per controller with shared axes. Draw every unit at low opacity and thin width. Draw the mean at full opacity and thicker width. Use `fill_between()` for mean minus and plus one standard deviation. Clamp the y-axis to zero through one.

### Task 5: Plot all installation power

**Files:**
- Modify: `analysis/controller_analysis.ipynb`

- [ ] **Step 1: Create the 80-panel plotting function**

Implement:

```python
def plot_installations(frame: pd.DataFrame, controller: str) -> None:
    selected = frame[frame["controller"] == controller]
    install_ids = sorted(selected["install_id"].unique())
    fig, axes = plt.subplots(10, 8, figsize=(24, 30), sharex=True, sharey=True)
    for axis, install_id in zip(axes.flat, install_ids):
        site = selected[selected["install_id"] == install_id]
        axis.plot(site["time_unix"], site["load_w"], label="demand")
        axis.plot(site["time_unix"], site["battery_w"], label="battery")
        axis.plot(site["time_unix"], site["grid_w"], label="grid")
        axis.set_title(install_id)
    fig.legend(["demand", "battery", "grid"], loc="upper center", ncol=3)
    fig.suptitle(f"{controller}: every installation")
    fig.tight_layout()
```

Hide unused axes if a smaller test comparison is loaded. Call the function once for greedy and once for look-ahead.

### Task 6: Plot price against demand

**Files:**
- Modify: `analysis/controller_analysis.ipynb`

- [ ] **Step 1: Build fleet time series**

Group installation rows by controller and time. Sum `load_w` and `grid_w`. Join wholesale price from `run.json`.

- [ ] **Step 2: Create time-series and scatter views**

Create a time-series figure with wholesale price on one axis and total house and grid demand on the other. Draw one grid-demand line per controller and one house-demand reference line.

Create a scatter plot with wholesale price on the x-axis and total grid demand on the y-axis. Use one color per controller and include zero-grid-power reference.

### Task 7: Display final summary and execute

**Files:**
- Modify: `analysis/controller_analysis.ipynb`
- Modify: `docs/current_state.md`
- Modify: `docs/runbook.md`
- Modify: `docs/project-log/2026-09-01.md`

- [ ] **Step 1: Calculate the final summary**

Group installation rows by controller and calculate total company profit, customer bill, no-battery bill, wholesale settlement, wear, and missed-delivery penalty. Join unit profit mean, standard deviation, minimum, and maximum.

Display the result as a styled pandas table.

- [ ] **Step 2: Execute the notebook**

Run:

```bash
.venv/bin/jupyter nbconvert \
  --to notebook \
  --execute analysis/controller_analysis.ipynb \
  --output controller_analysis.ipynb \
  --output-dir analysis
```

Expected: exit code zero and every chart cell contains output.

- [ ] **Step 3: Verify the notebook**

Read the executed notebook and confirm:

- both controller names appear
- both histograms contain data
- charge-level figures include 100 unit lines
- each installation figure includes all 80 installation titles
- price and demand figures contain both controllers
- no cell contains an exception

- [ ] **Step 4: Update documentation**

Add the comparison-generation command and notebook command to the runbook. Update current state with links to the normalized run data and notebook. Record measured results and anything that broke in the daily project log.

- [ ] **Step 5: Run final checks**

Run:

```bash
.venv/bin/pytest -q
```

Read IDE diagnostics for edited Python files. Expected: all tests pass and no new diagnostics exist.

No commits are included unless the user requests one.
