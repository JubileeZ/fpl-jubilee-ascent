---
idea_id: EXT-01
name: "Asymmetric Conditional Substitution Hazard & Beta-Binomial 60-Minute Survival"
tier: P1
component: xp_minutes
status: dead-match
replaces: Replaces the linear p_60_plus_given_start calculation inside ParticipationStateHybridModel._compute_participation_states and updates H3 duration-to-threshold mapping in AdaptiveCausalChallengerModel.
grid: "K_surv=12,beta_surv=0.5,H_half=19; K_surv=18,beta_surv=0.65,H_half=19; K_surv=24,beta_surv=0.65,H_half=38; K_surv=18,beta_surv=0.80,H_half=19; K_surv=30,beta_surv=0.50,H_half=38"
inputs: features.position; features.chance_of_playing; history.minutes_ped_lag1; history.starts_ewm_19; history.sixty_plus_given_start_ewm_19; history.prior_season_starts; history.prior_season_sixty_plus_starts
nearest_ledger_row: Apex Predator Challenger (Composite ML p_start + start duration + shrunk xG goals + LOO assist finishing with GW1-9 Champion stability and schedule congestion)
spec_path: ideas/EXT-01-asymmetric-conditional-substitution-hazard-beta-binomial-60-minute-survival.md
---

# EXT-01: Asymmetric Conditional Substitution Hazard & Beta-Binomial 60-Minute Survival

## Checkpoint status (2026-10-28)

Screened against locked Dead lever; skipped, no new empirical run. Queue/ledger own mechanism match and revisit boundary. Current status: `idea_queue.csv` + Candidate Ledger. Proposal body below records original intake, not a current gate verdict.

## 1. Concept & Football Hypothesis

The Champion models 60-minute threshold survival P(60+ \mid \text{Start}) as a deterministic linear function of expected starter duration: \text{clip}((\text{xmins}_{\text{start}} - 45.0) / 30.0, 0.0, 1.0). This conflates mean duration with 60-minute boundary survival. In physical match play, center-backs and goalkeepers have near-zero tactical substitution hazard before minute 60 (exiting only via rare injury or red card), whereas wide forwards, attacking midfielders, and wing-backs face concentrated tactical hook hazard between minutes 55 and 65. Consequently, a budget center-back (£4.5m) and a rotation winger (£6.5m) with similar mean minutes have vastly different probabilities of banking the 2-point appearance and clean sheet eligibility threshold.
## 2. Mathematical Formulation

Let S_{i,t} \in \{0, 1\} denote starting match t, and Y_{i,t} = \mathbb{I}(\text{Minutes}_{i,t} \ge 60 \mid S_{i,t} = 1) denote conditional 60-minute survival. We model Y_{i,t} via a conjugate Beta-Binomial Empirical Bayes estimator anchored to a position-specific prior mean \mu_{0, \text{pos}} (e.g., \text{GKP}=0.97, \text{DEF}=0.91, \text{MID}=0.82, \text{FWD}=0.78) and pseudo-start concentration K_{\text{surv}}:
   
   $$N_{i, \text{starts}}(g) = \sum_{t \lt g} \omega^{g - t} S_{i,t}, \quad C_{i, 60}(g) = \sum_{t \lt g} \omega^{g - t} S_{i,t} Y_{i,t}$$
   $$\hat{\theta}_{i, 60 \mid \text{start}}(g) = \frac{C_{i, 60}(g) + K_{\text{surv}} \mu_{0, \text{pos}(i)}}{N_{i, \text{starts}}(g) + K_{\text{surv}}}$$
   
   where \omega = \exp(-\ln(2) / H_{\text{half}}) weights historical starts. We then blend the empirical survival rate with the duration-implied baseline via shrinkage weight \beta_{\text{surv}} \in [0, 1]:
   
   $$P_i(60+ \mid \text{Start}, g) = (1 - \beta_{\text{surv}}) \cdot \text{clip}\left(\frac{\widehat{\text{xMins}}_{\text{start}, i, g} - 45.0}{30.0}, 0.0, 1.0\right) + \beta_{\text{surv}} \cdot \hat{\theta}_{i, 60 \mid \text{start}}(g)$$
   
   Unconditional 60-minute probability becomes P_i(60+, g) = P_i(\text{Start}, g) \cdot P_i(60+ \mid \text{Start}, g) (since sub-in appearances exceeding 60 minutes are negligible and governed by early first-half injury substitutions).
## 3. Decoupled Architecture Placement

Operates in M_{\text{mins}} (xp_minutes), propagating directly into M_{\text{events}} (xp_clean_sheets) via the pitch clean sheet multiplier e^{-\lambda_{\text{pitch}}} \times P(60+).
## 4. Replaces / Integration Hook

Replaces the linear p_60_plus_given_start calculation inside ParticipationStateHybridModel._compute_participation_states and updates H3 duration-to-threshold mapping in AdaptiveCausalChallengerModel.
## 5. Parameter Sweep Grid

K_surv=12,beta_surv=0.5,H_half=19; K_surv=18,beta_surv=0.65,H_half=19; K_surv=24,beta_surv=0.65,H_half=38; K_surv=18,beta_surv=0.80,H_half=19; K_surv=30,beta_surv=0.50,H_half=38
## 6. Small-Sample & Cold-Start Strategy

Warm historical seeding (N_{\text{prior}}=1) initializes N_{i, \text{starts}} and C_{i, 60} from the prior season discounted by 0.50. For newly promoted or transferred players with N_{i, \text{starts}} = 0, \hat{\theta}_{i, 60 \mid \text{start}} collapses exactly to the positional prior \mu_{0, \text{pos}}, preventing early-season variance while scaling smoothly with N_{\text{eff}} as in-season starts accumulate.
## 7. Budget-Constrained Optimizer Interaction

Under the £83.5m Constrained Legal Formation XI and ADR 0061 Starter Minutes Floor (\text{xMins} \ge 65.0), this mechanism properly elevates nailed £4.5m center-backs (who play 90 minutes whenever starting) over £5.5m attacking fullbacks or wingers who get hooked at minute 58. Because \hat{\theta}_{i, 60 \mid \text{start}} is regularized with K_{\text{surv}} \ge 12 starts, week-to-week state probabilities remain smooth, keeping squad churn well below the +0.50 players/GW guardrail.
## 8. Point-in-Time Feature Requirements

features.position; features.chance_of_playing; history.minutes_ped_lag1; history.starts_ewm_19; history.sixty_plus_given_start_ewm_19; history.prior_season_starts; history.prior_season_sixty_plus_starts
## 9. Python Code Skeleton

```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel


class AsymmetricSubHazardChallengerModel(AdaptiveCausalChallengerModel):
    """Decouples P(60+ | Start) from linear mean duration via Beta-Binomial survival."""

    POS_SURVIVAL_PRIORS: dict[str, float] = {
        "GKP": 0.97,
        "DEF": 0.91,
        "MID": 0.82,
        "FWD": 0.78,
    }

    def __init__(
        self,
        k_surv: float = 18.0,
        beta_surv: float = 0.65,
        half_life_gws: float = 19.0,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.k_surv = float(k_surv)
        self.beta_surv = float(beta_surv)
        self.half_life_gws = float(half_life_gws)

    def _compute_conditional_60_plus(
        self,
        df: pd.DataFrame,
        xmins_start: pd.Series,
    ) -> pd.Series:
        linear_p60 = ((xmins_start - 45.0) / 30.0).clip(lower=0.0, upper=1.0)
        pos_prior = df["position"].map(self.POS_SURVIVAL_PRIORS).fillna(0.84)

        eff_starts = (
            0.5 * df.get("prior_season_starts", 0.0).fillna(0.0)
            + df.get("starts_ewm_19", 0.0).fillna(0.0)
        )
        eff_60_hits = (
            0.5 * df.get("prior_season_sixty_plus_starts", 0.0).fillna(0.0)
            + df.get("sixty_plus_given_start_ewm_19", 0.0).fillna(0.0)
        )

        eb_survival = (eff_60_hits + self.k_surv * pos_prior) / (
            eff_starts + self.k_surv
        )
        blended = (1.0 - self.beta_surv) * linear_p60 + self.beta_surv * eb_survival
        return blended.clip(lower=0.0, upper=1.0)
```

## Ledger Audit & Revisit Justification
- **Flagged Match**: `Apex Predator Challenger (Composite ML p_start + start duration + shrunk xG goals + LOO assist finishing with GW1-9 Champion stability and schedule congestion)`
- **Audit Status**: Cleared (False Positive)
- **Rationale**: False positive token overlap on `minutes`/`starts`/`duration`. The core mechanism is position-conditioned Beta-Binomial 60-min survival ($P(60+ \mid \text{Start})$), structurally distinct from Apex Predator's composite ML talisman regression. Cleared to `untested`.
