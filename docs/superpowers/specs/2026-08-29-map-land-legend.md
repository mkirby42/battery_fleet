# Map: inland sites + legend

Random 26–36 N / 106–94 W puts pins in the Gulf and on top of each other. No legend.

## Placement — `battery_fleet/fleet.py`

Replace the Texas box with an **inland** box (no Gulf):

- lat `29.0`–`34.5`
- lon `−102.0`–`−95.5`

When placing a site, **reject** a draw if it is within `0.25` degrees (approx Euclidean in lat/lon) of an already placed site. Retry up to 80 times, then keep the last draw.

Two units at one house still share one pin. Do not jitter units.

Update `tests/test_fleet.py` `test_build_fleet_places_sites_in_texas_box` to the new box. Add `test_build_fleet_sites_are_separated`: 80 sites, seed 1, every pair ≥ `0.25` deg (or all-but-the-exhausted-retry; with 80 sites in this box, 0.25 should fit — assert min pairwise ≥ 0.25).

## Legend — `dashboard/src/MapPanel.tsx` / CSS

Four-item overlay, bottom-left above the run chip (or bottom-right if it collides):

- copper swatch — charge
- teal — discharge
- muted — idle
- red ring (empty circle) — unreachable

Keep Carto Dark Matter, site circles, existing color rules.

## Out of scope

Hover hit-testing (separate spec). Bookmarks, log, prices.

## Verify

`.venv/bin/pytest tests/test_fleet.py -q`

`cd dashboard && npx tsc --noEmit`

Do not regenerate the 80/100 demo run (world-fix agent owns that). Do not commit.
