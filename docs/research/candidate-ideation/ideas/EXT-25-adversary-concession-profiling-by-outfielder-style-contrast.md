---
idea_id: EXT-25
name: Adversary Concession Profiling by Outfielder Style Contrast
tier: P1
component: xp_goals
status: untested
replaces: DefXgShrinkChallengerModel.predict and CalibratedMatchupHybridModel._project_event_components.
grid: "xi_modality=0.08,k_modality=360.0; xi_modality=0.12,k_modality=360.0; xi_modality=0.16,k_modality=360.0; xi_modality=0.10,k_modality=540.0; xi_modality=0.14,k_modality=540.0; xi_modality=0.18,k_modality=540.0"
inputs: features.position_id; features.per90_xg; features.per90_xa; features.per90_threat; features.per90_creativity; features.opponent_id; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.expected_assists; history.threat; history.creativity; history.opponent_club_id
nearest_ledger_row: null
spec_path: ideas/EXT-25-adversary-concession-profiling-by-outfielder-style-contrast.md
---

# EXT-25: Adversary Concession Profiling by Outfielder Style Contrast

## 1. Concept & Football Hypothesis

Opponents concede scoring opportunities through fundamentally different defensive failure modes: some allow high shot volume inside the box (conceding to pure finishers with high `per90_threat` and `per90_xg`), while others concede from wide crosses and cutbacks (conceding to creators with high `per90_creativity` and `per90_xa`). Currently, all outfielders on a team receive identical linear matchup share multipliers regardless of whether their personal playing style attacks the specific vulnerability of the adversary.

## 2. Mathematical Formulation

Calculate player attacking style index from pre-deadline metrics:
   $$\theta_{\text{style}, i} = \frac{\text{per90\_xg}_i}{\text{per90\_xg}_i + \text{per90\_xa}_i + \epsilon} \in [0.0, 1.0]$$
   Calculate opponent concession profile from historical match logs (shrunk via $K_{\text{modality}} = 360$ minutes toward position baseline):
   $$\phi_{\text{opp}, c} = \frac{\sum \text{threat\_conceded}_c}{\sum \text{threat\_conceded}_c + \sum \text{creativity\_conceded}_c + \epsilon}$$
   Compute the style alignment contrast:
   $$\Delta_{\text{align}, i}(g) = (\theta_{\text{style}, i} - 0.5) \cdot (\phi_{\text{opp}, \text{opp}(i)} - 0.5)$$
   Apply bounded style modulation:
   $$\lambda_{xG, i}^*(g) = \text{per90\_xg}_i \cdot \left(1.0 + \xi_{\text{modality}} \cdot \text{clip}(4.0 \cdot \Delta_{\text{align}, i}(g), -1.0, 1.0)\right)$$
   $$\lambda_{xA, i}^*(g) = \text{per90\_xa}_i \cdot \left(1.0 - \xi_{\text{modality}} \cdot \text{clip}(4.0 \cdot \Delta_{\text{align}, i}(g), -1.0, 1.0)\right)$$
   where $\xi_{\text{modality}} \in [0.08, 0.18]$ governs the maximum style rebalancing.

## 3. Decoupled Architecture Placement

Operates in $M_{\text{events}}$ (`xp_goals`, `xp_assists`).

## 4. Replaces / Integration Hook

`DefXgShrinkChallengerModel.predict` and `CalibratedMatchupHybridModel._project_event_components`.

## 5. Parameter Sweep Grid

`xi_modality=0.08,k_modality=360.0; xi_modality=0.12,k_modality=360.0; xi_modality=0.16,k_modality=360.0; xi_modality=0.10,k_modality=540.0; xi_modality=0.14,k_modality=540.0; xi_modality=0.18,k_modality=540.0`

## 6. Small-Sample & Cold-Start Strategy

Style indices shrink smoothly toward positional averages ($0.60$ for FWD, $0.40$ for MID).

7. **Full Squad & Budget-Constrained Optimizer Interaction**: Differentiates between similar-priced options (e.g. £5.5m winger vs £5.5m poacher) based on specific opponent vulnerabilities, optimizing tactical squad selection without inflating transfer turnover.

## 8. Point-in-Time Feature Requirements

`features.position_id; features.per90_xg; features.per90_xa; features.per90_threat; features.per90_creativity; features.opponent_id; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.expected_assists; history.threat; history.creativity; history.opponent_club_id`

## 9. Python Code Skeleton

```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class AdversaryStyleContrastChallengerModel(DefXgShrinkChallengerModel):
    """Style contrast modulation matching attacker profile to opponent concession pattern."""

    def __init__(self, xi_modality: float = 0.12, k_modality: float = 360.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.xi_modality = float(xi_modality)
        self.k_modality = float(k_modality)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        xg = pd.to_numeric(feat.get("per90_xg", 0.0), errors="coerce").fillna(0.0)
        xa = pd.to_numeric(feat.get("per90_xa", 0.0), errors="coerce").fillna(0.0)
        tot = xg + xa + 1e-6
        theta = (xg / tot).clip(0.0, 1.0)
        diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
        contrast = (theta - 0.5) * ((3.0 - diff) / 2.0)
        feat["per90_xg"] = xg * (1.0 + self.xi_modality * np.clip(2.0 * contrast, -1.0, 1.0))
        feat["per90_xa"] = xa * (1.0 - self.xi_modality * np.clip(2.0 * contrast, -1.0, 1.0))
        return super().predict(feat, horizon)
```

---
