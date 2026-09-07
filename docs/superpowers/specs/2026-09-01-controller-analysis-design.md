# Controller analysis design

## Goal

Generate matched greedy and locked look-ahead runs, save fleet, installation, and unit data at separate grains, and compare both plans in a repeatable analysis notebook.

## Run generation

Add `scripts/compare_controllers.py`.

The script creates two fleets with the same build arguments:

- 80 installations
- 100 units
- seed 1
- the same start time
- the same made-up wholesale market
- the same outage schedule
- the same 1,500 W load at every installation

One fleet runs greedy. The other runs locked look-ahead. Ancillary revenue is zero because the current flat five-dollar placeholder cannot be assigned honestly to an installation or unit.

Each controller gets its own run ID and run directory. Both runs include a shared comparison ID so the notebook can verify that they belong together.

## Saved files

Each new run directory contains:

```text
runs/<run-id>/
├── run.json
├── installation_ticks.jsonl
└── unit_ticks.jsonl
```

JSON Lines stores one complete record per line. This avoids loading the full detailed history just to inspect or process part of it.

### `run.json`

`run.json` contains:

- run ID
- comparison ID
- controller name
- fleet seed
- start time
- step length
- static installation data
- static unit data
- fleet totals for every step
- names of the installation and unit detail files

New `run.json` files do not repeat unit histories inside every fleet step.

### `installation_ticks.jsonl`

Each row contains:

- `run_id`
- `comparison_id`
- `controller`
- `tick_index`
- `time_unix`
- `install_id`
- `load_w`
- `battery_w`
- `grid_w`
- `customer_bill_usd`
- `no_battery_customer_bill_usd`
- `wholesale_pnl_usd`
- `degradation_cost_usd`
- `tracking_penalty_usd`
- `company_profit_usd`

Installation company profit excludes ancillary revenue.

### `unit_ticks.jsonl`

Each row contains:

- `run_id`
- `comparison_id`
- `controller`
- `tick_index`
- `time_unix`
- `install_id`
- `unit_id`
- `soc`
- `actual_w`
- `commanded_w`
- `reachable`
- `wholesale_contribution_usd`
- `customer_payment_change_usd`
- `degradation_cost_usd`
- `tracking_penalty_usd`
- `profit_contribution_usd`

Unit profit contribution measures the change in company profit caused by that unit:

```text
unit profit contribution
    = wholesale contribution
    + customer payment change
    - wear
    - missed-delivery penalty
```

Customer payment change is zero while charging. During discharge it is negative because lowering the customer bill removes company revenue.

For each installation and step, customer payment change equals the actual customer bill minus the no-battery customer bill. If it is negative, it is divided among discharging units in proportion to their delivered discharge energy. If no customer bill reduction occurred, every unit gets zero. The assigned values must add back to the installation value.

The unit contributions at an installation must add to actual installation company profit minus no-battery installation company profit. No-battery company profit is the no-battery customer bill plus wholesale settlement on house load alone.

## Compatibility

Existing saved runs contain unit histories inside `run.json`. They must continue to load.

For new runs, `read_run()` reads the two JSON Lines files and rebuilds the existing dashboard response with `ticks[].units`. The server API and dashboard data shape stay unchanged.

Tests cover:

- the three files are written
- row counts equal steps multiplied by installations or units
- installation rows add back to fleet totals
- unit customer-payment changes add back to installation changes
- unit profit contributions add back to battery-caused company profit
- new runs load into the existing dashboard shape
- old single-file runs still load

## Analysis notebook

Create `analysis/controller_analysis.ipynb`.

The notebook only reads saved runs. It does not run simulations or contain copies of simulation rules.

The first cell accepts the greedy and look-ahead run directories. It verifies that both runs have the same comparison ID, fleet seed, times, prices, loads, and outage schedule.

The notebook uses pandas, NumPy, and Matplotlib. Add an `analysis` optional dependency group to `pyproject.toml` containing JupyterLab, Matplotlib, NumPy, and pandas so the notebook environment is reproducible.

### Unit profit histograms

For each controller, sum `profit_contribution_usd` by unit over the full day. Plot greedy and look-ahead as separate, aligned histograms with identical bin edges and axis limits.

### Installation customer-bill histograms

For each controller, sum `customer_bill_usd` by installation over the full day. Plot both distributions with identical bin edges and axis limits. Include the no-battery bill as a vertical reference line.

### Unit charge-level time series

Create one figure per controller.

- Draw every unit's charge level as a faint line.
- Draw the fleet mean as a solid line.
- Shade mean minus one standard deviation through mean plus one standard deviation.
- Keep both controller figures on the same time and charge-level axes.

### Installation power time series

Create one 8-column by 10-row figure per controller so all 80 installations are present.

Each small chart shows:

- house demand
- battery power
- grid power

All charts use the same time range. Charts use the same power range within each controller figure so installations can be compared visually.

### Price versus demand

Create one time-series figure with wholesale price and total grid demand for both controllers.

Also show total house demand as a reference. It is expected to be flat in the current demo because every installation uses 1,500 W.

Create a second scatter plot of wholesale price against total grid demand. Use one color per controller.

### Summary

End with a compact summary containing:

- total company profit
- total customer bill
- customer savings from the no-battery case
- total wholesale settlement
- total wear
- total missed-delivery penalty
- mean and standard deviation of unit profit contribution
- minimum and maximum unit profit contribution

## Documentation

Update `docs/current_state.md` after implementation. Add generation and notebook commands to `docs/runbook.md`. Record the completed comparison and any surprising results in the daily project log.
