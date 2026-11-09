---
idea_id: EXT-23
name: Asymmetric Log-Linear Defensive Quality Decay for Clean Sheets
tier: P1
component: xp_clean_sheets
status: untested
replaces: CalibratedMatchupHybridModel._project_event_components (modifying per90_goals_conceded before Poisson/NegBin evaluation).
grid: "alpha_cs=0.12,k_cs=4.0; alpha_cs=0.16,k_cs=4.0; alpha_cs=0.20,k_cs=4.0; alpha_cs=0.15,k_cs=6.0; alpha_cs=0.18,k_cs=6.0; alpha_cs=0.24,k_cs=6.0"
inputs: features.position_id; features.per90_goals_conceded; features.opponent_id; features.difficulty; history.player_id; history.gameweek_id; history.minutes; history.opponent_club_id; history.expected_goals; history.expected_goals_conceded
nearest_ledger_row: null
spec_path: ideas/EXT-23-asymmetric-log-linear-defensive-quality-decay-for-clean-sheets.md
---

# EXT-23: Asymmetric Log-Linear Defensive Quality Decay for Clean Sheets

## 1. Concept & Football Hypothesis

Clean sheet probability in `CalibratedMatchupHybridModel` is calculated as $P(\text{CS}) = \exp(-\lambda_{\text{pitch}}) \cdot P(60+)$. In the production model, $\lambda_{\text{pitch}}$ only receives a linear additive shift from opponent goal difference ($\text{gc\_per90} + s_{\text{def}} \cdot \Delta_{\text{def}}$ with $s_{\text{def}} = 0.40$), while `defence_multiplier` is forced to $1.0$. However, against elite attacking sides (e.g. Manchester City, Arsenal, Liverpool), clean sheet probabilities collapse non-linearly. A linear shift severely over-projects clean sheets in difficulty 4–5 fixtures, causing the solver to over-invest in premium defenders during difficult fixture runs.

## 2. Mathematical Formulation

Replace the linear additive shift with an asymmetric log-linear hazard multiplier on pitch concession intensity:
   $$\lambda_{\text{pitch}}^*(g) = \lambda_{\text{base}} \cdot \exp\left(\alpha_{\text{cs}} \cdot \frac{\text{diff}(g) - 3.0}{1.5}\right)$$
   $$P(\text{CS}^*) = \exp(-\lambda_{\text{pitch}}^*(g)) \cdot P(60+)$$
   where $\text{diff}(g)$ is the match difficulty rating ($1.0 \dots 5.0$), and $\alpha_{\text{cs}} \in [0.12, 0.24]$.
   This ensures that difficulty 4 matches incur a factor of $e^{+0.67 \alpha} \approx 1.08 \dots 1.17$ on conceded intensity, dropping clean sheet odds exponentially, while difficulty 2 matches receive a modest boost ($e^{-0.67 \alpha} \approx 0.85 \dots 0.92$), fully controlling Jensen's inequality clean sheet explosion.

## 3. Decoupled Architecture Placement

Operates in $M_{\text{events}}$ (`xp_clean_sheet`, `xp_conceded`).

## 4. Replaces / Integration Hook

`CalibratedMatchupHybridModel._project_event_components` (modifying `per90_goals_conceded` before Poisson/NegBin evaluation).

## 5. Parameter Sweep Grid

`alpha_cs=0.12,k_cs=4.0; alpha_cs=0.16,k_cs=4.0; alpha_cs=0.20,k_cs=4.0; alpha_cs=0.15,k_cs=6.0; alpha_cs=0.18,k_cs=6.0; alpha_cs=0.24,k_cs=6.0`

## 6. Small-Sample & Cold-Start Strategy

Calibrated directly against pre-scheduled FDR `difficulty` and opponent season xG averages with warm seed prior ($N_{\text{prior}}=1$).

7. **Full Squad & Budget-Constrained Optimizer Interaction**: In a 15-player £100.0m squad, defenders represent the primary tactical lever for fixture targeting. When clean sheet probabilities accurately collapse in tough fixtures, the solver shifts budget away from premium defenders facing top-6 attacks toward budget rotating defenders with easy home fixtures.

## 8. Point-in-Time Feature Requirements

`features.position_id; features.per90_goals_conceded; features.opponent_id; features.difficulty; history.player_id; history.gameweek_id; history.minutes; history.opponent_club_id; history.expected_goals; history.expected_goals_conceded`

## 9. Python Code Skeleton

```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class AsymmetricLogLinearDefensiveChallengerModel(DefXgShrinkChallengerModel):
    """Log-linear hazard on goals conceded for clean-sheet sensitivity."""

    def __init__(self, alpha_cs: float = 0.16, k_cs: float = 4.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.alpha_cs = float(alpha_cs)
        self.k_cs = float(k_cs)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        if "per90_goals_conceded" in feat.columns:
            diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
            hazard_mult = np.exp(self.alpha_cs * (diff - 3.0) / 1.5)
            feat["per90_goals_conceded"] = pd.to_numeric(feat["per90_goals_conceded"], errors="coerce").fillna(1.2) * hazard_mult
        return super().predict(feat, horizon)
```

---
