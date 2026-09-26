# Segment-fix experiments after #123 (AFK evidence for #124)

**Updated**: 2026-09-26T18:10:00+07:00  
**Data stamp**: 2025-26 archive GW1–38 seed 2024-25; post-hoc scales on cached `goals_path_challenger` walk-forward  
**Status**: Active — AFK evidence for wayfinder [#124](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/124); does **not** resolve the route grill  
**Purpose**: Prove whether post-link CS/GC retunes and/or flat `xp_bonus` scales recover Historical Promotion Gate (≥2/3 Blended segments + primary↑ + MAE guardrails) vs Champion `hold_chase_challenger`  
**Scope**: Post-hoc scales on `goals_path` ledger (same algebra as `defence_link_challenger.predict`). No production model mutation. No Admission/`--apply`.  
**Related**: [#123](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/123) · [segment-loss-121](segment-loss-121.md) · map [#110](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/110)  
**Artifact**: [segment_fix_sweep_124.csv](segment_fix_sweep_124.csv) · [segment_fix_sweep_124.json](segment_fix_sweep_124.json) · [bonus_scale_sweep_124.csv](bonus_scale_sweep_124.csv) · [bonus_scale_sweep_124.json](bonus_scale_sweep_124.json)

## Sources

- **Primary**: `backtesting/promotion.py` `evaluate_historical_promotion_gate` / `SEASON_WINDOWS`
- **Primary**: `models/defence_link_challenger.py` post-link scale algebra
- **Repository data**: walk-forward Champion + `goals_path_challenger` on `data/archive/2025-26/processed` seed `2024-25` → companions above

## Agent Prompt

```text
Full redo docs/research/champion-component-gap/segment_fix_experiments_124.md

1. uv run python docs/research/champion-component-gap/segment_fix_sweep_124.py
2. uv run python docs/research/champion-component-gap/bonus_scale_sweep_124.py
3. Refresh CSV/JSON companions; update Verdict tables from cells.
4. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

1. Cache full-season walk-forwards for Champion + `goals_path_challenger` (`eval_target=blended_points`).
2. Apply `(k_cs, k_gc)` and/or `k_bonus` post-hoc to goals ledger; re-score gate vs Champion (Blended primary + Realized/Process MAE refs).
3. Sweeps: CS∈[0.85,1.30], GC∈{1, prod}, all-pool vs mins_60 calibrate, GKP+DEF-only scales; bonus∈[0.5,4] on goals / CS-prod / CS=1.10 bases.

### Metric Definitions & Direction

| Metric | Direction | Ideal | Description |
|---|---|---|---|
| `passed` | Higher $\uparrow$ | true | Full Historical Promotion Gate |
| `segment_wins` | Higher $\uparrow$ | ≥2/3 | Cold-Start / early_mid / late |
| `combined_primary_delta` | Higher $\uparrow$ | >0 | Champion − Candidate Blended `decision_regret` |
| `late_delta` | Higher $\uparrow$ | >0 | Late-window primary delta (GW20–38) |
| Realized/Process MAE | Lower $\downarrow$ | ≤ Champion | Reference guardrails |

## Findings

### Proven false (this archive window)

1. **Post-link CS/GC retune alone cannot pass the gate.** 43 configs; `any_pass=false`. Source: [segment_fix_sweep_124.json](segment_fix_sweep_124.json).
2. **No CS/GC config wins `late`.** `late_delta` never >0 across the CS/GC grid. Source: [segment_fix_sweep_124.csv](segment_fix_sweep_124.csv).
3. **Flat `xp_bonus` global scale alone (or on CS bases) also never wins `late`.** `any_late_win=false`; `any_pass=false`. Source: [bonus_scale_sweep_124.json](bonus_scale_sweep_124.json).
4. **All-pool CS calibrate ≡ k_cs=1** on goals_path (already inside τ) — so “switch calib pool to all” is goals-only for CS, which already fails primary + segments (#123).
5. **GKP+DEF-only prod scales worsen combined primary** vs full-roster prod (Δ −0.419 vs +0.077).

### Proven true (near-misses)

1. **Dropping GC scale while keeping prod CS** (`k_cs=1.296903`, `k_gc=1`) reaches **2/3** segments (cold_start+early_mid) and **primary↑** (+0.300), but **regresses Realized/Process MAE** and still **loses late** (−0.428). Same as `cs_mins60_gc_1`.
2. **MAE-friendly 2/3 exists** (e.g. `k_cs=1.10`, `k_gc=1`) but **primary↓** (−0.254) — cold_start margin too small.
3. **Near-miss combo** `k_cs=prod`, `k_gc=1`, `k_bonus=0.75`: **2/3**, primary↑ (+0.252), Realized MAE **1.0328 ≤ 1.0334**, Process MAE **0.9192 ≤ 0.9205**, but fails structural Champion guardrails (xMins MAE / |bias| / Spearman slightly worse) and **late still negative** (−0.299).

### Trade-off sketch

| Knob move | Segments | Combined primary | Late | R/P MAE |
|---|---|---|---|---|
| Prod CS+GC (#121) | 1/3 | ↑ tiny | lose | regress |
| CS prod, GC off | 2/3 | ↑ | lose | regress |
| Mild CS, GC off | 2/3 | ↓ | lose | often OK |
| Flat bonus ↑ | usually 1/3 | mixed | still lose | regress at high k |
| Bonus dampen + CS prod | 2/3 | ↑ | lose | can clear R/P MAE |

## Decision (evidence only — route still #124 HITL)

**Verdict**: Pure post-hoc **CS/GC retune cannot unlock late** or a full gate pass on 2025-26. Flat **bonus scale cannot unlock late** either. Closest knobs buy early_mid + cold_start at the cost of MAE or structural guardrails, with late still red.

**Implications for #124 route grill**:
- Re-tuning shipped `k_cs`/`k_gc` alone is a **weak** path to Destination (disproven for late + full pass).
- Bonus-first remains plausible only if the lever is **not** a flat global `xp_bonus` scale (needs smarter BPS Bonus Model / ranking-sensitive form) — flat scale disproven for late.
- Alternative redirects still open: non-scale defence form, goals re-shape for late regret, other residual arms, or accept slate Candidate without flip until a mid+late-capable arm exists.

**Trigger / kill switch**: Candidate that posts `late_delta>0` and ≥2/3 with Realized+Process MAE ≤ Champion on this archive window.

## Risks

- Post-hoc scale ≠ full retrain of Poisson λ / NegBin; approximates shipped Candidate algebra only.
- Decision Regret top-11 sensitive; component MAE explanatory.
- Structural guardrails (xMins/bias/Spearman) not swept as objectives.
