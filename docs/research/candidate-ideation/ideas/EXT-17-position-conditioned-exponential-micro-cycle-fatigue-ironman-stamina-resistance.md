---
idea_id: EXT-17
name: "Position-Conditioned Exponential Micro-Cycle Fatigue & Ironman Stamina Resistance"
tier: P1
component: xp_minutes
status: dead-match
replaces: LearnedStartChallengerModel._state_probabilities and ParticipationStateHybridModel._conditional_minutes (via DefXgShrinkChallengerModel.predict).
grid: "psi_start=0.35,psi_dur=0.04,k_iron=6.0; psi_start=0.50,psi_dur=0.05,k_iron=6.0; psi_start=0.65,psi_dur=0.06,k_iron=6.0; psi_start=0.50,psi_dur=0.03,k_iron=8.0; psi_start=0.40,psi_dur=0.06,k_iron=4.0; psi_start=0.55,psi_dur=0.00,k_iron=6.0"
inputs: features.player_id; features.position_id; features.fixture_id; features.gameweek_id; features.kickoff_time; features.p_start; features.xmins_if_start; features.n_starts_historical; history.player_id; history.fixture_id; history.gameweek_id; history.kickoff_time; history.minutes; history.starts
nearest_ledger_row: "Learned participation variants other than shipped learned_start_challenger: ridge-logistic p_start (per-position; +learned p_sub_in / xmins-if-start / club rotation; no / per-club / club\u00d7position mass), alone or with soft P(60) bonus eligibility"
spec_path: ideas/EXT-17-position-conditioned-exponential-micro-cycle-fatigue-ironman-stamina-resistance.md
---

# EXT-17: Position-Conditioned Exponential Micro-Cycle Fatigue & Ironman Stamina Resistance

## 1. Concept & Football Hypothesis

Nailed stamina outliers ("ironmen" such as Saliba, Gabriel, Bruno Fernandes, Haaland) play 90 minutes every 3 days without rotation, whereas high-sprint rotation-managed positions (fullbacks, wide forwards, box-to-box midfielders) routinely get hooked at 62 minutes or rotated on the third match of a 7-day micro-cycle. Physiological fatigue in football is governed by: (a) a continuous exponential workload kernel over exact kickoff-to-kickoff hours across the trailing 14 days, and (b) player-specific **Sub-Hook Susceptibility** ($1 - p_{60\mid \text{start}}$ and historical full-90 completion rate), which separates nailed 90-minute ironmen from rotation-managed squad players.

## 2. Mathematical Formulation

For player $i$ and target fixture $f$ with kickoff timestamp $t_{f}$ (from `features.kickoff_time`), compute the continuous physiological acute load from all pre-deadline appearances $m \in \mathcal{H}_{i, <g}$ with kickoff timestamp $t_m < t_f$:
   $$\mathcal{L}_{i,f}(g) = \sum_{m \in \mathcal{H}_{i, <g}} \frac{\text{minutes}_{i,m}}{90.0} \cdot \exp\left(-\frac{t_f - t_m}{\tau_{\text{pos}(i)}}\right)$$
   where $t_f - t_m$ is measured in days and $\tau_{\text{pos}}$ is the position recovery half-life ($\tau_{\text{GK}} = \infty$, $\tau_{\text{DEF}} = 3.2$ days, $\tau_{\text{MID}} = 3.8$ days, $\tau_{\text{FWD}} = 3.5$ days). Define the excess micro-cycle workload above a standard 7-day rest cycle ($\mathcal{L}_0 = e^{-7.0 / \tau_{\text{pos}}}$):
   $$\Delta \mathcal{L}_{i,f}(g) = \max\left(0.0, \; \mathcal{L}_{i,f}(g) - \mathcal{L}_0\right)$$
   Next, define player $i$'s Empirical Bayes **Ironman Resistance Index** $\rho_i(g) \in [0, 1]$ from decayed historical starts:
   $$\rho_i(g) = \frac{\sum_{m \in \text{Starts}_{i,<g}} w_m \cdot \mathbb{I}(\text{minutes}_{i,m} \ge 85) + K_{\text{iron}} \cdot \bar{\rho}_{\text{pos}(i)}}{\sum_{m \in \text{Starts}_{i,<g}} w_m + K_{\text{iron}}}, \quad K_{\text{iron}} = 6.0\text{ starts}$$
   A player's rotation vulnerability is $V_i(g) = (1 - \rho_i(g))$ for outfielders ($V_i = 0$ for GKP). Under acute load $\Delta \mathcal{L}_{i,f}(g) > 0$, the pre-rescaling learned start probability and conditional start minutes are modulated by:
   $$\text{logit}\left(p_{\text{start}, i, f}^{\text{adj}}\right) = \text{logit}\left(p_{\text{start}, i, f}^{\text{champ}}\right) - \omega(N_{\text{eff}, g}) \cdot \psi_{\text{start}} \cdot V_i(g) \cdot \Delta \mathcal{L}_{i,f}(g)$$
   $$xMins_{\text{start}, i, f}^{\text{adj}} = xMins_{\text{start}, i, f}^{\text{champ}} \cdot \left(1.0 - \omega(N_{\text{eff}, g}) \cdot \psi_{\text{dur}} \cdot V_i(g) \cdot \Delta \mathcal{L}_{i,f}(g)\right)$$
   Followed by `preserve_mass` per Gameweek to match Champion global start mass, ensuring zero Playable Pool Bias drift.

## 3. Decoupled Architecture Placement

Operates in $M_{\text{mins}}$ (`p_start`, `xmins_if_start`, `projected_minutes`, `xp_minutes`).

## 4. Replaces / Integration Hook

`LearnedStartChallengerModel._state_probabilities` and `ParticipationStateHybridModel._conditional_minutes` (via `DefXgShrinkChallengerModel.predict`).

## 5. Parameter Sweep Grid

`psi_start=0.35,psi_dur=0.04,k_iron=6.0; psi_start=0.50,psi_dur=0.05,k_iron=6.0; psi_start=0.65,psi_dur=0.06,k_iron=6.0; psi_start=0.50,psi_dur=0.03,k_iron=8.0; psi_start=0.40,psi_dur=0.06,k_iron=4.0; psi_start=0.55,psi_dur=0.00,k_iron=6.0`

## 6. Small-Sample & Cold-Start Strategy

In GW1–4, fixture spacing is $\ge 7$ days ($\Delta \mathcal{L}_{i,f}(g) = 0$) and $\omega(N_{\text{eff}, g})$ ramps smoothly from $N_{\min}=3500$ to $N_{\text{full}}=7500$. Ironman resistance $\rho_i(g)$ is shrunk by $K_{\text{iron}}=6.0$ starts toward the position prior, preventing early-season noise while protecting 90-minute talismans ($V_i \to 0$) during festive/spring turnaround blocks.

## 7. Budget-Constrained Optimizer Interaction

Directly synergizes with the HiGHS MILP **Starter Expected Minutes Floor** ($xMins \ge 65.0$, $-10.0$/min slack penalty) and **First-Bench Cover Nailedness** ($\ge 12$ players with $xMins \ge 65.0$). By selectively trimming `xmins_if_start` and `p_start` only for rotation-vulnerable ($V_i$ high) players entering compressed $<4$-day turnarounds while leaving 90-minute ironmen untouched, the solver avoids fragile mid-price wingers right before festive/DGW rotation traps without churning nailed core starters.

## 8. Point-in-Time Feature Requirements

`features.player_id`; `features.position_id`; `features.fixture_id`; `features.gameweek_id`; `features.kickoff_time`; `features.p_start`; `features.xmins_if_start`; `features.n_starts_historical`; `history.player_id`; `history.fixture_id`; `history.gameweek_id`; `history.kickoff_time`; `history.minutes`; `history.starts`

## 9. Python Code Skeleton (Optional)

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from models.learned_start_challenger import learned_start_probabilities, target_start_probabilities

_TAU_POS = {1: 1e6, 2: 3.2, 3: 3.8, 4: 3.5}
_HIST_REQ = ("player_id", "gameweek_id", "kickoff_time", "minutes", "starts")


class MicroCycleFatigueRecoveryChallengerModel(DefXgShrinkChallengerModel):
    """DefXgShrink Champion + position-conditioned exponential micro-cycle fatigue & ironman resistance."""

    def __init__(
        self,
        psi_start: float = 0.50,
        psi_dur: float = 0.05,
        k_iron: float = 6.0,
        n_min: float = 3500.0,
        n_full: float = 7500.0,
    ) -> None:
        super().__init__()
        self.psi_start = float(psi_start)
        self.psi_dur = float(psi_dur)
        self.k_iron = float(k_iron)
        self.n_min = float(n_min)
        self.n_full = float(n_full)
        self._fatigue_hist = pd.DataFrame()

    @property
    def name(self) -> str:
        return "micro_cycle_fatigue_recovery_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if history_df.empty or not set(_HIST_REQ).issubset(history_df.columns):
            self._fatigue_hist = pd.DataFrame()
            return
        self._fatigue_hist = history_df[list(_HIST_REQ)].copy()

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._fatigue_hist.empty or features_df.empty or "kickoff_time" not in features_df.columns:
            return super().predict(features_df, horizon)
        target_gw = resolve_asof_target_gw(features_df, self._fatigue_hist)
        prior = self._fatigue_hist[pd.to_numeric(self._fatigue_hist["gameweek_id"], errors="coerce") < target_gw].copy()
        if prior.empty:
            return super().predict(features_df, horizon)

        prior["minutes"] = pd.to_numeric(prior["minutes"], errors="coerce").fillna(0.0)
        prior["starts"] = pd.to_numeric(prior["starts"], errors="coerce").fillna(0.0)
        prior["ko"] = pd.to_datetime(prior["kickoff_time"], utc=True, errors="coerce")
        prior = prior[(prior["minutes"] > 0) & prior["ko"].notna()]
        if prior.empty:
            return super().predict(features_df, horizon)

        n_seed = float(features_df.drop_duplicates("player_id").get("n_starts_historical", pd.Series(0.0)).sum())
        n_eff = 0.5 * n_seed + float(len(prior))
        omega = float(np.clip((n_eff - self.n_min) / max(1.0, self.n_full - self.n_min), 0.0, 1.0))

        starts_df = prior[prior["starts"] >= 1.0].copy()
        starts_df["is_85"] = (starts_df["minutes"] >= 85.0).astype(float)
        grp = starts_df.groupby("player_id").agg(n=("is_85", "size"), s85=("is_85", "sum"))
        iron_map = ((grp["s85"] + self.k_iron * 0.55) / (grp["n"] + self.k_iron)).to_dict()
        last_ko_by_player = {
            int(pid): sub[["ko", "minutes"]].to_records(index=False)
            for pid, sub in prior.groupby("player_id")
        }

        feat = features_df.copy()
        p_learn = learned_start_probabilities(self._raw_history, feat)
        feat_ko = pd.to_datetime(feat["kickoff_time"], utc=True, errors="coerce")

        dur_mult = np.ones(len(feat), dtype=float)
        for idx, (pid, pos_id, f_ko) in enumerate(
            zip(feat["player_id"].astype(int), feat["position_id"].astype(int), feat_ko)
        ):
            if pos_id == 1 or pd.isna(f_ko) or pid not in last_ko_by_player:
                continue
            tau = _TAU_POS.get(pos_id, 3.5)
            recs = last_ko_by_player[pid]
            dt_days = np.array([(f_ko - pd.Timestamp(r["ko"])).total_seconds() / 86400.0 for r in recs], dtype=float)
            mask = (dt_days > 0.1) & (dt_days <= 14.0)
            if not mask.any():
                continue
            mins = np.array([float(r["minutes"]) for r in recs], dtype=float)[mask]
            load = float(np.sum((mins / 90.0) * np.exp(-dt_days[mask] / tau)))
            excess = max(0.0, load - float(np.exp(-7.0 / tau)))
            if excess <= 0.0:
                continue
            vuln = 1.0 - float(iron_map.get(pid, 0.55))
            dur_mult[idx] = max(0.88, 1.0 - omega * self.psi_dur * vuln * excess)
            if pid in p_learn and int(feat.iloc[idx]["gameweek_id"]) == target_gw:
                p0 = np.clip(p_learn[pid], 1e-4, 1.0 - 1e-4)
                logit = np.log(p0 / (1.0 - p0)) - omega * self.psi_start * vuln * excess
                p_learn[pid] = float(1.0 / (1.0 + np.exp(-logit)))

        feat["xmins_if_start"] = pd.to_numeric(feat["xmins_if_start"], errors="coerce").fillna(78.0).to_numpy(float) * dur_mult
        self._p_target = target_start_probabilities(feat, p_learn, target_gw=target_gw)
        positions = feat.drop_duplicates("player_id").set_index("player_id")["position_id"]
        from models.def_xg_shrink_challenger import _POSITION_K, _RATIO_CLIP, shrunk_xg_rates
        if not self._xg_hist.empty:
            new = shrunk_xg_rates(self._xg_hist, positions, _POSITION_K)
            old = shrunk_xg_rates(self._xg_hist, positions, {})
            ratio = (new / old.where(old > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)
            feat["per90_xg"] = feat["per90_xg"] * feat["player_id"].map(ratio).fillna(1.0).to_numpy()
        self._assist_rates = self._fit_assist_rates(feat)
        from models.face_value_challenger import FaceValueChallengerModel
        return FaceValueChallengerModel.predict(self, feat, horizon)
```

---

## Ledger Audit & Revisit Justification
- **Flagged Match**: `Learned participation variants other than shipped learned_start_challenger: ridge-logistic p_start (per-position; +learned p_sub_in / xmins-if-start / club rotation; no / per-club / club×position mass), alone or with soft P(60) bonus eligibility`
- **Audit Status**: Pending Review
- **Rationale**: [Document why this proposal is structurally distinct from the flagged dead lever before promoting to status: untested]
