---
name: run-spinup
description: Start a sim run the only legal way and refresh the generated index. Use when creating a run, adding a scenario, or when someone is about to mkdir under runs/.
---

# Run spinup

## Do

```bash
python -m battery_fleet run scenarios/<name>.yaml
```

That function: validate → create folder → snapshot pieces into `run.db` → step → checks → `success` only if checks pass → rebuild `runs/index.json` from folders.

## Do not

- `mkdir` under `runs/`
- Edit `runs/index.json` by hand
- Mark a run `success` if checks failed or the loop died
- Point a run at live scenario files after spinup (the db must own its copies)

## Comparable pair

Two successes are comparable only if the cards share locations, units, installs, market event, outages, weather, seed, HQ policy — and differ by local policy.
