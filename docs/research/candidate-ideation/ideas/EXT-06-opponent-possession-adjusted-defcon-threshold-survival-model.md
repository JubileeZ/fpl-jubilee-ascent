---
idea_id: EXT-06
name: Opponent Possession-Adjusted Defcon Threshold Survival Model
tier: P1
component: xp_defcon
status: untested
replaces: "Modifies ComponentBaselineModel._project_defcon_points by introducing the shrunk opponent demand multiplier M_{\\text{opp\\_dc}, o}(g) prior to the Negative Binomial survival evaluation."
grid: "K_dc=1350,s_dc=0.25; K_dc=1350,s_dc=0.35; K_dc=1800,s_dc=0.30; K_dc=1800,s_dc=0.40; K_dc=1080,s_dc=0.25"
inputs: features.position; features.opponent_id; history.defcon_per90_eb; history.opp_defcon_induced_per90_eb; history.league_avg_defcon_per90
nearest_ledger_row: "ARCH-12: Defcon over-dispersion mixture"
spec_path: ideas/EXT-06-opponent-possession-adjusted-defcon-threshold-survival-model.md
---

# EXT-06: Opponent Possession-Adjusted Defcon Threshold Survival Model

## 1. Concept & Football Hypothesis

FPL awards +2 points when a player reaches the Defensive Contributions (Defcon) threshold (\ge 10 CBI+tackles for DEF; \ge 12 for MID/FWD). The Champion models Defcon using a player's baseline per-90 defensive action rate and a fixed Negative Binomial dispersion (r=3.0), ignoring opponent tactical style. In reality, defensive action volume is bounded by time spent out of possession: when a budget center-back or defensive midfielder (£4.5m–£5.0m) faces a high-possession, high-final-third-entry opponent, their expected CBI+tackle rate surges by +20\% to +35\%. Because +2 points is a right-tail step threshold (\ge 10 or \ge 12), a +25\% shift in mean rate \mu_{\text{dc}} nearly doubles the tail crossing probability P(\text{Defcon} \ge \tau_{\text{pos}}).
## 2. Mathematical Formulation

Let \hat{\lambda}_{\text{DC}, i}(g) be player i's Empirical Bayes per-90 CBI+tackle rate shrunk toward the positional mean with K_{\text{DC}} = 1350 pseudo-minutes (avoiding Dead Lever #12 by keeping Negative Binomial dispersion fixed at r = 3.0). Define the Opponent Defensive Action Demand multiplier M_{\text{opp\_dc}, o}(g) using the opponent's shrunk final-third passes / possession share relative to league average, damped by shrinkage factor s_{\text{dc}} \in [0.20, 0.40]:
   
   $$M_{\text{opp\_dc}, o}(g) = 1.0 + s_{\text{dc}} \left(\frac{\text{DefActions}_{\text{induced}, o, \lt g}}{\overline{\text{DefActions}}_{\text{league}, \lt g}} - 1.0\right)$$
   
   Given starter expected duration \text{xMins}_{\text{start}, i, g}, conditional expected count is \mu_{i, g}^{\text{start}} = \frac{\text{xMins}_{\text{start}, i, g}}{90.0} \hat{\lambda}_{\text{DC}, i}(g) M_{\text{opp\_dc}, o}(g). With fixed dispersion r = 3.0 and threshold \tau_{\text{pos}} \in \{10, 12\}, expected Defcon points are:
   
   $$\mathbb{E}[\text{DefconPts}_{i,g}] = 2.0 \cdot P_i(\text{Start}, g) \cdot \left(1.0 - F_{\text{NegBin}}\left(\tau_{\text{pos}(i)} - 1 \;\middle\vert{}\; \mu = \mu_{i, g}^{\text{start}}, \, r = 3.0\right)\right)$$
   
   where a league-wide scalar normalization \nu_g ensures mean playable Defcon points match the Champion's baseline mean to guarantee zero Playable Pool Bias drift.
## 3. Decoupled Architecture Placement

Operates in M_{\text{events}} (xp_defcon and xp_bonus).
## 4. Replaces / Integration Hook

Modifies ComponentBaselineModel._project_defcon_points by introducing the shrunk opponent demand multiplier M_{\text{opp\_dc}, o}(g) prior to the Negative Binomial survival evaluation.
## 5. Parameter Sweep Grid

K_dc=1350,s_dc=0.25; K_dc=1350,s_dc=0.35; K_dc=1800,s_dc=0.30; K_dc=1800,s_dc=0.40; K_dc=1080,s_dc=0.25
## 6. Small-Sample & Cold-Start Strategy

Does NOT estimate per-player over-dispersion or Beta-Binomial mixture parameters (strictly respecting Dead Lever #12). Dispersion remains locked at r=3.0, and opponent demand M_{\text{opp\_dc}, o} is warm-seeded from the prior season with K_{\text{opp}} = 10 matches and shrunk by s_{\text{dc}} \le 0.35.
## 7. Budget-Constrained Optimizer Interaction

This mechanism directly addresses the £83.5m Constrained Legal Formation XI and ADR 0061 First-Bench Cover / Rotation dynamics. Budget £4.5m center-backs and £5.0m defensive midfielders (ball-winning 6s) suffer clean sheet decay in tough fixtures, causing the baseline model to over-penalize them or burn transfers rotating them out. Recognizing that their Defcon threshold probability rises in tough fixtures acts as a natural variance hedge, stabilizing their floor around 3.2\text{--}3.8 xP and reducing unnecessary defensive squad churn.
## 8. Point-in-Time Feature Requirements

features.position; features.opponent_id; history.defcon_per90_eb; history.opp_defcon_induced_per90_eb; history.league_avg_defcon_per90
## 9. Python Code Skeleton

```python
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import nbinom
from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel


class OpponentAdjustedDefconChallengerModel(AdaptiveCausalChallengerModel):
    """Scales Defcon mean rate by shrunk opponent defensive action demand with fixed NegBin r=3.0."""

    DEFCON_THRESHOLDS: dict[str, int] = {
        "GKP": 10,
        "DEF": 10,
        "MID": 12,
        "FWD": 12,
    }

    def __init__(
        self,
        k_dc_mins: float = 1350.0,
        s_dc_shrink: float = 0.30,
        negbin_r: float = 3.0,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.k_dc_mins = float(k_dc_mins)
        self.s_dc_shrink = float(s_dc_shrink)
        self.negbin_r = float(negbin_r)

    def _compute_defcon_expected_points(
        self,
        df: pd.DataFrame,
        p_start: pd.Series,
        xmins_start: pd.Series,
    ) -> pd.Series:
        base_dc_90 = df.get("defcon_per90_eb", 5.0).fillna(5.0)
        opp_induced = df.get("opp_defcon_induced_per90_eb", 42.0).fillna(42.0)
        league_avg = df.get("league_avg_defcon_per90", 42.0).fillna(42.0).clip(lower=1.0)

        m_opp = 1.0 + self.s_dc_shrink * ((opp_induced / league_avg) - 1.0)
        m_opp = m_opp.clip(lower=0.75, upper=1.30)

        mu_start = (xmins_start / 90.0) * base_dc_90 * m_opp
        mu_start = mu_start.clip(lower=1e-4)

        r = self.negbin_r
        p_nb = r / (r + mu_start)
        thresholds = df["position"].map(self.DEFCON_THRESHOLDS).fillna(12).astype(int)

        prob_hit = 1.0 - nbinom.cdf(thresholds - 1, r, p_nb)
        return 2.0 * p_start * pd.Series(prob_hit, index=df.index)
```

## Ledger Audit & Revisit Justification
- **Flagged Match**: `ARCH-12: Defcon over-dispersion mixture`
- **Audit Status**: Cleared (False Positive)
- **Rationale**: False positive keyword trigger on `defcon` and `dispersion`. The proposal explicitly locks dispersion at $r=3.0$ to respect ARCH-12, scaling only the mean demand via opponent defensive action volume. Cleared to `untested`.
