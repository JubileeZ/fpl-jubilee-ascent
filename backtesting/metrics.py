"""Decision-aware metrics for player/gameweek projection backtests."""

from collections.abc import Iterable

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp


_MINUTE_BAND_LABELS = ("0", "1-59", "60+")
_LEDGER_COMPONENTS = (
    "xp_minutes",
    "xp_goals",
    "xp_assists",
    "xp_clean_sheet",
    "xp_conceded",
    "xp_saves",
    "xp_penalties_saved",
    "xp_penalties_missed",
    "xp_own_goals",
    "xp_yellow_cards",
    "xp_red_cards",
    "xp_defcon",
    "xp_bonus",
)


_POS_GKP = 1
_POS_DEF = 2
_POS_MID = 3
_POS_FWD = 4

_TIE_BREAK_COST_WEIGHT = 1e-8
_TIE_BREAK_ID_WEIGHT = 1e-12

_LEGAL_FORMATIONS = (
    (3, 5, 2),
    (3, 4, 3),
    (4, 4, 2),
    (4, 3, 3),
    (4, 5, 1),
    (5, 3, 2),
    (5, 4, 1),
    (5, 2, 3),
)


def _canonical_sort(df: pd.DataFrame, sort_col: str, cost_col: str = "now_cost") -> pd.DataFrame:
    """Sort DataFrame deterministically by [sort_col DESC, cost_col ASC, player_id ASC]."""
    if df.empty:
        return df
    has_pid = "player_id" in df.columns
    has_cost = cost_col in df.columns
    keys = (
        df["player_id"].to_numpy() if has_pid else np.arange(len(df)),
        df[cost_col].fillna(0.0).to_numpy(dtype=float) if has_cost else np.zeros(len(df)),
        -df[sort_col].fillna(0.0).to_numpy(dtype=float),
    )
    return df.iloc[np.lexsort(keys)].reset_index(drop=True)


def _legacy_best_legal_xi(group: pd.DataFrame, sort_col: str, cost_col: str = "now_cost") -> pd.DataFrame:
    """Legacy unconstrained formation scan (ADR 0054)."""
    sorted_group = _canonical_sort(group, sort_col, cost_col)
    if "position_id" not in sorted_group.columns or len(sorted_group) < 11:
        return sorted_group.iloc[:min(11, len(sorted_group))].copy()

    gkp = sorted_group[sorted_group["position_id"] == _POS_GKP].iloc[:1]
    defs = sorted_group[sorted_group["position_id"] == _POS_DEF].iloc[:5]
    mids = sorted_group[sorted_group["position_id"] == _POS_MID].iloc[:5]
    fwds = sorted_group[sorted_group["position_id"] == _POS_FWD].iloc[:3]

    if len(gkp) < 1 or len(defs) < 3 or len(mids) < 2 or len(fwds) < 1:
        return sorted_group.iloc[:min(11, len(sorted_group))].copy()

    best_xi: pd.DataFrame | None = None
    best_score = float("-inf")
    for d, m, f in _LEGAL_FORMATIONS:
        if len(defs) >= d and len(mids) >= m and len(fwds) >= f:
            candidate = pd.concat([gkp, defs.iloc[:d], mids.iloc[:m], fwds.iloc[:f]])
            score = float(candidate[sort_col].sum())
            if score > best_score:
                best_score = score
                best_xi = candidate

    return best_xi if best_xi is not None else sorted_group.iloc[:min(11, len(sorted_group))].copy()


def _solve_constrained_lineup_milp(
    group: pd.DataFrame,
    sort_col: str,
    *,
    total_players: int,
    pos_bounds: dict[int, tuple[int, int]],
    pos_top_n: dict[int, int],
    pos_bottom_cost_n: dict[int, int],
    budget_cap: float | None,
    max_per_club: int = 3,
    cost_col: str = "now_cost",
    club_col: str = "club_id",
) -> pd.DataFrame | None:
    sorted_group = _canonical_sort(group, sort_col, cost_col)
    if "position_id" not in sorted_group.columns or len(sorted_group) < total_players:
        return sorted_group.iloc[:min(total_players, len(sorted_group))].copy()

    has_cost = cost_col in sorted_group.columns and budget_cap is not None
    has_club = club_col in sorted_group.columns and max_per_club > 0

    if not has_cost and not has_club:
        return None

    # Deterministic pool construction: slice canonical top and budget enablers
    parts = []
    for pos_id, top_count in pos_top_n.items():
        pos_df = sorted_group[sorted_group["position_id"] == pos_id]
        parts.append(pos_df.iloc[:min(top_count, len(pos_df))])
        if has_cost and pos_id in pos_bottom_cost_n:
            b_count = pos_bottom_cost_n[pos_id]
            b_sorted = pos_df.sort_values(
                [cost_col, "player_id"] if "player_id" in pos_df.columns else [cost_col]
            )
            parts.append(b_sorted.iloc[:min(b_count, len(b_sorted))])

    pool = pd.concat(parts).drop_duplicates(
        "player_id" if "player_id" in sorted_group.columns else None
    ).reset_index(drop=True)
    n = len(pool)
    if n < total_players:
        return sorted_group.iloc[:min(total_players, len(sorted_group))].copy()

    costs = pool[cost_col].fillna(0.0).to_numpy(dtype=float) if cost_col in pool.columns else np.zeros(n)
    player_ids = pool["player_id"].fillna(0).to_numpy(dtype=float) if "player_id" in pool.columns else np.arange(n, dtype=float)
    scores = pool[sort_col].fillna(0.0).to_numpy(dtype=float)

    cost_scale = 10.0 if np.max(costs) <= 20.0 and np.max(costs) > 0 else 1.0
    scaled_costs = costs * cost_scale
    if budget_cap is not None:
        effective_budget = budget_cap * 10.0 if budget_cap <= 150.0 and cost_scale == 10.0 else budget_cap
    else:
        effective_budget = float("inf")

    c = -(scores - _TIE_BREAK_COST_WEIGHT * scaled_costs - _TIE_BREAK_ID_WEIGHT * player_ids)

    positions = pool["position_id"].to_numpy(dtype=int)
    clubs = pool[club_col].to_numpy() if club_col in pool.columns else np.zeros(n, dtype=int)
    unique_clubs = np.unique(clubs) if club_col in pool.columns else []

    A_rows = [
        np.ones(n),
        (positions == _POS_GKP).astype(float),
        (positions == _POS_DEF).astype(float),
        (positions == _POS_MID).astype(float),
        (positions == _POS_FWD).astype(float),
    ]
    lb = [
        float(total_players),
        float(pos_bounds[_POS_GKP][0]),
        float(pos_bounds[_POS_DEF][0]),
        float(pos_bounds[_POS_MID][0]),
        float(pos_bounds[_POS_FWD][0]),
    ]
    ub = [
        float(total_players),
        float(pos_bounds[_POS_GKP][1]),
        float(pos_bounds[_POS_DEF][1]),
        float(pos_bounds[_POS_MID][1]),
        float(pos_bounds[_POS_FWD][1]),
    ]

    if has_cost:
        A_rows.append(scaled_costs)
        lb.append(0.0)
        ub.append(effective_budget)

    if has_club:
        for cl in unique_clubs:
            A_rows.append((clubs == cl).astype(float))
            lb.append(0.0)
            ub.append(float(max_per_club))

    A = np.array(A_rows)
    constraints = LinearConstraint(A, np.array(lb), np.array(ub))
    integrality = np.ones(n)
    bounds = Bounds(0, 1)

    res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)

    if res.success:
        selected_idx = np.where(res.x > 0.5)[0]
        selected_df = pool.iloc[selected_idx].copy()
        return _canonical_sort(selected_df, sort_col, cost_col)

    return None


def select_legal_formation_xi(
    group: pd.DataFrame,
    sort_col: str,
    *,
    budget_cap: float | None = 835.0,
    max_per_club: int = 3,
    cost_col: str = "now_cost",
    club_col: str = "club_id",
) -> pd.DataFrame:
    """Select the best legal 11-player lineup maximizing sum(sort_col).

    Enforces:
    1. Legal formation (1 GKP, 3-5 DEF, 2-5 MID, 1-3 FWD, exactly 11 players).
    2. Optional starting XI budget cap (default £83.5m / 835.0 in 0.1m units).
    3. Club quota (max 3 players per club).
    4. Deterministic tie-breaking on [sort_col DESC, cost ASC, player_id ASC].
    """
    res = _solve_constrained_lineup_milp(
        group,
        sort_col,
        total_players=11,
        pos_bounds={_POS_GKP: (1, 1), _POS_DEF: (3, 5), _POS_MID: (2, 5), _POS_FWD: (1, 3)},
        pos_top_n={_POS_GKP: 15, _POS_DEF: 30, _POS_MID: 35, _POS_FWD: 20},
        pos_bottom_cost_n={_POS_GKP: 5, _POS_DEF: 10, _POS_MID: 10, _POS_FWD: 5},
        budget_cap=budget_cap,
        max_per_club=max_per_club,
        cost_col=cost_col,
        club_col=club_col,
    )
    if res is not None:
        return res
    return _legacy_best_legal_xi(group, sort_col, cost_col)


best_legal_xi = select_legal_formation_xi


def select_top_15_squad(
    group: pd.DataFrame,
    sort_col: str = "projected_points",
    *,
    squad_budget: float = 1000.0,
    max_per_club: int = 3,
    cost_col: str = "now_cost",
    club_col: str = "club_id",
) -> pd.DataFrame:
    """Select optimal 15-player squad (2 GKP, 5 DEF, 5 MID, 3 FWD) subject to £100.0m budget."""
    res = _solve_constrained_lineup_milp(
        group,
        sort_col,
        total_players=15,
        pos_bounds={_POS_GKP: (2, 2), _POS_DEF: (5, 5), _POS_MID: (5, 5), _POS_FWD: (3, 3)},
        pos_top_n={_POS_GKP: 10, _POS_DEF: 25, _POS_MID: 30, _POS_FWD: 15},
        pos_bottom_cost_n={_POS_GKP: 5, _POS_DEF: 10, _POS_MID: 10, _POS_FWD: 5},
        budget_cap=squad_budget,
        max_per_club=max_per_club,
        cost_col=cost_col,
        club_col=club_col,
    )
    if res is not None:
        return res
    return _canonical_sort(group, sort_col, cost_col).iloc[:min(15, len(group))].copy()


def compute_top_15_squad_churn_by_gameweek(
    df_eval: pd.DataFrame,
    sort_col: str = "projected_points",
    *,
    squad_budget: float = 1000.0,
    max_per_club: int = 3,
    cost_col: str = "now_cost",
    club_col: str = "club_id",
) -> pd.Series:
    """Per-GW squad churn Churn_g = 15 - |S_g cap S_{g-1}| across rolling top-15 squads."""
    if "position_id" not in df_eval.columns or cost_col not in df_eval.columns:
        return pd.Series(dtype=float)

    squads_by_gw: dict[int, set[int]] = {}
    for gw, group in df_eval.groupby("gameweek"):
        if len(group) >= 15:
            squad = select_top_15_squad(
                group,
                sort_col,
                squad_budget=squad_budget,
                max_per_club=max_per_club,
                cost_col=cost_col,
                club_col=club_col,
            )
            squads_by_gw[int(gw)] = set(squad["player_id"])

    sorted_gws = sorted(squads_by_gw.keys())
    churn_dict: dict[int, float] = {}
    for i in range(1, len(sorted_gws)):
        gw_prev = sorted_gws[i - 1]
        gw_curr = sorted_gws[i]
        s_prev = squads_by_gw[gw_prev]
        s_curr = squads_by_gw[gw_curr]
        churn = float(15 - len(s_prev & s_curr))
        churn_dict[gw_curr] = churn

    return pd.Series(churn_dict, dtype=float)


def _formation_xi_stats(
    group: pd.DataFrame,
    *,
    target_column: str = "actual_points",
    budget_cap: float | None = 835.0,
    max_per_club: int = 3,
    cost_col: str = "now_cost",
    club_col: str = "club_id",
) -> tuple[float, float, float]:
    """Return (overlap, regret, captain_regret) for formation-constrained legal XI."""
    if len(group) == 0:
        return 0.0, 0.0, 0.0
    predicted_xi = select_legal_formation_xi(
        group,
        "projected_points",
        budget_cap=budget_cap,
        max_per_club=max_per_club,
        cost_col=cost_col,
        club_col=club_col,
    )
    actual_xi = select_legal_formation_xi(
        group,
        target_column,
        budget_cap=budget_cap,
        max_per_club=max_per_club,
        cost_col=cost_col,
        club_col=club_col,
    )
    predicted_ids = set(predicted_xi["player_id"])
    actual_ids = set(actual_xi["player_id"])
    count = max(len(predicted_xi), 1)
    overlap = len(predicted_ids & actual_ids) / count
    regret = float(actual_xi[target_column].sum() - predicted_xi[target_column].sum())

    if len(predicted_xi) > 0:
        pred_cap = predicted_xi.nlargest(1, "projected_points")
        max_target = predicted_xi[target_column].max()
        cap_target = pred_cap[target_column].iloc[0]
        captain_regret = float(max_target - cap_target)
    else:
        captain_regret = 0.0

    return overlap, regret, captain_regret


def formation_xi_regret_by_gameweek(
    df_eval: pd.DataFrame,
    *,
    target_column: str = "actual_points",
    budget_cap: float | None = 835.0,
    max_per_club: int = 3,
    cost_col: str = "now_cost",
    club_col: str = "club_id",
) -> pd.Series:
    """Per-GW formation-constrained legal XI regret, indexed by gameweek."""
    if "position_id" not in df_eval.columns:
        return top_k_regret_by_gameweek(df_eval, 11, target_column=target_column)
    return pd.Series(
        {
            gw: _formation_xi_stats(
                group,
                target_column=target_column,
                budget_cap=budget_cap,
                max_per_club=max_per_club,
                cost_col=cost_col,
                club_col=club_col,
            )[1]
            for gw, group in df_eval.groupby("gameweek")
        },
        dtype=float,
    )


def _top_k_stats(group: pd.DataFrame, k: int, *, target_column: str = "actual_points") -> tuple[float, float]:
    count = min(k, len(group))
    if count == 0:
        return 0.0, 0.0
    predicted = group.nlargest(count, "projected_points")
    actual = group.nlargest(count, target_column)
    predicted_ids = set(predicted["player_id"])
    actual_ids = set(actual["player_id"])
    overlap = len(predicted_ids & actual_ids) / count
    regret = float(actual[target_column].sum() - predicted[target_column].sum())
    return overlap, regret


def top_k_regret_by_gameweek(df_eval: pd.DataFrame, k: int = 11, *, target_column: str = "actual_points") -> pd.Series:
    """Per-GW top-k regret (same definition as ``top_{k}_regret``), indexed by gameweek."""
    return pd.Series(
        {gw: _top_k_stats(group, k, target_column=target_column)[1] for gw, group in df_eval.groupby("gameweek")},
        dtype=float,
    )


def _minute_bands(minutes: pd.Series) -> pd.Categorical:
    return pd.cut(
        minutes,
        bins=[-0.1, 0.0, 59.999, float("inf")],
        labels=_MINUTE_BAND_LABELS,
    )


def _validate_component_ledger(df_eval: pd.DataFrame) -> None:
    """Reject predictions or actuals that do not reconcile to total points."""
    predicted_columns = [component for component in _LEDGER_COMPONENTS if component in df_eval.columns]
    actual_columns = [f"actual_{component}" for component in _LEDGER_COMPONENTS if f"actual_{component}" in df_eval.columns]
    complete_ledger = (
        len(predicted_columns) == len(_LEDGER_COMPONENTS)
        and len(actual_columns) == len(_LEDGER_COMPONENTS)
    )
    if complete_ledger:
        predicted_residual = df_eval["projected_points"] - df_eval[predicted_columns].sum(axis=1)
        if not np.allclose(predicted_residual, 0.0, atol=1e-9):
            raise ValueError("Predicted component ledger does not reconcile to projected_points")
        actual_residual = df_eval["actual_points"] - df_eval[actual_columns].sum(axis=1)
        if not np.allclose(actual_residual, 0.0, atol=1e-9):
            raise ValueError("Actual component ledger does not reconcile to actual_points")


def evaluate_predictions(
    df_eval: pd.DataFrame,
    top_k_values: Iterable[int] = (11, 15),
    *,
    target_column: str = "actual_points",
) -> dict[str, object]:
    """Calculate forecast, ranking, and shortlist metrics.

    ``df_eval`` must already be at one row per player/gameweek. Missing actual
    rows should be represented as zero points before calling this function.

    ``target_column`` is usually ``actual_points`` (Realized Points) or
    ``process_points`` (Process Points; ADR 0038).
    """
    required = {"player_id", "gameweek", "projected_points", target_column}
    missing = required.difference(df_eval.columns)
    if missing:
        raise ValueError(f"Missing evaluation columns: {sorted(missing)}")
    if df_eval.empty:
        raise ValueError("Cannot evaluate an empty prediction frame")

    if target_column == "actual_points":
        _validate_component_ledger(df_eval)
    errors = df_eval["projected_points"] - df_eval[target_column]
    correlations: list[float] = []
    undefined_rank_gameweeks = 0
    for _, group in df_eval.groupby("gameweek"):
        if len(group) < 2:
            undefined_rank_gameweeks += 1
            continue
        correlation = group["projected_points"].corr(group[target_column], method="spearman")
        if pd.isna(correlation):
            undefined_rank_gameweeks += 1
        else:
            correlations.append(float(correlation))

    position_metrics: dict[str, dict[str, float]] = {}
    if "position_id" in df_eval.columns:
        for position_id, group in df_eval.groupby("position_id"):
            position_errors = group["projected_points"] - group[target_column]
            position_metrics[str(position_id)] = {
                "sample_count": float(len(group)),
                "mae": float(position_errors.abs().mean()),
                "bias": float(position_errors.mean()),
            }

    minutes_band_metrics: dict[str, dict[str, float]] = {}
    if "actual_minutes" in df_eval.columns:
        bands = _minute_bands(df_eval["actual_minutes"])
        for band, group in df_eval.groupby(bands, observed=True):
            band_errors = group["projected_points"] - group[target_column]
            minutes_band_metrics[str(band)] = {
                "sample_count": float(len(group)),
                "mae": float(band_errors.abs().mean()),
                "bias": float(band_errors.mean()),
            }

    minutes_forecast_metrics: dict[str, object] = {}
    if {"projected_minutes", "actual_minutes"}.issubset(df_eval.columns):
        minute_errors = df_eval["projected_minutes"] - df_eval["actual_minutes"]
        by_actual_band: dict[str, dict[str, float]] = {}
        for band, group in df_eval.groupby(_minute_bands(df_eval["actual_minutes"]), observed=True):
            band_errors = group["projected_minutes"] - group["actual_minutes"]
            by_actual_band[str(band)] = {
                "sample_count": float(len(group)),
                "mean_projected": float(group["projected_minutes"].mean()),
                "mean_actual": float(group["actual_minutes"].mean()),
                "mae": float(band_errors.abs().mean()),
                "bias": float(band_errors.mean()),
            }
        minutes_forecast_metrics = {
            "mean_projected": float(df_eval["projected_minutes"].mean()),
            "mean_actual": float(df_eval["actual_minutes"].mean()),
            "mae": float(minute_errors.abs().mean()),
            "bias": float(minute_errors.mean()),
            "rmse": float(np.sqrt(np.mean(minute_errors**2))),
            "by_actual_band": by_actual_band,
        }

    component_metrics: dict[str, dict[str, float]] = {}
    component_keys = list(_LEDGER_COMPONENTS)
    for comp in component_keys:
        act_col = f"actual_{comp}"
        if comp in df_eval.columns and act_col in df_eval.columns:
            comp_errors = df_eval[comp] - df_eval[act_col]
            component_metrics[comp] = {
                "mean_projected": float(df_eval[comp].mean()),
                "mean_actual": float(df_eval[act_col].mean()),
                "mae": float(comp_errors.abs().mean()),
                "bias": float(comp_errors.mean()),
                "rmse": float(np.sqrt(np.mean(comp_errors**2))),
            }

    metrics: dict[str, object] = {
        "sample_count": int(len(df_eval)),
        "eval_target": target_column,
        "mae": float(errors.abs().mean()),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "bias": float(errors.mean()),
        "spearman": float(np.mean(correlations)) if correlations else None,
        "valid_rank_gameweeks": len(correlations),
        "undefined_rank_gameweeks": undefined_rank_gameweeks,
        "samples_by_gameweek": {
            int(gameweek): int(len(group))
            for gameweek, group in df_eval.groupby("gameweek")
        },
        "position_metrics": position_metrics,
        "minutes_band_metrics": minutes_band_metrics,
        "minutes_forecast_metrics": minutes_forecast_metrics,
        "component_metrics": component_metrics,
    }

    for k in top_k_values:
        overlaps: list[float] = []
        regrets: list[float] = []
        for _, group in df_eval.groupby("gameweek"):
            overlap, regret = _top_k_stats(group, k, target_column=target_column)
            if len(group) > 0:
                overlaps.append(overlap)
                regrets.append(regret)
        metrics[f"top_{k}_overlap"] = float(np.mean(overlaps)) if overlaps else None
        metrics[f"top_{k}_regret"] = float(np.mean(regrets)) if regrets else None

    if "position_id" in df_eval.columns:
        f_overlaps: list[float] = []
        f_regrets: list[float] = []
        f_cap_regrets: list[float] = []
        for _, group in df_eval.groupby("gameweek"):
            if len(group) > 0:
                overlap, regret, cap_regret = _formation_xi_stats(group, target_column=target_column)
                f_overlaps.append(overlap)
                f_regrets.append(regret)
                f_cap_regrets.append(cap_regret)
        metrics["formation_xi_overlap"] = float(np.mean(f_overlaps)) if f_overlaps else None
        metrics["formation_xi_regret"] = float(np.mean(f_regrets)) if f_regrets else None
        metrics["captain_regret"] = float(np.mean(f_cap_regrets)) if f_cap_regrets else None

        if "now_cost" in df_eval.columns:
            churn_series = compute_top_15_squad_churn_by_gameweek(df_eval, "projected_points")
            metrics["top_15_squad_churn"] = float(churn_series.mean()) if len(churn_series) > 0 else None

    return metrics
