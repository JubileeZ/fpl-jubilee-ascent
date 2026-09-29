"""CS Exposure Model Candidate (explore-candidate Queue mode 2026-09-29; smoke variant ``def_02_m60_k4``).

Subclass of ``club_def_prior_challenger`` with CS exposure over 60+ starts (``docs/research/component-model-ideas``
idea DEF-02): Clean sheet scoring requires 60+ minutes on pitch. Exposure on pitch uses the player's as-of
mean minutes conditional on starting and playing >= 60 minutes, shrunk toward 85.0 minutes with K=4 starts.
Applied by overriding ``clean_sheet_minutes`` in ``_project_event_components`` for GK and DEF in start state.
"""

from __future__ import annotations

import pandas as pd

from models.club_def_prior_challenger import ClubDefPriorChallengerModel

_M60_PRIOR = 85.0
_K_STARTS = 4.0
_HIST_COLUMNS = ("player_id", "gameweek_id", "minutes", "starts")


class CsExposureChallengerModel(ClubDefPriorChallengerModel):
    """Club x DEF prior Champion plus clean-sheet exposure conditioned on 60+ starts."""

    def __init__(self) -> None:
        super().__init__()
        self._m60_by_player: dict[int, float] = {}

    @property
    def name(self) -> str:
        return "cs_exposure_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if history_df.empty or not set(_HIST_COLUMNS).issubset(history_df.columns):
            self._m60_by_player = {}
            return
        hist = history_df[list(_HIST_COLUMNS)].copy()
        for col in ("player_id", "minutes", "starts"):
            hist[col] = pd.to_numeric(hist[col], errors="coerce").fillna(0.0)
        s60 = hist[(hist["starts"] >= 1.0) & (hist["minutes"] >= 60.0)]
        if s60.empty:
            self._m60_by_player = {}
            return
        grouped = s60.groupby("player_id", as_index=True)
        sums = grouped["minutes"].sum()
        counts = grouped["starts"].sum()
        shrunk = (sums + _K_STARTS * _M60_PRIOR) / (counts + _K_STARTS)
        self._m60_by_player = {int(k): float(v) for k, v in shrunk.items()}

    def _get_m60(self, row: pd.Series) -> float:
        pid = int(row["player_id"])
        return self._m60_by_player.get(pid, _M60_PRIOR)

    def _project_event_components(
        self,
        row: pd.Series,
        position: str,
        expected_minutes: float,
        *,
        clean_sheet_minutes: float,
        p_sixty_mins: float = 1.0,
    ) -> dict[str, float]:
        if position in ("GK", "D") and clean_sheet_minutes >= 45.0:
            clean_sheet_minutes = self._get_m60(row)
        return super()._project_event_components(
            row,
            position,
            expected_minutes,
            clean_sheet_minutes=clean_sheet_minutes,
            p_sixty_mins=p_sixty_mins,
        )
