---
idea_id: EXT-02
name: "State-Decoupled Cameo Event Intensity & Late-Game Fatigue Scaling"
tier: P1
component: xp_goals
status: dead-match
replaces: Modifies minute-scaling of event rates inside ParticipationStateHybridModel._project_event_components where xmins / 90.0 currently scales xg_per_90 and xa_per_90 uniformly.
grid: "K_sub=450,gamma_fwd=1.25,gamma_mid=1.15,gamma_def=0.70; K_sub=450,gamma_fwd=1.35,gamma_mid=1.20,gamma_def=0.65; K_sub=600,gamma_fwd=1.30,gamma_mid=1.18,gamma_def=0.65; K_sub=360,gamma_fwd=1.25,gamma_mid=1.15,gamma_def=0.75"
inputs: features.position; history.sub_minutes_cum; history.start_minutes_cum; history.sub_xg_cum; history.sub_xa_cum; history.prior_season_sub_minutes; history.prior_season_sub_xg
nearest_ledger_row: Assist finishing offsets (goals+assists pooled)
spec_path: ideas/EXT-02-state-decoupled-cameo-event-intensity-late-game-fatigue-scaling.md
---

# EXT-02: State-Decoupled Cameo Event Intensity & Late-Game Fatigue Scaling

## 1. Concept & Football Hypothesis

The Champion computes expected goals and assists by multiplying a player's pooled per-90 event rate by total expected minutes: \mathbb{E}[\text{Events}] = (\mathbb{E}[\text{Mins}] / 90.0) \cdot \hat{\lambda}_{90}. This assumes 18 minutes off the bench carry the exact same per-minute scoring intensity as 78 minutes from the start. In reality, substitute minutes occur almost exclusively after minute 65 against fatigued opposition defensive blocks and during skewed game states (attackers are subbed on when trailing or drawing to chase goals; defenders are subbed on to protect leads and run down the clock). Empirically, Premier League attacking substitutes generate \approx 1.30\times to 1.45\times higher xG+xA per 90 than starters, whereas defensive substitutes generate near-zero attacking involvement.
## 2. Mathematical Formulation

Decompose total expected minutes into starter volume V_{\text{start}, i} = P_i(\text{Start}) \cdot \frac{\text{xMins}_{\text{start}, i}}{90.0} and sub-in volume V_{\text{sub}, i} = P_i(\text{Sub}) \cdot \frac{\text{xMins}_{\text{sub}, i}}{90.0}. Let \hat{\lambda}_{i, 90}^{(e)} be the baseline Empirical Bayes per-90 rate for event e \in \{\text{xG}, \text{xA}\}. Define the position-specific cameo intensity multiplier \psi_{i, e}:
   
   $$\psi_{i, e}(g) = \frac{\sum_{t \lt g} \mathbb{I}(\text{Sub}_{i,t}=1) E_{i,e,t} \cdot 90.0 + K_{\text{sub}} (\gamma_{\text{pos}(i), e} \cdot \hat{\lambda}_{i, 90}^{(e)})}{\sum_{t \lt g} \mathbb{I}(\text{Sub}_{i,t}=1) \text{Mins}_{i,t} + K_{\text{sub}}}$$
   
   where \gamma_{\text{pos}, e} is the structural positional cameo multiplier (\gamma_{\text{FWD}} = 1.32, \gamma_{\text{MID}} = 1.20, \gamma_{\text{DEF}} = 0.65, \gamma_{\text{GKP}} = 1.00) and K_{\text{sub}} = 450 pseudo-sub-minutes prevents small-sample cameo explosions (respecting Dead Lever #2). To preserve global playable pool bias neutrality, starter intensity is conservation-adjusted over historical start/sub shares w_{\text{sub}, i} = \frac{\text{SubMins}_i}{\text{TotalMins}_i + K_{\text{pool}}}:
   
   $$\mathbb{E}[E_{i, e}] = V_{\text{start}, i} \cdot \hat{\lambda}_{i, 90}^{(e)} \left(\frac{1.0}{1.0 + w_{\text{sub}, i}(\gamma_{\text{pos}(i), e} - 1.0)}\right) + V_{\text{sub}, i} \cdot \psi_{i, e}(g)$$
## 3. Decoupled Architecture Placement

Operates in M_{\text{events}} (xp_goals, xp_assists), interacting with state probabilities from M_{\text{mins}}.
## 4. Replaces / Integration Hook

Modifies minute-scaling of event rates inside ParticipationStateHybridModel._project_event_components where xmins / 90.0 currently scales xg_per_90 and xa_per_90 uniformly.
## 5. Parameter Sweep Grid

K_sub=450,gamma_fwd=1.25,gamma_mid=1.15,gamma_def=0.70; K_sub=450,gamma_fwd=1.35,gamma_mid=1.20,gamma_def=0.65; K_sub=600,gamma_fwd=1.30,gamma_mid=1.18,gamma_def=0.65; K_sub=360,gamma_fwd=1.25,gamma_mid=1.15,gamma_def=0.75
## 6. Small-Sample & Cold-Start Strategy

Because K_{\text{sub}} = 450 minutes represents \approx 25 substitute appearances, no single 10-minute cameo goal can inflate \psi_{i,e} (avoiding Dead Lever #2). In cold_start and early_mid, \psi_{i,e}(g) is dominated by the prior \gamma_{\text{pos}(i), e} \cdot \hat{\lambda}_{i, 90}^{(e)}, ensuring zero early-season overfitting while accurately devaluing defensive bench cameos from GW1.
## 7. Budget-Constrained Optimizer Interaction

Under the £83.5m cap and ADR 0061 starter minutes floor (\ge 65.0 mins), the solver relies on v_b \approx 0.10 bench weights and evaluates £5.0m–£5.8m budget attackers. Conservation-adjusting starter rates strips out "super-sub" rate inflation from players transitioning from bench impact roles into starting lineups, preventing the optimizer from over-projecting high-per-90 cameo merchants when they are projected for 70+ minutes.
## 8. Point-in-Time Feature Requirements

features.position; history.sub_minutes_cum; history.start_minutes_cum; history.sub_xg_cum; history.sub_xa_cum; history.prior_season_sub_minutes; history.prior_season_sub_xg
## 9. Python Code Skeleton

```python
from __future__ import annotations
import pandas as pd
from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel


class StateDecoupledCameoChallengerModel(AdaptiveCausalChallengerModel):
    """Decouples starter vs substitute per-minute event intensities with EB shrinkage."""

    POS_CAMEO_GAMMA: dict[str, float] = {
        "GKP": 1.00,
        "DEF": 0.65,
        "MID": 1.20,
        "FWD": 1.32,
    }

    def __init__(
        self,
        k_sub_mins: float = 450.0,
        k_pool_mins: float = 900.0,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.k_sub_mins = float(k_sub_mins)
        self.k_pool_mins = float(k_pool_mins)

    def _compute_state_weighted_exposure(
        self,
        df: pd.DataFrame,
        p_start: pd.Series,
        p_sub: pd.Series,
        xmins_start: pd.Series,
        xmins_sub: pd.Series,
        base_rate_90: pd.Series,
        sub_event_cum_col: str,
    ) -> pd.Series:
        gamma = df["position"].map(self.POS_CAMEO_GAMMA).fillna(1.0)
        sub_mins = (
            0.5 * df.get("prior_season_sub_minutes", 0.0).fillna(0.0)
            + df.get("sub_minutes_cum", 0.0).fillna(0.0)
        )
        total_mins = sub_mins + df.get("start_minutes_cum", 0.0).fillna(0.0)
        sub_events = df.get(sub_event_cum_col, 0.0).fillna(0.0)

        prior_sub_rate = gamma * base_rate_90
        eb_sub_rate = (sub_events * 90.0 + self.k_sub_mins * prior_sub_rate) / (
            sub_mins + self.k_sub_mins
        )

        w_sub = sub_mins / (total_mins + self.k_pool_mins)
        starter_adj = 1.0 / (1.0 + w_sub * (gamma - 1.0))
        adj_start_rate = base_rate_90 * starter_adj

        v_start = p_start * (xmins_start / 90.0)
        v_sub = p_sub * (xmins_sub / 90.0)
        return v_start * adj_start_rate + v_sub * eb_sub_rate
```

## Ledger Audit & Revisit Justification
- **Flagged Match**: `Assist finishing offsets (goals+assists pooled)`
- **Audit Status**: Pending Review
- **Rationale**: [Document why this proposal is structurally distinct from the flagged dead lever before promoting to status: untested]
