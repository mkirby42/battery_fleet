---
name: trust-a-run
description: How every run earns trust — a short card plus automated checks. Use when finishing a run, writing checks, or when someone wants more uncertainty work.
---

# Trust a run

Every `run.db` gets:

1. **Card** — which pieces, seed, schema version, status, error.
2. **Checks** — rows that actually ran, not a vibe.

v1 checks:

- SOC in [0, capacity]
- Islanded location ⇒ no market kWh
- `fixed_reserve` never market-discharges through the floor
- Ticks line up with 5-min prices
- Failed run never marked success

Dashboard and notebook treat only `success` as playable/comparable by default.

Full uncertainty (many seeds, ranges, error bars) is `notes/later.md`. Do not start it.
