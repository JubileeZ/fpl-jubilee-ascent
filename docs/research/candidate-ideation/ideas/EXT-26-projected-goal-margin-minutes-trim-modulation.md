---
idea_id: EXT-26
name: Projected Goal Margin Minutes Trim Modulation
tier: P1
component: xp_minutes
status: untested
replaces: ParticipationStateHybridModel._conditional_minutes and LearnedStartChallengerModel.predict.
grid: "psi_margin=1.5,tau_margin=0.5; psi_margin=2.5,tau_margin=0.5; psi_margin=3.5,tau_margin=0.5; psi_margin=2.0,tau_margin=0.75; psi_margin=3.0,tau_margin=0.75; psi_margin=4.0,tau_margin=1.0"
inputs: features.position_id; features.team_attack_strength; features.opponent_defence_strength; features.p_start; features.xmins_if_start; history.player_id; history.gameweek_id; history.minutes; history.starts
nearest_ledger_row: null
spec_path: ideas/EXT-26-projected-goal-margin-minutes-trim-modulation.md
---

# EXT-26: Projected Goal Margin Minutes Trim Modulation

## 1. Concept & Football Hypothesis

In lopsided fixtures where a team is heavily favored, managers frequently substitute key attacking talismans early to rest them once victory is secured. A margin-dependent playing-time adjustment accounts for blowout substitution hazard while keeping base probabilities invariant. Currently, the Champion treats expected duration as fixture-independent. A modest, margin-dependent duration trim accounts for blowout substitution hazard without destabilizing $p_{\text{start}}$.

## 2. Mathematical Formulation

Estimate expected match goal margin from official attack and defence ratings:
   $$\Delta_{\text{margin}}(g) = \text{team\_attack\_strength}_g - \text{opponent\_defence\_strength}_g$$
   Apply a non-linear blowout hazard offset to expected starting minutes:
   $$\delta_{\text{mins}, i}(g) = -\psi_{\text{margin}} \cdot \max(0.0, \Delta_{\text{margin}}(g) - \tau_{\text{margin}})$$
   $$xMins_{\text{start}, i}^*(g) = \max(60.0, xMins_{\text{start}, i} + \delta_{\text{mins}, i}(g))$$
   where $\psi_{\text{margin}} \in [1.5, 4.0]$ minutes and $\tau_{\text{margin}} \in [0.5, 1.0]$.
   $p_{\text{start}}$ and $p_{\text{sub\_in}}$ remain completely untouched, ensuring total starting mass is invariant.

## 3. Decoupled Architecture Placement

Operates in $M_{\text{mins}}$ (`xp_minutes`).

## 4. Replaces / Integration Hook

`ParticipationStateHybridModel._conditional_minutes` and `LearnedStartChallengerModel.predict`.

## 5. Parameter Sweep Grid

`psi_margin=1.5,tau_margin=0.5; psi_margin=2.5,tau_margin=0.5; psi_margin=3.5,tau_margin=0.5; psi_margin=2.0,tau_margin=0.75; psi_margin=3.0,tau_margin=0.75; psi_margin=4.0,tau_margin=1.0`

## 6. Small-Sample & Cold-Start Strategy

Uses official pre-season club attack/defence strengths, ensuring full availability from GW1.

7. **Full Squad & Budget-Constrained Optimizer Interaction**: Slightly trims inflated talisman captaincy projections in blowout fixtures, redistributing expected minutes toward nailed 90-minute budget assets and improving captaincy regret guardrails.

## 8. Point-in-Time Feature Requirements

`features.position_id; features.team_attack_strength; features.opponent_defence_strength; features.p_start; features.xmins_if_start; history.player_id; history.gameweek_id; history.minutes; history.starts`

## 9. Python Code Skeleton

```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class GameStateMarginDurationChallengerModel(DefXgShrinkChallengerModel):
    """Starter playing duration modulation conditioned on projected match goal margin."""

    def __init__(self, psi_margin: float = 2.5, tau_margin: float = 0.5, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.psi_margin = float(psi_margin)
        self.tau_margin = float(tau_margin)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        if "team_attack_strength" in feat.columns and "opponent_defence_strength" in feat.columns:
            atk = pd.to_numeric(feat["team_attack_strength"], errors="coerce").fillna(1000.0) / 1000.0
            opp_def = pd.to_numeric(feat["opponent_defence_strength"], errors="coerce").fillna(1000.0) / 1000.0
            margin = (atk - opp_def).clip(lower=0.0)
            excess = np.maximum(0.0, margin - self.tau_margin)
            offset = -self.psi_margin * excess
            if "xmins_if_start" in feat.columns:
                feat["xmins_if_start"] = (pd.to_numeric(feat["xmins_if_start"], errors="coerce").fillna(78.0) + offset).clip(lower=60.0)
        return super().predict(feat, horizon)
```
