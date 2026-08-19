# Dual-Vector Canonical xP + generated research figures

**Objective:** Rebuild Stage 3 Canonical MILP on Prior-Season Dual-Vector Seed (calendar stays BB1+WC4, GW1–6, GW5 roll). Runners rewrite note/INDEX/current-state figures from CSV cells. AGENTS.md: path+column identity, not numeric literals.

**Acceptance:** `gw1-6_wc4_summary.csv` `total_6gw_xp` is Dual-Vector Seed; Stage 3 note / pipeline README / INDEX chip row / current-state research-truth generated from that CSV; Agent Prompts name the CSV column not a snapshot; First-Half stays sibling calendar (FH/TC, GW1–19). Live DCS on Seed; no first-half `dcs/` copy.

## Work Packet (SFDBN)

- **Status:** Done. Canonical Seed `total_6gw_xp` **383.76**. Live DCS on Seed. Figure caches generated. ruff / 182 pytest / verify.sh passed. Committing this turn.
- **Files:** Stage 3 Seed runner; live DCS `build_seed_fdr_matrix`; `docs/research/sync_live_research_figures.py`; `AGENTS.md`; first-half `run_all.py`; notes/INDEX/current-state.
- **Decisions:** Live research xP = Prior-Season Dual-Vector Seed. Production `_fixture_maps` FDR. Canonical calendar BB1+WC4. Figure identity = CSV path + column. One live DCS folder.
- **Blocked:** None.
- **Next:**
  - [x] Commit/push on request.
