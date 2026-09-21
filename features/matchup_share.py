"""Matchup share overlay for Feature Contract rates.

When this-season finished Club Fixtures exist, bump attack/defence rates from
opponent xG gaps and player xG/xA share. Force ``attack_multiplier`` /
``defence_multiplier`` to ×1.0 so Club Strength does not double-scale.

Fallback (caller): empty history → leave Club Strength / neutral multipliers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MATCHUP_SHARE_K = 10
EPS = 1e-6
PEN_XG_PER90 = 0.15


def _blended_rate(
    history: pd.DataFrame,
    *,
    value_col: str,
    is_home: bool,
    k: int,
    league_avg: float,
) -> float:
    """0.5·all + 0.5·venue, then w·mix + (1−w)·league_avg with w=min(1, n/K)."""
    if history.empty or league_avg <= 0:
        return float(league_avg) if league_avg > 0 else 1.0
    hist = history.sort_values("gameweek_id").tail(k)
    n = len(hist)
    w = min(1.0, n / float(k))
    rate_all = float(hist[value_col].mean())
    venue = hist[hist["was_home"] == is_home]
    rate_venue = float(venue[value_col].mean()) if not venue.empty else rate_all
    rate_mix = 0.5 * rate_all + 0.5 * rate_venue
    return w * rate_mix + (1.0 - w) * float(league_avg)


def _ensure_club_id(df_hist: pd.DataFrame, df_fixtures: pd.DataFrame) -> pd.DataFrame:
    if "club_id" in df_hist.columns and df_hist["club_id"].notna().any():
        out = df_hist.copy()
        out["club_id"] = out["club_id"].astype(int)
        return out
    if df_hist.empty or "fixture_id" not in df_hist.columns:
        return df_hist.copy()
    merged = df_hist.merge(
        df_fixtures[["id", "home_club_id", "away_club_id"]],
        left_on="fixture_id",
        right_on="id",
        how="left",
    )
    if "was_home" not in merged.columns:
        return df_hist.copy()
    merged["club_id"] = np.where(
        merged["was_home"], merged["home_club_id"], merged["away_club_id"]
    )
    merged["club_id"] = pd.to_numeric(merged["club_id"], errors="coerce")
    return merged


def _club_fixture_xg(df_hist: pd.DataFrame) -> pd.DataFrame:
    """Club-fixture xG sum and xGC (max among ≥60′ rows)."""
    work = df_hist.copy()
    for col in ("expected_goals", "expected_assists", "expected_goals_conceded"):
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)
    if "was_home" not in work.columns:
        work["was_home"] = False
    xg = work.groupby(
        ["fixture_id", "club_id", "gameweek_id", "was_home"], as_index=False
    )["expected_goals"].sum()
    full = work[pd.to_numeric(work.get("minutes", 0), errors="coerce").fillna(0.0) >= 60]
    if full.empty:
        xgc = xg[["fixture_id", "club_id"]].copy()
        xgc["expected_goals_conceded"] = 0.0
    else:
        xgc = (
            full.groupby(["fixture_id", "club_id"], as_index=False)["expected_goals_conceded"]
            .max()
        )
    return xg.merge(xgc, on=["fixture_id", "club_id"], how="left").fillna(
        {"expected_goals_conceded": 0.0}
    )


def _club_fixture_xa(df_hist: pd.DataFrame) -> pd.DataFrame:
    work = df_hist.copy()
    work["expected_assists"] = pd.to_numeric(
        work["expected_assists"], errors="coerce"
    ).fillna(0.0)
    if "was_home" not in work.columns:
        work["was_home"] = False
    return work.groupby(
        ["fixture_id", "club_id", "gameweek_id", "was_home"], as_index=False
    )["expected_assists"].sum()


def _player_contrib(df_hist: pd.DataFrame) -> pd.DataFrame:
    work = df_hist.copy()
    for col in ("expected_goals", "expected_assists"):
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)
    return work[
        ["player_id", "club_id", "fixture_id", "gameweek_id", "expected_goals", "expected_assists"]
    ].copy()


def _share_maps(
    player_contrib: pd.DataFrame,
    club_xg: pd.DataFrame,
    club_xa: pd.DataFrame,
) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], float]]:
    club_xg_tot = club_xg.groupby("club_id")["expected_goals"].sum().to_dict()
    club_xa_tot = club_xa.groupby("club_id")["expected_assists"].sum().to_dict()
    if player_contrib.empty:
        return {}, {}
    player_sums = player_contrib.groupby(["player_id", "club_id"], as_index=False)[
        ["expected_goals", "expected_assists"]
    ].sum()
    share_xg: dict[tuple[int, int], float] = {}
    share_xa: dict[tuple[int, int], float] = {}
    for row in player_sums.itertuples(index=False):
        key = (int(row.player_id), int(row.club_id))
        cx = float(club_xg_tot.get(int(row.club_id), 0.0))
        ca = float(club_xa_tot.get(int(row.club_id), 0.0))
        share_xg[key] = (
            float(min(max(float(row.expected_goals) / cx, 0.0), 1.0)) if cx > EPS else 0.0
        )
        share_xa[key] = (
            float(min(max(float(row.expected_assists) / ca, 0.0), 1.0)) if ca > EPS else 0.0
        )
    return share_xg, share_xa


def _club_rates(
    by_club: dict[int, pd.DataFrame],
    club_id: int,
    is_home: bool,
    *,
    league_xg: float,
    league_xgc: float,
) -> tuple[float, float]:
    hist = by_club.get(int(club_id), pd.DataFrame())
    xg = _blended_rate(
        hist, value_col="expected_goals", is_home=is_home, k=MATCHUP_SHARE_K, league_avg=league_xg
    )
    xgc = _blended_rate(
        hist,
        value_col="expected_goals_conceded",
        is_home=is_home,
        k=MATCHUP_SHARE_K,
        league_avg=league_xgc,
    )
    return max(xg, EPS), max(xgc, EPS)


def apply_matchup_share_overlay(
    df_feat: pd.DataFrame,
    df_hist: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    *,
    history_cutoff_gw: int,
) -> tuple[pd.DataFrame, bool]:
    """Apply matchup share when this-season club xG history exists before cutoff.

    Returns ``(features, applied)``. When ``applied`` is False, features are
    unchanged (caller keeps Club Strength / neutral multipliers).
    """
    required = {"expected_goals", "expected_assists", "expected_goals_conceded", "gameweek_id"}
    if df_hist.empty or not required.issubset(df_hist.columns):
        return df_feat, False

    hist = _ensure_club_id(df_hist, df_fixtures)
    hist = hist[hist["gameweek_id"] < history_cutoff_gw]
    if hist.empty or hist["club_id"].isna().all():
        return df_feat, False
    hist = hist.dropna(subset=["club_id"])
    hist["club_id"] = hist["club_id"].astype(int)

    club_xg = _club_fixture_xg(hist)
    if club_xg.empty or float(club_xg["expected_goals"].sum()) <= 0:
        return df_feat, False

    club_xa = _club_fixture_xa(hist)
    player_contrib = _player_contrib(hist)
    league_xg = float(club_xg["expected_goals"].mean())
    league_xgc = float(club_xg["expected_goals_conceded"].mean())
    if league_xg <= 0 or league_xgc <= 0:
        return df_feat, False

    by_club = {int(cid): group for cid, group in club_xg.groupby("club_id")}
    share_xg_map, share_xa_map = _share_maps(player_contrib, club_xg, club_xa)

    out = df_feat.copy()
    xg_vals: list[float] = []
    xa_vals: list[float] = []
    gc_vals: list[float] = []
    saves_vals: list[float] = []
    defcon_vals: list[float] = []

    for row in out.itertuples(index=False):
        opp_id = int(getattr(row, "opponent_id", 0) or 0)
        is_home = bool(getattr(row, "is_home", False))
        if opp_id <= 0:
            xg_vals.append(float(getattr(row, "per90_xg", 0.0) or 0.0))
            xa_vals.append(float(getattr(row, "per90_xa", 0.0) or 0.0))
            gc_vals.append(float(getattr(row, "per90_goals_conceded", 1.2) or 1.2))
            saves_vals.append(float(getattr(row, "per90_saves", 0.0) or 0.0))
            defcon_vals.append(float(getattr(row, "per90_defensive_contribution", 0.0) or 0.0))
            continue

        opp_xg, opp_xgc = _club_rates(
            by_club,
            opp_id,
            not is_home,
            league_xg=league_xg,
            league_xgc=league_xgc,
        )
        delta_att = opp_xgc - league_xgc
        delta_def = opp_xg - league_xg
        def_scale = opp_xg / league_xg
        key = (int(row.player_id), int(row.club_id))
        share_xg = share_xg_map.get(key, 0.0)
        share_xa = share_xa_map.get(key, 0.0)

        per90_xg = float(getattr(row, "per90_xg", 0.0) or 0.0)
        per90_xa = float(getattr(row, "per90_xa", 0.0) or 0.0)
        per90_gc = float(getattr(row, "per90_goals_conceded", 1.2) or 1.2)
        per90_saves = float(getattr(row, "per90_saves", 0.0) or 0.0)
        per90_defcon = float(getattr(row, "per90_defensive_contribution", 0.0) or 0.0)
        pen_order = float(getattr(row, "penalties_order", 0.0) or 0.0)

        addon_g = share_xg * delta_att
        if pen_order == 1.0:
            open_xg = max(0.0, per90_xg - PEN_XG_PER90)
            per90_xg = max(0.0, open_xg + addon_g) + PEN_XG_PER90
        else:
            per90_xg = max(0.0, per90_xg + addon_g)

        xg_vals.append(per90_xg)
        xa_vals.append(max(0.0, per90_xa + share_xa * delta_att))
        gc_vals.append(max(0.05, per90_gc + delta_def))
        saves_vals.append(max(0.0, per90_saves * def_scale))
        defcon_vals.append(max(0.0, per90_defcon * def_scale))

    out["per90_xg"] = xg_vals
    out["per90_xa"] = xa_vals
    out["per90_goals_conceded"] = gc_vals
    if "per90_saves" in out.columns:
        out["per90_saves"] = saves_vals
    if "per90_defensive_contribution" in out.columns:
        out["per90_defensive_contribution"] = defcon_vals
    out["attack_multiplier"] = 1.0
    out["defence_multiplier"] = 1.0
    return out, True
