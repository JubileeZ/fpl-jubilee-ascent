import pandas as pd
from pathlib import Path

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
