# Candidate Ledger (tried / untried levers)

**Updated**: 2026-09-28T13:30:00+07:00  
**Data stamp**: Evidence dates per row (source note `Updated`); gate data 2025-26 archive GW1–38 seed 2024-25  
**Season**: 2025/26 gate window  
**Status**: Live — read before proposing any Candidate / Champion lever  
**Purpose**: Stop re-running levers already proven dead. Each row = one lever class, verdict, evidence pointer, earliest revisit date.  
**Related**: [Eval canon](../INDEX.md) · [face-value-challenger](../face-value-challenger/face-value-challenger.md) · [champion-component-gap](../champion-component-gap/champion-component-gap.md)  
**Artifact**: [candidate_ledger.csv](candidate_ledger.csv) `status` / `evidence_date` / `revisit_after` / `evidence_path` — source of truth; tables below are views. `tests/test_candidate_ledger.py` enforces evidence exists + `revisit_after` ≥ `evidence_date` + 1 year.

## Hard rule: no revisit before 1 year

**Dead lever MUST NOT be rebuilt, re-swept, re-smoked, re-gated, or stacked into a Candidate before its `revisit_after` date (evidence date + 1 year). No exceptions** — not for new Champion, new season data, new harness, or "small tweak". Only user's explicit words override. `never` = structural (leakage); no revisit.

## Sealed holdout (ADR 0046)

2026-27 GW6+ = sealed holdout. Tuning, smoke, or ablation on it = protocol breach. ADR 0047: frozen Candidate promotes on gate PASS 2025-26 + 2024-25 (confirmation season, one run, no tuning); 2026-27 GW6+ = one post-promotion check per Champion. Log run date + verdict in Candidate's row.

## Rules

- **Dead** row: see hard rule. Retuning grid values, wider clamps, or new stack order of same form = same lever.
- New Champion does **not** reopen Dead row early. Different mechanism (new form, new signal) = new row, not revisit.
- After `Revisit after`: allowed; cite old row + reason data changed.
- **Shipped** row: already inside Champion or production contract; do not re-add as Candidate.
- **Open** row: tried-on-paper-but-deferred, or untried. Next-lever pool.
- Every Candidate attempt (pass or fail) → append/update row in `candidate_ledger.csv` + table view in same Checkpoint. Date = evidence date.
- Rows with evidence ≤ 2026-09-28 measured on pre-ADR-0046 features (terminal price/club/penalty order). Leak fix alone is not revisit exception; only user's explicit words reopen.
- Baseline column matters: deltas vs former Champion are hints, not verdicts vs current one — but Dead still holds until revisit date.

## Shipped (in Champion `face_value_challenger` or production)

| Lever | Where | Date | Evidence |
|---|---|---|---|
| Face-value G/A weights (1.0 xG, 0 threat); no in-season ridge refit | `models/face_value_challenger.py` | 2026-09-28 | [ADR 0045](../../adr/0045-champion-face-value-challenger.md) · `face_value_gate_summary.csv` |
| Minute-pooled goal finishing offset Σ(goals−xG)·90/(Σmin+1800) | same | 2026-09-28 | same (+0.96 combined, flips late) |
| Start-probability shrink p·(1−0.15(1−p)) | same | 2026-09-28 | same (xMins, \|bias\|) |
| Calibrated Matchup Share fixture scale → Club Strength → neutral | builder | 2026-09-22 | [ADR 0040](../../adr/0040-calibrated-matchup-share-shrinkage.md) · [ADR 0037](../../adr/0037-fdr-fallback-multiplier-neutral.md) |
| Participation penalty + calibrated matchup hybrid base (inherited via `hold_chase_challenger`) | `models/` lineage | 2026-09-22 | [ADR 0039](../../adr/0039-champion-participation-penalty-hybrid.md) · [ADR 0041](../../adr/0041-champion-calibrated-matchup-hybrid.md) |

## Dead (do not retry before `Revisit after`)

Baseline HC = former Champion `hold_chase_challenger`; FV = Champion `face_value_challenger`. Δ = combined Blended `top_11_regret` delta (positive = Candidate better). Smoke = [smoke_lane_results.csv](../face-value-challenger/smoke_lane_results.csv) `lane`/`variant`.

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
| Terminal archive columns as inputs (`total_points`, `minutes`, `goals_scored`, `expected_goals`, `bps`, `threat`, `selected_by_percent`, `now_cost`, `status`, `chance_of_playing`) | any | — | leakage (season-end values in archive features) | 2026-09-28 | never (structural) | face-value-challenger Method |

## Open (next-lever pool; not proven dead)

| Lever | State | Best evidence | Blocker / next step |
|---|---|---|---|
| Multi-feature Poisson GLM assist rate (xA target; xA/creativity/opp xG conceded/team xG/home) | Frozen Candidate `multi_feature_assist_challenger`; dev gate PASS +0.901 2/3 boot P 0.976 vs `face_value_challenger` | [multi-feature-event-rate](../multi-feature-event-rate/multi-feature-event-rate.md) `candidate_gate_summary.csv` | Holdout 2026-27 GW6+ pending (one run); Comparison Slate admission + `--apply` = user decision |
| Learned hurdle / direct residual correction on face-value base (ridge λ 10–100, min-GW 4–8) | On paper vs HC: +2.4 … +3.4, 3/3; holdout +2.51 < face-value base | Smoke B1 `v2_hurdle_face_*`, `hurdle_unfit_*` | Needs per-GW feature memory in live `fit` path; must beat `face_value_challenger`, not HC |
| Fixture downside attack scale | Won scorecard vs pre-HC Champion (blend MAE 0.9960 vs 1.0024) | [fixture-downside-scale](../fixture-downside-scale/fixture-downside-scale.md) `downside_swing_summary.csv` `blend_mae` | Plumb `matchup_*` params through WalkforwardConfig; gate vs current Champion |
| Position-split goals weight (restore FWD, keep MID/DEF dampen) | Untried as built Candidate | layer-diagnosis-133 option 1 | Differs from flat MID/FWD 0.9/1.1 (Dead); gate vs current Champion |
| Non-flat bonus beyond xbps weights + T: eligibility pool, expanded BPS terms, allocation form | Untried | [bonus-bps-inventory-125](../champion-component-gap/bonus-bps-inventory-125.md) | Must not reduce to flat scale or T/weight retune (Dead) |
| Dual-Vector ratios shrunk toward 1.0 (`1 + s·(r−1)`) | Untried | dual-vector-official-xg follow-up | Both eval targets; easy-slice bias ≤ neutral |
| True scoreline Poisson (player share × λ, CS = e^{−λ_against}) | Untried | team-poisson-lambda "next only if reopened" | Different form from Dead rate multiplier |
| xMins-side fixture effects | Untried | fixture-swing-candidates deferred list | New topic |
| Penalty-taker signal from per90 only | Untried | smoke brief idea | Verify `penalties_order` not terminal in archive before use |

## Agent Prompt

```text
Before any new Candidate work:
1. Read this ledger. Match proposed lever to a row by mechanism, not name.
2. Dead row with Revisit after > today → pick another lever or propose a new mechanism (new row).
3. After Candidate result (pass/fail): update candidate_ledger.csv row (status, evidence_date, revisit_after = date + 1 year for dead, evidence_path), then table view here. Run uv run pytest tests/test_candidate_ledger.py.
4. Update INDEX `Updated` if row moves to Shipped.
```
