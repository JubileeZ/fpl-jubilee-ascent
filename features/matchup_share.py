"""Matchup share overlay for Feature Contract rates.

When this-season finished Club Fixtures exist, bump attack/defence rates from
opponent xG gaps and player xG/xA share with calibrated shrinkage and Bayesian
positional share priors. Force ``attack_multiplier`` / ``defence_multiplier`` to
×1.0 so Club Strength does not double-scale. Peripheral defensive rates (saves
and DEFCON) are decoupled and remain neutral (×1.0).

Fallback (caller): empty history → leave Club Strength / neutral multipliers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MATCHUP_SHARE_K = 10
MATCHUP_SHRINK_ATT = 0.40
MATCHUP_SHRINK_DEF = 0.40
ATTACK_SCALE_MODES = ("none", "ratio", "downside")
ATTACK_RATIO_LO = 0.7
ATTACK_RATIO_HI = 1.4
RATIO_ATTACK_POSITIONS = frozenset({3, 4})  # MID/FWD only; DEF/GKP stay neutral
EPS = 1e-6
POSITION_PRIOR_WEIGHT = 4.0

# Positional baseline share priors: FWD ~ 0.26/0.14, MID ~ 0.14/0.18, DEF ~ 0.03/0.07, GK ~ 0.00/0.01
POSITION_DEFAULT_XG_SHARE = {1: 0.00, 2: 0.03, 3: 0.14, 4: 0.26}
POSITION_DEFAULT_XA_SHARE = {1: 0.01, 2: 0.07, 3: 0.18, 4: 0.14}


def _blended_rate(
    history: pd.DataFrame,
    *,
    value_col: str,
    is_home: bool,
    k: int,
    league_avg: float,
) -> float:
    """Venue-blended rate with sample-weighted venue weighting and sparse league blend."""
    if history.empty or league_avg <= 0:
        return float(league_avg) if league_avg > 0 else 1.0
    hist = history.sort_values("gameweek_id").tail(k)
    n = len(hist)
    w = min(1.0, n / float(k))
    rate_all = float(hist[value_col].mean())
    venue = hist[hist["was_home"] == is_home]
    n_venue = len(venue)
    if n_venue > 0:
        rate_venue = float(venue[value_col].mean())
        w_venue = min(0.5, n_venue / 6.0)
        rate_mix = (1.0 - w_venue) * rate_all + w_venue * rate_venue
    else:
        rate_mix = rate_all
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
    player_positions: dict[int, int] | None = None,
) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], float]]:
    club_xg_tot = club_xg.groupby("club_id")["expected_goals"].sum().to_dict()
    club_xa_tot = club_xa.groupby("club_id")["expected_assists"].sum().to_dict()
    if player_contrib.empty:
        return {}, {}
    player_sums = player_contrib.groupby(["player_id", "club_id"], as_index=False)[
        ["expected_goals", "expected_assists"]
    ].sum()
    positions = player_positions or {}
    share_xg: dict[tuple[int, int], float] = {}
    share_xa: dict[tuple[int, int], float] = {}
    for row in player_sums.itertuples(index=False):
        pid = int(row.player_id)
        cid = int(row.club_id)
        key = (pid, cid)
        cx = float(club_xg_tot.get(cid, 0.0))
        ca = float(club_xa_tot.get(cid, 0.0))
        pos_id = positions.get(pid, 3)
        prior_xg = POSITION_DEFAULT_XG_SHARE.get(pos_id, 0.14)
        prior_xa = POSITION_DEFAULT_XA_SHARE.get(pos_id, 0.14)

        denom_x = cx + POSITION_PRIOR_WEIGHT
        shrunk_xg = (
            (float(row.expected_goals) + POSITION_PRIOR_WEIGHT * prior_xg) / denom_x
            if denom_x > EPS
            else prior_xg
        )
        denom_a = ca + POSITION_PRIOR_WEIGHT
        shrunk_xa = (
            (float(row.expected_assists) + POSITION_PRIOR_WEIGHT * prior_xa) / denom_a
            if denom_a > EPS
            else prior_xa
        )

        share_xg[key] = float(min(max(shrunk_xg, 0.0), 1.0))
        share_xa[key] = float(min(max(shrunk_xa, 0.0), 1.0))
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
    shrink_att: float = MATCHUP_SHRINK_ATT,
    shrink_def: float = MATCHUP_SHRINK_DEF,
    attack_scale: str = "none",
) -> tuple[pd.DataFrame, bool]:
    """Apply matchup share when this-season club xG history exists before cutoff.

    Returns ``(features, applied)``. When ``applied`` is False, features are
    unchanged (caller keeps Club Strength / neutral multipliers).

    ``attack_scale="ratio"`` restores a clamped multiplicative attack scale
    (opponent xGC / league xGC) for MID/FWD instead of forcing ×1.0;
    ``attack_scale="downside"`` clamps the same ratio at 1.0 above, so hard
    fixtures scale attack down while easy fixtures never inflate;
    DEF/GKP and ``defence_multiplier`` stay neutral.
    """
    if attack_scale not in ATTACK_SCALE_MODES:
        raise ValueError(
            f"Unknown attack_scale {attack_scale!r}; expected one of {ATTACK_SCALE_MODES}"
        )
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
    club_xg_tot = club_xg.groupby("club_id")["expected_goals"].sum().to_dict()
    club_xa_tot = club_xa.groupby("club_id")["expected_assists"].sum().to_dict()

    player_positions: dict[int, int] = {}
    if "player_id" in df_feat.columns and "position_id" in df_feat.columns:
        for pid, pos in zip(df_feat["player_id"], df_feat["position_id"], strict=False):
            if pd.notna(pid) and pd.notna(pos):
                player_positions[int(pid)] = int(pos)

    share_xg_map, share_xa_map = _share_maps(
        player_contrib, club_xg, club_xa, player_positions=player_positions
    )

    out = df_feat.copy()
    xg_vals: list[float] = []
    xa_vals: list[float] = []
    gc_vals: list[float] = []
    saves_vals: list[float] = []
    defcon_vals: list[float] = []
    attack_mults: list[float] = []

    for row in out.itertuples(index=False):
        opp_id = int(getattr(row, "opponent_id", 0) or 0)
        is_home = bool(getattr(row, "is_home", False))
        if opp_id <= 0:
            xg_vals.append(float(getattr(row, "per90_xg", 0.0) or 0.0))
            xa_vals.append(float(getattr(row, "per90_xa", 0.0) or 0.0))
            gc_vals.append(float(getattr(row, "per90_goals_conceded", 1.2) or 1.2))
            saves_vals.append(float(getattr(row, "per90_saves", 0.0) or 0.0))
            defcon_vals.append(float(getattr(row, "per90_defensive_contribution", 0.0) or 0.0))
            attack_mults.append(1.0)
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

        key = (int(row.player_id), int(row.club_id))
        pos_id = int(getattr(row, "position_id", 3) or 3)
        prior_xg = POSITION_DEFAULT_XG_SHARE.get(pos_id, 0.14)
        prior_xa = POSITION_DEFAULT_XA_SHARE.get(pos_id, 0.14)
        cid = int(getattr(row, "club_id", 0) or 0)
        cx = float(club_xg_tot.get(cid, 0.0))
        ca = float(club_xa_tot.get(cid, 0.0))
        denom_x = cx + POSITION_PRIOR_WEIGHT
        denom_a = ca + POSITION_PRIOR_WEIGHT
        default_share_xg = (
            (POSITION_PRIOR_WEIGHT * prior_xg) / denom_x if denom_x > EPS else prior_xg
        )
        default_share_xa = (
            (POSITION_PRIOR_WEIGHT * prior_xa) / denom_a if denom_a > EPS else prior_xa
        )

        share_xg = share_xg_map.get(key, default_share_xg)
        share_xa = share_xa_map.get(key, default_share_xa)

        per90_xg = float(getattr(row, "per90_xg", 0.0) or 0.0)
        per90_xa = float(getattr(row, "per90_xa", 0.0) or 0.0)
        per90_gc = float(getattr(row, "per90_goals_conceded", 1.2) or 1.2)
        per90_saves = float(getattr(row, "per90_saves", 0.0) or 0.0)
        per90_defcon = float(getattr(row, "per90_defensive_contribution", 0.0) or 0.0)

        addon_g = shrink_att * share_xg * delta_att
        addon_a = shrink_att * share_xa * delta_att

        xg_vals.append(max(0.0, per90_xg + addon_g))
        xa_vals.append(max(0.0, per90_xa + addon_a))
        gc_vals.append(max(0.05, per90_gc + shrink_def * delta_def))
        # Saves and DEFCON decoupled from opponent xG scaling (neutral x1.0)
        saves_vals.append(per90_saves)
        defcon_vals.append(per90_defcon)
        if attack_scale in ("ratio", "downside") and (
            pos_id in RATIO_ATTACK_POSITIONS and league_xgc > EPS
        ):
            ceiling = 1.0 if attack_scale == "downside" else ATTACK_RATIO_HI
            attack_mults.append(
                min(max(opp_xgc / league_xgc, ATTACK_RATIO_LO), ceiling)
            )
        else:
            attack_mults.append(1.0)

    out["per90_xg"] = xg_vals
    out["per90_xa"] = xa_vals
    out["per90_goals_conceded"] = gc_vals
    if "per90_saves" in out.columns:
        out["per90_saves"] = saves_vals
    if "per90_defensive_contribution" in out.columns:
        out["per90_defensive_contribution"] = defcon_vals
    out["attack_multiplier"] = attack_mults
    out["defence_multiplier"] = 1.0
    return out, True
