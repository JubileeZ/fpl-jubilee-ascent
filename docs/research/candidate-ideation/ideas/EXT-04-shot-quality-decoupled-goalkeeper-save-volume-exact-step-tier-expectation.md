---
idea_id: EXT-04
name: "Shot-Quality Decoupled Goalkeeper Save Volume & Exact Step-Tier Expectation"
tier: P1
component: xp_saves
status: dead-match
replaces: Replaces goalkeeper save projection in ComponentBaselineModel._project_goalkeeper_saves and CalibratedMatchupHybridModel.
grid: "K_sot=1800,s_sot=0.30; K_sot=1800,s_sot=0.40; K_sot=2400,s_sot=0.35; K_sot=1200,s_sot=0.30; K_sot=2400,s_sot=0.25"
inputs: features.position; features.team_id; features.opponent_id; history.club_sot_conceded_per90_eb; history.opp_sot_for_per90_eb; history.league_avg_sot_per90; history.saves_per90_eb
nearest_ledger_row: "Club SoT volume x pooled save rate (Shots-on-target faced/90 = club GKP (saves+GC)/mins shrunk; x keeper save rate shrunk to 0.67; pool 0.5/1.0; K50/K200)"
spec_path: ideas/EXT-04-shot-quality-decoupled-goalkeeper-save-volume-exact-step-tier-expectation.md
---

# EXT-04: Shot-Quality Decoupled Goalkeeper Save Volume & Exact Step-Tier Expectation

## 1. Concept & Football Hypothesis

The Champion scales goalkeeper saves via generic defensive matchup multipliers and historical save averages. However, saves are governed by the divergence between Shot on Target (SoT) volume conceded and Shot Lethality (xG per SoT). Low-block, mid-to-lower table clubs (£4.5m GKs) systematically funnel opponents into speculative perimeter shots (high SoT volume, low xG/SoT), yielding frequent 1-point and 2-point save bonuses even in matches with moderate xGC. Conversely, high-line possession teams concede few shots, but those conceded are high-xG transition breakaways, starving premium GKs (£5.5m) of save points.
## 2. Mathematical Formulation

For goalkeeper i on club c facing opponent o, let \hat{\lambda}_{\text{GC}, c, o}(g) be the calibrated expected goals conceded (ADR 0040 shrunk by s=0.40). Model the club's baseline Conceded Shots on Target per 90 \hat{\lambda}_{\text{SoT}, c}(g) via Empirical Bayes shrinkage (K_{\text{SoT}} = 1800 mins) and scale by opponent shrunk shot-generation propensity M_{\text{SoT}, o}(g) = 1.0 + s_{\text{sot}}\left(\frac{\text{SoT}_{o, <g}}{\bar{\text{SoT}}_{\text{league}}} - 1.0\right):
   
   $$\hat{\lambda}_{\text{saves}, i, g} = \frac{\mathbb{E}[\text{Mins}_{i,g}]}{90.0} \cdot \max\left(0.5, \; \hat{\lambda}_{\text{SoT}, c}(g) \cdot M_{\text{SoT}, o}(g) - \hat{\lambda}_{\text{GC}, c, o}(g)\right)$$
   
   Rather than approximating save points linearly as \hat{\lambda}_{\text{saves}} / 3.0 (which violates Jensen's inequality on the step function \lfloor S / 3 \rfloor), evaluate the exact Poisson tier expectation truncated at K_{\max}=12:
   
   $$\mathbb{E}[\text{SavePts}_{i,g}] = \sum_{k=3}^{12} \left\lfloor \frac{k}{3} \right\rfloor \frac{\hat{\lambda}_{\text{saves}, i, g}^k e^{-\hat{\lambda}_{\text{saves}, i, g}}}{k!}$$
## 3. Decoupled Architecture Placement

Operates in M_{\text{events}} (xp_saves and xp_bonus for GKP position).
## 4. Replaces / Integration Hook

Replaces goalkeeper save projection in ComponentBaselineModel._project_goalkeeper_saves and CalibratedMatchupHybridModel.
## 5. Parameter Sweep Grid

K_sot=1800,s_sot=0.30; K_sot=1800,s_sot=0.40; K_sot=2400,s_sot=0.35; K_sot=1200,s_sot=0.30; K_sot=2400,s_sot=0.25
## 6. Small-Sample & Cold-Start Strategy

Club-level SoT conceded is seeded from the prior season (0.5 N_{\text{seed}}) with K_{\text{SoT}} = 1800 minutes (20 full matches). For promoted clubs without Premier League seed data, the prior defaults to the bottom-quartile defensive SoT baseline (5.2\text{ SoT/90}), immediately capturing the shot-volume boost of £4.0m–£4.5m promoted keepers in cold_start.
## 7. Budget-Constrained Optimizer Interaction

Under the £83.5m starting cap, saving £1.0m on a goalkeeper (£4.5m low-block keeper vs £5.5m premium keeper) frees critical budget for outfield slots. Moreover, ADR 0061 imposes a -1.5 pt Goalkeeper Transfer Friction penalty; because club low-block shot-funneling profiles are highly stable across a season (r \gt 0.70), this model identifies high-save £4.5m keepers early and holds them across fixture swings, reducing GK transfer churn.
## 8. Point-in-Time Feature Requirements

features.position; features.team_id; features.opponent_id; history.club_sot_conceded_per90_eb; history.opp_sot_for_per90_eb; history.league_avg_sot_per90; history.saves_per90_eb
## 9. Python Code Skeleton

```python
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import poisson
from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel


class ShotQualitySaveVolumeChallengerModel(AdaptiveCausalChallengerModel):
    """Models GK saves via SoT volume minus expected GC and exact Poisson floor tiers."""

    def __init__(
        self,
        k_sot_mins: float = 1800.0,
        s_sot_shrink: float = 0.35,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.k_sot_mins = float(k_sot_mins)
        self.s_sot_shrink = float(s_sot_shrink)

    def _compute_exact_gk_save_points(
        self,
        df: pd.DataFrame,
        xmins: pd.Series,
        expected_gc: pd.Series,
    ) -> pd.Series:
        is_gk = df["position"] == "GKP"
        club_sot_90 = df.get("club_sot_conceded_per90_eb", 4.4).fillna(4.4)
        opp_sot_90 = df.get("opp_sot_for_per90_eb", 4.4).fillna(4.4)
        league_sot_90 = df.get("league_avg_sot_per90", 4.4).fillna(4.4).clip(lower=1.0)

        m_sot_opp = 1.0 + self.s_sot_shrink * ((opp_sot_90 / league_sot_90) - 1.0)
        proj_sot = (xmins / 90.0) * club_sot_90 * m_sot_opp
        lam_saves = (proj_sot - expected_gc).clip(lower=0.3, upper=8.0)

        save_pts = pd.Series(0.0, index=df.index)
        if is_gk.any():
            gk_lam = lam_saves.loc[is_gk].to_numpy()[:, None]
            k_vals = np.arange(3, 15)[None, :]
            tier_weights = (k_vals // 3).astype(float)
            probs = poisson.pmf(k_vals, gk_lam)
            save_pts.loc[is_gk] = (probs * tier_weights).sum(axis=1)
        return save_pts
```

## Ledger Audit & Revisit Justification
- **Flagged Match**: `Club SoT volume x pooled save rate (Shots-on-target faced/90 = club GKP (saves+GC)/mins shrunk; x keeper save rate shrunk to 0.67; pool 0.5/1.0; K50/K200)`
- **Audit Status**: Pending Review
- **Rationale**: [Document why this proposal is structurally distinct from the flagged dead lever before promoting to status: untested]
