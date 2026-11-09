---
idea_id: EXT-22
name: Venue-Conditioned Empirical Bayes Attacking Output Dynamics
tier: P1
component: xp_goals
status: untested
replaces: DefXgShrinkChallengerModel.predict and CalibratedMatchupHybridModel._project_event_components.
grid: "beta_venue=0.06,k_venue=4.0; beta_venue=0.09,k_venue=4.0; beta_venue=0.12,k_venue=4.0; beta_venue=0.08,k_venue=6.0; beta_venue=0.10,k_venue=6.0; beta_venue=0.14,k_venue=8.0"
inputs: features.is_home; features.per90_xg; features.per90_xa; features.position_id; history.player_id; history.gameweek_id; history.was_home; history.expected_goals; history.expected_assists; history.minutes
nearest_ledger_row: null
spec_path: ideas/EXT-22-venue-conditioned-empirical-bayes-attacking-output-dynamics.md
---

# EXT-22: Venue-Conditioned Empirical Bayes Attacking Output Dynamics

## 1. Concept & Football Hypothesis

Premier League teams register approximately 24% higher offensive production at home versus away. While team metrics blend venue splits, individual projection outputs evaluate identically across home and away matches. An empirical Bayes home-away coefficient captures this persistent calendar advantage. Starters exhibit systematic home production premiums that transfer planning MILPs must exploit when scheduling rotations.

## 2. Mathematical Formulation

Model venue advantage as a log-multiplicative adjustment centered at unity across a balanced home/away schedule:
   $$V_i(g) = \exp\left(\beta_{\text{venue}} \cdot (2 \cdot \mathbb{I}(\text{is\_home}_g) - 1.0)\right)$$
   For a candidate parameter $\beta_{\text{venue}} \in [0.06, 0.14]$, this yields an exact home multiplier $e^{+\beta} \approx 1.06 \dots 1.15$ and away multiplier $e^{-\beta} \approx 0.94 \dots 0.87$, preserving geometric mean unity:
   $$\lambda_{xG, i}^*(g) = \text{per90\_xg}_i \cdot V_i(g)$$
   $$\lambda_{xA, i}^*(g) = \text{per90\_xa}_i \cdot V_i(g)$$
   Shrunk toward league baseline via Empirical Bayes weighting $w_v = \frac{n_{\text{played}}}{n_{\text{played}} + K_{\text{venue}}}$.

## 3. Decoupled Architecture Placement

Operates in $M_{\text{events}}$ (`xp_goals`, `xp_assists`).

## 4. Replaces / Integration Hook

`DefXgShrinkChallengerModel.predict` and `CalibratedMatchupHybridModel._project_event_components`.

## 5. Parameter Sweep Grid

`beta_venue=0.06,k_venue=4.0; beta_venue=0.09,k_venue=4.0; beta_venue=0.12,k_venue=4.0; beta_venue=0.08,k_venue=6.0; beta_venue=0.10,k_venue=6.0; beta_venue=0.14,k_venue=8.0`

## 6. Small-Sample & Cold-Start Strategy

Relies strictly on `is_home` (a binary calendar truth known perfectly in advance). Zero historical sample requirement for feature availability; EB shrinkage $K_{\text{venue}}$ prevents early-season venue noise.

7. **Full Squad & Budget-Constrained Optimizer Interaction**: In a 15-player £100.0m squad, bench players are frequently paired (e.g. two £4.5m defenders or £5.0m midfielders with alternating home/away schedules). Accurately reflecting venue premiums enables the solver to naturally bench away assets in favor of home assets without taking transfer hits.

## 8. Point-in-Time Feature Requirements

`features.is_home; features.per90_xg; features.per90_xa; features.position_id; history.player_id; history.gameweek_id; history.was_home; history.expected_goals; history.expected_assists; history.minutes`

## 9. Python Code Skeleton

```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class VenueConditionedDynamicsChallengerModel(DefXgShrinkChallengerModel):
    """Venue-conditioned empirical Bayes attacking dynamics."""

    def __init__(self, beta_venue: float = 0.09, k_venue: float = 4.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.beta_venue = float(beta_venue)
        self.k_venue = float(k_venue)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        is_home = feat.get("is_home", True).astype(bool)
        v_mult = np.where(is_home, np.exp(self.beta_venue), np.exp(-self.beta_venue))
        for col in ("per90_xg", "per90_xa"):
            if col in feat.columns:
                feat[col] = pd.to_numeric(feat[col], errors="coerce").fillna(0.0) * v_mult
        return super().predict(feat, horizon)
```

---
