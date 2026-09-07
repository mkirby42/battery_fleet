# Demo world fix

The dashboard is empty because the day is empty. Fix the world.

## Prices — `battery_fleet/prices.py`

`market_day_prices()` still 96 ticks, formula, not a CSV.

- Hours 0–6 (indices `0:24`): **all < −50**. So `solve_dispatch` charges. Band about −90 to −55.
- Hours 14–17 (indices `56:68`): still **max > 150**.
- Evening settles toward a small positive (idle), not another charge.

Update `tests/test_prices.py` `test_night_is_cheap` to match (night all `< -50`). Keep length-96 and afternoon-spike tests.

## Clock — `scripts/demo_market_day.py`

`t0` is **midnight UTC**, not `1_700_000_000`. Use `datetime(2024, 8, 15, tzinfo=timezone.utc).timestamp()` (ERCOT-summer-ish date). First tick label will be 00:15 after the step. That is fine.

## Offline during the spike

`run_market_day(..., offline_tick=60, online_tick=68)`. Five units still. Not 40/64 (that drops them before the money hour).

## Ancillary — `battery_fleet/demo.py`

`ancillary_revenue_usd` is `5.0` only when `abs(sum(commands.values())) > 1e-6`. Else `0.0`. Idle ticks must not write `$5` into `score_usd` / cumulative.

Add a tiny test: three prices `[-80, 20, 200]`, assert tick with idle-ish price 20 has `score.ancillary_revenue_usd == 0` (or `score_usd` without a $5 bump vs a 0-ancillary call).

## Out of scope

Dashboard CSS, map, log UI. Do not change `solve_dispatch` economics (the −50 / +50 break-evens stay).

## Verify

`.venv/bin/pytest tests/test_prices.py tests/test_dispatch.py tests/test_store.py -q`

Then regenerate:

`.venv/bin/python scripts/demo_market_day.py`

A good run has many charge ticks at night (`fleet_w > 0`), discharge around the spike (`fleet_w < 0`), `n_unreachable == 5` on ticks 60–67, and idle ticks with `score_usd` near 0 not 5. Print the new run id.

Do not commit.
