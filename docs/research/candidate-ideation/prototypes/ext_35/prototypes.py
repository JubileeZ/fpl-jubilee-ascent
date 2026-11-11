"""EXT-35: lagged creative-role donor prior with fixed defender shrinkage."""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import (
    _DECAY,
    _MIDFIELDER,
    _POSITION_K,
    _RATIO_CLIP,
    DefXgShrinkChallengerModel,
    shrunk_xg_rates,
)
from models.hold_chase_challenger import (
    _CEILING_TILT_FROM,
    _MINS_TILT,
    _XG_SHARP_FROM,
    _XG_SHARP_SLOPE,
    _XG_TRIM_BELOW,
    _XG_TRIM_FACTOR,
)

_DEFENDER = 2
_ROLE_K = 360.0
_ROLE_SCALE = 10.0
_DONOR_EXPOSURE_CAP = 900.0
_DONOR_COUNT_K = 8.0
_HISTORY_COLUMNS = (
    "player_id", "fixture_id", "gameweek_id", "was_home", "opponent_club_id",
    "minutes", "expected_goals", "creativity",
)
_ROLE_COLUMNS = (*_HISTORY_COLUMNS, "club", "position_id", "lag_role", "lag_role_reliability")
_DIAGNOSTIC_COLUMNS = (
    "champ_xg_rate", "candidate_xg_rate", "prior_delta", "donor_n_eff", "weighted_minutes", "defender_prior",
)


def _positive_integer(values: pd.Series) -> pd.Series:
    return np.isfinite(values) & values.gt(0.0) & values.mod(1.0).eq(0.0)


def prepare_role_history(history: pd.DataFrame, positions: pd.Series, target_gw: int) -> pd.DataFrame:
    """Recover historical fixture sides before filtering the donor population to defenders."""
    if history.empty or not set(_HISTORY_COLUMNS).issubset(history.columns):
        return pd.DataFrame(columns=list(_ROLE_COLUMNS))
    frame = history[list(_HISTORY_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    identity = (
        _positive_integer(frame["player_id"]) & _positive_integer(frame["fixture_id"])
        & _positive_integer(frame["gameweek_id"]) & _positive_integer(frame["opponent_club_id"])
        & frame["was_home"].isin([0.0, 1.0]) & frame["gameweek_id"].lt(target_gw)
    )
    frame = frame.loc[identity].copy()
    context = frame[["fixture_id", "was_home", "opponent_club_id"]].drop_duplicates()
    context_counts = context.groupby("fixture_id").agg(
        n_rows=("was_home", "size"), n_sides=("was_home", "nunique"),
        n_opponents=("opponent_club_id", "nunique"),
    )
    valid_fixture = context_counts.index[
        context_counts["n_rows"].eq(2) & context_counts["n_sides"].eq(2)
        & context_counts["n_opponents"].eq(2)
    ]
    single_gw = frame.groupby("fixture_id")["gameweek_id"].nunique().eq(1)
    valid_fixture = valid_fixture.intersection(single_gw.index[single_gw])
    context = context.loc[context["fixture_id"].isin(valid_fixture)].copy()
    context["was_home"] = 1.0 - context["was_home"]
    context = context.rename(columns={"opponent_club_id": "club"})
    frame = frame.merge(context, on=["fixture_id", "was_home"], how="inner", validate="many_to_one")
    frame["position_id"] = frame["player_id"].map(positions)
    valid_stats = np.isfinite(frame[["minutes", "expected_goals", "creativity"]]).all(axis=1)
    valid_stats &= frame["minutes"].gt(0.0) & frame["expected_goals"].ge(0.0) & frame["creativity"].ge(0.0)
    duplicate = frame.duplicated(["player_id", "fixture_id"], keep=False)
    return frame.loc[valid_stats & ~duplicate & frame["position_id"].eq(_DEFENDER)].reset_index(drop=True)


def role_summary(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty or float(history["minutes"].sum()) <= 0.0:
        return pd.DataFrame(columns=["role", "role_reliability"])
    by_player = history.groupby("player_id")[["minutes", "creativity"]].sum()
    creativity_prior = 90.0 * float(history["creativity"].sum()) / float(history["minutes"].sum())
    rate = (90.0 * by_player["creativity"] + _ROLE_K * creativity_prior) / (by_player["minutes"] + _ROLE_K)
    return pd.DataFrame({
        "role": np.log1p(rate / _ROLE_SCALE),
        "role_reliability": by_player["minutes"] / (by_player["minutes"] + _ROLE_K),
    })


def lagged_donor_panel(history: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for gw in sorted(history["gameweek_id"].unique()):
        prior = history.loc[history["gameweek_id"] < gw]
        summary = role_summary(prior)
        if summary.empty:
            continue
        target = history.loc[history["gameweek_id"] == gw].copy()
        target["lag_role"] = target["player_id"].map(summary["role"])
        target["lag_role_reliability"] = target["player_id"].map(summary["role_reliability"])
        rows.append(target.dropna(subset=["lag_role", "lag_role_reliability"]))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=list(_ROLE_COLUMNS))


def donor_prior_delta(
    panel: pd.DataFrame,
    player_id: int,
    club_id: int,
    target_gw: int,
    role: float,
    role_reliability: float,
    *,
    h: float,
    k_pool: float,
    exclude_target_club: bool,
    cap: float,
) -> tuple[float, float]:
    required = {"player_id", "club", "position_id", "gameweek_id", "minutes", "expected_goals",
                "lag_role", "lag_role_reliability"}
    parameters = [role, role_reliability, h, k_pool, cap]
    identities = np.asarray([player_id, club_id, target_gw], dtype=float)
    if (panel.empty or not required.issubset(panel.columns) or not np.isfinite(parameters).all()
            or not np.isfinite(identities).all() or (identities <= 0.0).any() or (identities % 1.0 != 0.0).any()
            or role < 0.0 or role_reliability <= 0.0 or h <= 0.0 or k_pool <= 0.0 or cap < 0.0):
        return 0.0, 0.0
    rows = panel[list(required)].apply(pd.to_numeric, errors="coerce")
    rows = rows.replace([np.inf, -np.inf], np.nan).dropna()
    valid = (
        _positive_integer(rows["player_id"]) & _positive_integer(rows["club"])
        & _positive_integer(rows["gameweek_id"]) & rows["gameweek_id"].lt(target_gw)
        & rows["player_id"].ne(player_id) & rows["position_id"].eq(_DEFENDER)
        & rows["minutes"].gt(0.0) & rows["expected_goals"].ge(0.0) & rows["lag_role"].ge(0.0)
    )
    if exclude_target_club:
        valid &= rows["club"].ne(club_id)
    rows = rows.loc[valid].copy()
    if rows.empty:
        return 0.0, 0.0
    minutes, xg = rows["minutes"], rows["expected_goals"]
    base = _DECAY ** (target_gw - rows["gameweek_id"])
    base *= rows["lag_role_reliability"].clip(0.0, 1.0)
    donor_exposure = (base * minutes).groupby(rows["player_id"]).sum()
    exposure_scale = (_DONOR_EXPOSURE_CAP / donor_exposure.clip(lower=1e-12)).clip(upper=1.0)
    base *= rows["player_id"].map(exposure_scale)
    total_exposure = float((base * minutes).sum())
    if total_exposure <= 0.0 or not np.isfinite(total_exposure):
        return 0.0, 0.0
    donor_mean = 90.0 * float((base * xg).sum()) / total_exposure
    distance = (rows["lag_role"] - role) / h
    weight = base * np.exp(-0.5 * distance.pow(2))
    exposure = (weight * minutes).groupby(rows["player_id"]).sum()
    exposure_sum, square_sum = float(exposure.sum()), float(exposure.pow(2).sum())
    if exposure_sum <= 0.0 or square_sum <= 0.0:
        return 0.0, 0.0
    n_eff = exposure_sum**2 / square_sum
    role_mean = (90.0 * float((weight * xg).sum()) + k_pool * donor_mean) / (exposure_sum + k_pool)
    delta = float(np.clip(role_reliability, 0.0, 1.0) * n_eff / (n_eff + _DONOR_COUNT_K)
                  * np.clip(role_mean - donor_mean, -cap, cap))
    return (delta, n_eff) if np.isfinite([delta, n_eff]).all() else (0.0, 0.0)


def fixed_k_defender_rate(weighted_xg: float, weighted_minutes: float, prior: float) -> float:
    k_def = _POSITION_K[_DEFENDER]
    return (weighted_xg + k_def * prior / 90.0) / (weighted_minutes + k_def) * 90.0


def _ceiling_mask(features: pd.DataFrame) -> pd.Series:
    xg = pd.to_numeric(features["per90_xg"], errors="coerce").fillna(0.0)
    xa = pd.to_numeric(features.get("per90_xa", pd.Series(0.0, index=features.index)), errors="coerce").fillna(0.0)
    sharp = 1.0 + _XG_SHARP_SLOPE * ((xg - _XG_SHARP_FROM) / _XG_SHARP_FROM).clip(lower=0.0, upper=1.0)
    sharp = sharp.where(xg >= _XG_TRIM_BELOW, _XG_TRIM_FACTOR)
    return ((xg * sharp).clip(lower=0.0) + xa).ge(_CEILING_TILT_FROM)


def compensate_minute_tilt(champion: pd.DataFrame, candidate: pd.DataFrame) -> pd.DataFrame:
    """Keep inherited conditional duration when altered xG crosses HoldChase's ceiling."""
    out = candidate.copy()
    champion_tilt, candidate_tilt = _ceiling_mask(champion), _ceiling_mask(candidate)
    crossed = champion_tilt.ne(candidate_tilt)
    if not crossed.any():
        return out
    for column, default in (("xmins_if_start", 78.0), ("xmins_if_sub_in", 18.0)):
        if column not in out.columns:
            continue
        original = pd.to_numeric(champion[column], errors="coerce")
        baseline_minutes = original.where(~champion_tilt, original.fillna(0.0) * _MINS_TILT).fillna(default)
        corrected = baseline_minutes / np.where(candidate_tilt, _MINS_TILT, 1.0)
        replacement = out[column].astype(object).copy()
        replacement.loc[crossed] = corrected.loc[crossed]
        out[column] = replacement
    return out


class _CreativeRoleKernelPriorModel(DefXgShrinkChallengerModel):
    variant_name: str = ""
    h: float = 0.45
    k_pool: float = 7200.0
    exclude_target_club: bool = True
    cap: float = 0.02

    def __init__(self) -> None:
        super().__init__()
        self._role_history = pd.DataFrame(columns=list(_HISTORY_COLUMNS))
        self.rate_diagnostics = pd.DataFrame(columns=list(_DIAGNOSTIC_COLUMNS))

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._role_history = (history_df[list(_HISTORY_COLUMNS)].copy()
                              if set(_HISTORY_COLUMNS).issubset(history_df.columns)
                              else pd.DataFrame(columns=list(_HISTORY_COLUMNS)))

    def prepare_event_features(self, features_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        champion = features_df.copy()
        diagnostics = pd.DataFrame(columns=list(_DIAGNOSTIC_COLUMNS))
        if self._xg_hist.empty or features_df.empty:
            return champion, champion.copy(), diagnostics
        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        old = shrunk_xg_rates(self._xg_hist, positions, {})
        rates = shrunk_xg_rates(self._xg_hist, positions, _POSITION_K)
        champion_ratio = (rates / old.where(old > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)
        champion["per90_xg"] = features_df["per90_xg"] * features_df["player_id"].map(champion_ratio).fillna(1.0).to_numpy()
        if not {"club_id", "gameweek_id"}.issubset(features_df.columns):
            return champion, champion.copy(), diagnostics
        gws = pd.to_numeric(features_df["gameweek_id"], errors="coerce")
        if not _positive_integer(gws).all():
            return champion, champion.copy(), diagnostics
        target_gw = int(gws.min())
        history = prepare_role_history(self._role_history, positions, target_gw)
        panel, roles = lagged_donor_panel(history), role_summary(history)
        if panel.empty or roles.empty:
            return champion, champion.copy(), diagnostics
        current = features_df[["player_id", "position_id", "club_id"]].apply(pd.to_numeric, errors="coerce")
        valid_current = _positive_integer(current["player_id"]) & _positive_integer(current["club_id"])
        current = current.loc[valid_current]
        consistent = current.groupby("player_id")[["position_id", "club_id"]].nunique().eq(1).all(axis=1)
        current = current.loc[current["player_id"].isin(consistent.index[consistent])].drop_duplicates("player_id")
        current = current.loc[current["position_id"].eq(_DEFENDER)].set_index("player_id")
        hist = self._xg_hist
        pos = hist["player_id"].map(positions).fillna(_MIDFIELDER)
        by_pos = hist.groupby(pos)[["expected_goals", "minutes"]].sum()
        if _DEFENDER not in by_pos.index:
            return champion, champion.copy(), diagnostics
        defender_prior = float(by_pos.loc[_DEFENDER, "expected_goals"] / max(by_pos.loc[_DEFENDER, "minutes"], 1.0) * 90.0)
        weight = _DECAY ** (hist.groupby("player_id")["gameweek_id"].transform("max") - hist["gameweek_id"])
        sums = pd.DataFrame({
            "player_id": hist["player_id"], "weighted_xg": hist["expected_goals"] * weight,
            "weighted_minutes": hist["minutes"] * weight,
        }).groupby("player_id").sum()
        new_rates = rates.copy()
        records: list[dict[str, float | int]] = []
        for player_id, row in current.iterrows():
            if player_id not in roles.index or player_id not in sums.index or player_id not in rates.index:
                continue
            delta, n_eff = donor_prior_delta(
                panel, int(player_id), int(row["club_id"]), target_gw,
                float(roles.loc[player_id, "role"]), float(roles.loc[player_id, "role_reliability"]),
                h=self.h, k_pool=self.k_pool, exclude_target_club=self.exclude_target_club, cap=self.cap,
            )
            if delta != 0.0:
                new_rate = fixed_k_defender_rate(
                    float(sums.loc[player_id, "weighted_xg"]), float(sums.loc[player_id, "weighted_minutes"]),
                    max(0.0, defender_prior + delta),
                )
                if np.isfinite(new_rate) and new_rate >= 0.0 and np.isfinite(rates.loc[player_id]):
                    new_rates.loc[player_id] = new_rate
            records.append({
                "player_id": int(player_id), "champ_xg_rate": float(rates.loc[player_id]),
                "candidate_xg_rate": float(new_rates.loc[player_id]), "prior_delta": delta, "donor_n_eff": n_eff,
                "weighted_minutes": float(sums.loc[player_id, "weighted_minutes"]), "defender_prior": defender_prior,
            })
        if records:
            diagnostics = pd.DataFrame(records).set_index("player_id")
        ratio = (new_rates / old.where(old > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)
        candidate = features_df.copy()
        adjusted = features_df["per90_xg"] * features_df["player_id"].map(ratio).fillna(1.0).to_numpy()
        candidate["per90_xg"] = adjusted.where(np.isfinite(adjusted) & adjusted.ge(0.0) & valid_current, champion["per90_xg"])
        return champion, compensate_minute_tilt(champion, candidate), diagnostics

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        _, candidate, self.rate_diagnostics = self.prepare_event_features(features_df)
        # Rates already include exactly one DEF-shrink replacement.
        return super(DefXgShrinkChallengerModel, self).predict(candidate, horizon)


_GRID = (
    ("ext_35_h045_k7200_xclub", 0.45, 7200.0, True, 0.02),
    ("ext_35_h070_k7200_xclub", 0.70, 7200.0, True, 0.02),
    ("ext_35_h045_k14400_xclub", 0.45, 14400.0, True, 0.02),
    ("ext_35_h045_k7200_allclubs", 0.45, 7200.0, False, 0.02),
)


def _make_variant(name: str, h: float, k_pool: float, exclude_target_club: bool, cap: float) -> type[_CreativeRoleKernelPriorModel]:
    return type(name, (_CreativeRoleKernelPriorModel,), {
        "variant_name": name, "h": h, "k_pool": k_pool, "exclude_target_club": exclude_target_club, "cap": cap,
    })


_MANIFEST = (
    "features.player_id", "features.position_id", "features.club_id", "features.gameweek_id", "features.per90_xg",
    "features.per90_xa", "features.xmins_if_start", "features.xmins_if_sub_in",
    *(f"history.{column}" for column in _HISTORY_COLUMNS),
    *(f"local.{column}" for column in (
        "club", "n_rows", "n_sides", "n_opponents", "lag_role", "lag_role_reliability", "role", "role_reliability",
        "weighted_xg", *_DIAGNOSTIC_COLUMNS,
    )),
)

PROTOTYPES = {name: _make_variant(name, h, k_pool, exclude, cap) for name, h, k_pool, exclude, cap in _GRID}
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
COMPONENTS = {name: "xp_goals" for name in PROTOTYPES}
