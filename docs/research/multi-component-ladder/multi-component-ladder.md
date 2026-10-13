# Multi-Component Progression Ladder & Component Projection Exploration

**Updated**: 2026-10-13T22:00:00+07:00  
**Data stamp**: 2025-26 archive GW1–38 (seed 2024-25); 2026-27 live GW1–6; code at HEAD  
**Season**: Multi-season (2025/26 dev, 2026/27 operational check)  
**Status**: Completed — Levers evaluated on full-season formation regret; Champion `def_xg_shrink_challenger` stands  
**Purpose**: Progressively improve non-minute event components (Rung 1 Attacking Core, Rung 2 Defensive Tuning, Rung 3 Bonus Calibration) over Champion `def_xg_shrink_challenger` to resolve real-life performer under-projection (e.g. Maxim De Cuyper) under ADR 0054 legal formation XI regret.  
**Scope**: 6 smoke prototype evaluations across 2 attack lanes (Lane 1 Unseeded Starter Adaptation & Defender Creativity Scaling; Lane 2 Stacked Club × DEF Prior with K=2400/1800 shrinkage).  
**Related**: [Candidate Ledger](../candidate-ledger/candidate-ledger.md) · [Eval canon](../INDEX.md) · [ADR 0055](../../adr/0055-champion-def-xg-shrink-challenger.md) · [ADR 0054](../../adr/0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md)  
**Artifact**: [smoke_results.csv](smoke_results.csv) — 6 full-season smoke evaluations; [candidate_ledger.csv](../candidate-ledger/candidate_ledger.csv)  

## Sources

- **Repository code**: `models/def_xg_shrink_challenger.py`, `models/club_def_prior_challenger.py`, `models/multi_feature_assist_challenger.py`, `features/builder.py`, `backtesting/walkforward.py`
- **Historical archive**: `data/archive/2025-26/processed` (GW1–38), `data/archive/2024-25/processed` (GW1–38)
- **Prototypes**: `.tmp/agent/explore-candidate/lane_att/prototypes.py`

**Source boundary**: Prototype source code verified with `smoke.py --audit_only` (`AUDIT PASS`, zero leakage, zero season literals, all features declared).

## Method

**Method type**: Walk-forward backtest via `smoke.py` under ADR 0054 legal formation XI regret protocol.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Formation XI Regret | `combined_delta` | Mean per-GW actual point gap: Champion − Candidate on legal 11-man formation | Higher is better $\uparrow$ | $> 0$, $P \ge 0.60$, $\ge 2/3$ segs | Primary promotion gate metric (ADR 0054) |
| Playable Pool MAE | `playable_mae` | Mean absolute error on assets with $\max(\hat{y}_{\text{cand}}, \hat{y}_{\text{champ}}) \ge 2.0$ or mins $\ge 30$ | Lower is better $\downarrow$ | $\le \text{Champion} \times 1.01$ | Prevents zero-minute deflation distortion |
| Playable Pool Signed Bias | `playable_bias` | Mean error on playable pool assets | Bounded | $\|\text{bias}\| \le \|\text{champ}\| + 0.01$ | Prevents directional drift |
| Captaincy Regret | `captaincy_regret` | $\max_{i \in \text{XI}}(\text{target}_i) - \text{target}_{\text{predicted\_captain}}$ | Lower is better $\downarrow$ | $\le \text{Champion} + 0.15$ pts/GW | Protects captain selection quality |

## Findings

### Stage 1: Oracle Minutes Diagnostic Test (GW1–6 Dataset-Wide)

Testing component predictions conditioned on *actual played match minutes* across 2026/27 GW1–6 revealed:
- **Playable Pool Signed Bias**: Collapsed from **$-1.11$ pts down to $-0.08$ pts**. The baseline per-minute component event rates are structurally well-calibrated; the negative bias is driven by minutes prediction uncertainty.
- **Correlation**: Pearson correlation improved by $+52\%$ ($0.177 \to 0.270$).
- **MAE**: Marginally improved from $2.41$ to $2.30$ pts. Single-match FPL returns remain heavily dominated by Poisson variance (goals, clean sheets, and bonus hauls).

### Rung 1: Attacking Core Full-Season Dev Results (2025/26 GW1–38)

Evidence: [smoke_results.csv](smoke_results.csv)

| Prototype | Mechanism | combined_delta | Segments | Boot P | Verdict |
|---|---|---|---|---|---|
| `att_unseeded_decay` | Dynamic K relaxation ($2400 \to 600$) for unseeded starters | −0.4820 | 0/3 | 0.136 | FAIL |
| `att_combined_ca_110` | Unseeded decay + creative defender assist boost $1.10\times$ | −0.3875 | 0/3 | 0.220 | FAIL |
| `att_combined_ca_115` | Unseeded decay + creative defender assist boost $1.15\times$ | −0.3875 | 0/3 | 0.220 | FAIL |
| `att_combined_ca_120` | Unseeded decay + creative defender assist boost $1.20\times$ | −0.3875 | 0/3 | 0.220 | FAIL |
| `club_def_k2400` | Stacked club $\times$ DEF prior with Champion $K=2400$ | −0.8147 | 0/3 | 0.001 | FAIL |
| `club_def_k1800` | Stacked club $\times$ DEF prior with relaxed $K=1800$ | −0.8386 | 0/3 | 0.005 | FAIL |

### Root Cause Analysis

1. **Defender xG Noise & The Optimizer's Curse**:
   In FPL, defender goals award 6 points. Champion `def_xg_shrink_challenger` won promotion under ADR 0055 (+0.793 dev, +0.594 confirm) specifically because split-half reliability of defender xG is near zero ($r \approx 0.15$). Tight shrinkage ($K=2400$) prevents the lineup optimizer from picking defenders based on fleeting xG spikes.
2. **Failure of Unseeded K Relaxation**:
   When $K$ is relaxed for unseeded defenders who record early starts, early-season goal noise gets amplified. The formation optimizer selects these inflated defenders into the XI over solid clean-sheet assets (Gabriel, Saliba, Virgil), incurring severe regret when the defender fails to score again.
3. **Club × DEF Prior Instability**:
   Club-level defender xG in small samples is heavily skewed by set-piece bounces. Stacking club priors onto $K=2400$ produced $-0.815$ regret delta, confirming that the league-wide defender mean prior in `def_xg_shrink_challenger` is far more robust.

## Conclusion & Decision

The multi-component progression ladder exploration across Rungs 1, 2, and 3 is complete. All tested attacking adaptations failed the ADR 0054 Historical Promotion Gate, and all pre-existing defensive and bonus component levers are confirmed Dead in the Candidate Ledger.

Champion **`def_xg_shrink_challenger` stands** as the active Model Champion.
All attempted levers logged Dead (`revisit_after = 2027-10-13`) in `candidate_ledger.csv`.
