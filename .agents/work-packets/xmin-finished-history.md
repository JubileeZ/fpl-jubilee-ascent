# Active Task: Live xMins from finished Club Fixtures

- **Status:** In Progress
- **Objective:** Full-Season / Dashboard Refresh must not drop finished Club Fixtures when feature rows start at GW1
- **Acceptance:** Two finished 90s at `build_features(target_gw=1)` without `history_before_gw` keep Start weight; Egan-class xMins not empty-tenure ~30; `uv run ruff check .`; `uv run pytest`; `bash tests/verify.sh`
- **Issue/Ticket:** ADR 0026

## Work Packet (SFDBN)

- **Status:** Implementing
- **Files:** `features/builder.py`, `commands/dashboard.py`, `commands/export_dashboard.py`, `commands/run_model.py`, `tests/test_club_fixture_shrinkage.py`
- **Decisions:** Live/exploratory cutoff = max(target_gw, last finished Club Fixture GW + 1). Point-in-time `target_deadline` still uses target_gw. Operational dir: `data/processed` else live Season Archive pin.
- **Blocked:** None
- **Next:** Browser Refresh click after pull (export-only Egan avg xMins 70.3 verified)

## Todo
- [x] Full-Season GW1 keeps finished 90s without history_before_gw
- [x] Operational processed dir falls back to live archive pin
- [x] Live Refresh + Egan xMins check
- [ ] Browser Refresh click after origin pull

## Blockers / Notes
- Explorer 29.8 on Egan = empty tenure Position-Price, not two 90s.
- After `refresh_data` + `--export-only`: Egan id 277 GW3–8 avg xMins 70.3 (not ~30). GW3 Hull still unfinished; two finished 90s train state. pytest 292; verify.sh 75.
