# Candidate Ledger (tried / untried levers)

**Updated**: 2026-09-28T21:20:00+07:00  
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

## Shipped (in Champion `learned_start_challenger` or production)

| Lever | Where | Date | Evidence |
|---|---|---|---|
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

## Open (next-lever pool; not proven dead)

| Lever | State | Best evidence | Blocker / next step |
|---|---|---|---|
| Position-split goals weight (restore FWD, keep MID/DEF dampen) | Untried as built Candidate | layer-diagnosis-133 option 1 | Differs from flat MID/FWD 0.9/1.1 (Dead); gate vs current Champion |
| Dual-Vector ratios shrunk toward 1.0 (`1 + s·(r−1)`) | Untried | dual-vector-official-xg follow-up | Both eval targets; easy-slice bias ≤ neutral |
| Penalty-taker signal from per90 only | Untried | smoke brief idea | `penalties_order` confirmed terminal (smoke audit refuses it; lineage penalty isolation inert in backtest) — derive taker from history only |

## Agent Prompt

```text
Before any new Candidate work:
1. Read this ledger. Match proposed lever to a row by mechanism, not name.
2. Dead row with Revisit after > today → pick another lever or propose a new mechanism (new row).
3. After Candidate result (pass/fail): update candidate_ledger.csv row (status, evidence_date, revisit_after = date + 1 year for dead, evidence_path), then table view here. Run uv run pytest tests/test_candidate_ledger.py.
4. Update INDEX `Updated` if row moves to Shipped.
```
