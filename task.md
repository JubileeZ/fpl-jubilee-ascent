# Task Work Packet

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** `data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv`, `docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md`, `docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py`, `data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv`, `data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/gw1-5_projections.csv`, `docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/build_expected_stats.py`, `docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.md`, `data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv`, `data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv`, `docs/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md`, `docs/research/gw1-6-preseason-pipeline/README.md`, `data/research/ownership-value-explorer/ownership_value_explorer.html`, `data/research/ownership-value-explorer/ownership_value_metrics.csv`, `data/research/ownership-value-explorer/season_projections.csv`, `docs/research/ownership-value-explorer/ownership-value-explorer.md`, `docs/agents/current-state.md`, `task.md`
- **Decisions:** 
  1. Full 564 FPL API player coverage in Expected Role dataset (5 roles: Nailed Starter, Regular Starter, Rotation, Cameo, Out of Contention).
  2. Multi-source consensus combining final preseason friendly lineups, Community Shield, official club news, FFS Team News, and FPL Meerkat.
  3. Minimum 900 minutes floor for 2025/26 Prior-Season Seed in Stage 2; researched career packages (FBref/European/Championship stats) for non-seed starters/rotation players; zero Draft on fallback baseline.
  4. Single canonical scenario in Stage 3: GW1 BB + WC4 with locked transfers in GW1-3, GW4 WC rebuild, GW5 roll FT (bank 4 FTs into GW6).
  5. Full-season (GW1-38) and GW1-6 Ownership Value Explorer updated with GW1 BB Core (★) and WC4 Core (⬡) overlays.
- **Blocked:** None.
- **Next:** Ready for commit and review.
- **Objective:** Overhaul preseason pipeline across Stages 1-3 and Ownership Value Explorer to reflect complete preseason evidence, 564-player coverage, 900-min seed floor with FBref career packages, GW1 BB + WC4 optimization, and interactive HTML refresh.
- **Acceptance:**
  - [x] Stage 1: All 564 FPL API players classified into 5 Expected Roles with Participation State priors; `expected-role-gw1-5.csv` and doc updated.
  - [x] Stage 2: `MIN_USABLE_MINUTES = 900` applied; career stats packages provided for all non-seed Draft-Eligible/Rotation players; `expected-stats-gw1-5.csv` and projections generated with zero Draft on fallback.
  - [x] Stage 3: GW1 BB + locked GW1-3 + WC4 + GW5 roll simulation executed; `gw1-6_wc4_simulation.csv` and `gw1-6_wc4_summary.csv` generated; markdown documentation updated.
  - [x] Ownership Value Explorer: Season projections (GW1-38) and value metrics recalculated across all 564 players; interactive HTML and note refreshed with ★/⬡ badges.
  - [x] Code quality: `uv run ruff check .`, `uv run pytest`, and `bash tests/verify.sh` green.
