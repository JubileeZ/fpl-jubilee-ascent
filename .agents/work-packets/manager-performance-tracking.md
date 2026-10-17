# Active Task: Manager Performance Tracking

- **Status:** Complete
- **Objective:** Design and implement a manager performance tracking workspace in Streamlit: rank & points over time across gameweeks, user and rival/global chip markers, lazy-loading comparison manager selector across joined leagues, delta vs league/global average to isolate rank movement drivers, Set 1/2 chip inventory matrix, and make it the default landing workspace with Entry ID resolution.
- **Acceptance:**
  1. `CONTEXT.md` updated with canonical glossary definitions (`Performance Surface`, `Entry History`, `Classic Mini-League`, `Comparison Managers`, `Global Gameweek Benchmark`, `Net Gameweek Points`).
  2. `clients/fpl_api.py` includes `fetch_classic_league_standings` with retry and raw cache saving.
  3. `features/processor.py` preserves `average_entry_score`, `highest_score`, `chip_plays`, and `ranked_count` in `gameweeks.parquet`.
  4. `dashboard/performance_service.py` provides two-tier (memory + disk) cached, polite on-demand fetching for `/entry/{id}/`, `/entry/{id}/history/`, and `/leagues-classic/{id}/standings/` with stale-cache fallback on rate-limits.
  5. `dashboard/performance_analytics.py` calculates per-GW manager metrics, benchmark deltas (Global vs Selected Rivals), chip timing attribution, and Set 1/2 chip inventories.
  6. `dashboard/performance_view.py` renders the responsive, Apple-utility-styled `Performance` workspace with Entry ID resolution, KPI strip, 3 Plotly charts (Rank/Points Trajectory with geometric chip markers, Diverging Delta Bar with Cumulative step-line, and Chip Adoption Strip), and attribution / chip matrix tabs.
  7. `dashboard/streamlit_dashboard.py` registers `Performance` as the first workspace in `PAGES` and handles default landing logic.
  8. Full test suite in `tests/test_manager_performance.py` passes with zero live external HTTP requests.
  9. Pre-commit gate (`ruff check .`, `pytest`, `verify.sh`) passes cleanly.

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** `CONTEXT.md`, `clients/fpl_api.py`, `features/processor.py`, `commands/export_dashboard.py`, `dashboard/performance_service.py`, `dashboard/performance_analytics.py`, `dashboard/performance_view.py`, `dashboard/streamlit_dashboard.py`, `tests/test_manager_performance.py`, `tests/test_streamlit_dashboard.py`, `tests/test_underlying_actuals.py`
- **Decisions:**
  - Manager-first view by default; zero peer histories fetched automatically.
  - Pull-as-you-go lazy fetching for at most 5 comparison managers from mini-league top 50 or manual Entry ID.
  - Two-tier memory (`@st.cache_data`) + disk (`data/planner/fpl_cache/`) caching with 15m TTL and stale fallback on 429/5xx.
  - Default per-GW baseline = Global Average (`average_entry_score`) from `bootstrap_static.json` / `gameweeks.parquet`.
  - Geometric marker shapes + direct text labels for chips (`WC` diamond, `FH` triangle, `BB` square, `TC` star).
- **Blocked:** None
- **Next:** User review and acceptance.

## Todo
- [x] Add domain terms to `CONTEXT.md`
- [x] Update `features/processor.py` to keep global event benchmarks in `gameweeks.parquet`
- [x] Add `fetch_classic_league_standings` to `clients/fpl_api.py`
- [x] Implement `dashboard/performance_service.py` with two-tier caching and fallback
- [x] Implement `dashboard/performance_analytics.py` for trajectory, deltas, chip timing, and inventory
- [x] Implement `dashboard/performance_view.py` with Plotly charts and Apple utility styling
- [x] Integrate into `dashboard/streamlit_dashboard.py` and `commands/export_dashboard.py`
- [x] Write unit and integration tests in `tests/test_manager_performance.py`
- [x] Run `ruff check .`, `pytest`, and `bash tests/verify.sh`
- [ ] Monitor user feedback and live usage on dashboard

## Blockers / Notes
- None
