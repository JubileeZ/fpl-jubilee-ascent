---
idea_id: EXT-16
name: "Co-Starter Playmaker Gravity & Non-Zero-Sum Space-Creation Synergy"
tier: P1
component: xp_goals
status: dead-match
replaces: CalibratedMatchupHybridModel._project_event_components and DefXgShrinkChallengerModel.predict.
grid: "theta_syn=0.12,k_syn=4.0; theta_syn=0.18,k_syn=4.0; theta_syn=0.24,k_syn=4.0; theta_syn=0.18,k_syn=6.0; theta_syn=0.15,k_syn=3.0; theta_syn=0.22,k_syn=6.0"
inputs: features.player_id; features.club_id; features.position_id; features.fixture_id; features.gameweek_id; features.p_start; features.p_start_prior; features.chance_of_playing; features.status; features.per90_xg; features.per90_xa; features.per90_creativity; history.player_id; history.fixture_id; history.gameweek_id; history.minutes; history.starts; history.expected_assists; history.creativity
nearest_ledger_row: Start vs sub attack intensity (pooled as-of sub/start per90 ratio rho by position; split player rate per state)
spec_path: ideas/EXT-16-co-starter-playmaker-gravity-non-zero-sum-space-creation-synergy.md
---

# EXT-16: Co-Starter Playmaker Gravity & Non-Zero-Sum Space-Creation Synergy

## 1. Concept & Football Hypothesis

When an elite creator or gravity talisman is sidelined, total team attacking quality drops and secondary finishers lose space; conversely, when a club's primary playmakers are healthy and projected to start ($p_{\text{start}}$ high), their passing gravity and box-entry delivery elevate the conversion environment for co-starting teammates. The active Champion projects each player's `per90_xg` and `per90_xa` from historical averages without conditioning on whether the club's key creators are active in the current Gameweek lineup vs ruled out ($p_{\text{start}} = 0$).

## 2. Mathematical Formulation

For each player $j$ on club $c$, compute their as-of shrunk creative gravity rate $\hat{g}_j(g)$ from pre-deadline `expected_assists` and `creativity` per 90 (shrunk with $K=360$ pseudo-minutes):
   $$\hat{g}_j(g) = \hat{\lambda}_{xA, j}(g) + 0.005 \cdot \hat{\kappa}_{\text{cre}, j}(g)$$
   For fixture $f$ in gameweek $g$, let $p_{\text{start}, j, f}$ be the Champion participation start probability (incorporating hard DNP rules $p_{\text{start}}=0$ for injured/suspended players). For player $i$ on club $c$, the **Active Teammate Creative Supply** is:
   $$G_{-i, c, f}(g) = \sum_{j \in \text{Club}(c), j \neq i} p_{\text{start}, j, f} \cdot \hat{g}_j(g)$$
   Compare $G_{-i, c, f}(g)$ against the historical baseline teammate creative supply $\bar{G}_{-i, c}(g)$ experienced by player $i$ during their historical appearances in $\mathcal{H}_{<g}$ (shrunk toward the current-squad baseline start prior $\sum_{j \neq i} p_{\text{start\_prior}, j} \hat{g}_j(g)$ over $K_{\text{syn}} = 4.0$ matches):
   $$\Delta G_{i, f}(g) = \frac{G_{-i, c, f}(g) - \bar{G}_{-i, c}(g)}{\bar{G}_{\text{league}}(g)}$$
   Notice that this is **strictly positive-sum (complementary)**: if a key playmaker is injured ($p_{\text{start}, j, f} = 0$), $\Delta G_{i, f}(g) < 0$, which *reduces* teammate $i$'s open-play goal expectation rather than inflating it. If a playmaker returns to the starting XI after an absence, $\Delta G_{i, f}(g) > 0$, boosting teammate $i$'s projected open-play xG/90:
   $$\lambda_{xG, i, f}^{\text{syn}}(g) = \lambda_{xG, i, f}^{\text{champ}}(g) \cdot \text{clip}\left(1.0 + \omega(N_{\text{eff}, g}) \cdot \theta_{\text{syn}} \cdot \Delta G_{i, f}(g), \; 0.85, \; 1.15\right)$$

## 3. Decoupled Architecture Placement

Operates in $M_{\text{events}}$ (`xp_goals` and downstream `xbps` / `xp_bonus`), conditioned on $M_{\text{mins}}$ (`p_start`).

## 4. Replaces / Integration Hook

`CalibratedMatchupHybridModel._project_event_components` and `DefXgShrinkChallengerModel.predict`.

## 5. Parameter Sweep Grid

`theta_syn=0.12,k_syn=4.0; theta_syn=0.18,k_syn=4.0; theta_syn=0.24,k_syn=4.0; theta_syn=0.18,k_syn=6.0; theta_syn=0.15,k_syn=3.0; theta_syn=0.22,k_syn=6.0`

## 6. Small-Sample & Cold-Start Strategy

Baseline teammate creative supply $\bar{G}_{-i, c}(g)$ is anchored to the pre-season/seed start prior (`p_start_prior`) with $K_{\text{syn}} \in [3.0, 6.0]$ matches and scaled by continuous $\omega(N_{\text{eff}, g})$ ($N_{\min}=3500, N_{\text{full}}=7500$). When all regular starters are healthy, $G_{-i, c, f}(g) \approx \bar{G}_{-i, c}(g)$ so $\Delta G_{i,f}(g) \approx 0$, preserving Champion projections on normal weeks while reacting accurately to playmaker injuries and returns.

## 7. Budget-Constrained Optimizer Interaction

Protects the £83.5m Constrained XI and multi-period MILP solver from holding or buying secondary attackers (e.g., £5.5m–£7.0m forwards/wingers) when their club's primary creator is injured/suspended, and immediately upgrades budget finishers when an elite playmaker returns from injury.

## 8. Point-in-Time Feature Requirements

`features.player_id`; `features.club_id`; `features.position_id`; `features.fixture_id`; `features.gameweek_id`; `features.p_start`; `features.p_start_prior`; `features.chance_of_playing`; `features.status`; `features.per90_xg`; `features.per90_xa`; `features.per90_creativity`; `history.player_id`; `history.fixture_id`; `history.gameweek_id`; `history.minutes`; `history.starts`; `history.expected_assists`; `history.creativity`

## 9. Python Code Skeleton (Optional)

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class PlaymakerSynergyChallengerModel(DefXgShrinkChallengerModel):
    """DefXgShrink Champion + non-zero-sum co-starter playmaker gravity synergy."""

    def __init__(
        self,
        theta_syn: float = 0.18,
        k_syn: float = 4.0,
        n_min: float = 3500.0,
        n_full: float = 7500.0,
    ) -> None:
        super().__init__()
        self.theta_syn = float(theta_syn)
        self.k_syn = float(k_syn)
        self.n_min = float(n_min)
        self.n_full = float(n_full)
        self._syn_hist = pd.DataFrame()

    @property
    def name(self) -> str:
        return "playmaker_synergy_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        req = {"player_id", "fixture_id", "gameweek_id", "minutes", "expected_assists", "creativity"}
        if history_df.empty or not set(req).issubset(history_df.columns):
            self._syn_hist = pd.DataFrame()
            return
        self._syn_hist = history_df[list(req)].apply(pd.to_numeric, errors="coerce").fillna(0.0)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._syn_hist.empty or features_df.empty:
            return super().predict(features_df, horizon)
        target_gw = resolve_asof_target_gw(features_df, self._syn_hist)
        prior = self._syn_hist[(self._syn_hist["gameweek_id"] < target_gw) & (self._syn_hist["minutes"] > 0)]
        if prior.empty:
            return super().predict(features_df, horizon)

        n_seed = float(features_df.drop_duplicates("player_id").get("n_starts_historical", pd.Series(0.0)).sum())
        n_eff = 0.5 * n_seed + float(len(prior))
        omega = float(np.clip((n_eff - self.n_min) / max(1.0, self.n_full - self.n_min), 0.0, 1.0))
        if omega <= 1e-6:
            return super().predict(features_df, horizon)

        feat = features_df.copy()
        xa = pd.to_numeric(feat.get("per90_xa", 0.0), errors="coerce").fillna(0.0)
        cre = pd.to_numeric(feat.get("per90_creativity", 0.0), errors="coerce").fillna(0.0)
        feat["_grav"] = xa + 0.005 * cre

        eff_p_start: list[float] = []
        for _, row in feat.iterrows():
            _, ps, _ = self._state_probabilities(row)
            chance = float(row.get("chance_of_playing", 100.0) or 100.0)
            status = str(row.get("status", "")).lower()
            if bool(row.get("is_immediate_next_gw", False)) and (chance <= 0.0 or status in {"i", "s", "u", "n"}):
                ps = 0.0
            eff_p_start.append(ps)
        feat["_eff_ps"] = eff_p_start
        feat["_base_ps"] = pd.to_numeric(feat.get("p_start_prior", feat["p_start"]), errors="coerce").fillna(0.5)
        feat["_cur_g"] = feat["_eff_ps"] * feat["_grav"]
        feat["_base_g"] = feat["_base_ps"] * feat["_grav"]

        club_cur = feat.groupby(["club_id", "fixture_id"])["_cur_g"].transform("sum") - feat["_cur_g"]
        club_base = feat.groupby(["club_id", "fixture_id"])["_base_g"].transform("sum") - feat["_base_g"]
        league_g = max(0.25, float(club_base[feat["fixture_id"] >= 0].mean()))
        delta_g = (club_cur - club_base) / league_g
        mult = np.clip(1.0 + omega * self.theta_syn * delta_g.to_numpy(float), 0.85, 1.15)
        outfield = (feat["fixture_id"] >= 0) & (feat["position_id"].isin([2, 3, 4]))
        feat["per90_xg"] = pd.to_numeric(feat["per90_xg"], errors="coerce").fillna(0.0).to_numpy(float) * np.where(
            outfield, mult, 1.0
        )
        feat.drop(columns=["_grav", "_eff_ps", "_base_ps", "_cur_g", "_base_g"], inplace=True)
        return super().predict(feat, horizon)
```

---

## Ledger Audit & Revisit Justification
- **Flagged Match**: `Start vs sub attack intensity (pooled as-of sub/start per90 ratio rho by position; split player rate per state)`
- **Audit Status**: Pending Review
- **Rationale**: [Document why this proposal is structurally distinct from the flagged dead lever before promoting to status: untested]
