---
idea_id: EXT-31
name: Opponent-Sample-Reliability Matchup Share (Promoted-Club Cold Start)
tier: P1
component: xp_goals
status: untested
replaces: The $s$ constant applied in CalibratedMatchupHybridModel (attack_multiplier, defence_multiplier), now per fixture.
grid: "K_t=10; K_t=19; K_t=38; K_t=19,rule=min; K_t=38,rule=min; K_t=19,w_floor=0.25"
inputs: features.club_id; features.opponent_id; features.gameweek_id; features.team_strength; features.attack_multiplier; features.defence_multiplier; history.fixture_id; history.gameweek_id; history.team_h_score; history.team_a_score; history.was_home
nearest_ledger_row: null
spec_path: ideas/EXT-31-opponent-sample-reliability-matchup-share-promoted-club-cold-start.md
---

# EXT-31: Opponent-Sample-Reliability Matchup Share (Promoted-Club Cold Start)

## 1. Concept & Football Hypothesis

Official strength ratings for newly promoted clubs, or clubs with little Premier League data, are far less reliable than for established clubs, yet the Champion applies the same $s$ to every opponent. Fixtures involving low-sample clubs should be attenuated early in the season and ramp to the full $s$ as data accumulates. This is attenuation only, never amplification.
## 2. Mathematical Formulation

For club $t$: $n_t = 0.5\,n_{\text{seed},t} + n_{\text{in-season},t}$, $w_t = \frac{n_t}{n_t + K_t}$. Normalized to a reference established club at GW1 ($n_{\text{ref}} = 19$): $\hat w_t = \min\!\left(1,\ w_t / w_{\text{ref}}\right)$. Pair weight: $\hat w_{\text{pair}} = \sqrt{\hat w_{\text{own}}\,\hat w_{\text{opp}}}$ (or the min). Effective share:
   $$s_{\text{eff}} = s\cdot \hat w_{\text{pair}},\qquad m = 1 + s_{\text{eff}}\,(R - 1)$$
   Promoted clubs with $n_t=0$ get $s_{\text{eff}}=0$ (neutral) at GW1.
## 3. Decoupled Architecture Placement

$M_{\text{events}}$ (`xp_goals`, `xp_assists`, `xp_clean_sheets`).
## 4. Replaces / Integration Hook

The $s$ constant applied in `CalibratedMatchupHybridModel` (`attack_multiplier`, `defence_multiplier`), now per fixture.
## 5. Parameter Sweep Grid

`K_t=10; K_t=19; K_t=38; K_t=19,rule=min; K_t=38,rule=min; K_t=19,w_floor=0.25`
## 6. Small-Sample & Cold-Start Strategy

This is a cold-start mechanism. It uses the same $N_{\text{eff}}$ form with seed weight 0.5 ($N_{\text{prior}}=1$). Established clubs have $\hat w=1$ and match the Champion at GW1. Promoted clubs ramp continuously, fully by roughly GW19 at $K_t=19$. There is no activation step and no ML.
7. **Full Squad & Budget-Constrained Optimizer Interaction**: Attenuation can only move projections toward neutral, so it cannot widen easy-fixture bias, and the guardrail margin is protected. It reduces early-season transfers made on unreliable promoted-club fixture swings, cutting hits and churn in GW2-10. It limits over-reliance on fixture runs against promoted sides when funding premiums from cheap enablers.
## 8. Point-in-Time Feature Requirements

`features.club_id; features.opponent_id; features.gameweek_id; features.team_strength; features.attack_multiplier; features.defence_multiplier; history.fixture_id; history.gameweek_id; history.team_h_score; history.team_a_score; history.was_home`
## 9. Python Code Skeleton (Optional)

```python
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class OpponentReliabilityMatchupChallengerModel(DefXgShrinkChallengerModel):
    def __init__(self, k_t: float = 19.0, rule: str = "geo", w_floor: float = 0.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.k_t, self.rule, self.w_floor = float(k_t), rule, float(w_floor)
```
