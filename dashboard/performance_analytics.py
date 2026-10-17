"""Analytical calculations for manager performance tracking, deltas, and chip attribution."""

from __future__ import annotations

from typing import Any
import pandas as pd

CHIP_NAME_MAP: dict[str, str] = {
    "wildcard": "WC",
    "bboost": "BB",
    "freehit": "FH",
    "3xc": "TC",
    "manager": "AM",
}

CHIP_SYMBOLS: dict[str, str] = {
    "WC": "diamond",
    "FH": "triangle-up",
    "BB": "square",
    "TC": "star",
    "AM": "circle",
}


def normalize_chip_name(name: str | None) -> str | None:
    if not name:
        return None
    cleaned = str(name).strip().lower()
    return CHIP_NAME_MAP.get(cleaned, cleaned.upper())


def compute_manager_series(
    history_data: dict[str, Any],
    global_benchmarks: dict[int, dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Transform /entry/{id}/history/ JSON into a clean per-Gameweek DataFrame."""
    current = history_data.get("current") or []
    if not current:
        return pd.DataFrame()

    chips_played = history_data.get("chips") or []
    # Map event -> chip short name
    chip_by_event: dict[int, str] = {}
    for c in chips_played:
        ev = int(c.get("event") or 0)
        c_name = normalize_chip_name(c.get("name"))
        if ev > 0 and c_name:
            chip_by_event[ev] = c_name

    benchmarks = global_benchmarks or {}

    rows: list[dict[str, Any]] = []
    for entry in current:
        gw = int(entry.get("event") or 0)
        pts = int(entry.get("points") or 0)
        cost = int(entry.get("event_transfers_cost") or 0)
        net_pts = pts - cost
        total_pts = int(entry.get("total_points") or 0)
        overall_rank = int(entry.get("overall_rank") or 0)
        gw_rank = int(entry.get("rank") or 0)
        bank = float(entry.get("bank") or 0) / 10.0
        val = float(entry.get("value") or 0) / 10.0
        bench = int(entry.get("points_on_bench") or 0)
        chip = chip_by_event.get(gw)

        gw_bench = benchmarks.get(gw, {})
        global_avg = gw_bench.get("average_entry_score")
        global_high = gw_bench.get("highest_score")
        ranked_count = gw_bench.get("ranked_count")

        delta_vs_global = (net_pts - global_avg) if global_avg is not None else None

        rows.append(
            {
                "gw": gw,
                "points": pts,
                "cost": cost,
                "net_points": net_pts,
                "total_points": total_pts,
                "overall_rank": overall_rank,
                "gw_rank": gw_rank,
                "bank": bank,
                "team_value": val,
                "bench_points": bench,
                "chip": chip,
                "global_avg": global_avg,
                "global_high": global_high,
                "ranked_count": ranked_count,
                "delta_vs_global": delta_vs_global,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty and "delta_vs_global" in df.columns:
        df["cum_delta_vs_global"] = df["delta_vs_global"].fillna(0).cumsum()
        df["rank_change"] = -df["overall_rank"].diff().fillna(0)  # positive means rank improved
    return df


def compute_rival_series_dict(
    rival_histories: dict[int, dict[str, Any]],
    global_benchmarks: dict[int, dict[str, Any]] | None = None,
) -> dict[int, pd.DataFrame]:
    """Compute per-GW series for all selected rivals."""
    out: dict[int, pd.DataFrame] = {}
    for eid, hist in rival_histories.items():
        rdf = compute_manager_series(hist, global_benchmarks=global_benchmarks)
        if not rdf.empty:
            out[eid] = rdf
    return out


def compute_composite_comparison_series(
    user_df: pd.DataFrame,
    rival_dfs: dict[int, pd.DataFrame],
) -> pd.DataFrame:
    """Align user and rival net points, calculating rivals mean and deltas."""
    if user_df.empty:
        return user_df

    df = user_df.copy()
    if not rival_dfs:
        df["rivals_mean"] = None
        df["delta_vs_rivals_mean"] = None
        df["cum_delta_vs_rivals_mean"] = None
        return df

    # Map gw -> list of rival net points
    rival_gw_points: dict[int, list[int]] = {}
    for _, rdf in rival_dfs.items():
        for _, row in rdf.iterrows():
            gw = int(row["gw"])
            rival_gw_points.setdefault(gw, []).append(int(row["net_points"]))

    rivals_means: list[float | None] = []
    deltas: list[float | None] = []
    for _, row in df.iterrows():
        gw = int(row["gw"])
        r_pts = rival_gw_points.get(gw, [])
        if r_pts:
            m = sum(r_pts) / len(r_pts)
            rivals_means.append(round(m, 1))
            deltas.append(round(row["net_points"] - m, 1))
        else:
            rivals_means.append(None)
            deltas.append(None)

    df["rivals_mean"] = rivals_means
    df["delta_vs_rivals_mean"] = deltas
    df["cum_delta_vs_rivals_mean"] = df["delta_vs_rivals_mean"].fillna(0).cumsum()
    return df


def compute_chip_timing_differential(
    user_df: pd.DataFrame,
    benchmark_col: str = "global_avg",
) -> dict[str, Any]:
    """Calculate point differential earned above benchmark on chip weeks vs non-chip weeks."""
    if user_df.empty:
        return {"chip_weeks": 0, "chip_delta_sum": 0, "chip_swing": 0, "regular_delta_mean": 0.0}

    chip_mask = user_df["chip"].notna()
    chip_rows = user_df[chip_mask]
    regular_rows = user_df[~chip_mask]

    delta_col = f"delta_vs_{benchmark_col.replace('global_avg', 'global').replace('rivals_mean', 'rivals_mean')}"
    if delta_col not in user_df.columns:
        delta_col = "delta_vs_global"

    if delta_col not in user_df.columns or user_df[delta_col].dropna().empty:
        return {"chip_weeks": len(chip_rows), "chip_delta_sum": 0, "chip_swing": 0, "regular_delta_mean": 0.0}

    chip_deltas = chip_rows[delta_col].dropna()
    regular_deltas = regular_rows[delta_col].dropna()

    chip_delta_sum = int(chip_deltas.sum()) if not chip_deltas.empty else 0
    regular_delta_mean = float(regular_deltas.mean()) if not regular_deltas.empty else 0.0

    # Net Chip Swing = total delta on chip weeks minus expected regular delta across those weeks
    expected_regular_pts = regular_delta_mean * len(chip_rows)
    chip_swing = round(chip_delta_sum - expected_regular_pts, 1)

    return {
        "chip_weeks": len(chip_rows),
        "chip_delta_sum": chip_delta_sum,
        "chip_swing": chip_swing,
        "regular_delta_mean": round(regular_delta_mean, 1),
    }


def extract_chip_inventory(history_data: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Determine status of Set 1 (GW1–19) and Set 2 (GW20–38) chips."""
    chips_played = history_data.get("chips") or []
    # Identify played chips by type and event
    played_chips: list[tuple[str, int]] = []
    for c in chips_played:
        c_code = normalize_chip_name(c.get("name"))
        ev = int(c.get("event") or 0)
        if c_code and ev > 0:
            played_chips.append((c_code, ev))

    inventory: dict[str, dict[str, str]] = {}
    for chip in ("WC", "BB", "FH", "TC"):
        events_for_chip = [ev for (c, ev) in played_chips if c == chip]
        set1_ev = next((ev for ev in events_for_chip if ev <= 19), None)
        set2_ev = next((ev for ev in events_for_chip if ev >= 20), None)

        set1_status = f"Played GW{set1_ev}" if set1_ev else "Available"
        set2_status = f"Played GW{set2_ev}" if set2_ev else "Available"

        inventory[chip] = {
            "Set 1 (GW1–19)": set1_status,
            "Set 2 (GW20–38)": set2_status,
        }
    return inventory


def compute_kpis(
    user_df: pd.DataFrame,
    summary: dict[str, Any],
    league_standings: dict[str, Any] | None = None,
    benchmark_col: str = "global_avg",
) -> dict[str, Any]:
    """Compute headline KPI strip metrics."""
    if user_df.empty:
        return {}

    last_row = user_df.iloc[-1]
    prev_row = user_df.iloc[-2] if len(user_df) >= 2 else None

    current_overall_rank = int(last_row["overall_rank"])
    prev_overall_rank = int(prev_row["overall_rank"]) if prev_row is not None else current_overall_rank
    rank_delta = prev_overall_rank - current_overall_rank  # positive = climb

    ranked_count = int(last_row.get("ranked_count") or 10_000_000)
    percentile = (current_overall_rank / ranked_count) * 100.0 if ranked_count > 0 else 0.0

    cum_net_points = int(last_row["total_points"])
    total_hits_cost = int(user_df["cost"].sum())
    total_bench_points = int(user_df["bench_points"].sum())

    chip_diff = compute_chip_timing_differential(user_df, benchmark_col=benchmark_col)

    # Mini-league metrics if standings provided
    league_leader_gap: int | None = None
    league_rank: int | None = None
    if league_standings:
        results = (league_standings.get("standings") or {}).get("results") or []
        user_id = int(summary.get("id") or 0)
        user_result = next((r for r in results if int(r.get("entry") or 0) == user_id), None)
        if user_result:
            league_rank = int(user_result.get("rank") or 0)
            if results:
                leader_total = int(results[0].get("total") or 0)
                league_leader_gap = leader_total - int(user_result.get("total") or 0)

    return {
        "overall_rank": current_overall_rank,
        "rank_delta": rank_delta,
        "percentile": round(percentile, 1),
        "cum_net_points": cum_net_points,
        "total_hits_cost": total_hits_cost,
        "total_bench_points": total_bench_points,
        "chip_swing": chip_diff["chip_swing"],
        "chip_weeks": chip_diff["chip_weeks"],
        "league_rank": league_rank,
        "league_leader_gap": league_leader_gap,
    }
