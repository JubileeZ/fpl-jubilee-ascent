---
idea_id: EXT-28
name: Schedule-Neutralized Attack Baselines
tier: P1
component: xp_goals
status: untested
replaces: The history aggregation feeding per90_xg/per90_xa inside CalibratedMatchupHybridModel._project_event_components. No new multiplier parameters are introduced.
grid: "phi=0.50; phi=0.75; phi=1.00; phi=0.75,xg_only; phi=0.75,xa_only; phi=0.75,in_season_only"
inputs: features.per90_xg; features.per90_xa; features.position_id; features.attack_multiplier; history.expected_goals; history.expected_assists; history.minutes; history.gameweek_id; history.fixture_id; history.was_home; history.opponent_club_id
nearest_ledger_row: null
spec_path: ideas/EXT-28-schedule-neutralized-attack-baselines.md
---

# EXT-28: Schedule-Neutralized Attack Baselines

## 1. Concept & Football Hypothesis

Player per-90 baselines pool minutes at face value. A player whose recent fixtures were easy carries an inflated `per90_xg`/`per90_xa`, which is then multiplied again by a green-fixture multiplier (a double count). This is a plausible driver of easy-fixture bias. The brief documents no schedule adjustment of baselines. The locked "fixture unscaling for derived penalty takers" lever was a taker signal; this applies to all MID/FWD baselines using the already shipped multiplier.
## 2. Mathematical Formulation

For each past fixture $h$, using the shipped pre-match multiplier $m^{\text{att}}_{i,h}$:
   $$\tilde x_{i,h} = \frac{x_{i,h}}{1 + \phi\,(m^{\text{att}}_{i,h} - 1)},\qquad \hat\lambda_i = \frac{\sum_h \tilde x_{i,h}\cdot 90 + K\,\bar\lambda_{\text{pos}}}{\sum_h \text{min}_{i,h} + K}$$
   Forward projection is unchanged: $\lambda^*_i(g) = \hat\lambda_i\, m^{\text{att}}_{i,g}$. $K=360$ is unchanged. MID/FWD only, so $K_{\text{DEF}}=2400$ logic is untouched.
## 3. Decoupled Architecture Placement

$M_{\text{events}}$ (`xp_goals`, `xp_assists`).
## 4. Replaces / Integration Hook

The history aggregation feeding `per90_xg`/`per90_xa` inside `CalibratedMatchupHybridModel._project_event_components`. No new multiplier parameters are introduced.
## 5. Parameter Sweep Grid

`phi=0.50; phi=0.75; phi=1.00; phi=0.75,xg_only; phi=0.75,xa_only; phi=0.75,in_season_only`
## 6. Small-Sample & Cold-Start Strategy

Seed rows are de-matchuped with their archived multipliers ($N_{\text{prior}}=1$), which are near 1 over a full season, so GW1-4 is almost identical to the Champion. The effect grows as schedule imbalance accumulates in-season, entering continuously through $N_{\text{eff}}$ with no activation date.
7. **Full Squad & Budget-Constrained Optimizer Interaction**: It stops the solver from buying players at the peak of an easy run and from selling them after a hard run. That reduces buy-high-sell-low transfers and churn. Cheap enablers on weak sides with a hard early schedule get fair credit, which helps fund premiums. Only bias-reducing corrections are made, with no fitted per-player terms.
## 8. Point-in-Time Feature Requirements

`features.per90_xg; features.per90_xa; features.position_id; features.attack_multiplier; history.expected_goals; history.expected_assists; history.minutes; history.gameweek_id; history.fixture_id; history.was_home; history.opponent_club_id`
## 9. Python Code Skeleton (Optional)

```python
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class ScheduleNeutralBaselineChallengerModel(DefXgShrinkChallengerModel):
    def __init__(self, phi: float = 0.75, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.phi = float(phi)
```

## Ledger Audit & Revisit Justification
- **Flagged Match**: `Penalty-taker signal from per90 only`
- **Audit Status**: Cleared (False Positive)
- **Rationale**: The proposal referenced the locked penalty-taker unscaling lever purely as a comparative contrast in its football hypothesis section. The actual mechanism in EXT-28 performs schedule de-biasing on historical per-90 rates ($\tilde x = x / (1 + \phi(m-1))$) for all MID/FWD players to eliminate double-counting favorable fixture runs when computing shrunk rates. It has no connection to penalty-taker inference; promoted to `untested`.
