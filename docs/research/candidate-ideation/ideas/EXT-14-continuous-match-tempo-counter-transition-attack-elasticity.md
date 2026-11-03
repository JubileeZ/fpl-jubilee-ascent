---
idea_id: EXT-14
name: "Continuous Match-Tempo & Counter-Transition Attack Elasticity"
tier: P1
component: xp_goals
status: untested
replaces: "DefXgShrinkChallengerModel.predict and CalibratedMatchupHybridModel._project_event_components (preserving DefXgShrinkChallengerModel $K_{\\text{DEF}}=2400$ shrinkage and MultiFeatureAssistChallengerModel GLM assist baseline)."
grid: "alpha_tempo=0.10,beta_trans=0.08; alpha_tempo=0.14,beta_trans=0.10; alpha_tempo=0.18,beta_trans=0.12; alpha_tempo=0.12,beta_trans=0.15; alpha_tempo=0.08,beta_trans=0.12; alpha_tempo=0.15,beta_trans=0.06"
inputs: features.player_id; features.club_id; features.opponent_id; features.position_id; features.fixture_id; features.gameweek_id; features.per90_xg; features.per90_xa; features.per90_threat; features.per90_creativity; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.was_home; history.minutes; history.expected_goals; history.expected_goals_conceded; history.threat; history.creativity
nearest_ledger_row: null
spec_path: ideas/EXT-14-continuous-match-tempo-counter-transition-attack-elasticity.md
---

# EXT-14: Continuous Match-Tempo & Counter-Transition Attack Elasticity

## 1. Concept & Football Hypothesis

Match tempo (combined open-play attacking intensity of both clubs) and asymmetric transition space systematically alter per-minute scoring and creative efficiency in ways that static additive matchup shares (`features/matchup_share.py`, $s=0.40$) miss. Specifically, `apply_matchup_share_overlay` adds a linear opponent xGC gap (`shrink_att * share_xg * (opp_xgc - league_xgc)`) that treats a slow, low-block opponent identically to a high-line, high-tempo opponent with the same average xGC. In association football, high-directness transition attackers (players with high box-entry and shot-volume `threat` relative to `creativity`) generate disproportionate expected goals and assists when facing high-tempo opponents whose matches feature elevated bidirectional xG+threat flow, while cross-variance zero-centering prevents easy-fixture bias inflation.

## 2. Mathematical Formulation

For club $c$ facing opponent $o$ in fixture $f$ at gameweek $g$, define the point-in-time Empirical Bayes shrunk club match tempo from completed pre-deadline fixtures $\mathcal{H}_{<g}$:
   $$\hat{T}_c(g) = \frac{\sum_{m \in \mathcal{H}_{c, <g}} w_m \left(xG_{c,m} + xGC_{c,m}\right) + K_{\text{club}} \cdot 2\bar{\lambda}_{\text{league}}}{\sum_{m \in \mathcal{H}_{c, <g}} w_m + K_{\text{club}}}, \quad w_m = \gamma^{g - 1 - gw(m)}$$
   with $\gamma = 0.95$ and $K_{\text{club}} = 6.0$ matches. The normalized fixture tempo index is:
   $$\widetilde{\mathcal{T}}_{c,o}(g) = \frac{0.5\left(\hat{T}_c(g) + \hat{T}_o(g)\right) - 2\bar{\lambda}_{\text{league}}}{2\bar{\lambda}_{\text{league}}}$$
   For outfield player $i$ ($position\_id \in \{2, 3, 4\}$), define the shrunk player directness profile $D_i(g) \in [-1, 1]$ from decayed pre-deadline `threat` and `creativity`:
   $$D_i(g) = \tanh\left(\frac{\log\left(\frac{\hat{\tau}_{i}(g) + 10.0}{\hat{\kappa}_{i}(g) + 10.0}\right) - \mu_{\text{pos}(i)}}{\sigma_{\text{pos}(i)}}\right)$$
   where $\hat{\tau}_i(g)$ and $\hat{\kappa}_i(g)$ are recency-decayed per-90 `threat` and `creativity` shrunk with $K=360$ pseudo-minutes. The continuous sample-shrunk modulation factor is:
   $$\eta_{i,f}(g) = \omega(N_{\text{eff}, g}) \cdot \left(\alpha_{\text{tempo}} \widetilde{\mathcal{T}}_{c,o}(g) + \beta_{\text{trans}} \max\left(0, D_i(g)\right) \cdot \frac{\hat{xG}_{o,\text{for}}(g) - \bar{\lambda}_{\text{league}}}{\bar{\lambda}_{\text{league}}}\right)$$
   where $\omega(N_{\text{eff}, g}) = \text{clip}\left(\frac{N_{\text{eff}, g} - 3500}{7500 - 3500}, 0.0, 1.0\right)$. To strictly satisfy the Playable Pool Bias guardrail ($|\text{Bias}_{\text{cand}}| \le |\text{Bias}_{\text{champ}}| + 0.01$), $\eta_{i,f}(g)$ is demeaned across active outfielders in gameweek $g$:
   $$\tilde{\eta}_{i,f}(g) = \text{clip}\left(\eta_{i,f}(g) - \bar{\eta}_g, -0.18, +0.18\right)$$
   Open-play per-90 rates (preserving penalty isolation in `CalibratedMatchupHybridModel._project_event_components`) are updated via:
   $$\lambda_{xG, i}^{\text{new}}(g) = \lambda_{xG, i}^{\text{champ}}(g) \cdot \exp\left(\tilde{\eta}_{i,f}(g)\right), \quad \lambda_{xA, i}^{\text{new}}(g) = \lambda_{xA, i}^{\text{champ}}(g) \cdot \exp\left(0.75 \cdot \tilde{\eta}_{i,f}(g)\right)$$

## 3. Decoupled Architecture Placement

Operates in $M_{\text{events}}$ (`xp_goals`, `xp_assists`, and downstream `xbps` / `xp_bonus`).

## 4. Replaces / Integration Hook

`DefXgShrinkChallengerModel.predict` and `CalibratedMatchupHybridModel._project_event_components` (preserving `DefXgShrinkChallengerModel` $K_{\text{DEF}}=2400$ shrinkage and `MultiFeatureAssistChallengerModel` GLM assist baseline).

## 5. Parameter Sweep Grid

`alpha_tempo=0.10,beta_trans=0.08; alpha_tempo=0.14,beta_trans=0.10; alpha_tempo=0.18,beta_trans=0.12; alpha_tempo=0.12,beta_trans=0.15; alpha_tempo=0.08,beta_trans=0.12; alpha_tempo=0.15,beta_trans=0.06`

## 6. Small-Sample & Cold-Start Strategy

Uses warm historical seed appearances weighted by $0.5$ in $N_{\text{eff}, g} = 0.5 N_{\text{seed}} + N_{\text{in\_season}, <g}$ with ramp thresholds $N_{\min}=3500, N_{\text{full}}=7500$ player-fixture rows and club shrinkage $K_{\text{club}}=6.0$ matches. In `cold_start` (GW1–4), $\omega(N_{\text{eff}, g})$ stays near zero and club tempo is anchored to the league prior $2\bar{\lambda}_{\text{league}}$, guaranteeing zero early-season variance inflation and preventing Nickell bias.

## 7. Budget-Constrained Optimizer Interaction

Under the £83.5m Constrained Legal Formation XI cap, the MILP must fill 3–4 starting midfield/forward slots with £5.0m–£6.5m counter-attacking wingers and forwards. Standard matchup share under-projects transition talismans on mid-table clubs when they face aggressive high-possession opponents. Zero-centered tempo elasticity identifies undervalued transition enablers without inflating green-fixture premiums or breaching the $+0.50$ players/GW squad churn guardrail.

## 8. Point-in-Time Feature Requirements

`features.player_id`; `features.club_id`; `features.opponent_id`; `features.position_id`; `features.fixture_id`; `features.gameweek_id`; `features.per90_xg`; `features.per90_xa`; `features.per90_threat`; `features.per90_creativity`; `history.player_id`; `history.fixture_id`; `history.gameweek_id`; `history.opponent_club_id`; `history.was_home`; `history.minutes`; `history.expected_goals`; `history.expected_goals_conceded`; `history.threat`; `history.creativity`

## 9. Python Code Skeleton (Optional)

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from models.multi_feature_assist_challenger import _club_fixture_table


class TempoTransitionElasticityChallengerModel(DefXgShrinkChallengerModel):
    """DefXgShrink Champion with continuous match-tempo and counter-transition attack elasticity."""

    def __init__(
        self,
        alpha_tempo: float = 0.14,
        beta_trans: float = 0.10,
        club_k: float = 6.0,
        n_min: float = 3500.0,
        n_full: float = 7500.0,
    ) -> None:
        super().__init__()
        self.alpha_tempo = float(alpha_tempo)
        self.beta_trans = float(beta_trans)
        self.club_k = float(club_k)
        self.n_min = float(n_min)
        self.n_full = float(n_full)
        self._tempo_hist = pd.DataFrame()

    @property
    def name(self) -> str:
        return "tempo_transition_elasticity_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        req = {"player_id", "fixture_id", "gameweek_id", "opponent_club_id", "minutes", "expected_goals", "threat", "creativity"}
        if history_df.empty or not req.issubset(history_df.columns):
            self._tempo_hist = pd.DataFrame()
            return
        self._tempo_hist = history_df[list(req)].apply(pd.to_numeric, errors="coerce").fillna(0.0)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._tempo_hist.empty or features_df.empty:
            return super().predict(features_df, horizon)
        target_gw = resolve_asof_target_gw(features_df, self._tempo_hist)
        prior = self._tempo_hist[self._tempo_hist["gameweek_id"] < target_gw]
        if prior.empty:
            return super().predict(features_df, horizon)

        n_seed = float(features_df.drop_duplicates("player_id").get("n_starts_historical", pd.Series(0.0)).sum())
        n_eff = 0.5 * n_seed + float((prior["minutes"] > 0).sum())
        omega = float(np.clip((n_eff - self.n_min) / max(1.0, self.n_full - self.n_min), 0.0, 1.0))
        if omega <= 1e-6:
            return super().predict(features_df, horizon)

        club_fx = _club_fixture_table(prior)
        if club_fx.empty:
            return super().predict(features_df, horizon)
        league_xg = max(0.5, float(club_fx["xg_for"].mean()))
        grp = club_fx.groupby("club").agg(n=("xg_for", "size"), xg_f=("xg_for", "sum"), xg_a=("xg_against", "sum"))
        tempo_map = ((grp["xg_f"] + grp["xg_a"] + self.club_k * 2.0 * league_xg) / (grp["n"] + self.club_k)).to_dict()
        att_map = ((grp["xg_f"] + self.club_k * league_xg) / (grp["n"] + self.club_k)).to_dict()

        feat = features_df.copy()
        own_t = feat["club_id"].map(tempo_map).fillna(2.0 * league_xg).to_numpy(float)
        opp_t = feat["opponent_id"].map(tempo_map).fillna(2.0 * league_xg).to_numpy(float)
        opp_att = feat["opponent_id"].map(att_map).fillna(league_xg).to_numpy(float)
        tempo_idx = (0.5 * (own_t + opp_t) - 2.0 * league_xg) / (2.0 * league_xg)

        thr = pd.to_numeric(feat.get("per90_threat", 0.0), errors="coerce").fillna(0.0).to_numpy(float)
        cre = pd.to_numeric(feat.get("per90_creativity", 0.0), errors="coerce").fillna(0.0).to_numpy(float)
        raw_dir = np.log((thr + 10.0) / (cre + 10.0))
        directness = np.tanh(raw_dir - np.median(raw_dir))

        eta = omega * (
            self.alpha_tempo * tempo_idx
            + self.beta_trans * np.maximum(0.0, directness) * ((opp_att - league_xg) / league_xg)
        )
        outfield = feat["position_id"].isin([2, 3, 4]) & (feat["fixture_id"] >= 0)
        if outfield.any():
            eta_centered = np.clip(eta - float(np.mean(eta[outfield])), -0.18, 0.18)
            mult = np.where(outfield, np.exp(eta_centered), 1.0)
            feat["per90_xg"] = pd.to_numeric(feat["per90_xg"], errors="coerce").fillna(0.0).to_numpy(float) * mult
            feat["per90_xa"] = pd.to_numeric(feat["per90_xa"], errors="coerce").fillna(0.0).to_numpy(float) * np.where(
                outfield, np.exp(0.75 * eta_centered), 1.0
            )
        return super().predict(feat, horizon)
```

---
