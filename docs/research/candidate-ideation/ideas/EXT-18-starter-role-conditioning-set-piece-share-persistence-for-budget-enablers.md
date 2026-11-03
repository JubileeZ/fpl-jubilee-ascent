---
idea_id: EXT-18
name: "Starter-Role Conditioning & Set-Piece Share Persistence for Budget Enablers"
tier: P1
component: xp_goals
status: untested
replaces: "DefXgShrinkChallengerModel.predict (shrunk_xg_rates generalized to role-conditioned attacker prior while preserving _POSITION_K = {2: 2400.0})."
grid: "k_atk=540,gamma_role=0.15; k_atk=540,gamma_role=0.22; k_atk=630,gamma_role=0.18; k_atk=720,gamma_role=0.20; k_atk=450,gamma_role=0.15; k_atk=630,gamma_role=0.12"
inputs: features.player_id; features.club_id; features.position_id; features.now_cost; features.per90_xg; features.per90_creativity; history.player_id; history.gameweek_id; history.minutes; history.starts; history.expected_goals; history.creativity
nearest_ledger_row: null
spec_path: ideas/EXT-18-starter-role-conditioning-set-piece-share-persistence-for-budget-enablers.md
---

# EXT-18: Starter-Role Conditioning & Set-Piece Share Persistence for Budget Enablers

## 1. Concept & Football Hypothesis

Under the ADR 0064 Constrained Legal Formation XI gate (£83.5m budget cap, $\le 3$ per club), the primary source of predictive alpha (`def_xg_shrink_challenger` beating `adaptive_causal_challenger` by $+0.8947$ pts/GW on Dev) is accurately ranking £4.0m–£5.5m budget starters. However, inspect `features/builder.py` (lines 681–726) and `DefXgShrinkChallengerModel` (`shrunk_xg_rates`):
   - Builder shrinks every player's `per90_*` rates with $4 \times 90 = 360$ pseudo-minutes toward a `price_band` prior (`_compute_position_price_priors`) computed over *all* appearances in that price band—where £4.5m–£5.0m price bands are heavily diluted by substitute cameos and defensive utility players.
   - Furthermore, for midfielders and forwards ($K=360$), builder's `per90_xg` and `per90_xa` treat a newly-nailed £5.0m starter who takes corners/free-kicks (high `creativity` share of club total) identically to a low-involvement winger whose early xG came from a single random scramble.
   By conditioning the Empirical Bayes prior for midfielders and forwards ($position\_id \in \{3, 4\}$) on **Verified Starter Role & Club Creative Share** (while keeping defender $K_{\text{DEF}}=2400$ xG shrinkage strictly intact), we eliminate the systematic downward prior drag on nailed £4.5m–£5.5m starters and stabilize open-play xG/xA estimates against cameo noise.

## 2. Mathematical Formulation

For outfield attackers ($position\_id \in \{3, 4\}$), partition pre-deadline historical appearances $\mathcal{H}_{<g}$ into verified starts ($\text{starts}_{i,m} = 1, \text{minutes}_{i,m} \ge 60$) vs bench cameos. Compute each player's shrunk **Club Creative Involvement Share** $\hat{\sigma}_{\text{cre}, i}(g)$ among active starters on club $c$:
   $$\hat{\sigma}_{\text{cre}, i}(g) = \frac{\sum_{m \in \mathcal{H}_{i,<g}} w_m \cdot \text{creativity}_{i,m} + K_{\text{cre}} \cdot \bar{\sigma}_{\text{pos}(i)} \bar{C}_{c}}{\sum_{m \in \mathcal{H}_{c,<g}} w_m \cdot \text{creativity}_{c,m} + K_{\text{cre}} \cdot \bar{C}_{c}}$$
   Rather than shrinking a nailed budget starter's `per90_xg` and `per90_xa` toward an unconditioned position-price mean diluted by bench fodder, construct a **Role-Conditioned Prior** $\pi_{xG, i}(g)$ for $position\_id \in \{3, 4\}$:
   $$\pi_{xG, i}(g) = \bar{\lambda}_{xG, \text{pos}(i)}^{\text{starter}}(g) \cdot \left(1.0 + \gamma_{\text{role}} \cdot \frac{\hat{\sigma}_{\text{cre}, i}(g) - \bar{\sigma}_{\text{pos}(i)}}{\bar{\sigma}_{\text{pos}(i)}}\right)$$
   where $\bar{\lambda}_{xG, \text{pos}(i)}^{\text{starter}}(g)$ is the pooled xG/90 across verified $\ge 60$-minute starts in position $\text{pos}(i)$. Re-shrink attacker `per90_xg` with $K_{\text{ATK}} \in [450, 720]$ pseudo-minutes toward $\pi_{xG, i}(g)$ (keeping $K_{\text{DEF}}=2400$ toward $\bar{\lambda}_{xG, \text{DEF}}$ untouched):
   $$\hat{\lambda}_{xG, i}^{\text{role}}(g) = \frac{\sum_{m \in \mathcal{H}_{i,<g}} w_m \cdot xG_{i,m} + K_{\text{ATK}} \cdot \frac{\pi_{xG, i}(g)}{90.0}}{\sum_{m \in \mathcal{H}_{i,<g}} w_m \cdot \text{minutes}_{i,m} + K_{\text{ATK}}} \times 90.0$$

## 3. Decoupled Architecture Placement

Operates in $M_{\text{events}}$ (`xp_goals`, `xp_assists`, and `xbps` / `xp_bonus`).

## 4. Replaces / Integration Hook

`DefXgShrinkChallengerModel.predict` (`shrunk_xg_rates` generalized to role-conditioned attacker prior while preserving `_POSITION_K = {2: 2400.0}`).

## 5. Parameter Sweep Grid

`k_atk=540,gamma_role=0.15; k_atk=540,gamma_role=0.22; k_atk=630,gamma_role=0.18; k_atk=720,gamma_role=0.20; k_atk=450,gamma_role=0.15; k_atk=630,gamma_role=0.12`

## 6. Small-Sample & Cold-Start Strategy

Uses the exact `DefXgShrinkChallengerModel` ratio replacement pattern (`new_rate / old_rate_360`) so that builder's warm historical seed prior (`seed_season`) and `apply_matchup_share_overlay` additive deltas survive intact at GW1–4, while smoothly transitioning to role-conditioned shrinkage as in-season minutes accumulate.

## 7. Budget-Constrained Optimizer Interaction

Directly optimizes selection within the £4.5m–£5.8m MID/FWD enabler tier under the £83.5m Constrained XI cap. Budget starters who command set-piece and creative volume (high $\hat{\sigma}_{\text{cre}, i}$) retain their true underlying prior instead of being dragged down to bench-fodder price-band averages, while one-game fluke scorers with low creative involvement are shrunk with $K_{\text{ATK}} = 540\text{--}720 > 360$, cutting squad churn and Optimizer's Curse regret.

## 8. Point-in-Time Feature Requirements

`features.player_id`; `features.club_id`; `features.position_id`; `features.now_cost`; `features.per90_xg`; `features.per90_creativity`; `history.player_id`; `history.gameweek_id`; `history.minutes`; `history.starts`; `history.expected_goals`; `history.creativity`

## 9. Python Code Skeleton (Optional)

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import (
    _BASE_K,
    _DECAY,
    _MIDFIELDER,
    _POSITION_K,
    _RATIO_CLIP,
    DefXgShrinkChallengerModel,
    shrunk_xg_rates,
)

_ROLE_HIST_COLS = ("player_id", "gameweek_id", "minutes", "expected_goals", "creativity")


class BudgetRolePriorChallengerModel(DefXgShrinkChallengerModel):
    """DefXgShrink Champion (DEF K=2400) + role-conditioned creative-share xG shrinkage for MID/FWD."""

    def __init__(self, k_atk: float = 540.0, gamma_role: float = 0.18) -> None:
        super().__init__()
        self.k_atk = float(k_atk)
        self.gamma_role = float(gamma_role)
        self._role_hist = pd.DataFrame(columns=list(_ROLE_HIST_COLS))

    @property
    def name(self) -> str:
        return "budget_role_prior_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if history_df.empty or not set(_ROLE_HIST_COLS).issubset(history_df.columns):
            self._role_hist = pd.DataFrame(columns=list(_ROLE_HIST_COLS))
            return
        hist = history_df[list(_ROLE_HIST_COLS)].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        self._role_hist = hist[hist["minutes"] > 0]

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._role_hist.empty or features_df.empty:
            return super().predict(features_df, horizon)
        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        hist = self._role_hist
        pos = hist["player_id"].map(positions).fillna(_MIDFIELDER)
        by_pos = hist.groupby(pos)[["expected_goals", "creativity", "minutes"]].sum()
        pos_xg_rate = (by_pos["expected_goals"] / by_pos["minutes"].clip(lower=1.0) * 90.0).to_dict()
        pos_cre_rate = (by_pos["creativity"] / by_pos["minutes"].clip(lower=1.0) * 90.0).to_dict()

        last = hist.groupby("player_id")["gameweek_id"].transform("max")
        weight = _DECAY ** (last - hist["gameweek_id"])
        sums = pd.DataFrame({
            "xg": hist["expected_goals"] * weight,
            "cre": hist["creativity"] * weight,
            "mins": hist["minutes"] * weight,
            "player_id": hist["player_id"],
        }).groupby("player_id").sum()

        player_pos = positions.reindex(sums.index).fillna(_MIDFIELDER)
        base_prior = player_pos.map(pos_xg_rate).fillna(0.0)
        cre_prior = player_pos.map(pos_cre_rate).fillna(10.0)
        shrunk_cre = (sums["cre"] + 360.0 * cre_prior / 90.0) / (sums["mins"] + 360.0) * 90.0
        rel_cre = np.clip((shrunk_cre - cre_prior) / cre_prior.clip(lower=1.0), -0.5, 1.5)

        is_atk = player_pos.isin([3, 4])
        adj_prior = np.where(is_atk, base_prior * (1.0 + self.gamma_role * rel_cre), base_prior)
        k_map = {2: _POSITION_K[2], 3: self.k_atk, 4: self.k_atk}
        k_vec = player_pos.map(k_map).fillna(_BASE_K)
        new_rates = (sums["xg"] + k_vec * adj_prior / 90.0) / (sums["mins"] + k_vec) * 90.0
        old_rates = shrunk_xg_rates(self._xg_hist, positions, {})
        ratio = (new_rates / old_rates.where(old_rates > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)

        features = features_df.copy()
        features["per90_xg"] = features["per90_xg"] * features["player_id"].map(ratio).fillna(1.0).to_numpy()
        return super(DefXgShrinkChallengerModel, self).predict(features, horizon)
```

---
