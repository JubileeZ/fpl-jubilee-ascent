---
idea_id: EXT-30
name: Component-Specific Matchup Elasticity from Team-Level Calibration Slopes
tier: P1
component: xp_goals
status: dead-match
replaces: "The single $s=0.40$ constant in ADR 0040 (attack_multiplier, defence_multiplier), replaced by $s_{\\text{att}}$ and $s_{\\text{def}}$."
grid: "K_s=150,att_def; K_s=300,att_def; K_s=600,att_def; K_s=300,att_only; K_s=300,def_only; K_s=300,att_def,beta_cap=0.60"
inputs: features.team_attack_strength; features.team_defence_strength; features.opponent_attack_strength; features.opponent_defence_strength; features.attack_multiplier; features.defence_multiplier; features.is_home; history.expected_goals; history.team_h_score; history.team_a_score; history.fixture_id; history.was_home
nearest_ledger_row: Fixture swing multiplicative (s_att) and additive arms
spec_path: ideas/EXT-30-component-specific-matchup-elasticity-from-team-level-calibration-slopes.md
---

# EXT-30: Component-Specific Matchup Elasticity from Team-Level Calibration Slopes

## 1. Concept & Football Hypothesis

The Champion uses one global $s=0.40$. The reliability of the attacking gradient and the defensive (clean-sheet) gradient need not match. The calibration slope can be estimated at team-fixture level (hundreds of observations per season), which is much less noisy than player-level slopes. This makes the elasticity calibrated per component instead of globally tuned.
## 2. Mathematical Formulation

Team-fixture log-link regression for $c \in \{\text{att}, \text{def}\}$: $\mathbb{E}[y_f] = \mu_c\,R_f^{\beta_c}$, with $y_f$ the team xG (att) or goals conceded (def), and $R_f$ the raw strength ratio from official strengths. First-order equivalence $s_c \approx \beta_c$. Shrunk and capped:
   $$s_c = \min\!\left(0.60,\ \frac{n_f\,\hat\beta_c + K_s\cdot 0.40}{n_f + K_s}\right),\quad n_f = 0.5\,n_{\text{seed}} + n_{\text{in-season}}$$
   $s_{\text{att}}$ drives the xG/xA multiplier and $s_{\text{def}}$ drives $\lambda_{\text{against}}$.
## 3. Decoupled Architecture Placement

$M_{\text{events}}$ (`xp_goals`, `xp_assists`, `xp_clean_sheets`).
## 4. Replaces / Integration Hook

The single $s=0.40$ constant in ADR 0040 (`attack_multiplier`, `defence_multiplier`), replaced by $s_{\text{att}}$ and $s_{\text{def}}$.
## 5. Parameter Sweep Grid

`K_s=150,att_def; K_s=300,att_def; K_s=600,att_def; K_s=300,att_only; K_s=300,def_only; K_s=300,att_def,beta_cap=0.60`
## 6. Small-Sample & Cold-Start Strategy

At GW1, $n_f$ is the seed weight only, and $K_s$ pulls both slopes toward 0.40, so the Champion is the default. In-season team-fixtures enter continuously through $N_{\text{eff}}$. This is not an ML activation and has no step.
7. **Full Squad & Budget-Constrained Optimizer Interaction**: It is calibrated at team level, so it is unbiased in-sample by construction. The 0.60 cap bounds the easy-fixture bias that sank the raw multipliers (+0.681 versus neutral +0.221). It changes fixture elasticity only, with no per-player terms, so there is little added churn. A better-calibrated $s_{\text{def}}$ affects clean-sheet value for cheap DEF/GKP enablers.
## 8. Point-in-Time Feature Requirements

`features.team_attack_strength; features.team_defence_strength; features.opponent_attack_strength; features.opponent_defence_strength; features.attack_multiplier; features.defence_multiplier; features.is_home; history.expected_goals; history.team_h_score; history.team_a_score; history.fixture_id; history.was_home`
## 9. Python Code Skeleton (Optional)

```python
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class ComponentElasticityChallengerModel(DefXgShrinkChallengerModel):
    def __init__(self, k_s: float = 300.0, beta_cap: float = 0.60, arms: str = "att_def", **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.k_s, self.beta_cap, self.arms = float(k_s), float(beta_cap), arms
```

## Ledger Audit & Revisit Justification
- **Flagged Match**: `CS exposure over 60+ starts (GK and DEF clean-sheet exposure uses as-of player mean start minutes given >=60 minutes; shrunk to 85.0 min with K=4 starts)` (keyword hit); Nearest true dead lever: `Fixture swing multiplicative (s_att) and additive arms` (Row 21)
- **Audit Status**: Confirmed Dead-Match
- **Rationale**: While `CS exposure over 60+ starts` was a false keyword match, the underlying proposal estimates independent component-specific matchup elasticities ($s_{\text{att}}$ and $s_{\text{def}}$), which belongs to the dead lever archetype `Fixture swing multiplicative (s_att) and additive arms` logged Dead on 2026-09-24 with `revisit_after = 2027-09-24` due to easy fixture over-prediction. Capping $\beta$ at 0.60 bounds the inflation but does not lift the 1-year lock without explicit user direction; retained as `dead-match`.
