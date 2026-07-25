import json
import logging
import pandas as pd
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading {path}: {e}")
        return None

def process_directory(input_dir: Path, output_dir: Path):
    """Processes raw FPL JSON cache in input_dir and saves Parquet tables to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Load Bootstrap Static
    bs_path = input_dir / "bootstrap_static.json"
    bootstrap = load_json(bs_path)
    if not bootstrap:
        logger.error(f"bootstrap_static.json not found in {input_dir}. Cannot process.")
        return
        
    # --- Clubs ---
    teams = bootstrap.get("teams", [])
    if teams:
        df_clubs = pd.DataFrame(teams)
        keep_club_cols = [
            "id", "name", "short_name", "strength", 
            "strength_overall_home", "strength_overall_away", 
            "strength_attack_home", "strength_attack_away", 
            "strength_defence_home", "strength_defence_away"
        ]
        df_clubs = df_clubs[[c for c in keep_club_cols if c in df_clubs.columns]]
        df_clubs.to_parquet(output_dir / "clubs.parquet", index=False)
        logger.info(f"Processed {len(df_clubs)} clubs -> clubs.parquet")

    # --- Gameweeks ---
    events = bootstrap.get("events", [])
    if events:
        df_gw = pd.DataFrame(events)
        keep_gw_cols = ["id", "name", "deadline_time", "finished", "is_current", "is_next"]
        df_gw = df_gw[[c for c in keep_gw_cols if c in df_gw.columns]]
        df_gw.to_parquet(output_dir / "gameweeks.parquet", index=False)
        logger.info(f"Processed {len(df_gw)} gameweeks -> gameweeks.parquet")
        
    # Determine current gameweek
    current_gw = next((e["id"] for e in events if e.get("is_current")), None)

    # --- Players ---
    elements = bootstrap.get("elements", [])
    if elements:
        df_players = pd.DataFrame(elements)
        # Rename FPL element fields to data dictionary fields
        df_players = df_players.rename(columns={
            "team": "club_id",
            "element_type": "position_id"
        })
        keep_player_cols = [
            "id", "code", "first_name", "second_name", "web_name", "club_id", "position_id",
            "now_cost", "status", "chance_of_playing_next_round", "chance_of_playing_this_round",
            "news", "news_added", "selected_by_percent",
            "corners_and_indirect_freekicks_order", "direct_freekicks_order", "penalties_order",
            # Season Totals
            "total_points", "minutes", "goals_scored", "assists", "clean_sheets",
            "goals_conceded", "own_goals", "penalties_saved", "penalties_missed",
            "yellow_cards", "red_cards", "saves", "bonus", "bps", "influence",
            "creativity", "threat", "ict_index", "starts", "expected_goals",
            "expected_assists", "expected_goal_involvements", "expected_goals_conceded"
        ]
        df_players = df_players[[c for c in keep_player_cols if c in df_players.columns]]
        df_players.to_parquet(output_dir / "players.parquet", index=False)
        logger.info(f"Processed {len(df_players)} players -> players.parquet")

    # --- Fixtures ---
    # Try multiple fixture file patterns
    fixtures = None
    for fix_file in ["fixtures_all.json", "fixtures_gw_None.json", "fixtures.json"]:
        fixtures = load_json(input_dir / fix_file)
        if fixtures:
            break
            
    if fixtures:
        df_fix = pd.DataFrame(fixtures)
        df_fix = df_fix.rename(columns={"event": "gameweek_id", "team_h": "home_club_id", "team_a": "away_club_id"})
        keep_fix_cols = [
            "id", "gameweek_id", "kickoff_time", "home_club_id", "away_club_id",
            "finished", "started", "team_h_score", "team_a_score",
            "team_h_difficulty", "team_a_difficulty"
        ]
        df_fix_sub = df_fix[[c for c in keep_fix_cols if c in df_fix.columns]].copy()
        
        # Add serialized raw stats
        if "stats" in df_fix.columns:
            df_fix_sub["raw_stats"] = df_fix["stats"].apply(lambda x: json.dumps(x) if isinstance(x, list | dict) else x)
            
        df_fix_sub.to_parquet(output_dir / "fixtures.parquet", index=False)
        logger.info(f"Processed {len(df_fix_sub)} fixtures -> fixtures.parquet")

    # --- Player Performances ---
    performances = []
    # Search for all element_summary_*.json files
    summary_files = list(input_dir.glob("element_summary_*.json"))
    for sf in summary_files:
        summary_data = load_json(sf)
        if not summary_data:
            continue
        history = summary_data.get("history", [])
        for perf in history:
            performances.append(perf)
            
    if performances:
        df_perf = pd.DataFrame(performances)
        df_perf = df_perf.rename(columns={
            "element": "player_id",
            "fixture": "fixture_id",
            "round": "gameweek_id",
            "opponent_team": "opponent_club_id",
            "value": "price"
        })
        keep_perf_cols = [
            "player_id", "fixture_id", "gameweek_id", "opponent_club_id", "was_home",
            "kickoff_time", "team_h_score", "team_a_score", "price", "selected",
            "transfers_balance", "transfers_in", "transfers_out",
            "minutes", "total_points", "goals_scored", "assists", "clean_sheets",
            "goals_conceded", "own_goals", "penalties_saved", "penalties_missed",
            "yellow_cards", "red_cards", "saves", "bonus", "bps", "influence",
            "creativity", "threat", "ict_index", "starts", "expected_goals",
            "expected_assists", "expected_goal_involvements", "expected_goals_conceded",
            "defensive_contribution"
        ]
        df_perf = df_perf[[c for c in keep_perf_cols if c in df_perf.columns]]
        df_perf.to_parquet(output_dir / "player_performances.parquet", index=False)
        logger.info(f"Processed {len(df_perf)} individual player performances -> player_performances.parquet")

    # --- User Picks & State ---
    # Find any my_team_*.json file
    team_files = list(input_dir.glob("my_team_*.json"))
    if team_files:
        team_data = load_json(team_files[0])
        entry_id = int(team_files[0].stem.split("_")[-1])
        
        # User Picks
        picks = team_data.get("picks", [])
        if picks:
            df_picks = pd.DataFrame(picks)
            df_picks = df_picks.rename(columns={
                "element": "player_id",
                "position": "lineup_index"
            })
            df_picks["entry_id"] = entry_id
            df_picks["gameweek_id"] = current_gw or 0
            
            # Derived fields
            df_picks["is_captain"] = df_picks["multiplier"].apply(lambda m: m in [2, 3])
            df_picks["is_vice_captain"] = df_picks.get("is_vice_captain", False)
            
            keep_picks_cols = [
                "entry_id", "gameweek_id", "player_id", "lineup_index",
                "multiplier", "is_captain", "is_vice_captain", "purchase_price", "selling_price"
            ]
            df_picks = df_picks[[c for c in keep_picks_cols if c in df_picks.columns]]
            df_picks.to_parquet(output_dir / "user_picks.parquet", index=False)
            logger.info(f"Processed {len(df_picks)} user picks -> user_picks.parquet")
            
        # User State
        transfers = team_data.get("transfers", {})
        chips = team_data.get("chips", [])
        
        # Find active chip if any
        active_chip = None
        for c in chips:
            if c.get("status") == "active":
                active_chip = c.get("name")
                break
                
        user_state_data = {
            "entry_id": entry_id,
            "bank": transfers.get("bank", 0),
            "value": transfers.get("value", 0),
            "free_transfers": transfers.get("limit", 1),
            "active_chip": active_chip
        }
        df_state = pd.DataFrame([user_state_data])
        df_state.to_parquet(output_dir / "user_state.parquet", index=False)
        logger.info("Processed user state -> user_state.parquet")
