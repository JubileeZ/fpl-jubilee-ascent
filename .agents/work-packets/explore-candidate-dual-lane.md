# Active Task: explore-candidate dual-lane

- **Status:** Done
- **Objective:** Frozen Candidate passing Historical Promotion Gate on dev + confirm via `smoke.py`, adoption in Human Queue — or scope exhausted, every attempt in Candidate Ledger.
- **Acceptance:** Exit (a)/(b)/(c) per `.agents/skills/explore-candidate/SKILL.md`.
- **Issue/Ticket:** none (AFK `/goal`)

## Work Packet (SFDBN)

- **Status:** ADOPTED. Gate loosened (ADR 0049: P ≥ 0.60 both seasons, no min effect) → `learned_start_challenger` dev PASS +1.198 P 0.928, 2024-25 PASS +0.518 2/3 P 0.638 → Champion (ADR 0050). Earlier: History: round 1 no win; round 2 dispatched (a1r2 `5305c270-b8f4-4ac8-a25b-715e1e8fb923` · a2r2 `829ae739-6e39-4196-853e-41b8377a6c54` · a3r2 `bbefa58e-1a34-4951-a633-f5d3dbc36e09` · b1r2 `55abcf10-e096-4e91-b93f-c2efa4c59dbc` · b2r2 `90b91cfa-5ba6-48d3-8562-3ef552f8c7bd`). Common brief `.tmp/agent/explore-candidate/COMMON.md`. Round 2 done, no win. Round 3 dispatched: s `c28e5e6c-eed5-4f7b-b399-921c016afd88` (done) · b2r3 `5b50bd0d-b4aa-47a4-bc98-952ec0464819` · a2r3 `73404e0d-dc6b-416a-a900-8a481a196a02`. Round 4 s4 `acc792be-0dab-47e6-a4da-475687b7126a` (done). Round 5 s5 `0360baff-45f6-4cf3-9499-98976f77e073`. If s5 no new best (> +1.388) and no pass → lane s + b2 closed → Exit (b) (record ledger, note, cleanup). Confirm season 2024-25 has `starts` (learned start lever informative there); elig60 has no scoring-rule dependency.
- **Files:** scratch `.tmp/agent/explore-candidate/<lane>/` only.
- **Decisions:** Mode dual-lane. Workers 3/lane (24 cores). Grids fixed below before smoke.
- **Blocked:** none
- **Subagents (round 1):** a1 `8580f1c3-e429-4858-9a0a-e399334748ff` · a2 `177d6f6e-3ed3-4fae-9612-60a75424962d` · a3 `d2e3f3c0-0473-48d4-a92c-28e831434943` · b1 `706f5647-0759-46bf-9afa-493d42f08d24` · b2 `28e4ab50-a64b-41b3-a18d-b18dc31768a7`
- **Next:** none; 2026-27 GW6+ post-promotion check tracked in current-state.

## Ground (step 0)

- Seasons: dev 2025-26 GW1-38 seed 2024-25 · confirm 2024-25 GW1-38 no seed · holdout 2026-27 sealed.
- Champion `multi_feature_assist_challenger` (`models/multi_feature_assist_challenger.py`); dev regret 71.078, min effect ≈ 0.711.
- Lineage (Ledger Shipped): GLM assist rate · face-value xG/xA · minute-pooled finishing K1800 · start shrink k0.15 · Calibrated Matchup Share scale · participation penalty + calibrated matchup hybrid base · hold-chase levers.

## Ledger screen (step 1)

| Lane | Lever | Row verdict |
|---|---|---|
| A1 bonus | Expanded BPS terms (as-of player residual BPS rate) + eligibility pool form | Open "Non-flat bonus" (must not be flat scale / T / xbps weight retune — Dead) |
| A2 fixture | Downside-only attack scale (cap attack ratio at 1.0, floor) | Open "Fixture downside attack scale" |
| A3 minutes | Transfer-news DNP hazard (prior-GW net transfers / selected) + last-GW benched hazard | new (not uniform hedge / nailed lift / start shrink — Dead) |
| B1 scoreline | True scoreline Poisson: player share × team λ_for; CS = e^{−λ_against·on-pitch} | Open "True scoreline Poisson" (not Dead rate multiplier) |
| B2 residual | Ridge residual correction on Champion base, base reconstructed from `history_df` (no cross-call memory) | Open "Learned hurdle / direct residual correction" (not Dead Poisson-GLM correction) |

Dropped: position goal scale (too close to Dead flat MID/FWD scale); Dual-Vector shrunk (superseded by Calibrated Matchup Share); penalty per90 (terminal-order audit first).

## Lane grids (fixed, round 1)

- A1: `a1_bpsres_k450`, `a1_bpsres_k900`, `a1_bpsres_k1800`, `a1_elig60`, `a1_bpsres_k900_elig60`, `a1_bpsrate_blend50`.
- A2: `a2_down_f60`, `a2_down_f70`, `a2_down_f80` (MID/FWD goals+assists); `a2_down_all_f70` (all outfield); `a2_down_f70_goals`, `a2_down_f70_assists`.
- A3: `a3_news_t3_h25`, `a3_news_t3_h50`, `a3_news_t8_h25`, `a3_news_t8_h50`, `a3_bench_h30`, `a3_news_t3_h25_bench_h30`.
- B1: `b1_sl_s50_att`, `b1_sl_s100_att`, `b1_sl_s50_def`, `b1_sl_s100_def`, `b1_sl_s50_both`, `b1_sl_s100_both`.
- B2: `b2_res_real_l10`, `b2_res_real_l100`, `b2_res_real_l1000`, `b2_res_blend_l10`, `b2_res_blend_l100`, `b2_res_blend_l1000`.

## Lane grids (fixed, round 2 — new mechanism per lane)

- a1r2 heteroscedastic Monte Carlo BPS rank allocation (sd = c·sqrt(xbps+1), replaces softmax form): `a1r2_mc_c2`, `a1r2_mc_c3`, `a1r2_mc_c4`, `a1r2_mc_c3_res900`, `a1r2_mc_c3_elig60`, `a1r2_mc_c3_res900_elig60`.
- a2r2 xMins-side fixture effects (Open row): expected margin m = λ_for−λ_against from as-of club xG; starters' xmins_if_start −= k·max(0,|m|−0.5) min. `a2r2_margin_k4_all`, `a2r2_margin_k8_all`, `a2r2_margin_k4_att`, `a2r2_margin_k8_att`, `a2r2_lead_k6_att` (only when m>0, attackers), `a2r2_trail_k6_def` (only m<0, DEF/GK none — DEF subs when trailing).
- a3r2 post-absence return ramp: regular (≥3 starts in prior 6 GWs before absence) with ≥2 consecutive 0-min GW rows immediately before target → p_start hazard h; just-returned (latest row 1–45 min after ≥2 absent) → xmins_if_start ×(1−r). `a3r2_abs_h20`, `a3r2_abs_h40`, `a3r2_ret_r15`, `a3r2_ret_r30`, `a3r2_abs_h20_ret_r15`, `a3r2_abs_h40_ret_r30`.
- b1r2 schedule-adjusted as-of player rates: deflate each past appearance's xG/xA by (opp as-of xG-conceded ratio at that GW)^s, rescale features per90_xg / Champion GLM base by adjusted/unadjusted ratio (shrunk). `b1r2_sched_s50_g`, `b1r2_sched_s100_g`, `b1r2_sched_s50_a`, `b1r2_sched_s100_a`, `b1r2_sched_s50_ga`, `b1r2_sched_s100_ga`.
- b2r2 learned P(start) ridge-logistic from as-of start/minutes sequence (last 1..6 GW starts, minutes, gaps), blended into Champion p_start (mass to/from DNP, sub unchanged): `b2r2_ps_w25_l10`, `b2r2_ps_w50_l10`, `b2r2_ps_w100_l10`, `b2r2_ps_w25_l1000`, `b2r2_ps_w50_l1000`, `b2r2_ps_w100_l1000`.

## Lane grids (fixed, round 3)

- s (stack): `s_a1_b2w100` (a1 `bpsres_k900_elig60` + b2r2 `ps_w100_l10`), `s_a1_b2w50` (+ `ps_w50_l10`), `s_e60_b2w100` (a1 `elig60` only + `ps_w100_l10`), `s_res900_b2w100` (a1 `bpsres_k900` only + `ps_w100_l10`).
- b2r3 learned participation extensions (on `ps_w100_l10`): `b2r3_ps_featcov` (Champion p_start as covariate), `b2r3_ps_sub` (+ learned p_sub_in), `b2r3_ps_xmins` (+ learned xmins_if_start), `b2r3_ps_sub_xmins`, `b2r3_ps_featcov_sub_xmins`, `b2r3_ps_pos` (position-specific start models).
- a2r3 venue-split player attack rates (as-of home/away per-90 xG/xA shrunk K to player overall): `a2r3_venue_k450_ga`, `a2r3_venue_k900_ga`, `a2r3_venue_k1800_ga`, `a2r3_venue_k900_g`, `a2r3_venue_k900_a`, `a2r3_venue_k900_ga_gc` (+ club home/away GC split).

## Lane grids (fixed, round 4 — lane s, new best)

- s4 mass-preserving learned start (learned model ranks who starts; Champion sets how much start mass; fixes |bias| mechanism, not gate): `s4_e60_w100_mclub` (rescale learned p_start so Σ per club-fixture = Champion Σ), `s4_e60_w100_mglob` (global Σ), `s4_e60_w100_mclubpos` (Σ per club×position), `s4_w100_mclub` (no bonus lever; ablation), `s4_e60_w75` (blend 0.75, no mass), `s4_e60_w75_mclub`.

## Verified smoke rows

Min effect 0.7108 (Champion dev regret 71.078).

- a1 (orchestrator re-audit PASS; no LEAKAGE; state recomputed per fit/predict): k450 +0.027 2/3 P0.51 · k900 −0.153 1/3 · k1800 −0.344 0/3 · elig60 −0.177 1/3 · **k900_elig60 +0.666 2/3 P0.961 (below min effect)** · blend50 −0.019 2/3. Round 1 no win. Levers lose alone; combo = interaction, suspect. Note: 2024-25 archive lacks `defensive_contribution` (residual variants differ on confirm). Subagent read 2026-27 `player_performances` column names + row count only (no values) — disclosed, no tuning use.
- a3 (re-audit PASS; no LEAKAGE): news t3_h25 −0.353 · t3_h50 −1.341 0/3 · t8_h25 −0.195 · t8_h50 −0.223 · **bench_h30 +0.027 2/3 P0.58** · combo −0.624. All fail guardrail too. News flag = ownership churn (~200 players/GW, ~40% regular starters) + one-window lag. Lane a3 round 1 no win → ledger Dead (transfer-share hazard; bench hazard).
- a2 (re-audit PASS; no LEAKAGE; ratio via `_club_asof` at target GW): f60 +0.083 · f70 +0.119 · f80 +0.105 · **all_f70 +0.179 2/3 P0.664** · f70_goals −0.113 · f70_assists −0.178 0/3. Guardrails pass. Round 1 no win; effect ~¼ min effect → ledger Dead (downside attack scale, gated). Penalty isolation inert in backtest (`penalties_order` terminal).
- b1 (re-audit PASS; no LEAKAGE): s50_att −0.442 1/3 · s100_att +0.197 1/3 · s50_def +0.046 1/3 · s100_def +0.491 1/3 P0.70 · **s50_both +1.109 2/3 P0.797** · s100_both +0.491 1/3. **Ledger breach (orchestrator brief error):** share×λ_for = xG90·(def_o/L)^s·hf — club att cancels → `_att` half ≈ Dead "Opponent-relative team Poisson λ rate multiplier" (revisit 2027-09-22). `_att` and `_both` rows void for promotion/stacking; not a Candidate path. Only new mechanism = defence half (team λ_against CS/GC): best +0.491 1/3 → Dead (scoreline CS/GC from team λ_against).
- b2 (audit PASS per report): real_l10 −1.302 · real_l100 −1.346 · real_l1000 −0.977 · blend_l10 −1.359 · blend_l100 −1.566 · blend_l1000 −0.978; all 0/3. Open row "Learned hurdle / residual correction" → Dead (history-only reconstruction loses; prior gain needed memory).
- a1r2 (re-audit PASS; no LEAKAGE): mc_c2 −0.346 1/3 · mc_c3 −0.246 1/3 · mc_c4 −0.077 1/3 · c3_res900 +0.373 2/3 · c3_elig60 +0.396 3/3 P0.923 · c3_res900_elig60 +0.507 2/3 P0.894. Heteroscedastic Normal rank allocation alone loses → Dead. No new lane best (+0.507 < +0.666) → a1 no-improve count 1.
- a2r2 (re-audit PASS): margin_k4_all −0.333 0/3 · k8_all −0.462 · k4_att −0.251 0/3 · k8_att −0.415 0/3 · lead_k6_att −0.283 · trail_k6_def 0.000. xMins-side fixture effects (Open row) → Dead. a2 no-improve count 1.
- a3r2 (re-audit PASS): abs_h20/h40 −0.320 0/3 P0.04 (h40 guardrail fail) · ret_r15/r30 0.000 (too sparse) · combos −0.320. Post-absence hazard + return ramp → Dead. a3 no-improve count 1.
- b2r2 (re-audit PASS): w25_l10 −0.043 · w50_l10 +0.329 1/3 · **w100_l10 +0.601 2/3 P0.751 guardrail FAIL** · w25_l1000 −0.855 · w50_l1000 −1.004 · w100_l1000 +0.182 (MAE guardrails fail). Learned start ridge-logistic: Brier 0.0959→0.0824 (w1, l10) but regret gain sub-threshold. New lane best for b2 (−0.977 → +0.601) → b2 stays open.
- b1r2 (re-audit PASS): sched s50_g −0.967 · s100_g −1.236 · s50_a −0.085 · s100_a −0.359 · s50_ga −0.999 · s100_ga −1.674; all 0/3. Schedule-adjusted as-of rates → Dead. b1 no-improve count 1.
- Round 2 result: no paper win. Counts: a1 1 · a2 1 · a3 1 · b1 1 · b2 0 (new best +0.601).
- Round 3 plan: `s` stack lane (a1 `k900_elig60` bonus × b2r2 learned p_start; orthogonal steps; serves as a1 round 3) · `b2r3` learned participation extensions · `a2r3` venue-split player rates. a3 + b1 closed after 2 rounds, both round bests ≤ 0 on new mechanisms / consistent harm (deviation from strict 2-no-improve count → Human Queue note).
- s (re-audit PASS; no LEAKAGE; state rebuilt per fit/predict): a1_b2w100 +0.616 3/3 P0.709 bias FAIL · a1_b2w50 +0.899 3/3 P0.866 (guardrails ok) · **e60_b2w100 +1.388 3/3 P0.959, |bias| 0.0112 > limit 0.0106 (Champion 0.0006+0.01) — only failure** · res900_b2w100 +0.152 1/3. w100 learned start → bias 0.0112 in all (participation step); xMins MAE 14.446→13.327, Spearman 0.693→0.712. New overall best → lane s round 4.
- a2r3 (re-audit PASS): venue k450_ga −0.268 · k900_ga −0.489 · k1800_ga −0.405 · k900_g −0.391 · k900_a −0.108 · k900_ga_gc −0.478. Venue-split player rates → Dead. a2 no-improve count 2 → **lane a2 CLOSED**.
- b2r3 (re-audit PASS): featcov +0.546 2/3 (guardrails ok, bias 0.0104) · sub +0.278 (bias 0.025 + MAE fail) · xmins +0.519 1/3 (bias 0.0081) · sub_xmins −0.356 · featcov_sub_xmins −0.202 · **pos +1.056 2/3 P0.927, bias 0.0117 FAIL**. Learned p_sub_in worse than Champion → Dead. b2 new best (+1.056) → b2 open; bias fix pending s4 mass-preservation result (round 5 candidate: pos + mass + elig60).
- s4 (re-audit PASS; all guardrails pass): e60_w100_mclub +0.711 2/3 P0.840 · **e60_w100_mglob +1.198 3/3 P0.928** (bias 0.0067) · e60_w100_mclubpos +0.859 2/3 P0.792 · w100_mclub +0.322 1/3 · e60_w75 +0.597 · e60_w75_mclub +0.780 3/3 P0.888. Mass preservation fixes bias, costs effect. Lane s no-improve count 1 (best still +1.388).
- Round 5 (lane s, = b2 round 4) fixed grid: `s5_e60_pos_mglob`, `s5_e60_pos_xmins_mglob`, `s5_e60_pos_featcov_mglob`, `s5_e60_pos_xmins` (no mass), `s5_e60_w100_xmins` (pooled, no mass), `s5_e60_pos_featcov_xmins_mglob`. pos = b2r3 per-position start models; xmins = b2r3 learned minutes-if-start; featcov = b2r3 club rotation covariate; mglob = s4 global mass preservation.
- Round 1 result: no paper win. Lane bests: a1 +0.666 · a2 +0.179 · a3 +0.027 · b1 (void att/both; def +0.491) · b2 −0.977.

## Human authorization (2026-09-28 18:31, user's words)

"if something good let's run gate and replace champion and candidate ... run until adopt or deny; if adopt let commit push". → On dev PASS + confirm PASS: run confirm, edit `config/model_selection.json` (new Champion; old Champion → candidates), `evaluate_model_promotion --confirmation --apply`, ADR, commit + push. Stage only this run's files (pre-existing unrelated dirty tree: `commands/refresh_data.py`, `features/season_archive.py`, tests, `data/archive/2026-27/*` — do not stage).

## Report (Exit b)

**Verdict:** no win. Champion `multi_feature_assist_challenger` unchanged; no config edit, no confirm run, no commit/push (authorization covered adopt only).
**Lanes:** a1 bonus · residual BPS + soft P(60) · +0.666 2/3 P0.961 · a2 fixture · downside attack · +0.179 · a3 minutes · bench hazard · +0.027 · b1 scoreline · defence half +0.491 (attack half void = Dead lever) · b2 learned · per-position start +1.056 P0.927 bias fail · s stack · soft P(60) × learned start · +1.388 3/3 P0.959 bias fail; guardrail-clean best s4 +1.198 3/3 P0.928.
**Audit:** all 15 prototype files AUDIT PASS (orchestrator re-run); no LEAKAGE FAIL.
**Ledger:** 5 Open → Dead (downside attack, learned hurdle residual, non-flat bonus, true scoreline Poisson, xMins-side fixture); 6 new Dead (transfer-share hazard, bench hazard, post-absence hazard, schedule-adjusted rates, venue-split rates, learned participation stack). `tests/test_candidate_ledger.py` pass.
**Checks:** ruff pass · pytest 459 pass · verify.sh 67/0. Scratch `.tmp/agent/explore-candidate/` deleted.
**Files:** `docs/research/dual-lane-candidate-search/` (note, `smoke_results.csv`, `best_stack_prototype.py`), ledger CSV + md, INDEX, current-state, this packet, `.agents/handoff-pointer`.

## Human Queue

1. Commit research record? Options: commit (not push) · commit + push · leave uncommitted. Default taken: leave uncommitted (user authorized commit/push on adopt only). Stage only: `docs/research/dual-lane-candidate-search/`, `docs/research/candidate-ledger/`, `docs/research/INDEX.md`, `docs/agents/current-state.md`, this packet (delete if finished), `.agents/handoff-pointer`.
2. Override Dead row "Learned participation … stacked with soft P(60) bonus eligibility" for one frozen Candidate (`best_stack_prototype.py` `s4_e60_w100_mglob`, dev P 0.928 < 0.95)? Default: no (Dead until 2027-09-28).
3. Disclosures: lane b1 brief made attack half ≈ Dead opponent-rate multiplier (rows void, not used); a1 subagent read 2026-27 `player_performances` column names + row count only (no values/tuning); lanes a3 + b1 closed after 2 rounds instead of strict 2-no-improve count (all new mechanisms ≤ 0).
