# Task: GKP full-season rotation horizon match

**Objective:** Fix Section 2 “Full Season Rotated xP” that reused GW1–6 totals; project horizon-matched FDR-min rotated xP via ParticipationStateHybridModel with flat-90 mins; rebuild baseline from expected-stats rates.

**Acceptance:**
- [x] `tot_rot_xp` horizon-matched (full season ≠ GW1–6)
- [x] FDR-min primary pick + `maxxp_delta` / `tot_rot_xp_maxxp`
- [x] Flat 90 starter minutes; promoted = tags
- [x] Baseline from `per90_saves` / `per90_goals_conceded`
- [x] Note + matrix + tests + RQI glossary sharpen
- [ ] Optional follow-up: recalibrate RQI $S_{\text{tot_xp}}$ 2.5–4.2 band (saturates under flat-90 hybrid)

## Work Packet (SFDBN)

- **Status:** Forward projector + note regenerated; 7 tests green; full suite 141 passed. Ready to commit.
- **Files:** `docs/research/gkp-fixture-rotation/run_gkp_rotation_analysis.py`; `gkp-fixture-rotation.md`; `data/research/gkp-fixture-rotation/gkp_rotation_matrix.csv`; `gkp_performance_baseline.csv`; `tests/test_gkp_fixture_rotation.py`; `CONTEXT.md`; `docs/research/INDEX.md`; `docs/agents/current-state.md`
- **Decisions:** Grill locks C→B→A→C(A)→A→B→A: hybrid flat-90, FDR-min primary, expected-stats baseline, all four horizons.
- **Blocked:** None.
- **Next:** Optional RQI scale recalibration; otherwise close task and delete `task.md`.
