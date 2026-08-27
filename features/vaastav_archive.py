"""Map vaastav FPL CSVs into archive processed Parquet (Prior-Season Seed)."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_CLUB_COLS = [
    "id",
    "name",
    "short_name",
    "strength",
    "strength_overall_home",
    "strength_overall_away",
    "strength_attack_home",
    "strength_attack_away",
    "strength_defence_home",
    "strength_defence_away",
]
_PLAYER_COLS = [
    "id",
    "code",
    "first_name",
    "second_name",
    "web_name",
    "club_id",
    "position_id",
    "now_cost",
    "status",
    "chance_of_playing_next_round",
    "chance_of_playing_this_round",
    "news",
    "news_added",
    "selected_by_percent",
    "corners_and_indirect_freekicks_order",
    "direct_freekicks_order",
    "penalties_order",
    "total_points",
    "minutes",
    "goals_scored",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "own_goals",
    "penalties_saved",
    "penalties_missed",
    "yellow_cards",
    "red_cards",
    "saves",
    "bonus",
    "bps",
    "influence",
    "creativity",
    "threat",
    "ict_index",
    "starts",
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "expected_goals_conceded",
]
_PERF_COLS = [
    "player_id",
    "fixture_id",
    "gameweek_id",
    "opponent_club_id",
    "was_home",
    "kickoff_time",
    "team_h_score",
    "team_a_score",
    "price",
    "selected",
    "transfers_balance",
    "transfers_in",
    "transfers_out",
    "minutes",
    "total_points",
    "goals_scored",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "own_goals",
    "penalties_saved",
    "penalties_missed",
    "yellow_cards",
    "red_cards",
    "saves",
    "bonus",
    "bps",
    "influence",
    "creativity",
    "threat",
    "ict_index",
    "starts",
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "expected_goals_conceded",
    "defensive_contribution",
]
_FIX_COLS = [
    "id",
    "gameweek_id",
    "kickoff_time",
    "home_club_id",
    "away_club_id",
    "finished",
    "started",
    "team_h_score",
    "team_a_score",
    "team_h_difficulty",
    "team_a_difficulty",
]


def _require_file(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"vaastav file not found: {path}")
    return path


def _keep(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return df[[c for c in columns if c in df.columns]].copy()


def process_vaastav_directory(input_dir: Path, output_dir: Path) -> Path:
    """Write clubs/players/fixtures/gameweeks/player_performances parquet from vaastav CSVs."""
    root = Path(input_dir)
    players_path = _require_file(root / "players_raw.csv")
    teams_path = _require_file(root / "teams.csv")
    fixtures_path = _require_file(root / "fixtures.csv")
    merged_path = root / "gws" / "merged_gw.csv"
    if not merged_path.exists():
        merged_path = _require_file(root / "merged_gw.csv")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    clubs = pd.read_csv(teams_path)
    clubs = _keep(clubs, _CLUB_COLS)
    clubs.to_parquet(output_dir / "clubs.parquet", index=False)
    logger.info("Processed %s clubs -> clubs.parquet", len(clubs))

    players = pd.read_csv(players_path)
    players = players.rename(columns={"team": "club_id", "element_type": "position_id"})
    players = _keep(players, _PLAYER_COLS)
    players.to_parquet(output_dir / "players.parquet", index=False)
    logger.info("Processed %s players -> players.parquet", len(players))

    fixtures = pd.read_csv(fixtures_path)
    fixtures = fixtures.rename(columns={"event": "gameweek_id", "team_h": "home_club_id", "team_a": "away_club_id"})
    fixtures = _keep(fixtures, _FIX_COLS)
    fixtures.to_parquet(output_dir / "fixtures.parquet", index=False)
    logger.info("Processed %s fixtures -> fixtures.parquet", len(fixtures))

    gw_ids = sorted({int(g) for g in fixtures["gameweek_id"].dropna().tolist()}) if "gameweek_id" in fixtures.columns else []
    gameweeks = pd.DataFrame(
        [{"id": gw, "name": f"Gameweek {gw}", "finished": True, "is_current": False, "is_next": False} for gw in gw_ids]
    )
    gameweeks.to_parquet(output_dir / "gameweeks.parquet", index=False)

    performances = pd.read_csv(merged_path)
    if "round" in performances.columns:
        gw_col = "round"
    elif "GW" in performances.columns:
        gw_col = "GW"
    else:
        raise ValueError("vaastav merged_gw.csv needs round or GW")
    performances = performances.rename(
        columns={
            "element": "player_id",
            "fixture": "fixture_id",
            gw_col: "gameweek_id",
            "opponent_team": "opponent_club_id",
            "value": "price",
        }
    )
    if "GW" in performances.columns and gw_col != "GW":
        performances = performances.drop(columns=["GW"])
    performances = _keep(performances, _PERF_COLS)
    performances.to_parquet(output_dir / "player_performances.parquet", index=False)
    logger.info("Processed %s player performances -> player_performances.parquet", len(performances))
    return output_dir
