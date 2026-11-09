---
idea_id: EXT-29
name: Opponent Positional Concession Share (Mean-Preserving)
tier: P1
component: xp_goals
status: dead-match
replaces: A new post-matchup stage in CalibratedMatchupHybridModel._project_event_components. ADR 0040 totals are unchanged.
grid: "K_x=15; K_x=30; K_x=60; K_x=120; K_x=60,xg_only; K_x=60,xa_only"
inputs: history.expected_goals; history.expected_assists; history.minutes; history.opponent_club_id; history.gameweek_id; history.fixture_id; features.player_id; features.position_id; features.per90_xg; features.per90_xa; features.opponent_id; features.attack_multiplier
nearest_ledger_row: Opponent conditional attacking role allocation (relative concession contrasts by MID/FWD profile, club attacker normalization)
spec_path: ideas/EXT-29-opponent-positional-concession-share-mean-preserving.md
---

# EXT-29: Opponent Positional Concession Share (Mean-Preserving)

## 1. Concept & Football Hypothesis

Opponents differ in where they concede (wide areas versus central, striker versus attacking-midfield chances). ADR 0040 scales the total opponent effect, but every attacker on a club gets the same factor. A compositional reallocation across positions can sharpen fixture discrimination without raising the pool mean, so it avoids the ARCH-05 failure mode. Unlike the locked rate multipliers, it is zero-sum across positions by construction.
## 2. Mathematical Formulation

For opponent $o$, position $\pi \in \{\text{MID},\text{FWD}\}$, component $c \in \{xG, xA\}$:
   $$\hat R_{o,\pi,c} = \frac{\sum_{h:\,\text{opp}=o,\,\text{pos}=\pi} x^c_h + K_x}{\sum_{h:\,\text{opp}=o,\,\text{pos}=\pi} E^c_h + K_x},\quad E^c_h = \hat\lambda^c_{i,h}\,\tfrac{\text{min}_{i,h}}{90}$$
   $$\rho_{o,\pi,c} = \frac{\hat R_{o,\pi,c}}{\sum_{\pi'} w_{\pi',c}\,\hat R_{o,\pi',c}},\qquad \lambda^*_i = \lambda_i\,\rho_{o,\text{pos}(i),c}$$
   $w$ is the league xG share per position, so $\sum_\pi w_\pi\rho_\pi = 1$. This is a gamma-Poisson posterior mean with prior 1. The player's then-current shrunk baseline is the exposure, which removes the confound of who faced $o$. The factor is applied after the matchup share, and DEF is untouched.
## 3. Decoupled Architecture Placement

$M_{\text{events}}$ (`xp_goals`, `xp_assists`).
## 4. Replaces / Integration Hook

A new post-matchup stage in `CalibratedMatchupHybridModel._project_event_components`. ADR 0040 totals are unchanged.
## 5. Parameter Sweep Grid

`K_x=15; K_x=30; K_x=60; K_x=120; K_x=60,xg_only; K_x=60,xa_only`
## 6. Small-Sample & Cold-Start Strategy

With no exposure, $\hat R=1$ and $\rho=1$, which reproduces the Champion. Seed-season opponent records enter at weight 0.5 ($N_{\text{prior}}=1$), and the effect ramps with accumulated exposure ($N_{\text{eff}}$), so GW1-4 stays near neutral.
7. **Full Squad & Budget-Constrained Optimizer Interaction**: Mean preservation keeps the pool bias guardrail intact. The candidate improves relative valuation of MID versus FWD options in specific fixtures, which helps captaincy and transfer timing without lifting every attacker. The strong shrink ($K_x$) limits tail inflation, which is the optimizer's-curse channel. It is opponent-specific rather than player-specific, so it adds little churn. It helps pick the cheaper attacker type against a given opponent.
## 8. Point-in-Time Feature Requirements

`history.expected_goals; history.expected_assists; history.minutes; history.opponent_club_id; history.gameweek_id; history.fixture_id; features.player_id; features.position_id; features.per90_xg; features.per90_xa; features.opponent_id; features.attack_multiplier`
## 9. Python Code Skeleton (Optional)

```python
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class PositionalConcessionShareChallengerModel(DefXgShrinkChallengerModel):
    def __init__(self, k_x: float = 60.0, components: str = "both", **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.k_x, self.components = float(k_x), components
```

## Ledger Audit & Revisit Justification
- **Flagged Match**: `Opponent conditional attacking role allocation (relative concession contrasts by MID/FWD profile, club attacker normalization)` (EXT-11)
- **Audit Status**: Confirmed Dead-Match
- **Rationale**: EXT-11 evaluated relative concession contrasts by MID/FWD attacker profile and failed dev season gating (delta -0.1709 to -0.8675 pts/GW across 3 variants), logged Dead in `candidate_ledger.csv` with `revisit_after = 2027-10-28`. EXT-29 implements a mathematically similar relative concession share by MID/FWD position with zero-sum position weighting. Under Candidate Ledger governance, dead levers cannot be retried prior to `revisit_after` without explicit user instruction; retained as `dead-match`.
