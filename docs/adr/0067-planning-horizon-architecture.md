# Planning Horizon Architecture: 10-GW Default, 12-GW Recommended Boundary, and 19-GW Half-Season Hard Cap

Operational planning requires evaluating transfer sequences across longer fixture runs and chip windows. We establish a three-tier horizon architecture: default 10 GW, recommended boundary $\le 12$ GW, and hard cap 19 GW.

1. **Default Planning Horizon (10 GW)**:
   - Sets `DEFAULT_PLANNING_HORIZON = 10` across `solver/utils.py`, `commands.solve`, `commands.injury_triage`, and product dashboard slicers.
   - Replaces the legacy 6-GW default, providing managers with a complete forward-looking transfer pathway spanning international breaks and fixture swings.
   - Seamlessly integrates with ADR 0065 discount scaling ($\text{scale}(10) \approx 1.44$).

2. **Recommended Boundary ($\le 12$ GW)**:
   - For $H \le 12$, HiGHS MILP routinely proves exact mathematical optimality (`gap 0.0`) in $\le 60\text{s}$.
   - Solves exceeding 12 GW scale to $>80,000$ rows and $>50,000$ variables, increasing branch-and-bound exploration time.
   - `commands.solve` logs an informational advisory when $H > 12$ and $\text{gap} = 0.0$, advising managers to consider `--gap 0.002` (0.2%) for rapid convergence.

3. **Half-Season Hard Cap (19 GW)**:
   - Sets `MAX_PLANNING_HORIZON = 19` in `solver/planning.py`, clamping inputs to $[1, 19]$.
   - Aligns the solver's maximum reach with FPL's native half-season chip architecture (Set 1: GW1–19, Set 2: GW20–38), allowing managers to plan complete half-season chip and transfer strategies when desired.
   - At season conclusion, `planning_gameweeks` automatically truncates at `SEASON_END_GW = 38`.

4. **Preservation of ADR 0066 Evaluation Gates**:
   - The Backtesting & Promotion Replay protocol ([ADR 0066](0066-backtesting-and-promotion-foundation.md)) strictly isolates its rolling evaluation windows to 6 GW (`tests/promotion_evidence_fixture.py`), preserving registered candidate historical evidence.

**Status:** Accepted. Supersedes ADR 0029.

**Considered:**
- *Full-season 38-GW cap*: Rejected: MILP formulation exceeds 200k rows with excessive distant projection noise.
- *Default 6 GW with 19 GW cap*: Rejected: user experience requires a default that plans through upcoming fixture blocks without requiring explicit CLI flags.
