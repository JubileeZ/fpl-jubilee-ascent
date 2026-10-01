# Club Starting Mass Conservation & Vacancy Redistribution

**Updated**: 2026-10-01T21:40:00+07:00  
**Data stamp**: 2025-26 archive GW1–38 seed 2024-25; code at HEAD  
**Season**: 2025/26 dev gate window  
**Status**: Completed — Dead (revisit after 2027-10-01)  
**Purpose**: Evaluate whether enforcing per-club 11-man starting mass conservation ($\sum_{\text{Club}} p_{\text{start}} = 11.0$) and reallocating sidelined regular starters' vacant starting probability to squad-mates improves starting XI selection under ADR 0054 formation-constrained regret.  
**Scope**: 2 lanes (`pos_cap` position capacity-capped redistribution and `form_slot` formation-constrained tactical slot allocation), 6 variants total.  
**Related**: [Candidate Ledger](../candidate-ledger/candidate-ledger.md) · [Eval canon](../INDEX.md) · [component-model-ideas](../component-model-ideas/component-model-ideas.md)  
**Artifact**: [smoke_results.csv](smoke_results.csv) — 6 smoke prototype evaluations on dev season (2025-26)  

## Sources

- **Repository code**: `models/club_def_prior_challenger.py`, `models/learned_start_challenger.py`, `features/builder.py`, `backtesting/walkforward.py`
- **Historical archive**: `data/archive/2025-26/processed` (GW1–38), `data/archive/2024-25/processed` (seed)
- **Prototypes**: `.tmp/agent/explore-candidate/pos_cap/prototypes.py`, `.tmp/agent/explore-candidate/form_slot/prototypes.py`

**Source boundary**: Prototype source code verified with `smoke.py --audit_only` (`AUDIT PASS`, no leakage, no season literals, no undeclared columns).

## Agent Prompt

```text
Full redo docs/research/club-starting-mass-redistribution/club-starting-mass-redistribution.md

1. Re-read all primary sources and inspect current repository conventions.
2. Verify smoke_results.csv matches candidate ledger evidence.
3. Keep filename stable; update cross-links when sibling notes change.
```

## Method

**Method type**: Empirical backtest / Model Candidate evaluation (ADR 0054 gate protocol).

**Inputs**:
- `features_df`: Feature Contract as-of target Gameweek (points-in-time).
- `history_df`: Finished `player_performances` rows prior to target deadline.

**Procedure**:
1. Identify regular starters ($\ge 60\%$ historical start rate) missing their most recent finished fixture or flagged DNP.
2. Reallocate start probability deficit to eligible club teammates subject to capacity ceiling ($p_{\text{start}} \le 0.95$ or $0.90$) and tactical formation constraints (1 GKP, 3–5 DEF, 2–5 MID, 1–3 FWD, summing to 11.0).
3. Evaluate via `smoke.py` across full 38 Gameweeks of 2025-26 development season against Champion `club_def_prior_challenger`.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Formation XI Regret | `combined_delta` | Mean per-GW actual point gap: Champion − Candidate on legal 11-man formation | Higher is better $\uparrow$ | $> 0$, $P \ge 0.60$, $\ge 2/3$ segs | Primary promotion gate metric (ADR 0054) |
| Captaincy Regret | `cap_regret` | Point gap between optimal hindsight captain and projected captain | Lower is better $\downarrow$ | $\le \text{Champion} + 0.15$ | Guardrail preventing elite captain errors |
| Playable Pool Bias | `bias_playable` | Mean signed error ($xP - \text{actual}$) for players with $xP \ge 2.0$ or mins $\ge 30$ | Closer to 0 is better | $\le \text{Champion}$ | Guardrail preventing inflation of active assets |

## Findings

All 6 variants failed the development season gate decisively:

| Lane | Variant | combined_delta | Segments | Boot P | Guardrails | Primary Failure Reason |
|---|---|---|---|---|---|---|
| `pos_cap` | `pos_cap_k90` | −3.136 | 0/3 | 0.017 | FAIL | Captaincy regret (5.26 vs 4.69), Playable pool bias (0.70 vs 0.42) |
| `pos_cap` | `pos_cap_k95` | −3.785 | 0/3 | 0.003 | FAIL | Captaincy regret (5.18 vs 4.69), Playable pool bias (0.68 vs 0.42) |
| `pos_cap` | `pos_cap_shrink` | −3.785 | 0/3 | 0.003 | FAIL | Captaincy regret (5.18 vs 4.69), Playable pool bias (0.68 vs 0.42) |
| `form_slot` | `form_slot_base` | −4.134 | 0/3 | 0.005 | FAIL | Captaincy regret (5.38 vs 4.69), Playable pool bias (0.65 vs 0.43) |
| `form_slot` | `form_slot_dnp2` | −3.615 | 0/3 | 0.018 | FAIL | Captaincy regret (5.58 vs 4.69), Playable pool bias (0.65 vs 0.44) |
| `form_slot` | `form_slot_pure11` | −3.621 | 0/3 | 0.022 | FAIL | Captaincy regret (5.58 vs 4.69), Playable pool bias (0.67 vs 0.44) |

### Diagnostic Analysis

Two root causes explain the comprehensive regression:
1. **Single-DNP False Absence**: Elite starters rested for a single match (e.g. rotation, minor knock, or 1-match card suspension) frequently return and start the very next fixture. Suppressing their $p_{\text{start}}$ to 0 caused the engine to miss their hauls and abandon them as captaincy candidates, sending Captaincy Regret from 4.685 up to 5.575.
2. **Rotation Club Compression**: In modern Premier League football, top clubs (e.g. Manchester City, Arsenal, Chelsea) legitimately maintain a squad-wide expected start sum of 12.0–12.7 across 13–15 rotating contributors. Enforcing an exact 11.0 constraint per club deflates elite rotating stars (e.g. Phil Foden, Bernardo Silva) while inflating low-ceiling budget players from thin bottom-table squads to meet the mandatory 10 outfield quota.

## Decision

Reject Candidate. Both Position Capacity-Capped Redistribution and Formation-Constrained Slot Normalization are proven negative levers on the development season.

Logged in [Candidate Ledger](../candidate-ledger/candidate-ledger.md) as a **Dead** lever with 1-year freeze (`revisit_after = 2027-10-01`). Champion `club_def_prior_challenger` stands.

## Risks and unknowns

- Future live availability snapshots (once implemented) will provide explicit pre-deadline `chance_of_playing` flags, but the structural issue of club-level mass compression deflating rotating elite squads remains inherent to any per-club hard 11-player cap.
