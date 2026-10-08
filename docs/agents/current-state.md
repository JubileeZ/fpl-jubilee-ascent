# Current Implementation State

Read if no prior context. `ROADMAP.md` = target. This file = what exists today. Historical dumps → `docs/archive/` (`docs/agents/progress.md`).

**Current phase:** Phases 1–5 complete. Season 2026/27 operations + research. Tracked implementation issues closed (`JubileeZ/FPL-Jubilee-Ascent`).

## Next work — start here

**Streamlit Planner, 2026-10-08:** `uv run python -m commands.streamlit_planner` @ `http://127.0.0.1:8501`; Apple utility direction (`DESIGN.md`), single editable plan, Player details, sell/bench split, automatic legal XI, persistent drafts, recovered solver jobs + completed-result cache. ADR 0059 supersedes branching UI for new planner. React dashboard/Explorer retained. Product spec + launch guide: `docs/product/streamlit-transfer-planner.md`, `docs/product/streamlit-planner-deployment.md`. Deployment deferred; Linux image + visual browser QA unverified on current host.

**Active map:** None. [#143 · [Wayfinder Map] Decision Tree Planner & Solve Engine Hardening](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/143) — **ALL TICKETS COMPLETED (#144-#149)**. Hardened branch solve model fallback to Champion, node serialization keys mapped, parent node squad/bank state inheritance live, risk presets hit limits enforced (Safe 0, Default 1, Optimistic 1, High Risk 2), operational 0% availability hard DNP exception live (ADR 0056), Plans Evaluation Suite refactored to deterministic comparison matrix & trade-off frontier, inline node chip booking live with downstream store propagation. Prior Map #135 completed.

Champion `def_xg_shrink_challenger` (ADR 0055, 2026-10-01, provisional) — see Formation eval retest below. Prior Champion `club_def_prior_challenger` (ADR 0051, 2026-09-29) — see Component-model-ideas Queue run below. Prior Champion `learned_start_challenger` (ADR 0050, 2026-09-28).

**Slate:** Champion `def_xg_shrink_challenger` (provisional); Candidates `club_def_prior_challenger`, `learned_start_challenger` (former Champions). `multi_feature_assist_challenger` → Catalog (2026-10-01). `face_value_challenger`, `hold_chase_challenger`, `defence_link_challenger`, `bonus_arm_challenger` → Catalog.

**Eval hardening 2026-09-28 (ADR 0046):** backtest features point-in-time (price/club pre-target, terminal player cols dropped); gate adds min effect 1% (removed, ADR 0049), block-bootstrap P ≥ 0.95 (now 0.60, ADR 0049), guardrail tolerances; 2026-27 GW6+ sealed holdout. Point-in-time re-gate: `face_value_challenger` vs `hold_chase_challenger` = regret tie (FAIL), accuracy win → Champion kept by user decision.

**Promotion protocol (ADR 0047, 0049):** gate PASS 2025-26 (boot P ≥ 0.60) + 2024-25 (no seed, one run, boot P ≥ 0.60) → promote on user's words; 2026-27 GW6+ = post-promotion check (FAIL → revert to prior Champion).

**Live data fix 2026-09-28:** `features/processor.py` ingests only `element_summary_<id>.json` for ids in current bootstrap. Raw cache held 174 stale 2025-26 summaries (ids 668–841) → 4401 prior-season rows in 2026-27 pin `player_performances` (fixture-id collisions; crashed new Champion). Pin rebuilt locally (`snapshot_season --season 2026-27 --from-raw-dir`), 3216 rows GW1–5. Source cleanup: `prune_stale_element_summaries` (`features/season_archive.py`) runs in `refresh_data` on `data/raw` and in `pin_season_archive` on pin raw; 174 stale files removed from both, pin hash refreshed.

**Dual-lane search 2026-09-28:** 88 variants vs Champion, no pass; 11 levers → Dead. User override: frozen `learned_start_challenger` promoted to Champion (ADR 0050, provisional). Slate: `multi_feature_assist_challenger`, `face_value_challenger`. Superseded by ADR 0051.

**Dual-lane search round 2 (2026-09-28):** 18 variants vs Champion `learned_start_challenger`. Position-split goals all negative; penalty taker detection inert (+0.0000); asymmetric finishing shrinkage dev PASS (+0.261 2/3 P 0.989), confirm 2024-25 FAIL (-0.231 0/3 P 0.199) -> Dead. Champion `learned_start_challenger` stands. Note `docs/research/asymmetric-finishing-challenger/asymmetric-finishing-challenger.md`.

**Component-model-ideas Queue run (2026-09-30):** explore-candidate Queue mode complete across all 29 queue rows in `idea_queue.csv`. ATK-05 club × DEF xG prior dev +0.504 2/3 P 0.955, confirm 2024-25 +0.080 2/3 P 0.619 → Champion `club_def_prior_challenger` (ADR 0051). 3 Candidates in catalog confirm-fail (ATK-04, DEF-02, MIN-07). MIN-07 unblocked by adding `kickoff_time` to Feature Contract; dev PASS (+0.063 2/3 P 0.967), confirm FAIL (-0.105 0/3 P 0.000) → Dead (`schedule_congestion_challenger`). Open levers re-tested against Champion CDP: DEF-01 Poisson GC and ATK-02 club assist mass failed dev → Dead. Dual-Vector ratios shrunk → Dead (superseded by ADR 0040). Candidate Ledger Open pool empty; all 29 queue ideas resolved. Note `docs/research/component-model-ideas/component-model-ideas.md`.

**Eval upgrade 2026-10-01 (ADR 0054):** Promotion gate primary upgraded from unconstrained `top_11_regret` to `formation_xi_regret` (closed-form scan across 8 legal formations: 1 GKP, 3–5 DEF, 2–5 MID, 1–3 FWD); Captaincy Regret guardrail added (tol +0.15 pts/GW); MAE and Signed Bias guardrails evaluated on Playable Pool (xp ≥ 2.0 or mins ≥ 30).

**Formation eval retest & promotion 2026-10-01 (ADR 0055):** Past dev winners re-screened under ADR 0054 legal formation XI eval. `def_xg_shrink_challenger` (ATK-04, DEF xG K=2400) dev PASS +0.793 3/3 P 0.944, confirm 2024-25 PASS +0.594 2/3 P 0.863 → Champion `def_xg_shrink_challenger` (ADR 0055, provisional). `cs_exposure_challenger` confirm FAIL (-0.216), `asymmetric_finishing_challenger` confirm FAIL (-0.155), `schedule_congestion_challenger` dev FAIL (+0.114, 1/3 segs). Note `docs/research/formation-eval-retest/formation-eval-retest.md`.

**Club starting mass redistribution search 2026-10-01:** Scoped explore-candidate evaluated 6 variants across 2 lanes (`pos_cap`, `form_slot`) enforcing club 11-player start conservation ($\sum_{\text{club}} p_{\text{start}} = 11.0$) and vacancy reallocation from sidelined regular starters. All 6 variants failed dev gate (−3.14 to −4.13 combined regret delta, 0/3 segs, boot P ≤ 0.022); Playable Pool Bias exploded (0.65–0.70 vs 0.42); Captaincy Regret regressed (5.26–5.58 vs 4.69). Root cause: single-DNP suppression penalizes rested elite assets; per-club 11.0 constraint deflates elite rotating squads (Man City/Chelsea ~12.5 starting mass) while inflating unplayable budget players. Lever logged Dead (`revisit_after = 2027-10-01`). Note `docs/research/club-starting-mass-redistribution/club-starting-mass-redistribution.md`.

**Player projection calibration search 2026-10-01:** Scoped explore-candidate evaluated 15 variants across 2 lanes targeting Haaland/elite rate over-inflation (8.5–9.8 pts vs 7.2 historical) and budget starter under-projection (−1.5 pt signed bias). Lane 1 bonus saturation ($B_{\max} \in [1.20, 1.50]$) failed dev gate (−0.16 to −0.38 delta) by starving forward expected value. Lane 2 natural rates (`calibrated_rate_challenger`: unsharp xG slope 0.0, untrim low-xG 1.0, 90-min clamp) dev PASS (+0.355 2/3 P 0.901), confirm 2024-25 FAIL (−0.449 1/3 P 0.237) due to Palmer/Haaland 2024-25 haul capture reliance on sharp slope. Levers logged Dead (`revisit_after = 2027-10-01`). Champion `def_xg_shrink_challenger` stands. Note `docs/research/player-projection-calibration/player-projection-calibration.md`.

**Next leads:** 2026-27 GW6+ = post-promotion check for `def_xg_shrink_challenger` (ADR 0047). GW5 last finished, GW6 deadline 2026-10-10 → status stays provisional. Deferred eval work: White/SPA across variants.


Eval canon: `docs/research/INDEX.md`. Prior residual work: `docs/research/champion-component-gap/`.

## Research truth

Live index: `docs/research/INDEX.md` — **Eval canon** block = promotion metrics vs component-gap metrics (read first for Candidate/Champion work). Companions live in topic folders. Production minutes/rates = Club Fixture shrinkage + Trailing Start Window (ADR 0035). Production difficulty = **Modified FDR** (difficulty only). Fixture xP scale = **Calibrated Matchup Share** when this-season Official club xG exists (ADR 0040); else Club Strength; else neutral ×1.0 (ADR 0037). Champion = `def_xg_shrink_challenger` (ADR 0055; see Slate above). Component-gap crown = `xp_goals` structural (`docs/research/champion-component-gap/component_gap_summary.csv` `mse_share`). Research ranking = **DCS**. Dual-Vector Strength not in production Python.

## What exists

| Area | Path | Notes |
|------|------|-------|
| Scaffold | `AGENTS.md`, `ROADMAP.md`, `CONTEXT.md` | Config, phases, glossary |
| Deps | `pyproject.toml`, `.venv/` | uv |
| Clients | `clients/` | FPL API + Playwright/JWT auth |
| Data dictionary | `docs/data_dictionary.md` | API → parquet |
| CLI | `commands/` | Refresh, snapshot, model, backtest, FDR, solve, dashboard, bias |
| Models | `models/`, `docs/model_name.md` | Catalog `name`. Champion in `config/model_selection.json` |
| Features / projections | `features/`, `projections/` | Typed contracts; Explorer slice; Role retired; Trailing Start Window default (ADR 0035); Calibrated Matchup Share overlay (`features/matchup_share.py`, ADR 0040); Official processed heals from Live Season Pin on resolve (ADR 0036) |
| Dashboard | `dashboard/`, `commands/dashboard.py`, `DESIGN.md` | Explorer + Decision Tree Planner + Research Reader + Model Methodology via collapsible left sidebar. `http://127.0.0.1:8000`. IPv4 bind. Decision Tree Planner (ADR 0058): straight-line parallel branch matrix (`nodesDraggable=false`), horizon-locked box depth (dynamic prune/extend, bi-directional navbar sync), Pre-GW6 Current Squad root origin, score-optimized starting XI (closed-form scan across 8 legal formations, descending bench xP, score-based (C)/(V) assignment), dual-state solver recommendation cache with 1-click `↩ Revert`, per-node branch Highs MILP solve with in-horizon chip filtering, and collapsible pitch drawer (`▬ Min`). Explorer and Research retained intact. |
| README | `README.md` | How to use + CLI |
| Backtesting | `backtesting/` | Walk-forward, Decision Regret, Transfer Plan Walk-Forward |
| Solver | `solver/` | open-fpl-solver `2ff829f` highspy; live Transfer Plan default gap 0% with deterministic digest caching (ADR 0057, superseding ADR 0043); Dream Team and Walk-Forward stay gap 0 |
| Research | `docs/research/`, `docs/archive/` | Live INDEX + topics. `data/archive/` = Season Archive pins |

## What does NOT exist yet (do not assume)

- `availability-snapshots` branch missing on `origin`. Capture workflow kept. Promotion provisional until two Live Validation Windows.
- Snapshot-backed nonzero-chance calibration not implemented; opt-in model applies next-GW `0%` hard DNP only.
- Transfer-plan regret deferred until one-Gameweek Decision Regret passes holdout. First-Half Walk-Forward ranking exists as research companion.

## Safe commands today

```bash
uv run pytest
uv run ruff check .
uv run python -m commands.refresh_data
uv run python -m commands.run_model club_def_prior_challenger
uv run python -m commands.dashboard
uv run python -m commands.solve --preseason --xmin_lb 0
uv run python -m commands.measure_champion_bias
uv run python -m commands.transfer_plan_walkforward
```

Catalog names and more recipes: `README.md` (weekly dashboard path first), `docs/model_name.md`.

## Agent pitfalls

- Playwright Chromium required for `refresh_data` / `snapshot_season` when `FPL_TOKEN` unset.
- Windows console cp1252; commands call `configure_utf8_stdio()` before non-ASCII prints.
- pytest `pythonpath = ["."]`; do not drop it.
- Tests use `sys.executable`, not `.venv/bin/python`.
- Transfer Plan Scenarios need User Squad; plan JSON is `data/transfer_plan_scenarios.json`, not `dashboard_data.json`.

## Doc map

Index: `docs/README.md`. Weekly path / Key Commands: `README.md`, `AGENTS.md`.
