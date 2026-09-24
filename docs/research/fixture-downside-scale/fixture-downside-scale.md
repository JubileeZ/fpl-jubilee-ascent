# Downside-only attack scale vs Champion

**Updated**: 2026-09-24T14:00:00+07:00
**Data stamp**: Design + code only; no full-window evidence yet (2-GW smoke in note)
**Season**: 2025/26 walk-forward GW1–38, seed 2024-25
**Status**: Draft
**Purpose**: Test whether scaling attack down in hard fixtures only (MID/FWD, floor 0.7, never inflate easy) restores swing without spending easy-ceiling bias
**Scope**: Two arms (Champion / downside) on the same Champion model. Coherence: attack and clean swings reported per arm; conceded-delta path untouched; share-gating retained. Slices in two families: FDR slices carry the gate (caps transfer); xG-profile slices (rolling opp xGC/game vs league median, DGW opp = max) are sensitivity only. Not a live change; winner enters via Candidate Admission.
**Related**: [ADR 0040](../../adr/0040-calibrated-matchup-share-shrinkage.md) · [ADR 0044](../../adr/0044-blended-eval-target-promotion-primary.md) · [Cross-GW dispersion](../xp-cross-gw-dispersion/xp-cross-gw-dispersion.md) · [Closed swing candidates](../../archive/fixture-swing-candidates/fixture-swing-candidates.md) · [INDEX](../INDEX.md)
**Artifact**: [downside_swing_summary.csv](downside_swing_summary.csv) `blend_mae` (to be written by full run)

> `Updated` is last note revision time. `Data stamp` is freshness of data or source evidence. Do not add duplicate `Last update` fields.

## Sources

- **Code**: `features/matchup_share.py` — `attack_scale="downside"` clamps ratio at 1.0 above; `features/builder.py` passthrough; archived dual-vector `_easy_mask` reused for FDR easy slice
- **Evidence**: closed topic (both prior arms dead); GW20–21 smoke: attack_swing champion 0.083 vs downside TBD in full run

**Source boundary**: Mechanism + smoke only. Full-window verdict pending.

## Agent Prompt

```text
Full redo docs/research/fixture-downside-scale/fixture-downside-scale.md

1. Require data/archive/2025-26/processed and data/archive/2024-25/processed.
2. Run: uv run python docs/research/fixture-downside-scale/runner.py
   (~50 min two arms; writes downside_swing_summary.csv in this folder)
3. Refresh Findings from downside_swing_summary.csv blend_mae / easy_bias /
   hard_bias / attack_swing / clean_swing_60. Do not snapshot numeric totals
   in this prompt.
4. Apply kill rules in Decision; archive on close per layout convention.
5. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Planned candidate experiment (runner smoke-tested on GW20–21)

**Procedure**:
1. Per GW: one base build (`apply_matchup_share=False`), overlay per arm (Champion defaults / downside ratio-capped-at-1.0), predict, compare grain with difficulty, process, blend columns.
2. FDR slices: `easy_mid_fwd` (diff ≤ 2, MID/FWD, xmins ≥ 60; cap +0.450), `hard_mid_fwd` (diff ≥ 4, same gates; floor −0.450 starting guess).
3. xG slices (sensitivity): rolling opp xGC/game before the GW vs league median; easy/hard halves on 60+ MID/FWD. DGW opponent = max club id (documented arbitrary).
4. Swings: `attack_swing` (60+ MID/FWD xp-attack SD ÷ Process SD same slice), `clean_swing_60` (60+ DEF/GKP xp-clean SD), `xp_swing_60` context.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Blend MAE | `blend_mae` | mean abs error vs Blended Eval Target | Lower $\downarrow$ | Beat 1.0024 | Primary; decides the arm |
| Easy bias | `easy_bias` | signed bias vs Process, FDR easy slice | Bounded | ≤ +0.450 | Ceiling spend cap (transferred) |
| Hard bias | `hard_bias` | signed bias vs Process, FDR hard slice | Bounded | ≥ −0.450 | Floor guardrail (starting guess) |
| Attack Swing Ratio | `attack_swing` | per glossary | Context ↑ | Directional lift | Diagnostic; never the objective |
| Clean swing | `clean_swing_60` | 60+ DEF/GKP xp-clean SD | Context | Must not collapse vs Champion | Coherence half of the check |

**Validation boundary**: Smoke only. Full run pending.

## Source synthesis

- Closed experiment: additive ties MAE with worse easy bias; multiplicative loses MAE and breaches the cap. Swing and easy-ceiling bias coupled under symmetric scale.
- FDR slices keep gate comparability (caps measured on them); xG-profile slices answer whether the ruler matters — both emitted from one run at zero model cost.

## Project interpretation

### Decision rules

- Admit iff: wins blend MAE, holds realized/process, easy_bias ≤ +0.450, hard_bias ≥ −0.450, attack swing lifts, clean swing coherent (no collapse vs Champion).
- Breach cap/floor or lose blend MAE: arm dead immediately.
- Win on MAE but incoherent swings: no admission; open coherence as its own topic.

### Practical implications

- Winner rides explicit overlay params only; production defaults frozen until a gate pass.

## Findings

### Evidence

- GW20–21 smoke: runner end-to-end green (exact cells in full-run companion, not quoted here).

### Alternatives

- Wider/narrower downside floor (0.5/0.8) — only if the arm wins but pins the 0.7 edge.
- FDR fallback when strengths null — still deferred.
- Position-scoped unshrink — closed with the prior topic.

## Decision

**Verdict**: Pending full run.

**Recommended action**:
- Run GW1–38, apply kill rules, admit or archive.

**Trigger / kill switch**:
- Cap/floor breach or blend MAE loss ends the arm on sight.

## Risks and unknowns

- Hard floor −0.450 is a mirrored guess, not evidence; first job of the full run is to check the Champion's own hard-slice number.
- xG median-split halves are not tails; sensitivity only.
- DGW opponent = max is arbitrary; rare enough to not move the verdict.

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
