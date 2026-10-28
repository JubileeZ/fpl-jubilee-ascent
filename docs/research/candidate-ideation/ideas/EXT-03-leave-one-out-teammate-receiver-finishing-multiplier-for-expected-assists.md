---
idea_id: EXT-03
name: Leave-One-Out Teammate Receiver Finishing Multiplier for Expected Assists
tier: P1
component: xp_assists
status: dead-match
replaces: Replaces or augments the Group B LOO assist finishing head in MLComponentChallengerModel._apply_assist_finishing_adjustment and operates across all 38 GWs rather than waiting for GW 20.
grid: "K_rec_xg=20.0,kappa_max=0.12; K_rec_xg=25.0,kappa_max=0.12; K_rec_xg=25.0,kappa_max=0.15; K_rec_xg=30.0,kappa_max=0.10; K_rec_xg=35.0,kappa_max=0.15"
inputs: features.team_id; history.player_goals_ewm; history.player_xg_ewm; history.club_goals_ewm; history.club_xg_ewm; history.prior_season_club_goals; history.prior_season_club_xg
nearest_ledger_row: Assist finishing offsets (goals+assists pooled)
spec_path: ideas/EXT-03-leave-one-out-teammate-receiver-finishing-multiplier-for-expected-assists.md
---

# EXT-03: Leave-One-Out Teammate Receiver Finishing Multiplier for Expected Assists

## Checkpoint status (2026-10-28)

Screened against locked Dead lever; skipped, no new empirical run. Queue/ledger own mechanism match and revisit boundary. Current status: `idea_queue.csv` + Candidate Ledger. Proposal body below records original intake, not a current gate verdict.

## 1. Concept & Football Hypothesis

Expected Assists (xA) measures the probability that a pass becomes a goal given the spatial coordinates of the shot taken by the receiver. However, actual FPL assist realization depends on the finishing efficiency of the receiving teammates. While AdaptiveCausalChallengerModel includes a Group B assist residual on the creator's historical (A - xA), a creator's own (A - xA) is dominated by small-sample shot variance. Directly modeling the minute-weighted finishing skill (G - xG) of the other attacking players on the same club (j \neq i) captures true structural conversion alpha with 10x larger sample size (pooling across all club shooters).
## 2. Mathematical Formulation

For player i on club c at gameweek g, define the Leave-One-Out (LOO) club teammate pool \mathcal{C}_{c \setminus \{i\}}. Using exponentially decayed (\omega = 0.95^{\Delta g}) historical goals G_{j, <g}, expected goals xG_{j, <g}, and minutes M_{j, <g} (including 0.5-weighted warm seed prior season totals), compute the LOO club finishing ratio:
   
   $$G_{c \setminus \{i\}, <g} = \sum_{j \in \mathcal{C}_{c \setminus \{i\}}} G_{j, <g}, \quad X_{c \setminus \{i\}, <g} = \sum_{j \in \mathcal{C}_{c \setminus \{i\}}} xG_{j, <g}$$
   
   Apply Empirical Bayes shrinkage with pseudo-xG parameter K_{\text{rec\_xg}} \in [15.0, 35.0] expected goals and smoothly bound via hyperbolic tangent to prevent outlier distortion:
   
   $$\mathcal{R}_{c \setminus \{i\}}(g) = 1.0 + \kappa_{\max} \tanh\left( \frac{G_{c \setminus \{i\}, <g} - X_{c \setminus \{i\}, <g}}{X_{c \setminus \{i\}, <g} + K_{\text{rec\_xg}}} \right)$$
   
   where \kappa_{\max} \in [0.10, 0.18] caps the maximum receiver finishing boost/penalty. The player's projected assist rate becomes:
   
   $$\hat{\lambda}_{xA, i}^{\text{adj}}(g) = \hat{\lambda}_{xA, i}^{\text{base}}(g) \cdot \mathcal{R}_{c \setminus \{i\}}(g)$$
## 3. Decoupled Architecture Placement

Operates in M_{\text{events}} (xp_assists and downstream xp_bonus via assist BPS contribution).
## 4. Replaces / Integration Hook

Replaces or augments the Group B LOO assist finishing head in MLComponentChallengerModel._apply_assist_finishing_adjustment and operates across all 38 GWs rather than waiting for GW 20.
## 5. Parameter Sweep Grid

K_rec_xg=20.0,kappa_max=0.12; K_rec_xg=25.0,kappa_max=0.12; K_rec_xg=25.0,kappa_max=0.15; K_rec_xg=30.0,kappa_max=0.10; K_rec_xg=35.0,kappa_max=0.15
## 6. Small-Sample & Cold-Start Strategy

Because club-level xG accumulates across 10 outfield players simultaneously (\approx 1.5\text{ xG/GW} per club), a warm-seeded club enters GW1 with 0.5 \times 55 \approx 27.5 prior pseudo-xG. Combined with K_{\text{rec\_xg}} = 25.0, the denominator exceeds 50.0 xG from GW1, completely avoiding Nickell bias and early-season noise while satisfying the cold_start (\ge -0.25) and early_mid (\ge -0.15) segment floors.
## 7. Budget-Constrained Optimizer Interaction

Under the £83.5m Constrained Legal Formation XI, the optimizer must select 2 to 3 budget midfielders or attacking defenders (£4.5m–£5.8m) who take corners/free kicks or supply clinical strikers. Accurately boosting set-piece creators feeding clinical finishers (and penalizing creators feeding chronic under-finishers) sharpens budget midfielder differentiation without inflating premium forward projections (since the striker is excluded from their own LOO pool c \setminus \{i\}), directly preserving Captaincy Regret guardrails.
## 8. Point-in-Time Feature Requirements

features.team_id; history.player_goals_ewm; history.player_xg_ewm; history.club_goals_ewm; history.club_xg_ewm; history.prior_season_club_goals; history.prior_season_club_xg
## 9. Python Code Skeleton

```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel


class ReceiverFinishingAssistChallengerModel(AdaptiveCausalChallengerModel):
    """Adjusts xA conversion using Leave-One-Out club teammate finishing skill."""

    def __init__(
        self,
        k_rec_xg: float = 25.0,
        kappa_max: float = 0.12,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.k_rec_xg = float(k_rec_xg)
        self.kappa_max = float(kappa_max)

    def _compute_loo_receiver_multiplier(self, df: pd.DataFrame) -> pd.Series:
        club_g = (
            0.5 * df.get("prior_season_club_goals", 0.0).fillna(0.0)
            + df.get("club_goals_ewm", 0.0).fillna(0.0)
        )
        club_xg = (
            0.5 * df.get("prior_season_club_xg", 0.0).fillna(0.0)
            + df.get("club_xg_ewm", 0.0).fillna(0.0)
        )
        self_g = (
            0.5 * df.get("prior_season_goals", 0.0).fillna(0.0)
            + df.get("player_goals_ewm", 0.0).fillna(0.0)
        )
        self_xg = (
            0.5 * df.get("prior_season_xg", 0.0).fillna(0.0)
            + df.get("player_xg_ewm", 0.0).fillna(0.0)
        )

        loo_g = (club_g - self_g).clip(lower=0.0)
        loo_xg = (club_xg - self_xg).clip(lower=0.0)

        raw_ratio = (loo_g - loo_xg) / (loo_xg + self.k_rec_xg)
        multiplier = 1.0 + self.kappa_max * np.tanh(raw_ratio)
        return pd.Series(multiplier, index=df.index).clip(
            lower=1.0 - self.kappa_max, upper=1.0 + self.kappa_max
        )
```

## Ledger Audit & Revisit Justification
- **Flagged Match**: `Assist finishing offsets (goals+assists pooled)`
- **Audit Status**: Pending Review
- **Rationale**: [Document why this proposal is structurally distinct from the flagged dead lever before promoting to status: untested]
