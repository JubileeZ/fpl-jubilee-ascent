---
idea_id: EXT-24
name: Price-Conditioned Fixture Sensitivity for Budget Midfielders and Forwards
tier: P1
component: xp_goals
status: untested
replaces: DefXgShrinkChallengerModel.predict and CalibratedMatchupHybridModel._project_event_components.
grid: "gamma_budget=0.15,cost_cutoff=55.0; gamma_budget=0.22,cost_cutoff=55.0; gamma_budget=0.30,cost_cutoff=55.0; gamma_budget=0.20,cost_cutoff=60.0; gamma_budget=0.28,cost_cutoff=60.0; gamma_budget=0.35,cost_cutoff=60.0"
inputs: features.now_cost; features.position_id; features.per90_xg; features.per90_xa; features.opponent_id; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.expected_assists; history.opponent_club_id; history.expected_goals_conceded
nearest_ledger_row: null
spec_path: ideas/EXT-24-price-conditioned-fixture-sensitivity-for-budget-midfielders-and-forwards.md
---

# EXT-24: Price-Conditioned Fixture Sensitivity for Budget Midfielders and Forwards

## 1. Concept & Football Hypothesis

Under the 15-player £100.0m squad constraint (ADR 0066), budget outfielders (£4.5m–£5.5m) exhibit extreme fixture elasticity: in easy home fixtures against bottom-table sides, their underlying production rivals mid-priced players, making them viable 11th starters; but against elite defensive units, their chance creation drops close to zero. Premium talismans (Haaland, Salah), by contrast, generate chances regardless of opposition quality. The active Champion applies identical fixture shrinkage to all assets regardless of price, failing to identify when budget enablers become high-utility starters.

## 2. Mathematical Formulation

Scale fixture responsiveness as an inverse function of player price (`now_cost` in £0.1m units):
   $$\gamma_{\text{price}, i} = \gamma_{\text{budget}} \cdot \max\left(0.0, \frac{\text{cost\_cutoff} - \text{now\_cost}_i}{15.0}\right)$$
   $$\lambda_{xG, i}^*(g) = \text{per90\_xg}_i \cdot \left(1.0 + \gamma_{\text{price}, i} \cdot \frac{3.0 - \text{difficulty}_g}{2.0}\right)$$
   $$\lambda_{xA, i}^*(g) = \text{per90\_xa}_i \cdot \left(1.0 + \gamma_{\text{price}, i} \cdot \frac{3.0 - \text{difficulty}_g}{2.0}\right)$$
   For assets priced above $\text{cost\_cutoff} \in [55.0, 60.0]$ (£5.5m–£6.0m), $\gamma_{\text{price}} = 0.0$ and Champion projections remain untouched. For £4.5m starters in a difficulty 2 fixture, their attacking rates receive a calibrated $+15\%\dots +30\%$ boost.

## 3. Decoupled Architecture Placement

Operates in $M_{\text{events}}$ (`xp_goals`, `xp_assists`).

## 4. Replaces / Integration Hook

`DefXgShrinkChallengerModel.predict` and `CalibratedMatchupHybridModel._project_event_components`.

## 5. Parameter Sweep Grid

`gamma_budget=0.15,cost_cutoff=55.0; gamma_budget=0.22,cost_cutoff=55.0; gamma_budget=0.30,cost_cutoff=55.0; gamma_budget=0.20,cost_cutoff=60.0; gamma_budget=0.28,cost_cutoff=60.0; gamma_budget=0.35,cost_cutoff=60.0`

## 6. Small-Sample & Cold-Start Strategy

Price and fixture difficulty are verified pre-deadline primitives available from GW1. Integrates seamlessly with historical warm seeding.

7. **Full Squad & Budget-Constrained Optimizer Interaction**: Enables the HiGHS MILP solver to reliably field £4.5m–£5.0m budget enablers in favorable fixtures, freeing £1.5m–£2.5m of team budget to lock in permanent premium captains without suffering squad churn or transfer hits.

## 8. Point-in-Time Feature Requirements

`features.now_cost; features.position_id; features.per90_xg; features.per90_xa; features.opponent_id; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.expected_assists; history.opponent_club_id; history.expected_goals_conceded`

## 9. Python Code Skeleton

```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class PriceConditionedFixtureChallengerModel(DefXgShrinkChallengerModel):
    """Price-conditioned fixture sensitivity for budget midfielders and forwards."""

    def __init__(self, gamma_budget: float = 0.22, cost_cutoff: float = 55.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.gamma_budget = float(gamma_budget)
        self.cost_cutoff = float(cost_cutoff)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        pos = feat.get("position_id", 3)
        is_attacker = pos.isin([3, 4])
        cost = pd.to_numeric(feat.get("now_cost", 100.0), errors="coerce").fillna(100.0)
        diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
        price_weight = np.maximum(0.0, (self.cost_cutoff - cost) / 15.0)
        mult = 1.0 + np.where(is_attacker, self.gamma_budget * price_weight * ((3.0 - diff) / 2.0), 0.0)
        for col in ("per90_xg", "per90_xa"):
            if col in feat.columns:
                feat[col] = pd.to_numeric(feat[col], errors="coerce").fillna(0.0) * mult
        return super().predict(feat, horizon)
```

---
