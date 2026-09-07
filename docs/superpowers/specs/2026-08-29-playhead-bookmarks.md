# Playhead bookmarks

12s of PLAY through idle ticks hides the only interesting minutes.

## Behavior

`dashboard/src` only. Do not edit Python.

Derive up to three bookmarks from the loaded `Run`:

| id | label | first tick where |
| --- | --- | --- |
| charge | CHARGE | `fleet_w > 10_000` |
| spike | SPIKE | max `price_usd_per_mwh` (skip nulls) |
| offline | OFFLINE | `n_unreachable > 0` |

Omit a mark if that tick does not exist. Same tick may win two names; one diamond, labels joined with ` · `.

Diamonds sit on the scrubber range at that tick. Click → `setIndex(tick)` and pause. Label shows on hover and when the playhead is on that tick.

**PLAY starts at the first bookmark index** (CHARGE if present, else OFFLINE, else SPIKE, else 0). Not tick 0 if a bookmark exists.

Active diamond (current index == that tick) fills copper. PLAY is the only rectangular toggle.

## Files

`playback.ts` (optional helper `bookmarks(run)`), `Scrubber.tsx`, `App.tsx`, `rail.css`. Keep every file under 250 lines.

## Out of scope

Do not change prices, map, or command log.

## Verify

`cd dashboard && npx tsc --noEmit`

Do not commit.
