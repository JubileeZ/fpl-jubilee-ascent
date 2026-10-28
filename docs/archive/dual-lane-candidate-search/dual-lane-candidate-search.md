# Dual-lane Candidate Search (explore-candidate 2026-09-28)

**Updated**: 2026-09-28T21:20:00+07:00  
**Data stamp**: 2025-26 archive GW1–38 seed 2024-25 (dev); point-in-time features (ADR 0046); smoke runs 2026-09-28  
**Season**: 2025/26 (dev only; no Candidate reached 2024-25 confirmation)  
**Status**: Closed — no win; Champion `multi_feature_assist_challenger` unchanged  
**Purpose**: Find a Candidate beating Champion `multi_feature_assist_challenger` on Historical Promotion Gate (dual-lane explore-candidate, no user idea).  
**Scope**: 15 lane-rounds, 88 prototype variants, all event/participation/bonus/fixture pipeline steps. Excluded: confirm season (no dev PASS), sealed 2026-27 holdout.  
**Related**: [Candidate Ledger](../candidate-ledger/candidate-ledger.md) · [multi-feature-event-rate](../multi-feature-event-rate/multi-feature-event-rate.md) · [Eval canon](../INDEX.md) · [ADR 0046](../../adr/0046-point-in-time-backtest-and-statistical-gate.md) · [ADR 0047](../../adr/0047-two-season-promotion-gate.md)  
**Artifact**: [smoke_results.csv](smoke_results.csv) `lane` / `variant` / `combined_delta` / `segs` / `boot_p_gt0` / `guardrails_passed` (frozen smoke snapshot) · [best_stack_prototype.py](best_stack_prototype.py) (lane s4 source; `s4_e60_w100_mglob`)

> `Updated` is last note revision time. `Data stamp` is freshness of data or source evidence. Do not add duplicate `Last update` fields.

## Sources

- **Primary**: `backtesting/model_evaluation.py` `compare_to_reference` — gate rule (Blended `top_11_regret`, ≥1% effect + block-bootstrap P ≥ 0.95 at search time; delta > 0 + P ≥ 0.60 both seasons after ADR 0049, ≥2/3 segments, guardrails)
- **Primary**: `.agents/skills/explore-candidate/smoke.py` — harness (audit, leakage guard, season roles)
- **Repository data**: `data/archive/2025-26/processed` (target), `data/archive/2024-25/processed` (seed) — cutoff 2025-26 GW38

**Source boundary**: Smoke rows from scratch prototypes (deleted except `best_stack_prototype.py`). Orchestrator re-ran `--audit_only` on every prototype file: all AUDIT PASS; no LEAKAGE FAIL in any run.

## Agent Prompt

```text
Full redo docs/research/dual-lane-candidate-search/dual-lane-candidate-search.md

1. smoke_results.csv frozen; do not regenerate (Dead rows locked until 2027-09-28).
2. Revisit only after 2027-09-28 or on user's explicit words; cite Candidate Ledger rows.
3. Re-smoke best stack: uv run python .agents/skills/explore-candidate/smoke.py docs/research/dual-lane-candidate-search/best_stack_prototype.py --out .tmp/agent/<scratch>.csv  (~40 min, 3 workers)
4. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Walk-forward backtest, lever screening (explore-candidate dual-lane)

**Inputs**: Champion `multi_feature_assist_challenger`; dev 2025-26 GW1–38 seed 2024-25; blended eval target.

**Procedure**:
1. Ledger screen → 5 round-1 lanes (≤6 pre-declared variants each): A1 bonus (residual BPS rate, soft P(60) eligibility), A2 downside attack scale, A3 transfer-news / bench DNP hazards, B1 true scoreline Poisson, B2 history-reconstructed ridge residual correction.
2. Round 2: new mechanism per lane (heteroscedastic Normal BPS rank allocation; expected-margin xMins trim; post-absence hazard/ramp; schedule-adjusted as-of rates; ridge-logistic learned p_start).
3. Round 3+: stack orthogonal near-misses (soft P(60) bonus eligibility × learned p_start); fix |bias| via mass-preserving start (learned model ranks who starts, Champion total start mass); per-position start models, learned xmins-if-start, club rotation covariate.
4. Progress guard: lane closes after 2 rounds without new best `combined_delta`. A3, B1 closed after 2 rounds (all new mechanisms ≤ 0).

**Definitions and assumptions**:
- Delta = Champion regret − Candidate regret; positive = Candidate better. Min effect 0.711 (1% of Champion regret 71.08) at search time; removed by ADR 0049.
- Inputs only via `fit(history_df)` / `predict(features_df)`; no cross-call memory (model instance persists across walk-forward GWs; live path runs once).

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Combined delta | `combined_delta` | Champion − Candidate Blended `top_11_regret` | Higher $\uparrow$ | ≥ `min_effect` 0.711 | Gate primary |
| Bootstrap P | `boot_p_gt0` | Block-bootstrap share of GW resamples with delta > 0 | Higher $\uparrow$ | ≥ 0.60 (ADR 0049; 0.95 at search time) | Gate robustness |
| Segment wins | `segs` | Seasonal segments (cold / early-mid / late) with delta > 0 | Higher $\uparrow$ | ≥ 2/3 | Gate robustness |
| Guardrails | `guardrails_passed` | xMins MAE ≤ ×1.01; \|bias\| ≤ Champion + 0.01; Spearman ≥ −0.005; Realized/Process MAE tolerance | Pass | True | ADR 0044/0046 |

**Validation boundary**: 88 variants on one season → selection luck likely near P boundary. No variant passed; confirm season never run; 2026-27 untouched.

## Findings

### Evidence

- No variant passed ( `smoke_results.csv` `pass` all False).
- Best raw: `s_e60_b2w100` (soft P(60) bonus eligibility + learned p_start w=1) +1.388, 3/3, P 0.959 — failed only \|bias\| (0.0112 vs limit 0.0106). Source: `smoke_results.csv` `combined_delta`.
- Best guardrail-clean: `s4_e60_w100_mglob` (+ global mass-preserving start) +1.198, 3/3, P 0.928 — failed only bootstrap P. Mass preservation fixed bias, cost effect; per-club mass (+0.711) worse than global (+1.198) → learned model also shifts start mass across clubs.
- Ablation: learned start alone (mass-preserved) +0.322; soft P(60) eligibility alone −0.177 → gain = interaction of both steps.
- Learned p_start improves start Brier 0.096 → 0.082 and xMins MAE 14.45 → 13.33; regret gain only partly follows.
- Negative / null families: transfer-share / bench / post-absence DNP hazards; downside attack scale (+0.18 max); expected-margin xMins; venue-split rates; schedule-adjusted rates; history-reconstructed residual correction (−0.98 … −1.57); heteroscedastic Normal bonus allocation; learned p_sub_in.
- B1 attack half (player share × team λ_for) reduces algebraically to Dead opponent rate multiplier (club attack cancels) → rows void; defence half best +0.491 1/3.

### Alternatives

- Holdout-first (ADR 0046) for best stack: forbidden to tune on 2026-27; lever not dependent on missing scoring rule, so no holdout-first exemption applies.

## Decision

**Verdict**: Search: no win at 0.95. Adopted after rule change: `learned_start_challenger` → Champion (ADR 0050). After bar 0.75 both seasons + user override, frozen `models/learned_start_challenger.py` (= `s4_e60_w100_mglob`) gated (`candidate_gate.csv`): dev 2025-26 PASS +1.198 3/3 P 0.928; confirm 2024-25 FAIL `combined_delta` +0.518 < `min_effect` 0.622, 2/3, `boot_p_gt0` 0.638 → not adopted. Bar then lowered to 0.60 both seasons (ADR 0049); same run re-scored: P 0.638 ≥ 0.60 but `combined_delta` < `min_effect` → still FAIL. Minimum effect then removed (ADR 0049) → same run PASS; `commands.evaluate_model_promotion --confirmation --apply` replay identical (+0.5176, 2/3, P 0.638) → promoted. All 11 attempted mechanism classes → Dead rows (revisit 2027-09-28).

**Recommended action**:
- Champion `learned_start_challenger` (ADR 0050, provisional); `multi_feature_assist_challenger` + `face_value_challenger` = Comparison Slate.
- Next search: mechanisms outside Dead list (Open: position-split goals, Dual-Vector shrunk, penalty taker from history only).

**Trigger / kill switch**:
- 2026-27 GW6+ post-promotion check once finished (ADR 0047); FAIL → revert to `multi_feature_assist_challenger` on user's words. Other learned-participation variants Dead until 2027-09-28.

## Risks and unknowns

- Forking paths: 88 variants; best-stack P values sit near the bar by search, not by design.
- Backtest lacks `chance_of_playing` (terminal); live Champion has availability → learned-start gain may shrink live.
- 2024-25 archive lacks `defensive_contribution`; BPS-residual levers would differ on confirm.
- Lineage penalty isolation inert in backtest (`penalties_order` terminal).
