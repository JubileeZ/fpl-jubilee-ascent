---
idea_id: EXT-15
name: "Territorial Possession-Tilt & Deep-Block Defcon Elasticity"
tier: P1
component: xp_defcon
status: untested
replaces: DefXgShrinkChallengerModel.predict (modifying per90_defensive_contribution prior to CalibratedMatchupHybridModel._project_event_components).
grid: "k_defcon=900,gamma_siege=0.18; k_defcon=1200,gamma_siege=0.18; k_defcon=1200,gamma_siege=0.25; k_defcon=1500,gamma_siege=0.22; k_defcon=900,gamma_siege=0.25; k_defcon=1500,gamma_siege=0.15"
inputs: features.player_id; features.club_id; features.opponent_id; features.position_id; features.fixture_id; features.gameweek_id; features.per90_defensive_contribution; features.n_starts_historical; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.minutes; history.defensive_contribution; history.creativity
nearest_ledger_row: null
spec_path: ideas/EXT-15-territorial-possession-tilt-deep-block-defcon-elasticity.md
---

# EXT-15: Territorial Possession-Tilt & Deep-Block Defcon Elasticity

## 1. Concept & Football Hypothesis

In `features/matchup_share.py` (line 315) and `CalibratedMatchupHybridModel._project_event_components` (line 109), defensive contributions (`per90_defensive_contribution`) are completely decoupled from opponent territorial context (`defence_multiplier = 1.0`), while builder's `per90_defensive_contribution` uses a uniform $4 \times 90 = 360$ pseudo-minute shrinkage. In physical football, outfield players accumulate clearances, blocks, interceptions, and tackles (`defensive_contribution`) when their team is pinned in a low block by an opponent with high sustained final-third pass/delivery volume (`creativity`) relative to the player's own club. Because the +2 pt FPL defcon award is a step threshold at $\ge 10$ (DEF) or $\ge 12$ (MID/FWD) modeled via $\text{NegBin}(\lambda_{\text{defcon}}, r)$, combining higher player-level Empirical Bayes shrinkage ($K_{\text{defcon}} \in [900, 1500]$) with opponent-vs-own creative siege tilt yields marginal expected value for £4.5m–£5.0m center-backs and defensive midfielders without inflating clean sheet projections.

## 2. Mathematical Formulation

First, replace the noisy 360-minute builder defcon rate for outfield players with an Empirical Bayes shrinkage rate over $K_{\text{defcon}}$ pseudo-minutes from pre-deadline history $\mathcal{H}_{<g}$:
   $$\hat{\lambda}_{\text{defcon}, i}^{0}(g) = \frac{\sum_{m \in \mathcal{H}_{i,<g}} w_m \cdot \text{defcon}_{i,m} + K_{\text{defcon}} \cdot \frac{\bar{d}_{\text{pos}(i)}}{90}}{\sum_{m \in \mathcal{H}_{i,<g}} w_m \cdot \text{minutes}_{i,m} + K_{\text{defcon}}} \times 90.0$$
   Second, for each club $c$, compute the as-of shrunk per-match final-third creation volume $\hat{C}_c(g)$ from summed club `creativity` per match in $\mathcal{H}_{<g}$ shrunk by $K_{\text{club}} = 6.0$ matches toward the league mean $\bar{C}_{\text{league}}(g)$. Define the **Territorial Siege Tilt** for club $c$ facing opponent $o$:
   $$\mathcal{S}_{c,o}(g) = \log\left(\frac{\hat{C}_o(g) + \bar{C}_{\text{league}}(g)}{\hat{C}_c(g) + \bar{C}_{\text{league}}(g)}\right)$$
   When $\mathcal{S}_{c,o}(g) > 0$, opponent $o$ dominates final-third territorial possession against club $c$. The expected defcon count over state minutes $M_s$ is:
   $$\lambda_{\text{defcon}, i, f}(M_s) = \hat{\lambda}_{\text{defcon}, i}^{0}(g) \cdot \frac{M_s}{90.0} \cdot \exp\left(\omega(N_{\text{eff}, g}) \cdot \gamma_{\text{siege}} \cdot \text{clip}\left(\mathcal{S}_{c,o}(g), -0.60, +0.60\right)\right)$$
   Passed through the exact Champion Negative Binomial tail complement:
   $$P(\text{Defcon}_{i,f} \ge \tau_{\text{pos}} \mid M_s) = 1 - F_{\text{NB}}\left(\tau_{\text{pos}} - 1 \;;\; \lambda_{\text{defcon}, i, f}(M_s), r_{\text{pos}}\right)$$
   where $\tau_{\text{D}}=10, r_{\text{D}}=8.5$ and $\tau_{\text{M,F}}=12, r_{\text{M,F}}=7.0$.

## 3. Decoupled Architecture Placement

Operates in $M_{\text{events}}$ (`xp_defcon` and downstream `xbps` / `xp_bonus`), leaving `xp_clean_sheet` and `xp_conceded` untouched.

## 4. Replaces / Integration Hook

`DefXgShrinkChallengerModel.predict` (modifying `per90_defensive_contribution` prior to `CalibratedMatchupHybridModel._project_event_components`).

## 5. Parameter Sweep Grid

`k_defcon=900,gamma_siege=0.18; k_defcon=1200,gamma_siege=0.18; k_defcon=1200,gamma_siege=0.25; k_defcon=1500,gamma_siege=0.22; k_defcon=900,gamma_siege=0.25; k_defcon=1500,gamma_siege=0.15`

## 6. Small-Sample & Cold-Start Strategy

Player defcon rates shrink with $K_{\text{defcon}} \in [900, 1500]$ pseudo-minutes (2.5x to 4.2x stronger than builder's 360-minute default) to suppress early-season fluke tackle spikes. The territorial siege tilt $\mathcal{S}_{c,o}(g)$ is shrunk with $K_{\text{club}}=6.0$ matches and gated by continuous sample shrinkage $\omega(N_{\text{eff}, g})$ ($N_{\min}=3500, N_{\text{full}}=7500$).

## 7. Budget-Constrained Optimizer Interaction

Directly increases the accuracy of £4.5m center-backs and £5.0m defensive midfielders ("ball-recovery magnets" such as Caicedo, Tarkowski, Murillo) who play 90 minutes for low-possession or mid-table clubs. Under the £83.5m Constrained XI cap, accurately valuing their +2 pt defcon probability in siege matches prevents the solver from wasting budget on overpriced mid-tier defenders while keeping squad churn low because $K_{\text{defcon}} \ge 900$ stabilizes weekly rankings.

## 8. Point-in-Time Feature Requirements

`features.player_id`; `features.club_id`; `features.opponent_id`; `features.position_id`; `features.fixture_id`; `features.gameweek_id`; `features.per90_defensive_contribution`; `features.n_starts_historical`; `history.player_id`; `history.fixture_id`; `history.gameweek_id`; `history.opponent_club_id`; `history.minutes`; `history.defensive_contribution`; `history.creativity`

## 9. Python Code Skeleton (Optional)

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

_DECAY = 0.95
_REQ_COLS = (
    "player_id", "fixture_id", "gameweek_id", "opponent_club_id",
    "minutes", "defensive_contribution", "creativity",
)


class TerritorialDefconElasticityChallengerModel(DefXgShrinkChallengerModel):
    """DefXgShrink Champion + EB defcon shrinkage (K_defcon) + territorial possession-tilt elasticity."""

    def __init__(
        self,
        k_defcon: float = 1200.0,
        gamma_siege: float = 0.20,
        club_k: float = 6.0,
        n_min: float = 3500.0,
        n_full: float = 7500.0,
    ) -> None:
        super().__init__()
        self.k_defcon = float(k_defcon)
        self.gamma_siege = float(gamma_siege)
        self.club_k = float(club_k)
        self.n_min = float(n_min)
        self.n_full = float(n_full)
        self._defcon_hist = pd.DataFrame()

    @property
    def name(self) -> str:
        return "territorial_defcon_elasticity_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if history_df.empty or not set(_REQ_COLS).issubset(history_df.columns):
            self._defcon_hist = pd.DataFrame()
            return
        self._defcon_hist = history_df[list(_REQ_COLS)].apply(pd.to_numeric, errors="coerce").fillna(0.0)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._defcon_hist.empty or features_df.empty:
            return super().predict(features_df, horizon)
        target_gw = resolve_asof_target_gw(features_df, self._defcon_hist)
        prior = self._defcon_hist[(self._defcon_hist["gameweek_id"] < target_gw) & (self._defcon_hist["minutes"] > 0)]
        if prior.empty:
            return super().predict(features_df, horizon)

        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        pos = prior["player_id"].map(positions).fillna(3)
        by_pos = prior.groupby(pos)[["defensive_contribution", "minutes"]].sum()
        pos_rate = (by_pos["defensive_contribution"] / by_pos["minutes"].clip(lower=1.0) * 90.0).to_dict()

        last = prior.groupby("player_id")["gameweek_id"].transform("max")
        w = _DECAY ** (last - prior["gameweek_id"])
        sums = pd.DataFrame({
            "dc": prior["defensive_contribution"] * w,
            "mins": prior["minutes"] * w,
            "player_id": prior["player_id"],
        }).groupby("player_id").sum()

        p_pos = positions.reindex(sums.index).fillna(3)
        p_prior = p_pos.map(pos_rate).fillna(0.0)
        rate_k = (sums["dc"] + self.k_defcon * p_prior / 90.0) / (sums["mins"] + self.k_defcon) * 90.0
        rate_360 = (sums["dc"] + 360.0 * p_prior / 90.0) / (sums["mins"] + 360.0) * 90.0
        ratio = (rate_k / rate_360.where(rate_360 > 1e-6)).fillna(1.0).clip(0.3, 3.0)

        sides = prior.groupby("fixture_id")["opponent_club_id"].agg(["min", "max"])
        fx = prior.join(sides, on="fixture_id")
        fx = fx[fx["min"] != fx["max"]]
        fx = fx.assign(club=fx["min"] + fx["max"] - fx["opponent_club_id"])
        club_cre = fx.groupby(["fixture_id", "club"], as_index=False)["creativity"].sum()
        league_cre = max(10.0, float(club_cre["creativity"].mean())) if not club_cre.empty else 100.0
        c_grp = club_cre.groupby("club").agg(n=("creativity", "size"), cre=("creativity", "sum"))
        cre_map = ((c_grp["cre"] + self.club_k * league_cre) / (c_grp["n"] + self.club_k)).to_dict()

        n_seed = float(features_df.drop_duplicates("player_id").get("n_starts_historical", pd.Series(0.0)).sum())
        n_eff = 0.5 * n_seed + float(len(prior))
        omega = float(np.clip((n_eff - self.n_min) / max(1.0, self.n_full - self.n_min), 0.0, 1.0))

        feat = features_df.copy()
        own_c = feat["club_id"].map(cre_map).fillna(league_cre).to_numpy(float)
        opp_c = feat["opponent_id"].map(cre_map).fillna(league_cre).to_numpy(float)
        siege = np.clip(np.log((opp_c + league_cre) / (own_c + league_cre)), -0.60, 0.60)
        valid = (feat["fixture_id"] >= 0) & (feat["position_id"] != 1)
        siege_mult = np.where(valid, np.exp(omega * self.gamma_siege * siege), 1.0)
        eb_mult = feat["player_id"].map(ratio).fillna(1.0).to_numpy(float)
        feat["per90_defensive_contribution"] = (
            pd.to_numeric(feat["per90_defensive_contribution"], errors="coerce").fillna(0.0).to_numpy(float)
            * eb_mult
            * siege_mult
        )
        return super().predict(feat, horizon)
```

---
