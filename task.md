# Task Work Packet

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** `docs/research/defensive-fixture-rotation/defensive-fixture-rotation.md`, `docs/research/defensive-fixture-rotation/run_defensive_rotation_analysis.py`, `data/research/defensive-fixture-rotation/*.csv`, `docs/research/gw1-6-preseason-pipeline/refresh_downstream.py`, `docs/research/gkp-fixture-rotation/gkp-fixture-rotation.md`, `docs/research/def-fixture-rotation/def-fixture-rotation.md`, `docs/research/INDEX.md`, `docs/agents/current-state.md`, `task.md`
- **Decisions:** 
  1. Consolidated `gkp-fixture-rotation` and `def-fixture-rotation` into master unified topic `docs/research/defensive-fixture-rotation/` with companion `data/research/defensive-fixture-rotation/`.
  2. Implemented Two-Factor Defensive Composite Score ($\text{DCS} = 0.60 \times S_{\text{Score}} + 0.40 \times S_{\text{Risk}}$) combining Opportunity-Cost Adjusted Net xP ($\gamma = 0.2627$), Zero-Difficult %, Rotated FDR, and schedule correlation.
  3. Formally proved GKP strategy hierarchy: Active 2-GKP rotation (`Trafford + Lammens` / `Trafford + Roefs` / `Kelleher + Roefs`) outperforms Set-and-Forget by +8.0 xP in GW1–3 BB1 (+2.41 Net OC-Score) and provides 94.7% Zero-Diff coverage across GW1–19.
  4. Enforced Max 2 DEF per club across all 20 clubs: evaluated 153,216 valid 5-DEF club multisets; `AVL-CHE-LIV-MCI-NFO` #1 across GW1–19 (2.4386 rot FDR, 100% zero-diff).
  5. Evaluated full 7-asset backlines (2 GKP + 5 DEF) across GW1–3 (BB1), GW4–19 (WC4), and GW1–19. Top BB1 backline: `Trafford + Lammens` + `Calafiori + Vuskovic + O'Reilly + O'Nien + Ballard` (£36.0m, 88.17 xP, 2.23 eff FDR).
- **Blocked:** None.
- **Next:** Ready for review and commit.
- **Objective:** Consolidate GKP and DEF fixture rotation research into a unified defensive strategy authority refreshed against 564-player preseason pipeline with two-factor ranking and GW1 BB + WC4 backline lineups.
- **Acceptance:**
  - [x] Unified computation script `run_defensive_rotation_analysis.py` created and operational.
  - [x] All 10 companion CSV datasets generated in `data/research/defensive-fixture-rotation/`.
  - [x] Comprehensive research note `defensive-fixture-rotation.md` written with complete metric definitions, findings, and strategic decisions.
  - [x] `refresh_downstream.py` updated to run the unified defensive analysis.
  - [x] Deprecation notices placed in legacy topic folders and `docs/research/INDEX.md` updated.
  - [x] Code quality: `uv run ruff check .`, `uv run pytest`, and `bash tests/verify.sh` green.
