# Fixture-swing candidates: adjusted-additive vs multiplicative attack

**Updated**: 2026-09-24T13:50:00+07:00
**Data stamp**: Design only; no new evidence yet. Baseline cells: `xp-cross-gw-dispersion/dispersion_summary.csv` `mean_SD`, `matchup-share-addon-2025-26/matchup_share_summary.csv` `signed_bias`
**Season**: 2025/26 (planned eval window GW1–38, seed 2024-25)
**Status**: Draft
**Purpose**: Test whether adjusted-additive or multiplicative attack fixture scale restores xP swing toward blend behavior without breaking blend MAE
**Scope**: Three-arm walk-forward (Champion default / additive-adjusted / multiplicative). Model-effect-only: builder defaults unchanged, variants pass explicit params (blend_weight precedent). DEF/GKP untouched. Easy-slice spend bounded at +0.450 process bias. Not a live change; winner enters via Candidate Admission.
**Related**: [ADR 0040](../../adr/0040-calibrated-matchup-share-shrinkage.md) · [ADR 0044](../../adr/0044-blended-eval-target-promotion-primary.md) · [Cross-GW dispersion](../xp-cross-gw-dispersion/xp-cross-gw-dispersion.md) · [INDEX](../INDEX.md)
**Artifact**: [candidate_swing_summary.csv](candidate_swing_summary.csv) `blend_mae` (to be written)

> `Updated` is last note revision time. `Data stamp` is freshness of data or source evidence. Do not add duplicate `Last update` fields.

## Sources

- **Code**: `features/matchup_share.py:290,307` — additive add-on + forced ×1.0 multipliers; `models/calibrated_matchup_hybrid.py:80` — dead multiplicative path; `features/builder.py:1039` — overlay call site (shrink params accepted, never passed)
- **Evidence**: addon note `easy_mid_fwd` rows (`s=0.30→0.50` lifts process bias +0.334→+0.410); dispersion note headline (xp 12.5% of blend on `60+`)

**Source boundary**: Mechanism diagnosed from code + existing companions. No variant has been run.

## Agent Prompt

```text
Full redo docs/research/fixture-swing-candidates/fixture-swing-candidates.md

1. Require data/archive/2025-26/processed and data/archive/2024-25/processed.
2. Implement builder passthrough for shrink_att/shrink_def + attack_scale mode
   (defaults = production; variants pass explicit params only).
3. Write runner.py: three-arm walk-forward (Champion / additive-adjusted /
   multiplicative) on blend MAE primary, realized+process hold, easy_mid_fwd
   process bias cap +0.450, Attack Swing Ratio diagnostic.
4. Refresh Findings from candidate_swing_summary.csv blend_mae / easy_bias /
   attack_swing. Do not snapshot numeric totals in this prompt.
5. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Planned candidate experiment (not yet run)

**Procedure**:
1. Arm A (additive-adjusted): explicit `shrink_att` variants for MID/FWD at overlay call (e.g. 0.6), rest default.
2. Arm M (multiplicative): new overlay `attack_scale="ratio"` — `attack_multiplier` from opponent xGC/league ratio clamped (e.g. 0.7–1.4), additive bump retained; DEF/GKP stay ×1.0.
3. Score all arms on 2025-26 GW1–38 walk-forward: blend MAE primary; realized/process MAE hold; `easy_mid_fwd` process bias ≤ +0.450; Attack Swing Ratio diagnostic.

**Definitions and assumptions**:
- Defaults frozen: any run without explicit params reproduces production exactly.
- Directional swing bar only; no fixed ratio (expectation stays below actuals).

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Blend MAE | `blend_mae` | mean abs error vs Blended Eval Target | Lower $\downarrow$ | Beat Champion | Primary; decides the arm |
| Easy-slice bias | `easy_bias` | signed bias vs Process on `easy_mid_fwd` | Bounded | ≤ +0.450 | Spend cap for swing |
| Attack Swing Ratio | `attack_swing` | 60+ MID/FWD xp-attack SD ÷ Process SD on the same slice | Context ↑ | Directional lift | Diagnostic; never the objective |

**Validation boundary**: Design only. No variant evidence exists.

## Source synthesis

- ADR 0040 settled s=0.40 to tame easy-fixture ceiling (+0.450 → +0.371); all-pool MAE flat across s=0.30–0.50.
- Dispersion: xp swing 12.5% of blend; attack component near zero by construction (forced ×1.0 + shrunk additive).

## Project interpretation

### Decision rules

- If one arm wins blend MAE, holds both guardrails, respects the easy cap, and lifts attack swing: admit as Model Candidate.
- If neither beats Champion on blend: close topic, keep Champion; swing stays diagnostic.
- No live or contract-default change from this topic either way.

### Practical implications

- Winner's params ride the candidate's evaluation only; production defaults untouched until a gate pass.

## Findings

### Evidence

- None yet. Mechanism hypothesis (to be tested): multiplicative arm restores proportional swing for low-xG players without the additive ceiling blowup; additive arm replays the known s/bias trade.

### Alternatives

- FDR-derived multipliers when strengths null — deferred (reopens ADR 0037; revisit if both arms fail).
- Horizon-varying xMins — deferred (touches minutes model; risks xMins guardrail).
- Fixed halfway swing bar — rejected (Q4 directional lock).

## Decision

**Verdict**: Pending experiment. Both arms to be tested, not picked blind.

**Recommended action**:
- Implement builder passthrough + overlay ratio mode, then run the three-arm walk-forward.

**Trigger / kill switch**:
- Either arm breaching the easy cap or losing blend MAE ends that arm immediately.

## Risks and unknowns

- Ratio-mode clamp bounds (0.7–1.4) are a starting guess, not evidence.
- Runner runtime ~3× single walk-forward (≈75 min); run in background.
- Threat/creativity weights may absorb part of the scale change; component attribution will show it.

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
