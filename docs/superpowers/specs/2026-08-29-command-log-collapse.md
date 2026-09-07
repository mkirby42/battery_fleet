# Command log collapse

A price crossing logs ~100 identical setpoints. Unreadable.

## Behavior

`dashboard/src/CommandLog.tsx` (+ `rail.css` if the grid changes). Do not edit Python or the stored JSON.

Filter `time_unix <=` playhead, newest first, as now.

**Collapse setpoints** that share the same `time_unix` and the same `watts` (ε `1e-6`) into one row:

- kind: `setpoint`
- unit/site: `N units` (N = group size)
- watts: that shared value

Do not collapse target / offline / online / clip. Do not collapse setpoints that differ in watts.

**Drop the note column.** Header and rows: time, kind, unit/site, watts. Count is collapsed row count.

## Out of scope

Store schema, map, playback.

## Verify

`cd dashboard && npx tsc --noEmit`

Do not commit.
