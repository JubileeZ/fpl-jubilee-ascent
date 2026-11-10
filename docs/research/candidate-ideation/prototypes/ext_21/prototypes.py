from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class _BaseEXT21(DefXgShrinkChallengerModel):
    variant_name: str = ""
    gamma_fix: float = 0.15
    kappa_scale: float = 1.0

    def __init__(
        self,
        gamma_fix: float | None = None,
        kappa_scale: float | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__()
        if gamma_fix is not None:
            self.gamma_fix = float(gamma_fix)
        if kappa_scale is not None:
            self.kappa_scale = float(kappa_scale)
        self._opp_xgc: dict[int, float] = {}
        self._opp_n: dict[int, int] = {}
        self._league_mean_xgc: float = 1.35
        self._league_std_xgc: float = 0.35

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._opp_xgc = {}
        self._opp_n = {}
        self._league_mean_xgc = 1.35
        self._league_std_xgc = 0.35
        if (
            history_df.empty
            or "fixture_id" not in history_df.columns
            or "opponent_club_id" not in history_df.columns
        ):
            return

        cols = [
            c
            for c in (
                "fixture_id",
                "opponent_club_id",
                "minutes",
                "expected_goals",
                "expected_goals_conceded",
            )
            if c in history_df.columns
        ]
        hist = history_df[cols].copy()
        for col in cols:
            hist[col] = pd.to_numeric(hist[col], errors="coerce").fillna(0.0)

        if "minutes" in hist.columns:
            fx_mins = hist.groupby("fixture_id")["minutes"].sum()
            valid_fx = fx_mins[fx_mins > 0].index
            hist = hist[hist["fixture_id"].isin(valid_fx)]

        if hist.empty:
            return

        sides = hist.groupby("fixture_id")["opponent_club_id"].agg(["min", "max"])
        two_sided = sides[sides.iloc[:, 0] != sides.iloc[:, 1]].index
        hist = hist[hist["fixture_id"].isin(two_sided)]
        if hist.empty:
            return

        if "expected_goals" in hist.columns and (hist["expected_goals"] > 0).any():
            club_fx = hist.groupby(["fixture_id", "opponent_club_id"])[
                "expected_goals"
            ].sum()
        elif "expected_goals_conceded" in hist.columns:
            min_side = hist["fixture_id"].map(sides.iloc[:, 0])
            max_side = hist["fixture_id"].map(sides.iloc[:, 1])
            defending_club = min_side + max_side - hist["opponent_club_id"]
            club_fx = hist.groupby([hist["fixture_id"], defending_club])[
                "expected_goals_conceded"
            ].max()
        else:
            return

        if club_fx.empty:
            return

        total_xgc = float(club_fx.sum())
        total_matches = len(club_fx)
        league_mean = total_xgc / total_matches if total_matches > 0 else 1.35
        self._league_mean_xgc = (
            league_mean if np.isfinite(league_mean) and league_mean > 0 else 1.35
        )

        club_means = club_fx.groupby(level=1).mean()
        std_val = float(club_means.std(ddof=1)) if len(club_means) > 1 else 0.35
        self._league_std_xgc = (
            std_val if np.isfinite(std_val) and std_val > 0.05 else 0.35
        )

        sum_xgc = club_fx.groupby(level=1).sum()
        cnt_matches = club_fx.groupby(level=1).count()

        k_prior = 4.0
        for c, n_c in cnt_matches.items():
            cid = int(c)
            n_val = int(n_c)
            s_val = float(sum_xgc.get(c, 0.0))
            shrunk_lambda = (s_val + k_prior * self._league_mean_xgc) / (
                n_val + k_prior
            )
            self._opp_xgc[cid] = float(shrunk_lambda)
            self._opp_n[cid] = n_val

    def _project_event_components(
        self,
        row: pd.Series,
        position: str,
        expected_minutes: float,
        *,
        clean_sheet_minutes: float,
        p_sixty_mins: float,
    ) -> dict[str, float]:
        components = super()._project_event_components(
            row,
            position,
            expected_minutes,
            clean_sheet_minutes=clean_sheet_minutes,
            p_sixty_mins=p_sixty_mins,
        )

        opp_id_raw = row.get("opponent_id")
        if opp_id_raw is None or pd.isna(opp_id_raw):
            opp_id_raw = row.get("opponent_club_id")
        opp_id = None
        if opp_id_raw is not None and not pd.isna(opp_id_raw):
            try:
                opp_id = int(opp_id_raw)
            except (ValueError, TypeError):
                opp_id = None

        diff = float(pd.to_numeric(row.get("difficulty", 3.0), errors="coerce"))
        if np.isnan(diff):
            diff = 3.0
        z_fdr = (3.0 - diff) / 1.5

        n_opp = self._opp_n.get(opp_id, 0) if opp_id is not None else 0
        if n_opp > 0 and opp_id in self._opp_xgc:
            w = min(1.0, float(n_opp) / 4.0)
            z_opp = (self._opp_xgc[opp_id] - self._league_mean_xgc) / (
                self._league_std_xgc + 1e-6
            )
            z = (1.0 - w) * z_fdr + w * z_opp
        else:
            z = z_fdr

        m_open = 1.0 + self.gamma_fix * np.tanh(self.kappa_scale * z)

        pen_order = float(
            pd.to_numeric(row.get("penalties_order", 0.0), errors="coerce")
        )
        if np.isnan(pen_order):
            pen_order = 0.0
        is_pen = pen_order == 1.0
        goal_pts = (
            5.0
            if position == "M"
            else (4.0 if position == "F" else (6.0 if position == "D" else 10.0))
        )
        old_xp_goals = float(components["xp_goals"])

        if is_pen and expected_minutes > 0:
            pen_xg_per90 = 0.15
            pen_xp_goals = min(
                old_xp_goals, pen_xg_per90 * expected_minutes / 90.0 * goal_pts
            )
            open_xp_goals = max(0.0, old_xp_goals - pen_xp_goals)
            new_xp_goals = pen_xp_goals + open_xp_goals * m_open
        else:
            new_xp_goals = max(0.0, old_xp_goals * m_open)

        delta_goals = new_xp_goals - old_xp_goals
        components["xp_goals"] = new_xp_goals
        components["projected_points"] += delta_goals
        delta_goal_events = delta_goals / goal_pts
        components["xbps"] += 24.0 * delta_goal_events
        return components


def _make_variant(
    name: str, gamma_fix: float, kappa_scale: float
) -> type[_BaseEXT21]:
    return type(
        name,
        (_BaseEXT21,),
        {
            "variant_name": name,
            "gamma_fix": float(gamma_fix),
            "kappa_scale": float(kappa_scale),
        },
    )


_GRID = (
    ("ext_21_g10_k08", 0.10, 0.8),
    ("ext_21_g15_k10", 0.15, 1.0),
    ("ext_21_g20_k10", 0.20, 1.0),
    ("ext_21_g15_k12", 0.15, 1.2),
    ("ext_21_g18_k08", 0.18, 0.8),
    ("ext_21_g22_k12", 0.22, 1.2),
)

PROTOTYPES = {name: _make_variant(name, g, k) for name, g, k in _GRID}
_MANIFEST = (
    "features.per90_xg",
    "features.position_id",
    "features.difficulty",
    "features.opponent_id",
    "history.fixture_id",
    "history.opponent_club_id",
    "history.expected_goals",
    "history.expected_goals_conceded",
    "history.minutes",
    "history.gameweek_id",
    "local.penalties_order",
    "local.xbps",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
