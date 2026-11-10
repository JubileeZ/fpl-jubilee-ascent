---
idea_id: EXT-33
name: Truly Asymmetric Convex-Balanced Clean Sheet Hazard
tier: P1
component: xp_clean_sheets
status: untested
replaces: Replaces DefXgShrinkChallengerModel.predict and overrides HoldChaseChallengerModel._apply_hard_fixture_defence with identity.
grid: "alpha_cs=0.18,rho_cs=0.25,k_cs=8.0; alpha_cs=0.22,rho_cs=0.25,k_cs=8.0; alpha_cs=0.22,rho_cs=0.20,k_cs=10.0; alpha_cs=0.26,rho_cs=0.20,k_cs=10.0; alpha_cs=0.18,rho_cs=0.33,k_cs=6.0; alpha_cs=0.22,rho_cs=0.33,k_cs=6.0"
inputs: features.per90_goals_conceded; features.difficulty; features.opponent_id; history.fixture_id; history.opponent_club_id; history.expected_goals; history.gameweek_id; history.minutes
nearest_ledger_row: null
spec_path: ideas/EXT-33-truly-asymmetric-convex-balanced-clean-sheet-hazard.md
---

# EXT-33: Truly Asymmetric Convex-Balanced Clean Sheet Hazard

## 1. Concept & Football Hypothesis

Clean sheet odds collapse non-linearly against elite attacks. Solves EXT-23 failure modes by enforcing strict convex combination (1-w)*z_fdr + w*z_opp with K_cs=8 match shrinkage, and replacing symmetric exponential hazard with truly asymmetric decay: full alpha hazard on tough fixtures (z >= 0) and damped beta = rho * alpha (rho 0.20-0.35) on easy fixtures (z < 0) satisfying ARCH-05.
In `CalibratedMatchupHybridModel`, clean sheet probability is projected as $P(\text{CS}) = \exp(-\lambda_{\text{pitch}}) \cdot P(60+)$. In the Champion, fixture difficulty shifts $\text{gc\_per90}$ only through a crude linear additive adjustment ($\Delta_{\text{def}}$ with scale $0.40$).
In reality, clean sheet probabilities collapse exponentially against elite attacks (e.g. Manchester City, Liverpool, Arsenal). While EXT-23 passed the Tier 2 Oracle event gate with $+0.63$ pts/GW and posted $+0.2338$ overall walkforward delta across $2/3$ segments, it stumbled on early-mid segment regression ($-0.693 < -0.15$) due to a convex weighting bug and symmetric exponential hazard violating ARCH-05.
EXT-33 enforces strict convex combination $(1 - w) \cdot z_{\text{fdr}} + w \cdot z_{\text{opp}}$ with $K_{\text{cs}} \in [6.0, 10.0]$ match shrinkage, and applies an asymmetric hazard function that heavily penalizes tough fixtures while capping green fixture inflation.

## 2. Mathematical Formulation

From match history $\mathcal{H}_{<g}$, compute empirical Bayes shrunk opponent attack strength:
$$\hat{\lambda}_{\text{opp}}(c) = \frac{\sum_{m \in \mathcal{H}_{c, <g}} xG_m + K_{\text{cs}} \cdot \bar{\lambda}_{\text{league}}}{N_{c} + K_{\text{cs}}}$$
Define standardized deviations:
$$z_{\text{opp}} = \frac{\hat{\lambda}_{\text{opp}}(c) - \bar{\lambda}_{\text{league}}}{\bar{\lambda}_{\text{league}}}, \quad z_{\text{fdr}} = \frac{\text{difficulty} - 3.0}{1.5}$$
Strict Convex Weighting:
$$w_c = \frac{N_c}{N_c + K_{\text{cs}}}, \quad z_{\text{comb}} = (1.0 - w_c) \cdot z_{\text{fdr}} + w_c \cdot z_{\text{opp}}$$
Truly Asymmetric Hazard Multiplier:
$$H(z_{\text{comb}}) = \begin{cases} \exp\left(\text{clip}(\alpha_{\text{cs}} \cdot z_{\text{comb}}, 0.0, 0.60)\right) & \text{if } z_{\text{comb}} \ge 0 \\ \exp\left(\text{clip}(\beta_{\text{cs}} \cdot z_{\text{comb}}, -0.30, 0.0)\right) & \text{if } z_{\text{comb}} < 0 \end{cases}$$
where $\beta_{\text{cs}} = \rho_{\text{cs}} \cdot \alpha_{\text{cs}}$ with $\rho_{\text{cs}} \in [0.20, 0.35]$.
Applied to `per90_goals_conceded`:
$$\text{gc\_per90}^* = \text{gc\_per90} \times H(z_{\text{comb}})$$

## 3. Decoupled Architecture Placement

Operates in $M_{\text{events}}$ (`xp_clean_sheet`, `xp_conceded`, and defensive `xbps`). Attacking parameters, appearance states, and minutes remain untouched.

## 4. Replaces / Integration Hook

Replaces `DefXgShrinkChallengerModel.predict` and overrides `HoldChaseChallengerModel._apply_hard_fixture_defence` with identity.

## 5. Parameter Sweep Grid

alpha_cs=0.18,rho_cs=0.25,k_cs=8.0; alpha_cs=0.22,rho_cs=0.25,k_cs=8.0; alpha_cs=0.22,rho_cs=0.20,k_cs=10.0; alpha_cs=0.26,rho_cs=0.20,k_cs=10.0; alpha_cs=0.18,rho_cs=0.33,k_cs=6.0; alpha_cs=0.22,rho_cs=0.33,k_cs=6.0

## 6. Small-Sample & Cold-Start Strategy

Strict convex combination $(1 - w) z_{\text{fdr}} + w z_{\text{opp}}$ guarantees that at early gameweeks ($N \le 3$, $w \le 0.25$), fixture evaluation is dominated by the pre-computed FDR $z_{\text{fdr}}$. Elevated $K_{\text{cs}} \in [6, 10]$ prevents early-season xG anomalies from distorting projections. Damping green fixtures ($\beta_{\text{cs}} \le 0.06$) prevents early-mid season catastrophic regressions.

7. **Full Squad & Budget-Constrained Optimizer Interaction**:
Defenders represent the primary rotation levers in a 15-player £100m MILP squad. Accurately depressing clean sheet expectation in difficult fixtures enables the solver to bench or transfer out defenders facing Man City, Liverpool, and Arsenal, rotating in £4.5m home starters. Capping green-fixture upside stops the solver from overpaying for low-quality defenders facing weak teams.

## 8. Point-in-Time Feature Requirements

features.per90_goals_conceded; features.difficulty; features.opponent_id; history.fixture_id; history.opponent_club_id; history.expected_goals; history.gameweek_id; history.minutes

## 9. Python Code Skeleton

```python
"""EXT-33 prototypes: Truly Asymmetric Convex-Balanced Clean Sheet Hazard."""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

_REQUIRED_HIST_COLS = {"fixture_id", "opponent_club_id", "expected_goals", "gameweek_id", "minutes"}


class _BaseEXT33(DefXgShrinkChallengerModel):
    """DefXgShrink Champion + Truly Asymmetric Convex-Balanced Clean Sheet Hazard."""

    variant_name: str = ""
    alpha_cs: float = 0.20
    rho_cs: float = 0.25
    k_cs: float = 8.0

    def __init__(
        self,
        alpha_cs: float | None = None,
        rho_cs: float | None = None,
        k_cs: float | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__()
        if alpha_cs is not None:
            self.alpha_cs = float(alpha_cs)
        if rho_cs is not None:
            self.rho_cs = float(rho_cs)
        if k_cs is not None:
            self.k_cs = float(k_cs)
        self._club_lambda: dict[int, float] = {}
        self._club_matches: dict[int, int] = {}
        self._league_mean_xg: float = 1.35

    @property
    def name(self) -> str:
        return self.variant_name

    @staticmethod
    def _apply_hard_fixture_defence(feat: pd.DataFrame) -> pd.DataFrame:
        """Bypass inherited hard fixture penalty; replaced by asymmetric hazard decay."""
        return feat

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._club_lambda = {}
        self._club_matches = {}
        self._league_mean_xg = 1.35
        if history_df.empty or not _REQUIRED_HIST_COLS.issubset(history_df.columns):
            return

        hist = history_df[list(_REQUIRED_HIST_COLS)].copy()
        for col in _REQUIRED_HIST_COLS:
            hist[col] = pd.to_numeric(hist[col], errors="coerce").fillna(0.0)

        sides = hist.groupby("fixture_id")["opponent_club_id"].agg(["min", "max"])
        min_side = hist["fixture_id"].map(sides.iloc[:, 0])
        max_side = hist["fixture_id"].map(sides.iloc[:, 1])
        two_sided = min_side != max_side

        hist = hist.loc[two_sided].copy()
        if hist.empty:
            return
        hist["club"] = (min_side.loc[two_sided] + max_side.loc[two_sided] - hist["opponent_club_id"]).astype(int)

        club_fx = hist.groupby(["fixture_id", "club"], as_index=False)["expected_goals"].sum()
        if club_fx.empty:
            return

        total_xg = float(club_fx["expected_goals"].sum())
        total_matches = len(club_fx)
        league_mean = total_xg / total_matches if total_matches > 0 else 1.35
        self._league_mean_xg = league_mean if np.isfinite(league_mean) and league_mean > 0 else 1.35

        sum_xg = club_fx.groupby("club")["expected_goals"].sum()
        cnt_matches = club_fx.groupby("club")["expected_goals"].count()

        for c, n_c in cnt_matches.items():
            cid = int(c)
            n_val = int(n_c)
            s_val = float(sum_xg.get(c, 0.0))
            shrunk_lambda = (s_val + self.k_cs * self._league_mean_xg) / (n_val + self.k_cs)
            self._club_lambda[cid] = shrunk_lambda
            self._club_matches[cid] = n_val

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        if "per90_goals_conceded" in feat.columns:
            diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
            z_fdr = (diff - 3.0) / 1.5

            if "opponent_id" in feat.columns:
                opp_ids = pd.to_numeric(feat["opponent_id"], errors="coerce")
            elif "opponent_club_id" in feat.columns:
                opp_ids = pd.to_numeric(feat["opponent_club_id"], errors="coerce")
            else:
                opp_ids = pd.Series(np.nan, index=feat.index)

            z = z_fdr.copy()
            if self._club_lambda and not opp_ids.isna().all():
                opp_lambda = opp_ids.map(self._club_lambda)
                opp_n = opp_ids.map(self._club_matches).fillna(0.0)
                valid = opp_lambda.notna() & (opp_n > 0)
                if valid.any():
                    z_opp = (opp_lambda.loc[valid] - self._league_mean_xg) / self._league_mean_xg
                    # Strict convex combination (1 - w)*z_fdr + w*z_opp
                    w = opp_n.loc[valid] / (opp_n.loc[valid] + self.k_cs)
                    z.loc[valid] = (1.0 - w) * z_fdr.loc[valid] + w * z_opp

            # Truly Asymmetric Hazard: full alpha on tough fixtures (z >= 0), damped beta = rho * alpha on easy fixtures (z < 0)
            beta_cs = self.rho_cs * self.alpha_cs
            hazard_mult = np.where(
                z >= 0.0,
                np.exp(np.clip(self.alpha_cs * z, 0.0, 0.60)),
                np.exp(np.clip(beta_cs * z, -0.30, 0.0)),
            )

            feat["per90_goals_conceded"] = (
                pd.to_numeric(feat["per90_goals_conceded"], errors="coerce").fillna(1.2) * hazard_mult
            )
        return super().predict(feat, horizon)


def _make_variant(name: str, alpha_cs: float, rho_cs: float, k_cs: float) -> type[_BaseEXT33]:
    return type(
        name,
        (_BaseEXT33,),
        {
            "variant_name": name,
            "alpha_cs": float(alpha_cs),
            "rho_cs": float(rho_cs),
            "k_cs": float(k_cs),
        },
    )


_GRID = (
    ("ext_33_a18_r25_k8", 0.18, 0.25, 8.0),
    ("ext_33_a22_r25_k8", 0.22, 0.25, 8.0),
    ("ext_33_a22_r20_k10", 0.22, 0.20, 10.0),
    ("ext_33_a26_r20_k10", 0.26, 0.20, 10.0),
    ("ext_33_a18_r33_k6", 0.18, 0.33, 6.0),
    ("ext_33_a22_r33_k6", 0.22, 0.33, 6.0),
)

_MANIFEST = (
    "features.per90_goals_conceded",
    "features.difficulty",
    "features.opponent_id",
    "history.fixture_id",
    "history.opponent_club_id",
    "history.expected_goals",
    "history.gameweek_id",
    "history.minutes",
    "local.club",
)

PROTOTYPES = {name: _make_variant(name, a, r, k) for name, a, r, k in _GRID}
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
```
