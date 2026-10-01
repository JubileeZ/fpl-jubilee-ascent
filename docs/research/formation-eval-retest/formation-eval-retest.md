# Formation-constrained Legal XI Eval Retest

**Updated**: 2026-10-01T14:45:00+07:00  
**Data stamp**: 2025-26 archive GW1–38 seed 2024-25 (dev); 2024-25 archive GW1–38 unseeded (confirm); ADR 0054 gate  
**Season**: Multi-season (2025/26 dev, 2024/25 confirm)  
**Status**: Complete — `def_xg_shrink_challenger` passes both seasons  
**Purpose**: Re-evaluate candidate models and component ideas that won dev eval under unconstrained top-11 regret but failed confirmation or stalled before adoption, following the upgrade to formation-constrained legal XI regret ([ADR 0054](../../adr/0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md)).  
**Scope**: Candidates: `def_xg_shrink_challenger` (ATK-04), `cs_exposure_challenger` (DEF-02), `asymmetric_finishing_challenger`, `schedule_congestion_challenger` (MIN-07). Baseline: Champion `club_def_prior_challenger`.  
**Related**: [ADR 0054](../../adr/0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md) · [component-model-ideas](../component-model-ideas/component-model-ideas.md) · [asymmetric-finishing-challenger](../asymmetric-finishing-challenger/asymmetric-finishing-challenger.md) · [candidate-ledger](../candidate-ledger/candidate-ledger.md)  
**Artifact**: [smoke_results.csv](smoke_results.csv) · [candidate_gate.csv](candidate_gate.csv)  

## Sources

- **Primary**: `backtesting/model_evaluation.py`, `backtesting/promotion.py`, `backtesting/metrics.py` (ADR 0054)
- **Repository data**: `data/archive/2025-26/processed` (dev target), `data/archive/2024-25/processed` (confirm target / dev seed)

## Method

**Method type**: Walk-forward backtest via `smoke.py` / `model_evaluation.compare_to_reference` under ADR 0054 gate:
### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Formation XI Regret | `formation_xi_regret` | Oracle Legal XI Blended pts − Model Legal XI Blended pts across 8 legal topologies | Lower $\downarrow$ | $\Delta = \text{Ref} - \text{Cand} > 0$ | Primary promotion metric under ADR 0054 |
| Playable Pool MAE | `playable_mae` | Mean absolute error on assets with $\max(\hat{y}_{\text{cand}}, \hat{y}_{\text{champ}}) \ge 2.0$ or mins $\ge 30$ | Lower $\downarrow$ | $\le \text{Ref} \times 1.01$ | Prevents zero-minute deflation distortion |
| Playable Pool Signed Bias | `playable_bias` | Mean error on playable pool assets | Bounded | $|\text{bias}| \le |\text{champ}| + 0.01$ | Prevents directional drift |
| Captaincy Regret | `captaincy_regret` | $\max_{i \in \text{XI}}(\text{target}_i) - \text{target}_{\text{predicted\_captain}}$ | Lower $\downarrow$ | $\le \text{Ref} + 0.15$ pts/GW | Protects captain selection quality |
| xMins MAE | `xmins_mae` | Mean absolute error vs realized minutes | Lower $\downarrow$ | $\le \text{Ref} \times 1.01$ | Minutes projection accuracy |
| Spearman Correlation | `spearman` | Rank correlation between predicted and blended target | Higher $\uparrow$ | $\ge \text{Ref} - 0.005$ | Asset ranking fidelity |

## Findings

Evidence: [candidate_gate.csv](candidate_gate.csv)

| Candidate Model | Lever / Mechanism | Dev 2025-26 | Confirm 2024-25 | Gate Verdict |
|---|---|---|---|---|
| **`def_xg_shrink_challenger`** | ATK-04: DEF xG rate shrink $K=2400$ pseudo-min | **PASS** (+0.7929, 3/3, P 0.944) | **PASS** (+0.5941, 2/3, P 0.863) | **CONFIRM PASS** → Adoption queued |
| `cs_exposure_challenger` | DEF-02: CS exposure over 60+ starts ($m_{60}=85$, $K=4$) | **PASS** (+0.3829, 2/3, P 0.901) | **FAIL** (-0.2162, 1/3, P 0.189) | Confirm FAIL |
| `asymmetric_finishing_challenger` | Asymmetric finishing shrinkage ($K_{pos}=1500$, $K_{neg}=3000$) | **PASS** (+0.1028, 2/3, P 0.644) | **FAIL** (-0.1553, 1/3, P 0.296) | Confirm FAIL |
| `schedule_congestion_challenger` | MIN-07: Schedule congestion logit shift -0.2 | **FAIL** (+0.1137, 1/3, P 0.623) | — (failed dev) | Dev FAIL |

### Analysis

1. **Why `def_xg_shrink_challenger` passed both seasons under ADR 0054:**
   Under unconstrained `top_11_regret`, outfield picks were heavily skewed toward attackers, meaning DEF xG noise had little negative impact in 2024-25. With ADR 0054 mandating 3–5 defenders in the XI, dampening noisy defender xG ($K=2400$) avoids costly fluke defender selections across both seasons (+0.7929 pts/GW on 2025-26 and +0.5941 pts/GW on 2024-25).
2. **`cs_exposure_challenger`:**
   While dev performance improved dramatically under formation constraints (+0.096 → +0.3829), it still failed to transfer to 2024-25 (-0.2162, 1/3 segments, P 0.189).
3. **`asymmetric_finishing_challenger`:**
   Remains a 2025-26 specific phenomenon that inverts on 2024-25.

## Decision

`def_xg_shrink_challenger` passes the Historical Promotion Gate on both development (2025-26) and confirmation (2024-25) seasons under ADR 0054. Adoption queued in Human Queue for user authorization.
