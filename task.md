# Task Work Packet

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** `docs/research/def-fixture-rotation/def-fixture-rotation.md`, `docs/research/def-fixture-rotation/build_zero_diff_cs_picks.py`, `docs/research/INDEX.md`, `data/research/def-fixture-rotation/def_gw1_3_zero_diff_cs_picks.csv`, `data/research/def-fixture-rotation/def_bb2_zero_diff_cs_picks.csv`, `data/research/def-fixture-rotation/def_gw4_19_zero_diff_cs_picks.csv`, `docs/agents/current-state.md`, `task.md`
- **Decisions:** Same GW1–19 method on three horizons. Unordered 5-club. 100% zero-diff. Sort all-easy desc then corr. CS gate ≥2 CS-core ≤1 promoted. Does not replace FDR-min #1s. BB2 all-easy = worst started FDR (GW2 max-of-5; GW1/3 3rd-easiest). Rebuild: `uv run python docs/research/def-fixture-rotation/build_zero_diff_cs_picks.py`.
- **Blocked:** None.
- **Next:** None. Packet done.
- **Objective:** Rank GW1–3, BB2 sprint, and GW4–19 100% zero-diff 5-club sets by all-easy then pairwise correlation, overlay Stage 2 GKP CS priors, finalize top 20 each, consolidate into def-fixture-rotation note.
- **Acceptance:**
  - [x] GW1–3 zero-diff 5-club ranking + CS-gated top 20
  - [x] BB2 sprint zero-diff ranking + CS-gated top 20 (all-easy uses GW2 all-5 + GW1/GW3 top-3)
  - [x] GW4–19 zero-diff 5-club ranking + CS-gated top 20
  - [x] Companions written; research note + INDEX updated
