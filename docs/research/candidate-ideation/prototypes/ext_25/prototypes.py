from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

_REQUIRED_HIST_COLS = {"opponent_club_id", "threat", "creativity", "minutes"}


class _BaseEXT25(DefXgShrinkChallengerModel):
    variant_name: str = ""
    xi_modality: float = 0.12
    k_modality: float = 360.0

    def __init__(
        self,
        xi_modality: float | None = None,
        k_modality: float | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__()
        self.xi_modality = float(
            xi_modality if xi_modality is not None else self.xi_modality
        )
        self.k_modality = float(
            k_modality if k_modality is not None else self.k_modality
        )
        self._opp_phi: dict[int, float] = {}
        self._opp_mins: dict[int, float] = {}

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._opp_phi = {}
        self._opp_mins = {}
        if history_df.empty or not _REQUIRED_HIST_COLS.issubset(history_df.columns):
            return

        cols = ["opponent_club_id", "threat", "creativity", "minutes"]
        hist = history_df[cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        hist = hist[(hist["minutes"] > 0) & (hist["opponent_club_id"] > 0)]
        if hist.empty:
            return

        grouped = hist.groupby("opponent_club_id")[["threat", "creativity", "minutes"]].sum()
        total_threat = float(grouped["threat"].sum())
        total_creativity = float(grouped["creativity"].sum())
        phi_bar = (
            total_threat / (total_threat + total_creativity)
            if (total_threat + total_creativity) > 0.0
            else 0.50
        )

        for club_id, row in grouped.iterrows():
            cid = int(club_id)
            t_c = float(row["threat"])
            c_c = float(row["creativity"])
            m_c = float(row["minutes"])
            w = m_c / (m_c + self.k_modality)
            phi_raw = t_c / (t_c + c_c + 1e-6)
            phi_c = (1.0 - w) * phi_bar + w * phi_raw
            self._opp_phi[cid] = float(phi_c)
            self._opp_mins[cid] = float(m_c)

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
        if position not in ("M", "F"):
            return components

        xg_raw = row.get("per90_xg", 0.0)
        xa_raw = row.get("per90_xa", 0.0)
        xg = float(pd.to_numeric(xg_raw, errors="coerce"))
        xa = float(pd.to_numeric(xa_raw, errors="coerce"))
        if np.isnan(xg):
            xg = 0.0
        if np.isnan(xa):
            xa = 0.0
        tot = xg + xa
        if tot > 0.05:
            theta = float(np.clip(xg / tot, 0.0, 1.0))
        else:
            theta = 0.60 if position == "F" else 0.40

        opp_raw = row.get("opponent_id")
        if opp_raw is None or pd.isna(opp_raw):
            opp_raw = row.get("opponent_club_id")
        if opp_raw is None or pd.isna(opp_raw):
            return components

        try:
            c = int(float(opp_raw))
        except (ValueError, TypeError):
            return components

        phi = self._opp_phi.get(c, 0.50)
        if phi == 0.50:
            return components

        if theta > 0.5:
            adj = 4.0 * (theta - 0.5) * (phi - 0.5)
        else:
            adj = -4.0 * (0.5 - theta) * (0.5 - phi)
        adj = float(np.clip(adj, -1.0, 1.0))

        mult_g = 1.0 + self.xi_modality * adj
        mult_a = 1.0 - self.xi_modality * adj

        old_xp_goals = float(components["xp_goals"])
        new_xp_goals = max(0.0, old_xp_goals * mult_g)
        delta_goals = new_xp_goals - old_xp_goals

        old_xp_assists = float(components["xp_assists"])
        new_xp_assists = max(0.0, old_xp_assists * mult_a)
        delta_assists = new_xp_assists - old_xp_assists

        components["xp_goals"] = new_xp_goals
        components["xp_assists"] = new_xp_assists
        components["projected_points"] += delta_goals + delta_assists

        goal_pts = 5.0 if position == "M" else 4.0
        delta_goal_events = delta_goals / goal_pts
        delta_assist_events = delta_assists / 3.0
        components["xbps"] += 24.0 * delta_goal_events + 12.0 * delta_assist_events
        return components


def _make_variant(name: str, xi_modality: float, k_modality: float) -> type[_BaseEXT25]:
    return type(
        name,
        (_BaseEXT25,),
        {
            "variant_name": name,
            "xi_modality": float(xi_modality),
            "k_modality": float(k_modality),
        },
    )


_GRID = (
    ("ext_25_x08_k360", 0.08, 360.0),
    ("ext_25_x12_k360", 0.12, 360.0),
    ("ext_25_x16_k360", 0.16, 360.0),
    ("ext_25_x10_k540", 0.10, 540.0),
    ("ext_25_x14_k540", 0.14, 540.0),
    ("ext_25_x18_k540", 0.18, 540.0),
)

PROTOTYPES = {name: _make_variant(name, x, k) for name, x, k in _GRID}
_MANIFEST = (
    "features.position_id",
    "features.per90_xg",
    "features.per90_xa",
    "features.opponent_id",
    "history.opponent_club_id",
    "history.threat",
    "history.creativity",
    "history.minutes",
    "local.xbps",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
