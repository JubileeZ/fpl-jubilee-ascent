# Asymmetric Finishing Challenger & Dual-Lane Search Round 2

**Updated**: 2026-09-28T23:25:00+07:00  
**Data stamp**: 2025-26 archive GW1–38 seed 2024-25 (dev); 2024-25 archive GW1–38 seed none (confirm); smoke runs 2026-09-28  
**Season**: Multi-season (2025/26 dev, 2024/25 confirm)  
**Status**: Closed — no win; Champion `learned_start_challenger` unchanged  
**Purpose**: Evaluate Candidate levers against Champion `learned_start_challenger` on Historical Promotion Gate (ADR 0047, ADR 0049).  
**Scope**: 3 lanes, 18 prototype variants: Lane A1 position-split goals (Row 38), Lane A2 asymmetric finishing shrinkage (component gap crown), Lane A3 penalty taker detection (Row 43). Confirmation run on frozen Candidate `asymmetric_finishing_challenger`. Excluded: sealed 2026-27 holdout.  
**Related**: [Candidate Ledger](../candidate-ledger/candidate-ledger.md) · [dual-lane-candidate-search](../dual-lane-candidate-search/dual-lane-candidate-search.md) · [Eval canon](../INDEX.md) · [ADR 0047](../../adr/0047-two-season-promotion-gate.md) · [ADR 0049](../../adr/0049-gate-bootstrap-060-no-min-effect.md) · [ADR 0050](../../adr/0050-champion-learned-start-challenger.md)  
**Artifact**: [candidate_gate.csv](candidate_gate.csv) `pass` / `combined_delta` / `segs` / `boot_p_gt0` · [smoke_results.csv](smoke_results.csv) `lane` / `variant` / `combined_delta` / `boot_p_gt0`

## Sources

- **Primary**: `backtesting/model_evaluation.py` `compare_to_reference` — promotion gate rule (Blended `top_11_regret`, delta > 0, block-bootstrap P ≥ 0.60 both seasons, ≥2/3 segments, guardrails)
- **Primary**: `.agents/skills/explore-candidate/smoke.py` — harness (leakage guard, audit, season roles)
- **Repository data**: `data/archive/2025-26/processed` (dev), `data/archive/2024-25/processed` (confirm)

**Source boundary**: Archive backtest results point-in-time (ADR 0046). Zero leakage; all prototypes passed audit and feature contract constraints.

## Agent Prompt

```text
Full redo docs/research/asymmetric-finishing-challenger/asymmetric-finishing-challenger.md

1. smoke_results.csv and candidate_gate.csv frozen; do not regenerate (Dead rows locked until 2027-09-28).
2. Revisit only after 2027-09-28 or on user's explicit words; cite Candidate Ledger rows.
3. Candidate asymmetric_finishing_challenger registered in models/ and cataloged in docs/model_name.md.
4. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Walk-forward backtest, lever screening and historical promotion gate

**Inputs**:
- Champion: `learned_start_challenger`
- Dev season: 2025-26 GW1–38 seed 2024-25
- Confirm season: 2024-25 GW1–38 seed none (one run per ADR 0047)
- Eval target: `blended_points` (50/50 Realized / Process)

**Procedure**:
1. Ledger screen:
   - Lane A1: Position-split goals scaling (Ledger Open Row 38, `layer-diagnosis-133` option 1). 6 variants.
   - Lane A2: Asymmetric finishing shrinkage (new mechanism on `xp_goals` component crown). 6 variants.
   - Lane A3: Penalty taker detection from history (Ledger Open Row 43). 6 variants.
2. Dev season smoke runs across 7 parallel workers.
3. Winner identification: Lane A2 variant `a2_asym_fin_kp1500_kn3000` won dev season (+0.2611, 2/3 segs, boot P 0.989).
4. Candidate build: `models/asymmetric_finishing_challenger.py`, `tests/test_asymmetric_finishing_challenger.py`, registered in `docs/model_name.md`.
5. Freeze check on dev season: reproduced exact delta +0.2611.
6. Confirmation season gate (2024-25, one run per ADR 0047): delta -0.2311, 0/3 segs, boot P 0.199 -> FAIL.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Combined delta | `combined_delta` | Champion − Candidate Blended `top_11_regret` | Higher $\uparrow$ | > 0.0 (ADR 0049) | Gate primary |
| Bootstrap P | `boot_p_gt0` | Circular block-bootstrap share of GW resamples with delta > 0 | Higher $\uparrow$ | ≥ 0.60 (ADR 0049) | Statistical confidence |
| Segment wins | `segs` | Seasonal segments (cold / early-mid / late) with delta > 0 | Higher $\uparrow$ | ≥ 2/3 | Season-wide consistency |
| Guardrails | `guardrails_passed` | xMins MAE ≤ ×1.01; \|bias\| ≤ Champ + 0.01; Spearman ≥ −0.005 | Pass | True | Guardrail integrity |

## Findings

### Evidence

- **Lane A1 (Position-split goals, Row 38)**: all 6 variants negative vs Champion (`learned_start_challenger`). Dampening MID/DEF goals caused missed midfield hauls (-0.28 to -0.69 delta), and boosting FWD goals over-indexed on forwards (-0.38 to -0.89 delta). Mechanism fails vs current Champion.
- **Lane A2 (Asymmetric finishing shrinkage)**:
  - Strong negative shrinkage ($K_{\text{neg}} \ge 3600$) with $K_{\text{pos}}=1800$ failed (deltas -0.127 to -0.537).
  - Balanced moderate asymmetric shrinkage ($K_{\text{pos}}=1500, K_{\text{neg}}=3000$) passed dev season: `combined_delta` **+0.2611**, `segs` **2/3**, `boot_p_gt0` **0.9885**, all guardrails passed.
  - Confirmation run on independent 2024–25 season: `combined_delta` **-0.2311**, `segs` **0/3**, `boot_p_gt0` **0.1987** -> FAIL.
- **Lane A3 (Penalty taker detection from history, Row 43)**: all 6 variants yielded `delta +0.0000`, 0/3 segs, boot P 0.000. Fixture unscaling for derived penalty takers has zero effect on the optimal top-11 selection.

## Decision

**Verdict**: No win. Champion `learned_start_challenger` unchanged.

**Recommended action**:
- Champion stays `learned_start_challenger` (ADR 0050, provisional).
- Move attempted mechanisms to Candidate Ledger Dead rows:
  - Position-split goals weight (Row 38 -> Dead until 2027-09-28)
  - Asymmetric finishing shrinkage (New -> Dead until 2027-09-28)
  - Penalty-taker signal from history (Row 43 -> Dead until 2027-09-28)
- Candidate `asymmetric_finishing_challenger` cataloged in `docs/model_name.md` as Model Candidate (failed confirmation).

## Risks and unknowns

- Finishing offsets in 2024–25 without prior-season seed behaved differently than in 2025–26 with seed.
- 2026–27 GW6+ remains sealed holdout for post-promotion check of Champion `learned_start_challenger`.
