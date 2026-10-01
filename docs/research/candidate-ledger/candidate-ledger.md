# Candidate Ledger (tried / untried levers)

**Updated**: 2026-09-29T02:50:00+07:00  
**Data stamp**: Evidence dates per row (source note `Updated`); gate data 2025-26 archive GW1–38 seed 2024-25  
**Season**: 2025/26 gate window  
**Status**: Live — read before proposing any Candidate / Champion lever  
**Purpose**: Stop re-running levers already proven dead. Each row = one lever class, verdict, evidence pointer, earliest revisit date.  
**Related**: [Eval canon](../INDEX.md) · [face-value-challenger](../face-value-challenger/face-value-challenger.md) · [champion-component-gap](../champion-component-gap/champion-component-gap.md)  
**Artifact**: [candidate_ledger.csv](candidate_ledger.csv) `status` / `evidence_date` / `revisit_after` / `evidence_path` — source of truth; tables below are views. `tests/test_candidate_ledger.py` enforces evidence exists + `revisit_after` ≥ `evidence_date` + 1 year.

## Hard rule: no revisit before 1 year

**Dead lever MUST NOT be rebuilt, re-swept, re-smoked, re-gated, or stacked into a Candidate before its `revisit_after` date (evidence date + 1 year). No exceptions** — not for new Champion, new season data, new harness, or "small tweak". Only user's explicit words override. `never` = structural (leakage); no revisit.

## Sealed holdout + confirmation season (ADR 0046, 0047, 0048)

2026-27 GW6+ = sealed holdout. Tuning, smoke, or ablation on it = protocol breach. ADR 0047: frozen Candidate promotes on gate PASS 2025-26 + 2024-25 (confirmation season, one run, no tuning; ADR 0049: bootstrap bar 0.60 on both seasons, no minimum effect); 2026-27 GW6+ = one post-promotion check per Champion. Log run date + verdict in Candidate's row.

## Rules

- **Dead** row: see hard rule. Retuning grid values, wider clamps, or new stack order of same form = same lever.
- New Champion does **not** reopen Dead row early. Different mechanism (new form, new signal) = new row, not revisit.
- After `Revisit after`: allowed; cite old row + reason data changed.
- **Shipped** row: already inside Champion or production contract; do not re-add as Candidate.
- **Open** row: tried-on-paper-but-deferred, or untried. Next-lever pool.
- Every Candidate attempt (pass or fail) → append/update row in `candidate_ledger.csv` + table view in same Checkpoint. Date = evidence date.
- Rows with evidence ≤ 2026-09-28 measured on pre-ADR-0046 features (terminal price/club/penalty order). Leak fix alone is not revisit exception; only user's explicit words reopen.
- Baseline column matters: deltas vs former Champion are hints, not verdicts vs current one — but Dead still holds until revisit date.

## Shipped (in Champion `def_xg_shrink_challenger` or production)

| Lever | Where | Date | Evidence |
|---|---|---|---|
| Position-specific xG/xA rate shrink K (DEF xG 2400 pseudo-min vs flat 360; FWD 900; as-of split-half K; + xA) | `models/def_xg_shrink_challenger.py` | 2026-10-01 | [ADR 0055](../../adr/0055-champion-def-xg-shrink-challenger.md) · [formation-eval-retest](../formation-eval-retest/formation-eval-retest.md) `candidate_gate.csv` (dev PASS +0.793 3/3 P 0.944; 2024-25 PASS +0.594 2/3 P 0.863 under ADR 0054 legal XI eval) |
| Club × DEF xG rate prior (DEF xG/90 shrinks 360 pseudo-min toward as-of club × DEF pooled rate; club prior 5 matches to DEF mean) | `models/club_def_prior_challenger.py` | 2026-09-29 | [ADR 0051](../../adr/0051-champion-club-def-prior-challenger.md) · [component-model-ideas](../component-model-ideas/component-model-ideas.md) `candidate_gate.csv` (dev PASS +0.504 2/3 P 0.955; 2024-25 PASS +0.080 2/3 P 0.619) |
| Learned start probability (ridge-logistic, per-GW mass preserved to Champion total) + P(60)-weighted bonus pool | `models/learned_start_challenger.py` | 2026-09-28 | [ADR 0050](../../adr/0050-champion-learned-start-challenger.md) · `candidate_gate.csv` (user override of Dead row; dev PASS +1.198 P 0.928; 2024-25 PASS +0.518 2/3 P 0.638 under ADR 0049) |
| Multi-feature Poisson GLM assist rate (xA target; xA/creativity/opp xG conceded/team xG/home) | `models/multi_feature_assist_challenger.py` | 2026-09-28 | [ADR 0048](../../adr/0048-champion-multi-feature-assist-challenger.md) · `confirmation_gate_summary.csv` (dev PASS; 2024-25 P 0.896 passes 0.60 bar, and 0.60 both-season bar per ADR 0049) |
| Face-value G/A weights (1.0 xG, 0 threat); no in-season ridge refit | `models/face_value_challenger.py` | 2026-09-28 | [ADR 0045](../../adr/0045-champion-face-value-challenger.md) · `face_value_gate_summary.csv` |
| Minute-pooled goal finishing offset Σ(goals−xG)·90/(Σmin+1800) | same | 2026-09-28 | same (+0.96 combined, flips late) |
| Start-probability shrink p·(1−0.15(1−p)) | same | 2026-09-28 | same (xMins, \|bias\|) |
| Calibrated Matchup Share fixture scale → Club Strength → neutral | builder | 2026-09-22 | [ADR 0040](../../adr/0040-calibrated-matchup-share-shrinkage.md) · [ADR 0037](../../adr/0037-fdr-fallback-multiplier-neutral.md) |
| Participation penalty + calibrated matchup hybrid base (inherited via `hold_chase_challenger`) | `models/` lineage | 2026-09-22 | [ADR 0039](../../adr/0039-champion-participation-penalty-hybrid.md) · [ADR 0041](../../adr/0041-champion-calibrated-matchup-hybrid.md) |

## Dead (do not retry before `Revisit after`)

Baseline HC = former Champion `hold_chase_challenger`; FV = former Champion `face_value_challenger`; MFA = Champion `multi_feature_assist_challenger`. Δ = combined Blended `top_11_regret` delta (positive = Candidate better). Smoke = [smoke_lane_results.csv](../face-value-challenger/smoke_lane_results.csv) `lane`/`variant`.

| Lever class | Tried as | Baseline | Result | Evidence date | Revisit after | Evidence |
|---|---|---|---|---|---|---|
| In-season ridge G/A refit + per-player offsets n/(n+15) (any K) | A1 `d_k50`, `d_k150`, `a_weights_only`, `b_default_w_offsets`, `b_default_w_k150` | HC | Δ −0.13 … −1.41; bias ↑; cameo goal explodes rate | 2026-09-28 | 2027-09-28 | Smoke A1 |
| xG-only weights while keeping fit | A1 `f_xg_only_weights` | HC | Δ −0.63 | 2026-09-28 | 2027-09-28 | Smoke A1 |
| Pooled fit, no offsets | B2 `pf_pooledfit_nooffs` | HC | Δ −0.96, 1/3 | 2026-09-28 | 2027-09-28 | Smoke B2 |
| Assist finishing offsets (goals+assists pooled) | A2 `off_k900/1800/3600` vs `off_goals_*` | HC | adds nothing vs goals-only; `off_k1800` 2/3 late −0.54 | 2026-09-28 | 2027-09-28 | Smoke A2 |
| Finishing pool K ≥ 3600 | A2 `off_goals_k3600` | HC | FAIL, Δ −0.10 | 2026-09-28 | 2027-09-28 | Smoke A2 |
| Flat MID/FWD goal scale 0.9 / 1.1 | A2 `mid_goal_*`, `fwd_goal_*` | HC | 2/3, late negative all | 2026-09-28 | 2027-09-28 | Smoke A2 |
| Bonus softmax temperature T 4/8/10 | A2 `bonus_t*` | HC | late −1.7 … −1.9; T8 FAIL | 2026-09-28 | 2027-09-28 | Smoke A2 |
| Attack/defence strength scale 0.75/1.25, xG sharp slope, mins tilt | A2 `atk_*`, `def_*`, `sharp_*`, `tilt_*` | HC | ≈ zero effect (Δ = base 0.05); `sharp_0`, `tilt_1.00` FAIL | 2026-09-28 | 2027-09-28 | Smoke A2 |
| Nailed-starter lift 0.15/0.50 | A2 `nailed_*` | HC | FAIL both | 2026-09-28 | 2027-09-28 | Smoke A2 |
| Start shrink k ≥ 0.30 | A3 `a3_k0.3*`, `a3_k0.45*` | HC | 1/3 seg; MAE ↓ but loses segments | 2026-09-28 | 2027-09-28 | Smoke A3 |
| Uniform play-probability hedge h 0.05 | A3 `*_h0.05_*` | HC | FAIL | 2026-09-28 | 2027-09-28 | Smoke A3 |
| Player per90 GC log-shrink to league (a 0.4–0.8) | A3 `a3_*_a0.*` | HC | FAIL / noise (a0.8 hurts late) | 2026-09-28 | 2027-09-28 | Smoke A3 |
| xMins-if-start compression toward 80 (s 0.7) | A3 `*_s0.7_*` | HC | FAIL | 2026-09-28 | 2027-09-28 | Smoke A3 |
| Club-pooled per90 GC (pool 0.5/1.0, ax shrink) | A3 `*_pool*_ax*` | HC | 2025-26 best +0.75 (2/3, late −1.81); holdout 2026-27 FAIL 1/3 | 2026-09-28 | 2027-09-28 | Smoke A3 |
| Learned correction as Poisson GLM | B1 `poisson_unfit_*` | HC | ≤ +0.51; λ10 FAIL | 2026-09-28 | 2027-09-28 | Smoke B1 |
| Ensemble with `component_baseline` | B2 `ens_P+CB*`, `component_baseline*` | HC | \|bias\| 0.17–1.36 FAIL | 2026-09-28 | 2027-09-28 | Smoke B2 |
| Equal-weight ensembles of hybrid Candidates | B2 `ens_eq_*` | HC | best +1.01 (P+D1), weight-fragile, below single-model winner | 2026-09-28 | 2027-09-28 | Smoke B2 |
| `defence_link_challenger` (post-link CS inflation) | Candidate #119 | HC | fit Δ +0.08 1/3; breaks MAE guardrails | 2026-09-27 | 2027-09-27 | [layer-diagnosis-133](../champion-component-gap/layer-diagnosis-133.md) |
| `goals_path_challenger` (goals layer re-shape) | Candidate | HC | fit Δ −0.81; opens late via FWD swaps | 2026-09-27 | 2027-09-27 | layer-diagnosis-133 |
| `bonus_arm_challenger` calibrated xbps weights + T (#129) | Candidate | HC | late −0.80; fit Δ −0.50 | 2026-09-27 | 2027-09-27 | layer-diagnosis-133 · Smoke B2 |
| Flat global bonus scale `xp_bonus *= k` | #124 sweep | HC | cannot unlock late | 2026-09-26 | 2027-09-26 | [segment_fix_experiments_124](../champion-component-gap/segment_fix_experiments_124.md) · `bonus_scale_sweep_124.csv` |
| Post-hoc CS/GC retune `k_cs` / `k_gc` (incl. GKP+DEF-only, 1.00–1.15, drop both) | #124, #133 | HC | late Δ < 0 always | 2026-09-27 | 2027-09-27 | segment_fix_experiments_124 · layer-diagnosis-133 |
| Fixture swing multiplicative (`s_att`) and additive arms | fixture-swing-candidates | `calibrated_matchup_hybrid` | mult breached easy cap +0.681; additive tied MAE, worse easy bias | 2026-09-24 | 2027-09-24 | [archive note](../../archive/fixture-swing-candidates/fixture-swing-candidates.md) |
| Raw FDR as attack/defence multiplier fallback | dual-vector-fdr-regime | pre-0037 | easy MID/FWD bias ≈ +0.75 | 2026-09-22 | 2027-09-22 | [archive note](../../archive/dual-vector-fdr-regime-2025-26/dual-vector-fdr-regime-2025-26.md) |
| Official FPL Dual-Vector multipliers (unshrunk) | dual-vector-official-xg | ADR 0037 neutral | not ready on Realized or Process | 2026-09-22 | 2027-09-22 | [archive note](../../archive/dual-vector-official-xg-2025-26/dual-vector-official-xg-2025-26.md) |
| Opponent-relative team Poisson λ rate multiplier | team-poisson-lambda | ADR 0037 neutral | over-predicts easy fixtures | 2026-09-22 | 2027-09-22 | [archive note](../../archive/team-poisson-lambda-2025-26/team-poisson-lambda-2025-26.md) |
| Uncalibrated Matchup Share | matchup-share-addon | neutral | all-pool worse than neutral; superseded by calibrated | 2026-09-22 | 2027-09-22 | [matchup-share note](../matchup-share-addon-2025-26/matchup-share-addon-2025-26.md) |
| Multi-feature Poisson GLM goals rate (xG/threat/opp xG conceded/team xG/home; +finishing/position) | smoke `g_*` | FV | best +0.547 1/3 P 0.70; no-fixture −0.263 | 2026-09-28 | 2027-09-28 | [multi-feature-event-rate](../multi-feature-event-rate/multi-feature-event-rate.md) `smoke_results.csv` |
| Multi-feature Poisson GLM goals-conceded rate (player xGC/opp xG/own xG conceded/home) | smoke `c_*` | FV | best `c_gc_l10` +0.986 2/3 P 0.923 (near miss); opp-only −0.313 | 2026-09-28 | 2027-09-28 | same |
| Stacked multi-feature GLM rates (assists + GC and/or goals) | smoke `s_*` | FV | best +1.524 2/3 P 0.891; not additive | 2026-09-28 | 2027-09-28 | same |
| Fixture downside attack scale (clip opp ratio at 1.0, floor 0.6–0.8) | smoke `a2_down_*` | MFA | best +0.179 2/3 P 0.664 | 2026-09-28 | 2027-09-28 | [dual-lane-candidate-search](../dual-lane-candidate-search/dual-lane-candidate-search.md) `smoke_results.csv` |
| xMins-side fixture effects (expected-margin xmins_if_start trim) | smoke `a2r2_*` | MFA | all ≤ 0 | 2026-09-28 | 2027-09-28 | same |
| Venue-split player attack rates | smoke `a2r3_*` | MFA | all −0.11 … −0.49 | 2026-09-28 | 2027-09-28 | same |
| Non-flat bonus: residual BPS rate, soft P(60) eligibility, heteroscedastic Normal rank allocation | smoke `a1_*`, `a1r2_*` | MFA | standalone ≤ +0.03 or negative; combo +0.666 P 0.961 < min effect | 2026-09-28 | 2027-09-28 | same |
| Transfer-share DNP hazard | smoke `a3_news_*` | MFA | −0.20 … −1.34 (ownership churn, lagged) | 2026-09-28 | 2027-09-28 | same |
| Benched-last-GW DNP hazard | smoke `a3_bench_h30` | MFA | +0.027 guardrail fail | 2026-09-28 | 2027-09-28 | same |
| Post-absence DNP hazard + return ramp | smoke `a3r2_*` | MFA | −0.320 / 0.000 | 2026-09-28 | 2027-09-28 | same |
| True scoreline Poisson (share × λ_for; CS/GC from λ_against) | smoke `b1_sl_*` | MFA | attack half = Dead opp rate multiplier (void); defence best +0.491 1/3 | 2026-09-28 | 2027-09-28 | same |
| Schedule-adjusted as-of player xG/xA | smoke `b1r2_*` | MFA | −0.09 … −1.67 0/3 | 2026-09-28 | 2027-09-28 | same |
| Learned hurdle / residual correction (history-reconstructed base) | smoke `b2_res_*` | MFA | −0.98 … −1.57 0/3 | 2026-09-28 | 2027-09-28 | same |
| Learned participation variants other than shipped `learned_start_challenger` (per-position / learned xmins / p_sub_in / no or per-club mass), alone or + soft P(60) bonus eligibility | smoke `b2r2_*`, `b2r3_*`, `s_*`, `s4_*`, `s5_*` | MFA | near miss at 0.95: +1.388 3/3 P 0.959 bias fail; per-club mass +0.711 | 2026-09-28 | 2027-09-28 | `smoke_results.csv` · `best_stack_prototype.py` |
| Terminal archive columns as inputs (`total_points`, `minutes`, `goals_scored`, `expected_goals`, `bps`, `threat`, `selected_by_percent`, `now_cost`, `status`, `chance_of_playing`) | any | — | leakage (season-end values in archive features) | 2026-09-28 | never (structural) | face-value-challenger Method |
| Position-split goals weight (restore FWD; keep MID/DEF dampen) | smoke `a1_posgoals_*` (6) | LSC | all negative −0.28 … −0.89; MID/DEF dampen misses hauls | 2026-09-28 | 2027-09-28 | [asymmetric-finishing](../asymmetric-finishing-challenger/asymmetric-finishing-challenger.md) `smoke_results.csv` |
| Penalty-taker signal from per90 only | smoke `a3_pen_taker_*` (6) | LSC | delta +0.0000 0/3; inert on top-11 | 2026-09-28 | 2027-09-28 | same `smoke_results.csv` |
| State-conditional bonus logits (start-state / two-entrant xbps in logit; T6 pool6) | smoke `bon_01_*` (3) | LSC | all −0.687 1/3 P 0.131; variants identical on top-11 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Start vs sub attack intensity (pooled sub/start per90 ρ by position; per-state rate split) | smoke `atk_03_*` (5) | LSC | all 1/3 segs; best `atk_03_ga_k0` +0.176 P 0.827; start-deflate only −0.037 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Position FPL-assist conversion (GLM xA rate × (1 + α(c_pos − 1)), as-of pooled A/xA by position) | smoke `atk_01_*` (6) | LSC | 5/6 negative −0.16 … −0.53; best FWD-only +0.073 1/3 P 0.686 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Suspension ledger DNP hazard (5/10 cumulative yellows + red h1–h3; optional teammate mass) | smoke `min_01_*` (6) | LSC | all 1/3 segs; best `v4_preserve_mass` +0.593 P 0.784; rest +0.058 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Result-coupled two-stage bonus pool (Skellam W/D/L × shrunk team share; within-team PL) | smoke `bon_03_*` (4) | LSC | all −0.22 … −0.58 P ≤ 0.28 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Empirical-Bayes P(60\|state) Beta-binomial (n0 MoM/fixed per position) | smoke `min_02_*` (6) | LSC | all −0.07 … −0.85; best `n0_10` −0.074 1/3 P 0.39 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Asymmetric goal finishing shrinkage (K_pos=1500; K_neg=3000) | `asymmetric_finishing_challenger` (smoke `a2_asym_fin_*`) | LSC | dev 2025-26 PASS +0.261 2/3 boot P 0.989; confirm 2024-25 FAIL −0.231 0/3 boot P 0.199 | 2026-09-28 | 2027-09-28 | [asymmetric-finishing](../asymmetric-finishing-challenger/asymmetric-finishing-challenger.md) `candidate_gate.csv` |
| CS exposure over 60+ starts (GK and DEF clean-sheet exposure uses as-of player mean start minutes given >=60 minutes; shrunk to 85.0 min with K=4 starts) | `cs_exposure_challenger` (smoke `def_02_m60_k4`) | CDP | dev 2025-26 PASS +0.096 2/3 boot P 0.664; confirm 2024-25 FAIL −0.443 0/3 boot P 0.000 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `candidate_gate.csv` |
| Correlated Monte-Carlo BPS rank (team goals Poisson -> multinomial scorers + shared CS + assists + states; BPS with Champion weights; mean Plackett-Luce) | smoke `bon_02_*` (4) | CDP | all negative −1.09 … −1.76 0/3 boot P ≤ 0.058; best `bon_02_all_s2000` −1.086 0/3 P 0.013 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Route displaced start mass to bench (when p_start cut by learned blend; send fraction r to p_sub_in instead of 100% to DNP) | smoke `min_03_*` (5) | CDP | all negative −0.38 … −1.13; best `min_03_r045_fv_shrink` −0.380 2/3 P 0.123 (breaks MAE guardrails) | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Incumbent-return displacement (zero-sum club x position start mass transfer from stand-ins to returning incumbent after 2+ DNPs) | smoke `min_04_*` (4) | CDP | all negative −0.504 1/3 boot P 0.045 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Rare-event pooled rates bundle (GKP penalty save rate and outfield own-goal rate shrunk to as-of league average with K pseudo-minutes) | smoke `def_05_06_*` (4) | CDP | all negative −0.004 … −0.352 0/3 boot P ≤ 0.063; best `def_05_06_k900` −0.0036 0/3 P 0.000 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Pooled red-card rate (Position x state pooled red rate; player shrink K>=3600; K>=9000; K inf) | smoke `crd_02_*` (3) | CDP | all negative −0.13 … −0.26; best `crd_02_k9000`/`kinf` −0.126 1/3 boot P 0.355 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Penalty-miss de-noising (Replace noisy per-player penalty miss rate with zero; K3600; K9000; league const) | smoke `atk_07_*` (4) | CDP | all negative −0.41 … −0.43 0/3 boot P ≤ 0.013; best `atk_07_zero` −0.409 0/3 P 0.013 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Club SoT volume x pooled save rate (Shots-on-target faced/90 = club GKP (saves+GC)/mins shrunk; x keeper save rate shrunk to 0.67; pool 0.5/1.0; K50/K200) | smoke `def_08_*` (5) | CDP | all negative −0.27 … −0.41; best `def_08_pool05_k200` −0.267 0/3 boot P 0.090 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Back-line personnel lambda adjust (Multiplier on goals conceded per 90 based on absent regular defenders deficit; beta 0.2; 0.4; fitted) | smoke `def_09_*` (3) | CDP | all negative −0.47 … −0.62 1/3 boot P ≤ 0.196; best `def_09_beta04` −0.472 1/3 P 0.196; guardrail fail | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Teammate-absence share redistribution (Fraction w of absent players expected club xG share to present teammates; same-pos / outfield; goals / g+a) | smoke `atk_06_*` (5) | CDP | all negative −0.72 … −2.28; best `atk_06_w025_same_pos_goals` −0.722 1/3 boot P 0.152; severe MAE regressions on larger w | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Empirical-Bayes yellow card rate (Rate = (sum w*yc + K_pos*prior)/(sum w*min + K_pos)*90; K_pos 900; 1800; 3600; Method of Moments) | smoke `crd_01_*` (4) | CDP | all negative −0.51 … −0.78 1/3 boot P ≤ 0.185; best `crd_01_k1800` −0.505 1/3 P 0.185 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Minutes-state and venue card hazard (Per-appearance sub vs start yellow rate and/or away/home card multiplier) | smoke `crd_03_*` (3) | CDP | all negative −0.20 … −0.87 0/3 boot P ≤ 0.024; best `crd_03_state_on` −0.203 0/3 P 0.024 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| GKP club-fixture slot accounting (Softmax GKP start prob per club fixture sums to 1; excess to DNP; or linear scale / 11-cap) | smoke `min_05_*` (5) | CDP | all negative −0.11 … −1.21 1/3 boot P ≤ 0.239; best `min_05_gkp_scale` −0.108 1/3 P 0.239 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Fitted Plackett-Luce BPS rank model (Ridge utility on observed fixture-level BPS; lambda 10/50 with/without history bps) | smoke `bon_04_*` (4) | CDP | all negative −1.44 … −1.81 0/3 boot P ≤ 0.044; best `bon_04_lam10_no_bps` −1.443 0/3 P 0.044 | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Latent-role HMM participation modeling (3-4 hidden roles with EM transitions; replace or 50-50 blend with logistic model) | smoke `min_06_*` (6) | CDP | all negative −0.90 … −3.70 0/3 boot P ≤ 0.099; best `min_06_hmm3_pooled_blend` −0.896 0/3 P 0.099; all failed MAE guardrails | 2026-09-29 | 2027-09-29 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Defcon within-player dispersion and minutes mixture (NB dispersion r=15-25; 60+ vs early exit start mixture) | smoke `def_03_*` (6) | CDP | all negative −0.15 … −1.07 0/3 boot P ≤ 0.027; best `def_03_mix_r8p5_7` −0.146 0/3 P 0.000 | 2026-09-30 | 2027-09-30 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Defcon venue and opposition pressure scaling (Away/home venue multiplier + opp attack/team defence ratio beta 0.1-0.5) | smoke `def_07_*` (6) | CDP | all negative −0.17 … −0.77 0-1/3 boot P ≤ 0.355; best `def_07_beta01` −0.172 1/3 P 0.279 | 2026-09-30 | 2027-09-30 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Defcon Beta-binomial hit rate (Empirical hit rate of 10+/12+ defcon shrunk to NB-implied p0; a=4-16; 60+ starts vs all apps) | smoke `def_04_*` (6) | CDP | all negative −0.13 … −1.22 0-1/3 boot P ≤ 0.416; best `def_04_a4_60plus` −0.133 1/3 P 0.416 | 2026-09-30 | 2027-09-30 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Goals-conceded shape Poisson (E[floor(X/2)] under Poisson on Champion lambda; was NegBin r=3; CS unchanged) | smoke `def_01_*` (6) | CDP | dev 2025-26 FAIL vs Champion CDP: all negative −0.06 … −0.83 0/3 boot P ≤ 0.027; best `def_01_nb_r8` −0.057; `def_01_nu1p0` −0.087 | 2026-09-30 | 2027-09-30 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Club-coherent assist mass (club-fixture factor (1-w)+w*rho*club goals/club assists; rho as-of league assists/goals; w 0.5) | smoke `atk_02_*` (5) | CDP | dev 2025-26 FAIL vs Champion CDP: all negative −0.33 … −1.20 0-1/3 boot P ≤ 0.330; best `atk_02_w05_real` −0.334; MAE guardrail fail | 2026-09-30 | 2027-09-30 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `smoke_results.csv` |
| Dual-Vector ratios shrunk toward 1.0 | untried | — | superseded by shipped ADR 0040 (Calibrated Matchup Share); multiplicative scaling failed easy-bias cap (+0.681 vs neutral +0.221) and Jensen CS inflation | 2026-09-30 | 2027-09-30 | [archive note](../../archive/dual-vector-official-xg-2025-26/dual-vector-official-xg-2025-26.md) |
| Schedule-congestion start shift (logit shift -0.2 on learned p_start for fixtures <3.5 days after previous kickoff) | `schedule_congestion_challenger` (smoke `min_07_shift_m02_raw`) | CDP | dev 2025-26 PASS +0.063 2/3 boot P 0.967; confirm 2024-25 FAIL −0.105 0/3 boot P 0.000 | 2026-09-30 | 2027-09-30 | [component-model-ideas](../component-model-ideas/component-model-ideas.md) `candidate_gate.csv` |
| Club starting mass conservation (sum p_start=11) and vacancy redistribution (capacity-capped and formation-constrained) | smoke `pos_cap_*` (3), `form_slot_*` (3) | CDP | all negative −3.14 … −4.13 0/3 boot P ≤ 0.022; Playable Pool Bias exploded 0.65-0.70 vs 0.42; Captaincy Regret regressed 5.26-5.58 vs 4.69 | 2026-10-01 | 2027-10-01 | [club-starting-mass-redistribution](../club-starting-mass-redistribution/club-starting-mass-redistribution.md) `smoke_results.csv` |
| Plackett-Luce bonus pool saturation ($B_{\max} \in [1.20, 1.50]$) with zero-sum fixture redistribution to starters | smoke `bon_bmax120`, `bon_bmax130`, `bon_bmax140`, `bon_bmax130_nosave`, `bon_bmax150` (5) | DXS | all negative −0.16 … −0.38 0-1/3 segs boot P ≤ 0.377; forwards starved of expected value | 2026-10-01 | 2027-10-01 | [player-projection-calibration](../player-projection-calibration/player-projection-calibration.md) `smoke_results.csv` |
| Natural rate calibration (unsharp xG slope 0.0; untrim low-xG 1.0; clamp 90 min) | `calibrated_rate_challenger` (smoke `att2_nosharp_notrim_notilt`) | DXS | dev 2025-26 PASS +0.355 2/3 boot P 0.901; confirm 2024-25 FAIL −0.449 1/3 boot P 0.237 | 2026-10-01 | 2027-10-01 | [player-projection-calibration](../player-projection-calibration/player-projection-calibration.md) `candidate_gate.csv` |


## Open (next-lever pool; not proven dead)

None (all candidate levers evaluated or superseded).


## Agent Prompt

```text
Before any new Candidate work:
1. Read this ledger. Match proposed lever to a row by mechanism, not name.
2. Dead row with Revisit after > today → pick another lever or propose a new mechanism (new row).
3. After Candidate result (pass/fail): update candidate_ledger.csv row (status, evidence_date, revisit_after = date + 1 year for dead, evidence_path), then table view here. Run uv run pytest tests/test_candidate_ledger.py.
4. Update INDEX `Updated` if row moves to Shipped.
```
