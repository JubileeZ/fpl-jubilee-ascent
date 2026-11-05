---
idea_id: EXT-19
name: "Opponent Speculative Shot-Volume & Goalkeeper Save-Floor Elasticity"
tier: P1
component: xp_saves
status: fail
replaces: "DefXgShrinkChallengerModel.predict (updating per90_saves for position_id == 1 prior to CalibratedMatchupHybridModel._project_event_components)."
grid: "k_gk=720,xi_saves=0.30; k_gk=720,xi_saves=0.45; k_gk=900,xi_saves=0.35; k_gk=900,xi_saves=0.50; k_gk=540,xi_saves=0.35; k_gk=1080,xi_saves=0.40"
inputs: features.player_id; features.club_id; features.opponent_id; features.position_id; features.fixture_id; features.gameweek_id; features.per90_saves; features.n_starts_historical; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.minutes; history.saves; history.threat
nearest_ledger_row: null
spec_path: ideas/EXT-19-opponent-speculative-shot-volume-goalkeeper-save-floor-elasticity.md
---

# EXT-19: Opponent Speculative Shot-Volume & Goalkeeper Save-Floor Elasticity

## 1. Concept & Football Hypothesis

Inspect `features/matchup_share.py` (lines 313–334) and `CalibratedMatchupHybridModel._project_event_components` (lines 118–121):
   - In `CalibratedMatchupHybridModel`, expected saves are computed as `saves_per90 * expected_minutes / 90.0 * defence_multiplier`.
   - However, when `apply_matchup_share_overlay` runs in `features/builder.py` (for every Gameweek once at least 1 historical fixture exists), line 314 sets `saves_vals.append(per90_saves)` (neutral) AND line 334 forces `out["defence_multiplier"] = 1.0`!
   - As a result, **goalkeeper save projections in the active Champion have zero opponent fixture sensitivity from GW2 through GW38**!
   If we preserve each goalkeeper's individual Empirical Bayes `per90_saves` baseline and modulate it by the **opponent's speculative shot volume** (measured point-in-time by opponent `threat` per match relative to league average, which captures total box/perimeter shot attempts that drive saves), goalkeepers facing high-shot-volume opponents accurately project higher save points (`_expected_poisson_floor(expected_saves, 3)`) and higher save bonus (`+2.0 * expected_saves` in `xbps`).

## 2. Mathematical Formulation

For each club $o$, compute the point-in-time shrunk opponent attacking shot-threat volume per match from pre-deadline fixtures $\mathcal{H}_{<g}$:
   $$\hat{\Theta}_{o,\text{for}}(g) = \frac{\sum_{m \in \mathcal{H}_{o,<g}} w_m \cdot \text{Threat}_{o,m} + K_{\text{club}} \cdot \bar{\Theta}_{\text{league}}(g)}{\sum_{m \in \mathcal{H}_{o,<g}} w_m + K_{\text{club}}}, \quad K_{\text{club}} = 6.0$$
   Also compute shrunk player `per90_saves` for goalkeepers ($position\_id == 1$) with $K_{\text{GK}} \in [540, 1080]$ pseudo-minutes toward the league GKP mean $\bar{s}_{\text{GK}}(g)$:
   $$\hat{s}_{i}(g) = \frac{\sum_{m \in \mathcal{H}_{i,<g}} w_m \cdot \text{saves}_{i,m} + K_{\text{GK}} \cdot \frac{\bar{s}_{\text{GK}}(g)}{90.0}}{\sum_{m \in \mathcal{H}_{i,<g}} w_m \cdot \text{minutes}_{i,m} + K_{\text{GK}}} \times 90.0$$
   For goalkeeper $i$ facing opponent $o$ in fixture $f$, the opponent shot-volume save multiplier is:
   $$M_{\text{saves}, o}(g) = \text{clip}\left(1.0 + \omega(N_{\text{eff}, g}) \cdot \xi_{\text{saves}} \cdot \frac{\hat{\Theta}_{o,\text{for}}(g) - \bar{\Theta}_{\text{league}}(g)}{\bar{\Theta}_{\text{league}}(g)}, \; 0.75, \; 1.30\right)$$
   Then expected saves in `_project_event_components` are:
   $$\mathbb{E}[\text{Saves}_{i,f}] = \hat{s}_i(g) \cdot \frac{\text{expected\_minutes}}{90.0} \cdot M_{\text{saves}, o}(g)$$
   yielding $\text{xp\_saves} = \mathbb{E}\left[\lfloor \text{Saves}_{i,f} / 3 \rfloor\right]$ and $+2.0 \cdot \mathbb{E}[\text{Saves}_{i,f}]$ in `xbps`.

## 3. Decoupled Architecture Placement

Operates in $M_{\text{events}}$ (`xp_saves` and downstream `xbps` / `xp_bonus` for `position_id == 1`).

## 4. Replaces / Integration Hook

`DefXgShrinkChallengerModel.predict` (updating `per90_saves` for `position_id == 1` prior to `CalibratedMatchupHybridModel._project_event_components`).

## 5. Parameter Sweep Grid

`k_gk=720,xi_saves=0.30; k_gk=720,xi_saves=0.45; k_gk=900,xi_saves=0.35; k_gk=900,xi_saves=0.50; k_gk=540,xi_saves=0.35; k_gk=1080,xi_saves=0.40`

## 6. Small-Sample & Cold-Start Strategy

Keeps builder's warm-seeded `per90_saves` at GW1–4 via the ratio update `rate_K / rate_360` and scales opponent shot-volume elasticity by $\omega(N_{\text{eff}, g})$ ($N_{\min}=3500, N_{\text{full}}=7500$) and $K_{\text{club}}=6.0$ matches.

## 7. Budget-Constrained Optimizer Interaction

Under the £83.5m Constrained Legal Formation XI cap and the HiGHS MILP **Goalkeeper Transfer Friction** ($-1.5 \cdot s(H)$ pt penalty), selecting the optimal £4.5m starting goalkeeper is critical. In the active Champion, `per90_saves` ignores the opponent completely once matchup share activates; restoring calibrated opponent shot-volume save elasticity distinguishes £4.5m shot-stopper keepers facing high-volume perimeter shooting attacks (where they earn 1–2 save points plus bonus even on 1 goal conceded) from keepers facing low-volume clinical attacks.

## 8. Point-in-Time Feature Requirements

`features.player_id`; `features.club_id`; `features.opponent_id`; `features.position_id`; `features.fixture_id`; `features.gameweek_id`; `features.per90_saves`; `features.n_starts_historical`; `history.player_id`; `history.fixture_id`; `history.gameweek_id`; `history.opponent_club_id`; `history.minutes`; `history.saves`; `history.threat`

## 9. Python Code Skeleton (Optional)

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import _DECAY, DefXgShrinkChallengerModel

_GK_HIST_COLS = ("player_id", "fixture_id", "gameweek_id", "opponent_club_id", "minutes", "saves", "threat")


class GkSaveOpportunityElasticityChallengerModel(DefXgShrinkChallengerModel):
    """DefXgShrink Champion + EB goalkeeper save shrinkage + opponent threat-volume save elasticity."""

    def __init__(
        self,
        k_gk: float = 720.0,
        xi_saves: float = 0.35,
        club_k: float = 6.0,
        n_min: float = 3500.0,
        n_full: float = 7500.0,
    ) -> None:
        super().__init__()
        self.k_gk = float(k_gk)
        self.xi_saves = float(xi_saves)
        self.club_k = float(club_k)
        self.n_min = float(n_min)
        self.n_full = float(n_full)
        self._gk_hist = pd.DataFrame()

    @property
    def name(self) -> str:
        return "gk_save_opportunity_elasticity_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if history_df.empty or not set(_GK_HIST_COLS).issubset(history_df.columns):
            self._gk_hist = pd.DataFrame()
            return
        self._gk_hist = history_df[list(_GK_HIST_COLS)].apply(pd.to_numeric, errors="coerce").fillna(0.0)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._gk_hist.empty or features_df.empty or "per90_saves" not in features_df.columns:
            return super().predict(features_df, horizon)
        target_gw = resolve_asof_target_gw(features_df, self._gk_hist)
        prior = self._gk_hist[(self._gk_hist["gameweek_id"] < target_gw) & (self._gk_hist["minutes"] > 0)]
        if prior.empty:
            return super().predict(features_df, horizon)

        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        gk_prior = prior[prior["player_id"].map(positions).eq(1)]
        if gk_prior.empty:
            return super().predict(features_df, horizon)

        gk_mean = float(gk_prior["saves"].sum() / gk_prior["minutes"].sum().clip(min=1.0) * 90.0)
        last = gk_prior.groupby("player_id")["gameweek_id"].transform("max")
        w = _DECAY ** (last - gk_prior["gameweek_id"])
        sums = pd.DataFrame({
            "saves": gk_prior["saves"] * w,
            "mins": gk_prior["minutes"] * w,
            "player_id": gk_prior["player_id"],
        }).groupby("player_id").sum()

        rate_k = (sums["saves"] + self.k_gk * gk_mean / 90.0) / (sums["mins"] + self.k_gk) * 90.0
        rate_360 = (sums["saves"] + 360.0 * gk_mean / 90.0) / (sums["mins"] + 360.0) * 90.0
        eb_ratio = (rate_k / rate_360.where(rate_360 > 1e-6)).fillna(1.0).clip(0.5, 2.0)

        sides = prior.groupby("fixture_id")["opponent_club_id"].agg(["min", "max"])
        fx = prior.join(sides, on="fixture_id")
        fx = fx[fx["min"] != fx["max"]]
        fx = fx.assign(club=fx["min"] + fx["max"] - fx["opponent_club_id"])
        club_thr = fx.groupby(["fixture_id", "club"], as_index=False)["threat"].sum()
        league_thr = max(10.0, float(club_thr["threat"].mean())) if not club_thr.empty else 120.0
        t_grp = club_thr.groupby("club").agg(n=("threat", "size"), thr=("threat", "sum"))
        thr_map = ((t_grp["thr"] + self.club_k * league_thr) / (t_grp["n"] + self.club_k)).to_dict()

        n_seed = float(features_df.drop_duplicates("player_id").get("n_starts_historical", pd.Series(0.0)).sum())
        n_eff = 0.5 * n_seed + float(len(prior))
        omega = float(np.clip((n_eff - self.n_min) / max(1.0, self.n_full - self.n_min), 0.0, 1.0))

        feat = features_df.copy()
        opp_thr = feat["opponent_id"].map(thr_map).fillna(league_thr).to_numpy(float)
        opp_mult = np.clip(1.0 + omega * self.xi_saves * ((opp_thr - league_thr) / league_thr), 0.75, 1.30)
        is_gk = (feat["position_id"] == 1) & (feat["fixture_id"] >= 0)
        gk_eb = feat["player_id"].map(eb_ratio).fillna(1.0).to_numpy(float)
        feat["per90_saves"] = (
            pd.to_numeric(feat["per90_saves"], errors="coerce").fillna(0.0).to_numpy(float)
            * np.where(is_gk, gk_eb * opp_mult, 1.0)
        )
        return super().predict(feat, horizon)
```
