# Availability snapshot CI (nested FPL lists)

**Objective:** Unblock hourly Capture availability snapshot Action. Keep both GitHub workflows. Hash nested list columns from live bootstrap/fixtures.

**Acceptance:** `write_availability_snapshot` hashes players/clubs/fixtures with list fields (`price_change_projections`, `scout_risks`, fixture `stats`). Local capture writes GW1 package. Tests cover nested columns. Workflows pin Python 3.14; `checkout@v5` + `setup-uv@v7`.

## Seams (TDD)

- `features.availability_snapshots._canonical_frame` — JSON-serialize nested cells before sort/hash
- `tests.test_availability_snapshots.test_writer_hashes_nested_list_columns`

## Work Packet (SFDBN)

- **Status:** Implemented. Commit + push this packet. `origin/availability-snapshots` still missing until Capture Action writes.
- **Files:** `features/availability_snapshots.py`; `tests/test_availability_snapshots.py`; `.github/workflows/capture_availability_snapshot.yml`; `.github/workflows/evaluate_model_promotion.yml`; `task.md`; `docs/agents/current-state.md`; `.agents/session-handoff.md`
- **Decisions:** Keep both workflows (promotion already green). Root fail = pandas `sort_values` on unhashable lists, not unused YAML. Canonicalize nested JSON; do not drop FPL columns.
- **Blocked:** none
- **Next:**
  - [x] Reproduce hourly Action fail (list columns)
  - [x] Canonical hash + test
  - [x] Pin workflow Python/actions
  - [x] Commit + push so next hourly run can create `availability-snapshots`
  - [ ] User: copy pre-WC 15 into FPL app before GW1 deadline (`operational_squads.csv` `pre-WC`; XI `operational_select_11.csv` `gw=1`; Bench Boost)
