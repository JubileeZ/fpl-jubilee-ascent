---
idea_id: EXT-05
name: "Price-Stratified Huber-Regularized Continuous-N_{\\text{eff}} Causal Panel"
tier: P1
component: xp_minutes
status: untested
replaces: Replaces the global Ridge regression fit and GW 20 step ramp in AdaptiveCausalChallengerModel._compute_ml_blend_weight and MLComponentChallengerModel._fit_predict_panel_heads.
grid: "N_min=3500,N_full=7500,huber_delta=1.35,l2=50.0; N_min=3500,N_full=7500,huber_delta=1.50,l2=100.0; N_min=4000,N_full=8000,huber_delta=1.35,l2=75.0; N_min=3000,N_full=7000,huber_delta=1.20,l2=100.0"
inputs: features.now_cost; features.position; history.n_eff_panel_rows; features.ml_panel_covariates
nearest_ledger_row: null
spec_path: ideas/EXT-05-price-stratified-huber-regularized-continuous-n-text-eff-causal-panel.md
---

# EXT-05: Price-Stratified Huber-Regularized Continuous-N_{\text{eff}} Causal Panel

## 1. Concept & Football Hypothesis

ADR 0064 demonstrated that def_xg_shrink_challenger beat adaptive_causal_challenger by +0.8947 pts/GW under the £83.5m Constrained Legal Formation XI. The root cause is two-fold: (1) adaptive_causal_challenger fits its GW 20+ Ridge event residual models globally across all price tiers using squared error, allowing high-variance £10.0m+ premium assets to dominate gradient updates and induce systematic residual bias in the £4.5m–£5.8m budget enabler pool; and (2) the discrete GW 20 ramp ignores effective panel sample size N_{\text{eff}} across warm-seeded seasons. Stratifying feature standardization and residual zero-centering within position-by-price tiers while replacing squared error with Huber loss (\delta = 1.35) and continuous N_{\text{eff}} blending fixes budget enabler misranking.
## 2. Mathematical Formulation

Partition outfield players into 3 price-tier buckets b(i) \in \{\text{Budget } (\le £5.5\text{m}), \text{Mid } (£5.6\text{m}\text{--}£7.9\text{m}), \text{Premium } (\ge £8.0\text{m})\}. For causal panel target residual r_{i,t} = y_{i,t} - \hat{y}_{i,t}^{\text{EB}}, estimate parameters \hat{\boldsymbol{\beta}} via L2-penalized Huber loss to bound the influence of multi-goal outlier hauls:
   
   $$\hat{\boldsymbol{\beta}}_g = \arg\min_{\boldsymbol{\beta}} \sum_{t \lt g} \sum_{i} \omega^{g-t} \mathcal{L}_{\delta}\left(r_{i,t} - \mathbf{x}_{i,t}^\top \boldsymbol{\beta}\right) + \lambda_{\text{ridge}} \Vert{}\boldsymbol{\beta}\Vert{}_2^2$$
   
   Enforce zero-mean residual conservation within each price tier b on playable assets (\text{xMins}_{i,g} \ge 45):
   
   $$\tilde{\Delta}_{i,g}^{\text{ML}} = \mathbf{x}_{i,g}^\top \hat{\boldsymbol{\beta}}_g - \frac{1}{\vert{}\mathcal{P}_{b(i), g}\vert{}} \sum_{j \in \mathcal{P}_{b(i), g}} \mathbf{x}_{j,g}^\top \hat{\boldsymbol{\beta}}_g$$
   
   Blend continuously via effective sample size N_{\text{eff}, g} = 0.5 N_{\text{seed}} + N_{\text{in\_season}, \lt g} (avoiding Dead Lever #7):
   
   $$\alpha(N_{\text{eff}, g}) = \text{clip}\left(\frac{N_{\text{eff}, g} - N_{\min}}{N_{\text{full}} - N_{\min}}, 0.0, 1.0\right), \quad \hat{y}_{i,g} = \hat{y}_{i,g}^{\text{EB}} + \alpha(N_{\text{eff}, g}) \tilde{\Delta}_{i,g}^{\text{ML}}$$
## 3. Decoupled Architecture Placement

Operates across both M_{\text{mins}} (H1 start probability, H3 duration offset) and M_{\text{events}} (Group A xG residual).
## 4. Replaces / Integration Hook

Replaces the global Ridge regression fit and GW 20 step ramp in AdaptiveCausalChallengerModel._compute_ml_blend_weight and MLComponentChallengerModel._fit_predict_panel_heads.
## 5. Parameter Sweep Grid

N_min=3500,N_full=7500,huber_delta=1.35,l2=50.0; N_min=3500,N_full=7500,huber_delta=1.50,l2=100.0; N_min=4000,N_full=8000,huber_delta=1.35,l2=75.0; N_min=3000,N_full=7000,huber_delta=1.20,l2=100.0
## 6. Small-Sample & Cold-Start Strategy

Directly implements ADR 0064 / Issue #168 continuous N_{\text{eff}} shrinkage with N_{\min}=3500 and N_{\text{full}}=7500. In an unseeded cold start, \alpha(N_{\text{eff}, g}) = 0.0 throughout cold_start and early early_mid, guaranteeing 100% def_xg_shrink_challenger parity when sample size is small, while smoothly activating as panel observations cross N_{\min}.
## 7. Budget-Constrained Optimizer Interaction

Within-tier zero-mean centering \tilde{\Delta}_{i,g}^{\text{ML}} mathematically guarantees that the ML adjustment cannot systematically inflate £10m+ players relative to £5.0m players, nor violate the Playable Pool Bias guardrail (\vert{}\text{Bias}_{\text{cand}}\vert{} \le \vert{}\text{Bias}_{\text{champ}}\vert{} + 0.01). It strictly re-ranks players within their budget peer group, directly optimizing the £83.5m Constrained Legal Formation XI.
## 8. Point-in-Time Feature Requirements

features.now_cost; features.position; history.n_eff_panel_rows; features.ml_panel_covariates
## 9. Python Code Skeleton

```python
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.linear_model import HuberRegressor
from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel


class PriceStratifiedHuberPanelChallengerModel(AdaptiveCausalChallengerModel):
    """Replaces global Ridge + GW20 ramp with continuous N_eff Huber panel and price-tier centering."""

    def __init__(
        self,
        n_min: float = 3500.0,
        n_full: float = 7500.0,
        huber_delta: float = 1.35,
        l2_alpha: float = 75.0,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.n_min = float(n_min)
        self.n_full = float(n_full)
        self.huber_delta = float(huber_delta)
        self.l2_alpha = float(l2_alpha)

    def _compute_continuous_neff_weight(self, n_eff: float) -> float:
        if n_eff <= self.n_min:
            return 0.0
        return float(np.clip((n_eff - self.n_min) / (self.n_full - self.n_min), 0.0, 1.0))

    @staticmethod
    def _assign_price_tier(cost_tenths: pd.Series) -> pd.Series:
        return pd.cut(
            cost_tenths,
            bins=[-np.inf, 55.0, 79.0, np.inf],
            labels=["budget", "mid", "premium"],
        )

    def _center_residuals_by_price_tier(
        self,
        df: pd.DataFrame,
        raw_ml_delta: pd.Series,
        playable_mask: pd.Series,
    ) -> pd.Series:
        tiers = self._assign_price_tier(df["now_cost"])
        centered = raw_ml_delta.copy()
        for tier_label in ["budget", "mid", "premium"]:
            mask = (tiers == tier_label) & playable_mask
            if mask.any():
                tier_mean = raw_ml_delta.loc[mask].mean()
                centered.loc[tiers == tier_label] -= tier_mean
        return centered
```
