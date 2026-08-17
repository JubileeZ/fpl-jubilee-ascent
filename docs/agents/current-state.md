# Current Implementation State

Read if no prior context. `ROADMAP.md` shows target; this file shows what exists today. Current truth only — historical dumps → `docs/archive/` (see `docs/agents/progress.md`).

**Current phase:** New-season readiness complete — see `ROADMAP.md` Phase 5. All tracked implementation issues are closed (`JubileeZ/FPL-Jubilee-Ascent`).

## Next work — start here

Critical path (unblocks the new-season model, the reason this phase exists):

1. ~~#77 — FPL scoring matrix module~~ ✅ Done. `models/scoring_matrix.py` covers all 13 Event Components, including 2025/26 defensive contributions; tests in `tests/test_scoring_matrix.py`.
2. ~~#84 — Component model with Prior-Season Seed~~ ✅ Done. `models/component_baseline.py` reconstructs xP via the scoring matrix; `has_prior_seed`, `has_fallback_prior`, and `has_seed` distinguish seed sources in `features/builder.py`.
3. ~~#85 — Cold-Start fallback + current-season blend~~ ✅ Done. Prior-season seed + Position-Price Prior fallback + appearance-based blend in `features/builder.py`; cold-start guard disables player-specific prior at GW1-4.

Next on path:
- Maintenance, real-data validation, and future model improvements.

Unblocked quick wins (independent, grab anytime):
- None; #79/#80/#81/#82 complete locally.

Blocked, wait for deps:
- None.

Design decisions recorded in `docs/adr/0003-reconstruct-points-from-event-components.md`, `docs/adr/0004-cross-season-player-code-mapping.md`, `docs/adr/0005-hybrid-metrics-component-projection-model.md`, `docs/adr/0006-fixture-first-projection-contract.md`, and `docs/adr/0010-participation-state-snapshots-and-evaluation.md`; vocabulary in `CONTEXT.md`.

- **Role/stats/score audit (18 Aug, post-refresh):**
  - Score matrix OK (CS 4 / GK goal 10 / Defcon). Trafford dest GC LEE=1.474; Rushworth COV=1.375.
  - Role bugs: Meerkat `Nunes` matched Vitor Reis (middle name); Bruno G. stuck Out of Contention after ARS move.
  - Fix: single-token source names match `web_name` or surname last token only; incoming transfers floor Cameo/Out of Contention → Rotation.
  - Rebuild: Bruno G. ARS Rotation; Vitor Reis Rotation; Matheus N. Regular; Draft 234; Stage 3 canonical **364.21 xP**. Club FDR #1 still `AVL-CHE-LIV-MCI-NFO`. GKP DCS #1 still `Rushworth + Donnarumma`. Pushed `9e4ce74`. DCS = 0.60 S_Score + 0.40 S_Risk (OC-adjusted xP vs Zero-Diff / Rot FDR / corr).

- **Unified Defensive Architecture refresh vs live FPL (18 Aug):**
  - `refresh_data` 2026-08-18: 590 players, 380 fixtures. Trafford **LEE**, Rushworth **COV**. GW1 calendar matches live `/fixtures/?event=1` (no Wolves/Leicester).
  - Stage 1 rematch: 11 club rows synced from API; 575 contention; Trafford Leeds Nailed; Rushworth Coventry Regular.
  - Downstream rebuilt. GKP DCS #1 GW1–19: `Rushworth + Donnarumma`. GW1 BB opponents from parquet. Club FDR #1 still `AVL-CHE-LIV-MCI-NFO`. Stage 3 canonical **363.34 xP** (superseded 18 Aug name-match rebuild → **364.21 xP**).
  - Legacy `gkp-fixture-rotation` / `def-fixture-rotation` notes stamped superseded; not re-run.

- **Pre-Season Guide & Summer Transfers Refresh (17 Aug):**
  - Scraped live FFS guide index (modified 17 Aug) and child sources. Ingested new post-preseason friendly article: `docs/research/fpl-preseason-guide/fpl-4-0m-defenders-ranked.md` with full player profiles, DefCon rates, FotMob Coventry lineup, and GW1 Clean Sheet Odds.
  - Refreshed confirmed summer transfers register (`fpl-summer-transfers.md`) through 15 August (33 August signings; added Khalaili to Palace, Gelhardt/Gourna-Douath to Hull).
  - Updated parent directory `fpl-preseason-guide.md` (15 child notes active) and master research index `INDEX.md`. Tests 170/170 passing, verify.sh 29/29 green.

- **564-Player Preseason Pipeline & GW1 BB + WC4 Canonical Overhaul (17 Aug):**
  - Exhaustive 20-club role classification for all 564 FPL API players (92 Nailed, 158 Regular, 112 Rotation, 119 Cameo, 83 Out of Contention; 250 Draft-Eligible). Synced all 20 club markdown tables in `01-expected-role-gw1-5`.
  - Re-anchored Prior-Season Seed floor to $\ge 900$ mins in 2025/26 archive per user invariant. Added 132 researched FBref/senior league career packages in `build_expected_stats.py` ensuring zero Draft-Eligible players sit on `fallback_baseline`.
  - Rebuilt Stage 2 Expected Stats and GW1–5 $xP$ projections with Softmax bonus over 564 players. Top Draft: Haaland (26.35 xP), Isak (25.84 xP), Vuskovic (25.77 xP), Gabriel (25.17 xP), B.Fernandes (24.66 xP).
  - Rebuilt Stage 3 to single canonical strategy: **GW1 Bench Boost (BB1) + GW4 Wildcard (WC4)** with locked GW1–3 transfers (190.10 xP), GW4 Wildcard overhaul (172.38 xP), and 0 transfers in GW5 to bank 4 Free Transfers into GW6 post-international break. Total: **362.48 xP**.
  - Updated full-season (GW1–38) and GW1–6 projections for all 564 players in `ownership-value-explorer`, updated `plot_ownership_value_explorer.py` and regenerated `ownership_value_explorer.html` and `ownership_value_metrics.csv`.
  - Verified full test suite (170/170 passing) and delivery gates (`verify.sh` 29/29 green). Scratch files in `.tmp/agent/` cleaned.

- **GW1–3 / BB2 / GW4–19 zero-diff all-easy + CS overlays (16 Aug):** Same unordered 5-club method as GW1–19. GW1–3: 11,450 zero-diff; max 2/3 all-easy (176); start-here `ARS-HUL-MCI-MUN-SUN` / `ARS-HUL-LIV-MUN-SUN` / `MCI-MUN-NFO-SUN-TOT`. BB2 11-start: 824 zero-diff; max 1/3 all-easy (43, mostly GW3); start-here `BRE-LIV-MCI-MUN-SUN` / `BRE-EVE-LIV-MCI-MUN` / `BRE-LIV-MCI-MUN-TOT`. GW4–19: 1,752 zero-diff; 10 with 5+ all-easy; start-here `ARS-COV-LIV-MCI-SUN` / `BHA-COV-LIV-MCI-SUN` / `AVL-CHE-LIV-MCI-NFO`. Companions `def_gw1_3_zero_diff_cs_picks.csv`, `def_bb2_zero_diff_cs_picks.csv`, `def_gw4_19_zero_diff_cs_picks.csv`. Builder `docs/research/def-fixture-rotation/build_zero_diff_cs_picks.py`. FDR-min #1s unchanged.
- **GW1–19 zero-diff all-easy + CS overlay (15 Aug):** Unordered 5-club sets; 1,024 with 19/19 zero-diff. Sort all-easy desc then corr. CS gate ≥2 CS-core (ARS/MCI + LIV/BHA/MUN/AVL) and ≤1 promoted. Start-here: `ARS-COV-LIV-MCI-SUN` / `AVL-CHE-LIV-MCI-NFO` / `BHA-COV-LIV-MCI-SUN`. Companions `def_club_cs_priors.csv`, `def_gw1_19_zero_diff_cs_picks.csv`. FDR-min #1 unchanged.
- **Research metric definitions & target direction standardization (15 Aug):** Standardized metric documentation across active research notes, master index (`INDEX.md`), template (`research-note.md`), and repo rules (`AGENTS.md`). Embedded explicit `Metric Definitions & Direction` tables detailing formulas, target directions (Higher $\uparrow$ / Lower $\downarrow$), benchmarks/ideal values, and domain definitions across GKP rotation, DEF rotation, Ownership Explorer, Stage 3 Chip Matrix, Stage 2 Expected Stats, First-Half Chip Strategy, and Set-Piece Analysis. All 170 tests passing, verify.sh 29/29 green.
- **DEF & GKP rotation metrics redesign & cross-research alignment (15 Aug):** Replaced legacy FDR-min selection with unconditional $\max(xP)$ policy (plus 12%/3% auto-sub EV in DEF rotation). Replaced integer FDR Pearson $r$ with Poisson clean sheets ($xCS = e^{-\lambda}$) and Fixture Overlap Index ($\text{FOI} = \frac{1}{T}\sum (1 - p_{\text{cs1}})(1 - p_{\text{cs2}})$). Implemented Opportunity-Cost Adjusted Net Value (OC-RQI) via empirical outfield slope ($\gamma \approx 0.24-0.25\text{ xP/£1.0m/GW}$) from Stage 2 dataset. Fixed intra-club diagonal correlation ($r=1.0$) and recalibrated non-saturating RQI bounds. Full downstream refresh (`refresh_downstream.py`) executed; all CSV artifacts regenerated and research markdown notes updated. All 170 tests passing, verify.sh 29/29 green.
- **Research suite alignment to BB2 + TC3 + WC4 canonical strategy (14 Aug):** Aligned all 4 research suites to S13 BB2 + TC3 Haaland + WC4 Opt1 (340.14 xP) as canonical Max EV benchmark with S5 BB1 safe start (338.88 xP).
  - `def-fixture-rotation`: Added BB2 sprint lens (3+5+3 starts) to `run_def_rotation_analysis.py`, evaluated 5,464 club multisets and 4,319 tier lineups (`def_bb2_wc4_club_matrix.csv`, `def_bb2_wc4_tier_lineups.csv`); top 4-club `HUL-MUN-MUN-TOT-SUN` (GW2 2.00 FDR, 2.2727 eff FDR); updated main doc and WC4 bridges.
  - `gw1-6-preseason-pipeline`: Aligned master `README.md` and `gw1-6-chip-wc4-squads.md` around S13 #1 / S5 #2 hierarchy, S13 15-man squad picks, roll GW5 -> 4 banked FTs into GW6.
  - `gkp-fixture-rotation`: Added Pre-WC GW1-3 BB pairings (Donnarumma+Roefs 26.50 xP / Lammens+Roefs 26.32 xP / Verbruggen+Lammens 25.12 xP) vs Post-WC4 archetypes (Fodder Liquidation vs Active 2-GKP Rotation).
  - `ownership-value-explorer`: Added S13 overlay (`★`), WC4 Core squad tag (`⬡`), updated filter checkboxes and badges in `plot_ownership_value_explorer.py`, rebuilt interactive HTML and documentation. Tests green (169 passed), verify.sh green.
- **First-half chip strategy multi-source refresh & proofs (14 Aug):** Refreshed `docs/research/fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md` with multi-source synthesis (FPL Focal, FFS/Hub, Official Rules) and quantitative evaluation of all candidate branches against Stage 3 16-scenario MILP matrix. S13 TC3 Haaland (340.14 xP) confirmed #1; BB2 raw xP (+1.26) vs BB1 certainty proved; WC4 + roll GW5 preserves 4 FTs into GW6. Tests green.
- **DEF rotation correlation-first ranking (14 Aug):** GW4–19 dest #1 is `AVL-BOU-CHE-LIV-NFO` (rot 2.4375, r = −0.0994). Narrative now follows CSV, not City-core. Bridge dest picker uses same corr-first tie-break; `LIV-MCI-MUN-MUN-NFO` still dumps to `AVL-CHE-LIV-MCI-NFO` (only 2-swap dest). `--print-ranks` reprints Top-10s. Tests green.
- **Ownership explorer identity + full list (13 Aug):** Stage 1 `name_match` treated `Bruno G.` as FFS "Bruno Fernandes" (token `{bruno}` subset) and missed `Van Dijk`→`Virgil`. Fixed via `player_matches_source` using FPL first/second name. Bruno G. now ARS Rotation; B.Fernandes MUN nailed; Virgil LIV nailed. Explorer HTML adds searchable full player table. Stage 2–3 + season explorer rebuilt. Top FH3 S1 **328.22** / top TC3 S5 **335.01**; Bruno ban now binding.
- **Multi-Club (2–5 unique clubs) defender fixture rotation & partition study (12 Aug):** 41,344 club multisets / 944k lineups ≤ £26.0m. BB1 4-club `ARS-MUN-MUN-NFO-SUN`. GW1–19 #1 still `AVL-CHE-LIV-MCI-NFO`. GW4–19 dest ranking superseded 14 Aug (corr-first → `AVL-BOU-CHE-LIV-NFO`).
- **Ownership Value Explorer club filter UX (12 Aug):** Checkbox multi-select; search box narrows visible clubs; All/None select/deselect visible matches; Open & use section in research note.
- **Flexible 5-Defender fixture diversification & rotation research update (12 Aug):** Removed artificial promoted proxy exclusions; expanded player combination space to flexible pricing up to £26.0m total spend across 4 natural budget bands (Band 1 Budget £20.5m–£22.5m, Band 2 Mid-Value £23.0m–£24.0m, Band 3 Single Anchor £24.5m–£25.0m, Band 4 Dual Anchor £25.5m–£26.0m). Vectorized combinatorial simulation evaluates 634,874 valid 5-defender sets across GW1–19, GW1–3, GW4–19, GW1–38, and specialized GW1 BB + GW4 WC. Top overall rotation: Vuskovic+Thomas+Jacquet+O'Reilly+O'Nien (£24.5m, 346.34 xP, 2.4561 FDR, 100% zero-difficult GWs) and Calafiori+Vuskovic+Thomas+Jacquet+O'Reilly (£26.0m, 360.51 xP). Generated 5 CSV artifacts in `data/research/def-fixture-rotation/`; updated `docs/research/def-fixture-rotation/def-fixture-rotation.md`. Tests green.
- **def-fixture-rotation research note markdown repair (12 Aug):** Fixed broken preview in `docs/research/def-fixture-rotation/def-fixture-rotation.md` — removed LaTeX `$…$` / `$$…$$` (tables + xP/FDR symbols), restored blank lines before GFM tables, cleaned redundant bold in headings; aligned refresh-checklist `Updated` stamp with header. Content unchanged; no artifact or script rerun.
- **Ownership Value Explorer → full season standalone (12 Aug):** Moved out of GW1–6 pipeline Stage 4 into `docs/research/ownership-value-explorer/`. GW1–38 projections via Stage 2 rates + availability priors + `ParticipationStateHybridModel`; interactive HTML defaults to season xP/90 vs ownership % with GW1–6 toggle, position/club/price/xMins filters, S1/S5/user overlays. Artifacts under `data/research/ownership-value-explorer/`. Pipeline restored to 3 stages.
- **Stage 4 Ownership Value Explorer (12 Aug):** Superseded by full-season standalone topic above (was GW1–6-only Stage 4).
- **GW1–6 preseason pipeline audit & reproducibility sync (12 Aug):** `/grill-with-docs` review verified 2026/27 season/year data integrity and resolved `fallback_baseline` invariant violations for 5 newly scraped FFS XI starters (Touré, Meunier, Walle Egeli, Steur, Moore) with external research packages in `build_expected_stats.py` (0 Draft on `fallback_baseline`). Full 20-club markdown tables regenerated in `expected-role-gw1-5.md` (357 contention rows, 224 Draft-eligible). Stage 2 xP (Haaland #1 28.15 xP, Palmer #2 24.60 xP, Isak #3 24.20 xP) and Stage 3 16-scenario matrix (Top FH3 S1 327.40 xP, Top TC3 S5 335.42 xP) synced across research notes and master README. Embedded reproducibility prompts across pipeline docs. 152 tests passing, verify.sh green.
- **5-Defender fixture diversification & BB1+WC4 scenario study (10 Aug):** Full combinatorial evaluation of 15,504 5-club sets + multi-tier player lineups across GW1–3, GW4–19, GW1–19, full season, and specialized GW1 Bench Boost (BB1) + GW4 Wildcard (WC4) pre-wildcard scenario. PL-proven #1 5-club rotation is `AVL-CHE-LIV-MCI-NFO` (Rot FDR 2.4386, 100% zero difficult GWs, 26.3% all-easy GWs, r = -0.0679). BB1+WC4 #1 PL-proven set: `ARS-BRE-CHE-MUN-NFO` (11-start eff FDR 2.4545, zero GW1 clashes). Top budget BB1 lineup: Maatsen+Greaves+Shaw+Jair Cunha+Robertson (£22.0m, 52.05 xP, BB-RQI 65.16, 2.5455 eff FDR). Top anchor BB1 lineup: O'Reilly + Maatsen+Shaw+Jair Cunha+Robertson (£24.5m, 59.82 xP, BB-RQI 76.02). Artifacts under `data/research/def-fixture-rotation/`; research note at `docs/research/def-fixture-rotation/def-fixture-rotation.md`. Tests green.
- **Stage 2 Event Rate grill lock (10 Aug):** Dual-floor usable blend (any ≥450; latest slot ≥900; thin years older-mean only / equal-weight fallback); Defcon-only fill when usable years lack evidence; 15 Draft Regular external packages (zero Draft on `fallback_baseline`); Softmax stays full XI Contention; CONTEXT adds Research Position Baseline vs production Position-Price. Isak rises to #3 (24.19 5GW xP). Stage 3 re-run: top FH3 S1 **327.26** / top TC3 S5 **336.04**. Blend unit tests green.
- **GW1–6 preseason methodology grill lock (10 Aug):** `/grill-with-docs` audit revised pipeline Method. Stage 1: HTTP scrape FFS Team News + Meerkat with FFS XI injects. Availability: Watch $p_start\times0.70$ GW1–5; `exclude_gw1-5` zeros GW1–5 only. Stage 3: 16-scenario exploration matrix; dual winners FH3/TC3; user_picks + FT banking. Docs/CONTEXT synced.
- **Set-piece stats & projections research ingestion (9 Aug):** Ingested Opta Analyst × Solio Analytics 2026/27 pre-season dead-ball research note (`docs/research/fpl-set-piece-analysis/fpl-set-piece-analysis.md`) and 3 companion datasets (`corner_takers_2026_27.csv`, `team_set_piece_swing_2025_26.csv`, `player_set_piece_leaders_2025_26.csv`). Added 4 domain definitions to `CONTEXT.md` (`Set-Piece Hierarchy`, `Inswinging Corner Preference`, `Set-Play Target xG`, `Set-Piece Net Swing`). Linked in `docs/research/INDEX.md`.
- **No-Haaland GW1–2 + FH3 + WC4 strategy expansion (9 Aug):** Expanded `run_wc4_simulation.py` and `docs/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/` to solve No-Haaland GW1–2 drafts + GW3 Free Hit (FH3) single-GW MILP + GW4 Wildcard. Superseded by 10 Aug 16-scenario exploration matrix (see above).
- **Preseason pipeline & research suite refresh (9 Aug):** Re-audited and updated `docs/research/gw1-6-preseason-pipeline/` end-to-end. Updated `refresh_expected_role.py` with confirmed 8 Aug summer transfers. Superseded Stage 3 3×2 framing by 10 Aug exploration matrix.
- **Preseason pipeline consolidation & multi-source role overhaul (6 Aug):** Re-researched all 20 PL clubs via FFS Team News, FPL Meerkat, summer transfers, and official club news. Consolidated research & optimization into `docs/research/gw1-6-preseason-pipeline/` (Stage 1 role audit, Stage 2 stats/projections, Stage 3 WC4 3x2 matrix MILP). Master runner `run_pipeline.py` executes end-to-end. Updated Kinsky, Trafford, Rushworth, Tzolakis starters; Saliba/Rodri exclusions. Legacy duplicate folders purged. 142 tests passing.
- **FFS pre-season guide refresh (13 Aug):** Playwright recheck of parent guide (modified 2026-08-13) and 14 child sources. 13 price-bracket articles unchanged on `article:modified_time`; new £7.0m+ forwards article (published 2026-08-11) → `fpl-7-0m-forwards.md`. Summer transfers refreshed through 12 August (12 new moves: Rulli, Chavarria, Diomande, Shea Charles, Araujo loan, Hull reinforcements, Johnson/McNeil swap, etc.). Parent + INDEX updated to 14 child notes.
- **GKP full-season rotation fix (3 Aug):** Horizon-matched FDR-min rotated xP via `ParticipationStateHybridModel` + flat-90 mins; baseline from `expected-stats` saves/GC rates; matrix + `gkp_performance_baseline.csv`; tests in `tests/test_gkp_fixture_rotation.py`. PL-proven #1 Verbruggen+Lammens: GW1–6 RQI 87.89 / 38.77 xP; full season RQI 83.87 / 236.96 xP (max(xP) Δ 1.85). Prior “full season ~23 xP” was GW1–6 reuse bug.
- **Authenticated squad refresh & GW1–6 WC4 re-analysis (3 Aug):** Live Playwright FPL API login refreshed `data/processed/user_picks.parquet` for entry `822158` (£100.0m spend: Kinsky/Verbruggen, Ballard/Thomas/Shaw/Mitchell/N.Williams, Ampadu/Szoboszlai/B.Fernandes/Mbeumo/Xhaka, Haaland/Isak/Georginio). Re-evaluated `docs/research/gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md` against ParticipationStateHybridModel. GW1 BB = 55.34 xP (GW1–3 = 146.83 xP). Confined pre-WC opp loss = -21.10 xP (GW1 BB + WC4 Opt1 = 298.11 xP; Opt3 = 293.27 xP). Sticking without WC penalty = -42.49 xP (-51.21 xP no BB).
- **RQI standardization & research recalibration (3 Aug):** Points-Heavy RQI ($0.40 S_{\text{tot\_xp}} + 0.20 S_{\text{fdr}} + 0.20 S_{\text{corr}} + 0.10 S_{\text{easy}} + 0.10 S_{\text{cost}}$); promoted-proxy tags. Superseded by full-season rotation fix above for absolute season xP figures.
- **GKP fixture rotation & FDR correlation study (3 Aug):** Starter GKP pairs ≤ £9.5m across GW1–6/10/19/38; artifacts under `data/research/gkp-fixture-rotation/`. Superseded scoring path by full-season rotation fix above.
- **GW1–6 chip & WC4 squad optimization 3x2 matrix (3 Aug):** Expanded `run_wc4_simulation.py` and `docs/research/gw1-6-chip-wc4-squads/` to optimize all 6 scenarios (BB1 vs BB2 x WC4 Options 1, 2, 3) over a full 6-GW horizon. All plans roll transfer in GW5 to bank 2 FTs into GW6 post-international break. Verdict: S3 (BB1 + WC4 Option 3 Cheap DEF ≤ £31.5m + Liverpool 2+) selected for highest pre-WC points (74.15 xP in GW1, 167.86 xP GW1–3), Liverpool coverage (Isak + Mac Allister), 313.02 cumulative xP, and £3.5m ITB + 2 FTs in GW6.
- **FDR defence multiplier realignment (2 Aug):** Corrected pre-season FDR fallback calculation in `features/builder.py` and `models/metrics_component_hybrid.py` from `(6.0 - difficulty) / 3.0` to `difficulty / 3.0`, aligning clean sheet scaling with 2025/26 empirical data (760 team-matches). Re-ran expected stats projections (`gw1-5_projections.csv`), chip strategy simulation (`gw1-5_chip_simulation.csv`: BB1 **301.21** / BB2 **301.78** / Standard **284.68**), and GW1–6 chip & WC4 squad optimization (`gw1-6_wc4_simulation.csv`).
- **Expected-stats GW1–5 rebuild (2 Aug):** Grill-lock pipeline in `docs/research/expected-stats-gw1-5/`: Permanent Player Code Mapping, Usable Season ≥450 mins, 50/50 recency blend, separate attack/defence fixture mults, `ParticipationStateHybridModel.predict`, Softmax over XI Contention. External research packages for Draft fallback + CBIT upgrades; best-guess Defcon for 7 partial-source players. Haaland #1 (~28.9 5GW xP); Palmer #2; Vuskovic #3. Zero Nailed/Regular on fallback_baseline.
- **GW1–5 chip sim (2 Aug):** Re-run on grill-lock projections. BB1 **301.21** / BB2 **301.78** / Standard **284.68** (+16.5 / +17.1 vs no early BB). XI-aware MILP, £0.5m ITB, no TC. Captains: Haaland GW1/3/5, Palmer GW2/4. Not production solver.
- **Docs & Research policy (31 Jul):** Consolidated `AGENTS.md` lifecycle/research rules; added `data/research/` companion convention, `Artifact` link requirement, three-topic Active research index, and single-location archive immutability guidance. AZG-managed block unchanged.
- **Expected Role audit (31 Jul):** Rechecked all 194 prior Draft rows against official club/federation evidence, friendlies, and local FPL availability. Updated table/note: 339 rows, 193 fit-role Draft-eligible (90 Nailed + 103 Regular), 99 Rotation, 47 Cameo; 179 current Draft rows `eligible`, 9 `watch`, 4 `exclude_gw1`, 1 `exclude_gw1-5`. Perri → Rotation; Pope/Kinsky → Regular. Added direct source refs, API registration/availability fields, and dated overlays; Participation State availability guard remains follow-up.
- **Research documentation reset (31 Jul):** Superseded four 2026/27 strategy notes removed; universal template at `docs/research/template/research-note.md`; source synthesis at `docs/research/fpl-first-half-chip-strategy.md`. Future notes use stable slugs, `Updated`/`Data stamp`, and separate source synthesis from project interpretation.
- **Scout pre-season source set (31 Jul):** Added directory `docs/research/fpl-preseason-guide.md` plus budget goalkeeper, £4.5m defender, £4.0m defender, £4.5m midfielder, and summer-transfer notes. £4.0m defender and £4.5m midfielder notes remain partial where source pages are account-gated.
- **Scoring Matrix Realignment**: Corrected `_GOAL_POINTS` per position (GK=10, Defender=6, Midfielder=5, Forward=4), added defensive-contribution points, and retained official negative-event penalties in `models/scoring_matrix.py`.
- **Fixture-First Contract**: `features/builder.py` emits one row per player/fixture across the planning horizon; `projections/exporter.py` aggregates double-gameweeks for solver CSVs.
- **Hybrid Metrics Component Model (`metrics_component_hybrid`)**: Uses separate fixture attack/defence effects, rolling pre-cutoff attack-weight calibration, Poisson count expectations, direct Defcon expected points, and competitor-aware bonus allocation.
- **Backtesting Metrics**: `backtesting/metrics.py` reports forecast error, signed bias, rank validity, position strata, and shortlist overlap/regret.
- **Component Attribution Harness**: Updated `backtesting/metrics.py`, `models/metrics_component_hybrid.py`, `models/component_baseline.py`, and `commands/backtest.py` with per-component prediction export (`xp_minutes`, `xp_goals`, `xp_assists`, `xp_clean_sheet`, `xp_conceded`, `xp_defcon`, `xp_bonus`), component metrics evaluation, and `--component_breakdown` CLI reporting.
- **Backtest Archive Fallback**: `commands/backtest.py` selects the newest processed season archive when active performance history is unavailable.
- **Fixture Difficulty Report**: `commands/fdr_report.py` reads processed fixtures, preserves double gameweeks, and prints/exports a sortable club-by-horizon FDR matrix.
- **Captain/Vice Report**: `commands.report` prints next-gameweek recommendations and exports role columns.
- **Chip Validation**: `commands.solve` rejects duplicate, conflicting, and out-of-horizon booked chips before solver preparation.
- **Price History**: `commands.refresh_data` appends UTC price snapshots; `commands.price_report` reports refresh and season changes.
- **Tuning Surface**: `commands.run_model` exposes blend thresholds; `commands.solve` exposes horizon, decay, hit-cost, and validated overrides.
- **ADR 0005 Recorded**: Updated [`docs/adr/0005-hybrid-metrics-component-projection-model.md`](../../docs/adr/0005-hybrid-metrics-component-projection-model.md) to match shipped behavior.
- **Solio Pipeline Deprecated & Removed (ADR 0009)**: Audited and removed Solio market ingestion pipeline (`commands/fetch_solio.py`), feature merge in `features/builder.py`, and GitHub Action workflow (`.github/workflows/fetch_solio.yml`) due to top-N payload truncation and mathematical xMins inversion saturation. Retained local 2-State Empirical Bayes Mixture Model for minute estimations.
- **Participation State Model**: `participation_state_hybrid` is provisionally operational default; `metrics_component_hybrid` remains its Candidate. Archive-only results may support provisional promotion; verified snapshots support validated promotion. `commands.capture_availability_snapshot` writes immutable pre-deadline packages; `--require_snapshots` rejects missing or tampered packages for strict evaluation. Provisional status requires two four-Gameweek Live Validation Windows.
- **Image Generation Removal**: Removed PNG squad timeline visualization logic (`solver/visualization.py`, `commands/solve.py`) and deleted `data/images/` directory. Retained `matplotlib` in `pyproject.toml`.



---

## What exists

| Area | Path | Notes |
|------|------|-------|
| Project Scaffold | `AGENTS.md`, `ROADMAP.md`, `CONTEXT.md` | Configuration, roadmap, vocabulary |
| Dependencies | `pyproject.toml`, `.venv/` | Package configuration via uv |
| API Clients | `clients/fpl_api.py`, `clients/fpl_auth.py` | Inbound request handlers and JWT Playwright/tiered login (`.env` credentials → `data/session_token.json` → `user_picks.parquet`) |
| Data Dictionary | `docs/data_dictionary.md` | Mapping from raw API fields to flat files |
| CLI Commands | `commands/` | Scripts for refreshing, snapshotting, modeling, backtesting, FDR reporting, solving |
| Custom Models | `models/` | Linear, component, hybrid, and participation-state models |
| Features & Projections | `features/`, `projections/` | Data compilers and solver projection exporters |
| Backtesting Engine | `commands/backtest.py`, `backtesting/` | Walk-forward evaluation and decision-aware metrics |
| Vendored Solver | `solver/` | Port of open-fpl-solver modules |
| Research: Expected Role / Stats / Chip sim | `docs/research/`, `data/research/` | GW1–5 role table, Softmax projections, chip-strategy milp sim (research-only) |

---

## What does NOT exist yet (do not assume)

- Historical Availability Snapshot collection has not run yet; archive-backed promotion remains provisional until two Live Validation Windows complete.
- Committed Comparison Slate lives in `config/model_selection.json`; `commands/compare_models` and `commands.evaluate_model_promotion` implement automatic historical promotion with Promotion Evidence Records.
- Snapshot-backed nonzero-chance calibration is not implemented; the opt-in model only applies the immediate `0%` hard DNP rule.
- Transfer-plan regret remains intentionally out of scope until one-Gameweek Decision Regret passes the holdout gate.

---

## Safe commands today

```bash
uv run pytest                                          # Run pytest
uv run ruff check .                                    # Lint code
uv run python -m commands.refresh_data                 # Ingest current gameweek data
uv run python -m commands.run_model linear_baseline    # Generate projections
uv run python -m commands.run_model component_baseline # Generate component projections
uv run python -m commands.run_model participation_state_hybrid # Operational default
uv run python -m commands.run_model metrics_component_hybrid    # Comparison baseline
uv run python -m commands.capture_availability_snapshot --season 2026-27
uv run python -m commands.compare_models --gw_range 1-38 --data_dir data/archive/2025-26/processed
uv run python -m commands.evaluate_model_promotion --apply --gw_range 1-38 --data_dir data/archive/2025-26/processed
uv run python -m commands.decision_regret --entry_id <public-entry-id>
uv run python -m commands.solve --preseason --xmin_lb 0 # Optimize preseason transfers
uv run python -m commands.report                       # Print report
uv run python -m commands.price_report                # Print price changes
```

---

## Agent pitfalls

- Playwright Chromium binary must be installed (`uv run playwright install chromium`) to run `refresh_data`/`snapshot_season` when `FPL_TOKEN` is unset.
- Windows console is cp1252 by default; `commands.*` reconfigure stdio to UTF-8 via `clients.env_loader.configure_utf8_stdio()`. New commands that `print` non-ASCII (player names) must call it too.
- Tests rely on `tool.pytest.ini_options.pythonpath = ["."]`; don't remove it or collection breaks with `ModuleNotFoundError: No module named 'clients'`.
- Don't hardcode `.venv/bin/python` in tests — use `sys.executable` (cross-platform).

---

## Doc map

| Question | Read |
|----------|------|
| Documentation map | `docs/README.md` |
| Glossary | `CONTEXT.md` |
| Phases & checklist | `ROADMAP.md` |
| Agent rules | `AGENTS.md` |
| How to update progress | `docs/agents/progress.md` |
