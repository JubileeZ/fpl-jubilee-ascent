from pathlib import Path

import pandas as pd

MAX_SOLVER_GAMEWEEK = 38


def export_projections(
    predictions_df: pd.DataFrame, 
    players_df: pd.DataFrame, 
    clubs_df: pd.DataFrame,
    output_path: Path
):
    """
    Exports a ProjectionContract DataFrame to the solver-ready CSV format.
    
    Expected predictions_df schema:
        - player_id (int)
        - fixture_id (int, optional)
        - gameweek_id (int)
        - projected_points (float)
        - projected_minutes (float)
    """
    # 1. Map player details
    pos_map = {1: "G", 2: "D", 3: "M", 4: "F"}
    
    df_players = players_df.copy()
    df_players["Pos"] = df_players["position_id"].map(pos_map)
    df_players["Price"] = df_players["now_cost"] / 10.0
    
    df_players = df_players.merge(clubs_df[["id", "short_name"]], left_on="club_id", right_on="id", how="left")
    df_players = df_players.rename(columns={"short_name": "Team", "id_x": "ID"})
    
    # 2. Aggregate fixture rows before pivoting to the solver's gameweek grain.
    # This preserves double-gameweek returns while keeping one solver value per
    # player/gameweek.
    grouped = (
        predictions_df.groupby(["player_id", "gameweek_id"], as_index=False)[
            ["projected_points", "projected_minutes"]
        ]
        .sum()
    )
    df_pivot_pts = grouped.pivot(index="player_id", columns="gameweek_id", values="projected_points")
    df_pivot_pts.columns = [f"{gw}_Pts" for gw in df_pivot_pts.columns]
    
    df_pivot_mins = grouped.pivot(index="player_id", columns="gameweek_id", values="projected_minutes")
    df_pivot_mins.columns = [f"{gw}_xMins" for gw in df_pivot_mins.columns]
    
    # Merge pivots
    df_pivoted = df_pivot_pts.join(df_pivot_mins)
    df_pivoted = df_pivoted.reset_index().rename(columns={"player_id": "ID"})
    
    # 3. Merge metadata with pivoted predictions
    meta_cols = ["ID", "web_name", "Pos", "Price", "Team"]
    if "code" in df_players.columns:
        meta_cols.append("code")
    df_out = df_players[meta_cols].merge(df_pivoted, on="ID", how="inner")
    df_out = df_out.rename(columns={"web_name": "Name"})
    
    # Save to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_path, index=False)


def solver_csv_covers_horizon(csv_path: Path, target_gw: int, horizon: int) -> bool:
    """True when CSV has `{week}_Pts` for every week the MILP will request."""
    if not csv_path.exists():
        return False
    columns = set(pd.read_csv(csv_path, nrows=0).columns)
    last_gw = min(MAX_SOLVER_GAMEWEEK, target_gw + horizon - 1)
    return all(f"{week}_Pts" in columns for week in range(target_gw, last_gw + 1))


def pad_solver_csv_horizon(csv_path: Path, target_gw: int, horizon: int) -> Path:
    """Add missing `{week}_Pts` / `{week}_xMins` columns so prep_data can load the horizon."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Data file {csv_path.name} not found in {csv_path.parent}.")
    df = pd.read_csv(csv_path)
    last_gw = min(MAX_SOLVER_GAMEWEEK, target_gw + horizon - 1)
    changed = False
    for week in range(target_gw, last_gw + 1):
        pts_col = f"{week}_Pts"
        mins_col = f"{week}_xMins"
        if pts_col not in df.columns:
            df[pts_col] = 0.0
            changed = True
        if mins_col not in df.columns:
            df[mins_col] = 0.0
            changed = True
    if changed:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False)
    return csv_path


def write_solver_projection_csvs(
    predictions_by_model: dict[str, pd.DataFrame],
    players_df: pd.DataFrame,
    clubs_df: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    """Write one solver ProjectionContract CSV per model name under output_dir."""
    paths: list[Path] = []
    for model_name, predictions_df in predictions_by_model.items():
        path = output_dir / f"{model_name}.csv"
        export_projections(predictions_df, players_df, clubs_df, path)
        paths.append(path)
    return paths
