---
idea_id: EXT-21
name: Bounded Soft-Saturating Matchup Factor on Open-Play Goal Expectancy
tier: P1
component: xp_goals
status: untested
replaces: DefXgShrinkChallengerModel.predict and CalibratedMatchupHybridModel._project_event_components.
grid: "gamma_fix=0.10,kappa_scale=0.8; gamma_fix=0.15,kappa_scale=1.0; gamma_fix=0.20,kappa_scale=1.0; gamma_fix=0.15,kappa_scale=1.2; gamma_fix=0.18,kappa_scale=0.8; gamma_fix=0.22,kappa_scale=1.2"
inputs: features.per90_xg; features.position_id; features.penalties_order; features.opponent_id; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.expected_goals_conceded; history.opponent_club_id
nearest_ledger_row: null
spec_path: ideas/EXT-21-bounded-soft-saturating-matchup-factor-on-open-play-goal-expectancy.md
---

# EXT-21: Bounded Soft-Saturating Matchup Factor on Open-Play Goal Expectancy

## 1. Concept & Football Hypothesis

Open-play goal scoring opportunities depend on rival defensive firmness, but simple scaling either vanishes or explodes. A hyperbolic tangent saturating coefficient specifically targeting open-play xG delivers calibrated sensitivity without exploding on weak opposition. Penalties, however, occur at an invariant baseline rate and must not scale with open-play opponent defensive lapses. A hyperbolic tangent saturating multiplier specifically targeting open-play xG delivers meaningful fixture sensitivity while mathematically guaranteeing that easy-fixture projections never explode.

## 2. Mathematical Formulation

For each target fixture $g$, extract pre-deadline opponent defensive quality $\Delta_{\text{xgc}}(g) = \text{opp\_xgc}(g) - \bar{\mu}_{\text{league\_xgc}}$.
   Partition player goal expectancy into penalty baseline and open-play xG:
   $$\text{xG}_{\text{pen}, i} = 0.15 \cdot \mathbb{I}(\text{penalties\_order}_i == 1)$$
   $$\text{xG}_{\text{open}, i} = \max(0.0, \text{per90\_xg}_i - \text{xG}_{\text{pen}, i})$$
   Apply a bounded, soft-saturating elasticity factor:
   $$M_{\text{open}, i}(g) = 1.0 + \gamma_{\text{fix}} \cdot \tanh\left(\kappa_{\text{scale}} \cdot \frac{\Delta_{\text{xgc}}(g)}{\bar{\sigma}_{\text{league\_xgc}} + \epsilon}\right)$$
   $$\lambda_{xG, i}^*(g) = \text{xG}_{\text{pen}, i} + \text{xG}_{\text{open}, i} \cdot M_{\text{open}, i}(g)$$
   where $\gamma_{\text{fix}} \in [0.10, 0.22]$ bounds the maximum possible fixture swing strictly to $[1.0 - \gamma_{\text{fix}}, 1.0 + \gamma_{\text{fix}}]$, and $\kappa_{\text{scale}} \in [0.8, 1.2]$ controls the curvature rate.

## 3. Decoupled Architecture Placement

Operates in $M_{\text{events}}$ (`xp_goals`).

## 4. Replaces / Integration Hook

`DefXgShrinkChallengerModel.predict` and `CalibratedMatchupHybridModel._project_event_components`.

## 5. Parameter Sweep Grid

`gamma_fix=0.10,kappa_scale=0.8; gamma_fix=0.15,kappa_scale=1.0; gamma_fix=0.20,kappa_scale=1.0; gamma_fix=0.15,kappa_scale=1.2; gamma_fix=0.18,kappa_scale=0.8; gamma_fix=0.22,kappa_scale=1.2`

## 6. Small-Sample & Cold-Start Strategy

Opponent metrics use warm historical seeding ($N_{\text{prior}}=1$). When pre-cutoff opponent history contains fewer than 3 matches, $\Delta_{\text{xgc}}$ shrinks smoothly toward 0.0 using Bayesian sample weighting $w = \min(1.0, n_{\text{opp}} / 4.0)$, yielding $M_{\text{open}} = 1.0$ at cold start.

7. **Full Squad & Budget-Constrained Optimizer Interaction**: By bounding the swing strictly at $\pm \gamma_{\text{fix}}$, it avoids the Optimizer's Curse in green fixtures (preserving playable pool bias) while providing sufficient signal for the MILP solver to rotate £5.0m–£6.5m budget outfielders into the starting XI during favorable 3-match runs, saving transfers and avoiding hits.

## 8. Point-in-Time Feature Requirements

`features.per90_xg; features.position_id; features.penalties_order; features.opponent_id; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.expected_goals_conceded; history.opponent_club_id`

## 9. Python Code Skeleton

```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class BoundedSoftSaturatingFixtureChallengerModel(DefXgShrinkChallengerModel):
    """Soft-saturating open-play fixture elasticity avoiding linear overprediction."""

    def __init__(self, gamma_fix: float = 0.15, kappa_scale: float = 1.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.gamma_fix = float(gamma_fix)
        self.kappa_scale = float(kappa_scale)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        is_pen = pd.to_numeric(feat.get("penalties_order", 0.0), errors="coerce").fillna(0.0).eq(1.0)
        xg = pd.to_numeric(feat.get("per90_xg", 0.0), errors="coerce").fillna(0.0)
        open_xg = (xg - np.where(is_pen, 0.15, 0.0)).clip(lower=0.0)
        pen_xg = np.where(is_pen, np.minimum(xg, 0.15), 0.0)
        diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
        delta_norm = (3.0 - diff) / 1.5
        m_open = 1.0 + self.gamma_fix * np.tanh(self.kappa_scale * delta_norm)
        feat["per90_xg"] = pen_xg + open_xg * m_open
        return super().predict(feat, horizon)
```

---
