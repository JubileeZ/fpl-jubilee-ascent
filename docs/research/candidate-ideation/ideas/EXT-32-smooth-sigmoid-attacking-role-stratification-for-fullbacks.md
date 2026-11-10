---
idea_id: EXT-32
name: Smooth Sigmoid Attacking-Role Stratification for Fullbacks
tier: P1
component: xp_goals
status: untested
replaces: Replaces DefXgShrinkChallengerModel.predict (shrunk_xg_rates generalized from rigid position mapping to smooth continuous player-level adaptive shrinkage).
grid: "tau_threat=15.0,k_oop=800,m_zero=360,gamma_oop=0.20,s_threat=3.0; tau_threat=15.0,k_oop=600,m_zero=360,gamma_oop=0.25,s_threat=3.0; tau_threat=15.0,k_oop=1000,m_zero=450,gamma_oop=0.20,s_threat=3.0; tau_threat=18.0,k_oop=800,m_zero=360,gamma_oop=0.25,s_threat=3.0; tau_threat=18.0,k_oop=600,m_zero=450,gamma_oop=0.25,s_threat=3.5; tau_threat=14.0,k_oop=800,m_zero=360,gamma_oop=0.20,s_threat=2.5"
inputs: features.player_id; features.position_id; features.per90_xg; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.threat
nearest_ledger_row: null
spec_path: ideas/EXT-32-smooth-sigmoid-attacking-role-stratification-for-fullbacks.md
---

# EXT-32: Smooth Sigmoid Attacking-Role Stratification for Fullbacks

## 1. Concept & Football Hypothesis

Retains K_DEF=2400 for traditional central defenders to prevent header noise. Replaces binary thresholding with a smooth logistic curve modulated by appearance minute accumulation R(M) = M / (M + M_0). Smoothly interpolates K_OOP for high-threat fullbacks to prevent transfer plan churn.
In `models/def_xg_shrink_challenger.py`, the active Champion shrinks all defenders (`position_id == 2`) with uniform pseudo-minutes $K_{\text{DEF}} = 2400.0$ toward the league defender mean prior $\bar{\lambda}_{xG, \text{DEF}} \approx 0.06\text{ xG/90}$. While this heavily dampens low-reliability set-piece header noise by central defenders (ADR 0055), it suppresses genuine Out-of-Position (OOP) attacking defenders and wingbacks (e.g. Pedro Porro, Lewis Hall, Maxim De Cuyper, Trent Alexander-Arnold) who generate sustained open-play threat.
EXT-20 addressed this via a step function ($\mathbb{I}(\hat{\Theta}_i \ge \tau_{\text{threat}})$), unlocking relaxed shrinkage $K_{\text{OOP}} \in [800, 1200]$. However, it failed to achieve promotion bootstrap significance ($P=0.671 < 0.75$) due to discontinuous threshold chatter: defenders hovering near $\tau=15.0$ flipped in and out of OOP status from GW to GW, inducing unnecessary transfer churn in the 15-player MILP solver.
EXT-32 replaces the step function with a smooth continuous sigmoid transition function $\sigma_i \in [0, 1]$ coupled with an asymptotic minute-reliability factor $R(M_i) = \frac{M_i}{M_i + M_0}$.

## 2. Mathematical Formulation

From pre-deadline match history $\mathcal{H}_{<g}$ with exponential recency decay $w_m = \delta^{\max(g) - g_m}$ ($\delta = 0.95$), compute accumulated minutes $M_i$, threat $T_i$, and goals $G_i$:
$$M_i = \sum_{m \in \mathcal{H}_{i, <g}} w_m \cdot \text{Minutes}_{i, m}, \quad T_i = \sum_{m \in \mathcal{H}_{i, <g}} w_m \cdot \text{Threat}_{i, m}, \quad G_i = \sum_{m \in \mathcal{H}_{i, <g}} w_m \cdot xG_{i, m}$$
Position baseline rates are pooled across all historical defender minutes:
$$\bar{\Theta}_{\text{DEF}} = \frac{\sum_{m \in \mathcal{H}_{\text{DEF}, <g}} \text{Threat}_m}{\sum_{m \in \mathcal{H}_{\text{DEF}, <g}} \text{Minutes}_m} \times 90.0, \quad \bar{\lambda}_{xG, \text{DEF}} = \frac{\sum_{m \in \mathcal{H}_{\text{DEF}, <g}} xG_m}{\sum_{m \in \mathcal{H}_{\text{DEF}, <g}} \text{Minutes}_m} \times 90.0$$
Each player's shrunk threat rate (using baseline $K_{\theta} = 360.0$) is:
$$\hat{\Theta}_i = \frac{T_i + 360.0 \cdot \frac{\bar{\Theta}_{\text{pos}(i)}}{90.0}}{M_i + 360.0} \times 90.0$$
For defenders ($position\_id == 2$), define the continuous attacking-role weight $\sigma_i \in [0, 1]$:
$$\sigma_i = \left(\frac{M_i}{M_i + M_0}\right) \cdot \frac{1}{1 + \exp\left(-\frac{\hat{\Theta}_i - \tau_{\theta}}{s_{\theta}}\right)}$$
Continuous Adaptive Shrinkage Constant $K_i$:
$$K_i = \begin{cases} (1.0 - \sigma_i) \cdot K_{\text{DEF}} + \sigma_i \cdot K_{\text{OOP}} & \text{if } position\_id == 2 \\ 360.0 & \text{if } position\_id \in \{1, 3, 4\} \end{cases}$$
Continuous Prior Elevation $\pi_{xG, i}$:
$$\pi_{xG, i} = \begin{cases} \bar{\lambda}_{xG, \text{DEF}} \cdot \left(1.0 + \sigma_i \cdot \gamma_{\text{oop}} \cdot \text{clip}\left(\frac{\hat{\Theta}_i - \bar{\Theta}_{\text{DEF}}}{\max(\bar{\Theta}_{\text{DEF}}, 1.0)}, 0.0, 2.5\right)\right) & \text{if } position\_id == 2 \\ \bar{\lambda}_{xG, \text{pos}(i)} & \text{if } position\_id \in \{1, 3, 4\} \end{cases}$$
The updated xG rate is then:
$$\hat{\lambda}_{xG, i} = \frac{G_i + K_i \cdot \frac{\pi_{xG, i}}{90.0}}{M_i + K_i} \times 90.0$$
Applied via ratio adjustment on `features["per90_xg"]`.

## 3. Decoupled Architecture Placement

Operates strictly in $M_{\text{events}}$ (`xp_goals`, `xbps`, and `xp_bonus`). Participation probabilities ($M_{\text{mins}}$: $p_{\text{start}}$, $x\text{Mins}$) and defensive concession rates remain untouched.

## 4. Replaces / Integration Hook

Replaces `DefXgShrinkChallengerModel.predict` (`shrunk_xg_rates` generalized from rigid position mapping to smooth continuous player-level adaptive shrinkage).

## 5. Parameter Sweep Grid

tau_threat=15.0,k_oop=800,m_zero=360,gamma_oop=0.20,s_threat=3.0; tau_threat=15.0,k_oop=600,m_zero=360,gamma_oop=0.25,s_threat=3.0; tau_threat=15.0,k_oop=1000,m_zero=450,gamma_oop=0.20,s_threat=3.0; tau_threat=18.0,k_oop=800,m_zero=360,gamma_oop=0.25,s_threat=3.0; tau_threat=18.0,k_oop=600,m_zero=450,gamma_oop=0.25,s_threat=3.5; tau_threat=14.0,k_oop=800,m_zero=360,gamma_oop=0.20,s_threat=2.5

## 6. Small-Sample & Cold-Start Strategy

At early season ($GW \le 4$), sample minutes are small ($M_i \le 360$). The factor $\frac{M_i}{M_i + M_0} \le 0.50$ automatically attenuates $\sigma_i$. If a defender has $M_i = 90$ minutes and 1 goal with high threat, $\sigma_i \le 0.20$, keeping $K_i \ge 2080$ pseudo-minutes. The model remains anchored to the safe Champion $K=2400$ baseline until multi-match evidence accumulates.

7. **Full Squad & Budget-Constrained Optimizer Interaction**:
Eliminating step-function chatter stabilizes rolling multi-period transfer plans. A defender whose threat wobbles slightly (e.g. 14.9 to 15.1) sees their projection change by $< 0.003$ pts/GW rather than $0.20$ pts/GW, stopping the MILP from wasting free transfers swapping lateral defenders. High-threat £4.5m–£5.5m wingbacks gain $\approx +0.15\dots +0.30$ projected points/GW when sustained.

## 8. Point-in-Time Feature Requirements

features.player_id; features.position_id; features.per90_xg; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.threat

## 9. Python Code Skeleton

```python
"""EXT-32 prototypes: Smooth Continuous Threat-Adaptive Defender Shrinkage."""

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

_THREAT_HIST_COLS = ("player_id", "gameweek_id", "minutes", "expected_goals", "threat")


class _BaseSmoothThreatAdaptiveDefenderModel(DefXgShrinkChallengerModel):
    """DefXgShrink Champion + smooth continuous sigmoid threat-adaptive K and prior elevation."""

    variant_name: str = ""
    tau_threat: float = 15.0
    k_oop: float = 800.0
    gamma_oop: float = 0.20
    m_zero: float = 360.0
    s_threat: float = 3.0

    def __init__(self) -> None:
        super().__init__()
        self._threat_hist = pd.DataFrame(columns=list(_THREAT_HIST_COLS))

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if history_df.empty or not set(_THREAT_HIST_COLS).issubset(history_df.columns):
            self._threat_hist = pd.DataFrame(columns=list(_THREAT_HIST_COLS))
            return
        hist = history_df[list(_THREAT_HIST_COLS)].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        self._threat_hist = hist[hist["minutes"] > 0]

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._threat_hist.empty or features_df.empty:
            return super().predict(features_df, horizon)

        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        hist = self._threat_hist
        pos = hist["player_id"].map(positions).fillna(_MIDFIELDER)

        by_pos = hist.groupby(pos)[["expected_goals", "threat", "minutes"]].sum()
        pos_xg_rate = (by_pos["expected_goals"] / by_pos["minutes"].clip(lower=1.0) * 90.0).to_dict()
        pos_threat_rate = (by_pos["threat"] / by_pos["minutes"].clip(lower=1.0) * 90.0).to_dict()

        last = hist.groupby("player_id")["gameweek_id"].transform("max")
        weight = _DECAY ** (last - hist["gameweek_id"])
        sums = pd.DataFrame({
            "xg": hist["expected_goals"] * weight,
            "threat": hist["threat"] * weight,
            "mins": hist["minutes"] * weight,
            "player_id": hist["player_id"],
        }).groupby("player_id").sum()

        player_pos = positions.reindex(sums.index).fillna(_MIDFIELDER)
        base_xg_prior = player_pos.map(pos_xg_rate).fillna(0.0)
        base_threat_prior = player_pos.map(pos_threat_rate).fillna(10.0)

        # Shrunk threat per 90 (K=360 pseudo-minutes)
        shrunk_threat = (sums["threat"] + 360.0 * base_threat_prior / 90.0) / (sums["mins"] + 360.0) * 90.0

        # Continuous sigmoid attacking-role transition conditioned on shrunk threat and minute reliability
        is_def = player_pos.eq(2)
        rel_minutes = sums["mins"] / (sums["mins"] + self.m_zero)
        z_threat = (shrunk_threat - self.tau_threat) / max(self.s_threat, 0.1)
        sigmoid_threat = 1.0 / (1.0 + np.exp(-np.clip(z_threat, -10.0, 10.0)))
        sigma_oop = np.where(is_def, rel_minutes * sigmoid_threat, 0.0)

        # Prior elevation for attacking defenders scaled smoothly by sigma_oop
        def_threat_mean = pos_threat_rate.get(2, 10.0)
        rel_threat = np.clip((shrunk_threat - def_threat_mean) / max(def_threat_mean, 1.0), 0.0, 2.5)
        adj_prior = np.where(
            is_def,
            base_xg_prior * (1.0 + sigma_oop * self.gamma_oop * rel_threat),
            base_xg_prior,
        )

        # Smoothly interpolate shrinkage constant K: K_DEF=2400 for sigma=0, K_OOP for sigma=1
        k_def = _POSITION_K.get(2, 2400.0)
        k_vec = np.where(
            is_def,
            (1.0 - sigma_oop) * k_def + sigma_oop * self.k_oop,
            _BASE_K,
        )

        new_rates = (sums["xg"] + k_vec * adj_prior / 90.0) / (sums["mins"] + k_vec) * 90.0
        old_rates = shrunk_xg_rates(self._xg_hist, positions, {})
        ratio = (new_rates / old_rates.where(old_rates > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)

        features = features_df.copy()
        features["per90_xg"] = features["per90_xg"] * features["player_id"].map(ratio).fillna(1.0).to_numpy()
        return super(DefXgShrinkChallengerModel, self).predict(features, horizon)


def _make_variant(
    name: str,
    tau_threat: float,
    k_oop: float,
    m_zero: float,
    gamma_oop: float,
    s_threat: float,
) -> type[_BaseSmoothThreatAdaptiveDefenderModel]:
    return type(
        name,
        (_BaseSmoothThreatAdaptiveDefenderModel,),
        {
            "variant_name": name,
            "tau_threat": float(tau_threat),
            "k_oop": float(k_oop),
            "m_zero": float(m_zero),
            "gamma_oop": float(gamma_oop),
            "s_threat": float(s_threat),
        },
    )


_GRID = (
    ("ext_32_t15_k800_m360", 15.0, 800.0, 360.0, 0.20, 3.0),
    ("ext_32_t15_k600_m360", 15.0, 600.0, 360.0, 0.25, 3.0),
    ("ext_32_t15_k1000_m450", 15.0, 1000.0, 450.0, 0.20, 3.0),
    ("ext_32_t18_k800_m360", 18.0, 800.0, 360.0, 0.25, 3.0),
    ("ext_32_t18_k600_m450", 18.0, 600.0, 450.0, 0.25, 3.5),
    ("ext_32_t14_k800_m360", 14.0, 800.0, 360.0, 0.20, 2.5),
)

_MANIFEST_ENTRIES = (
    "features.player_id",
    "features.position_id",
    "features.per90_xg",
    "history.player_id",
    "history.gameweek_id",
    "history.minutes",
    "history.expected_goals",
    "history.threat",
    "local.xg",
    "local.threat",
    "local.mins",
)

PROTOTYPES = {name: _make_variant(name, tau, k, m, g, s) for name, tau, k, m, g, s in _GRID}
FEATURES = {name: _MANIFEST_ENTRIES for name, _, _, _, _, _ in _GRID}
```
