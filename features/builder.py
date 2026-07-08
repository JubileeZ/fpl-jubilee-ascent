import pandas as pd
from pathlib import Path

EVENT_RATE_MAP = [
    ("goals_scored", "per90_goals"),
    ("assists", "per90_assists"),
    ("clean_sheets", "per90_clean_sheets"),
    ("goals_conceded", "per90_goals_conceded"),
    ("own_goals", "per90_own_goals"),
    ("penalties_saved", "per90_penalties_saved"),
    ("penalties_missed", "per90_penalties_missed"),
    ("yellow_cards", "per90_yellow_cards"),
    ("red_cards", "per90_red_cards"),
    ("saves", "per90_saves"),
    ("bonus", "per90_bonus"),
]
RATE_COLS = [rate_col for _, rate_col in EVENT_RATE_MAP]
BLEND_START_APPEARANCES = 3
BLEND_FULL_APPEARANCES = 8


def _price_band(now_cost: float) -> int:
    return int(float(now_cost) // 10)


def _latest_archive_processed_dir(processed_dir: Path) -> Path | None:
    archive_root = processed_dir.parent / "archive"
    if not archive_root.exists():
        return None
    candidates = []
    for season_dir in archive_root.iterdir():
        candidate = season_dir / "processed"
        if (
            candidate.exists()
            and (candidate / "player_performances.parquet").exists()
            and (candidate / "players.parquet").exists()
        ):
            candidates.append(candidate)
    return sorted(candidates)[-1] if candidates else None


def _compute_player_rates(df_perf: pd.DataFrame, player_id: int) -> tuple[dict[str, float], float, int]:
    player_hist = df_perf[df_perf["player_id"] == player_id]
    if player_hist.empty:
        return ({col: 0.0 for col in RATE_COLS}, 0.0, 0)
    total_minutes = float(player_hist["minutes"].sum())
    appearances = int((player_hist["minutes"] > 0).sum())
    avg_minutes = float(player_hist["minutes"].mean()) if len(player_hist) > 0 else 0.0
    rates = {}
    for raw_col, rate_col in EVENT_RATE_MAP:
        if raw_col in player_hist.columns and total_minutes > 0:
            rates[rate_col] = float(player_hist[raw_col].sum()) / total_minutes * 90.0
        else:
            rates[rate_col] = 0.0
    return rates, avg_minutes, appearances


def _compute_position_price_priors(df_perf: pd.DataFrame, df_players: pd.DataFrame) -> tuple[dict[tuple[int, int], dict], dict[int, dict]]:
    if df_perf.empty:
        return {}, {}
    perf = df_perf.copy()
    meta = df_players[["id", "position_id", "now_cost"]].rename(columns={"id": "player_id"})
    perf = perf.merge(meta, on="player_id", how="left")
    perf = perf.dropna(subset=["position_id", "now_cost"])
    if perf.empty:
        return {}, {}
    perf["price_band"] = perf["now_cost"].map(_price_band)

    priors_by_band: dict[tuple[int, int], dict] = {}
    priors_by_position: dict[int, dict] = {}

    for (position_id, band), grp in perf.groupby(["position_id", "price_band"]):
        total_minutes = float(grp["minutes"].sum())
        rates = {}
        for raw_col, rate_col in EVENT_RATE_MAP:
            if raw_col in grp.columns and total_minutes > 0:
                rates[rate_col] = float(grp[raw_col].sum()) / total_minutes * 90.0
            else:
                rates[rate_col] = 0.0
        priors_by_band[(int(position_id), int(band))] = {
            "avg_minutes": float(grp["minutes"].mean()) if len(grp) > 0 else 0.0,
            "rates": rates,
        }

    for position_id, grp in perf.groupby("position_id"):
        total_minutes = float(grp["minutes"].sum())
        rates = {}
        for raw_col, rate_col in EVENT_RATE_MAP:
            if raw_col in grp.columns and total_minutes > 0:
                rates[rate_col] = float(grp[raw_col].sum()) / total_minutes * 90.0
            else:
                rates[rate_col] = 0.0
        priors_by_position[int(position_id)] = {
            "avg_minutes": float(grp["minutes"].mean()) if len(grp) > 0 else 0.0,
            "rates": rates,
        }
    return priors_by_band, priors_by_position

def build_features(processed_dir: Path, target_gw: int) -> pd.DataFrame:
    """
    Compiles a FeatureContract DataFrame for a target gameweek.
    
    Contains historical rolling stats and upcoming fixture metadata.
    """
    # 1. Load Parquet tables
    df_players = pd.read_parquet(processed_dir / "players.parquet")
    df_fixtures = pd.read_parquet(processed_dir / "fixtures.parquet")
    df_clubs = pd.read_parquet(processed_dir / "clubs.parquet")
    
    perf_path = processed_dir / "player_performances.parquet"
    if perf_path.exists():
        df_perf = pd.read_parquet(perf_path)
    else:
        df_perf = pd.DataFrame(columns=["player_id", "gameweek_id", "total_points", "minutes"])

    df_players = df_players.rename(columns={"id": "player_id"})
    
    # 2. Compute current-season historical features (pre-target_gw)
    df_hist = df_perf[df_perf["gameweek_id"] < target_gw]

    # Simple rolling GW averages
    rolling_stats = []
    for pid in df_players["player_id"].unique():
        p_hist = df_hist[df_hist["player_id"] == pid].sort_values("gameweek_id", ascending=False)
        if len(p_hist) > 0:
            avg_pts_3gw = p_hist.head(3)["total_points"].mean()
            avg_mins_3gw = p_hist.head(3)["minutes"].mean()
        else:
            avg_pts_3gw = 0.0
            avg_mins_3gw = 0.0
        rolling_stats.append({
            "player_id": pid,
            "avg_points_3gw": float(avg_pts_3gw),
            "avg_mins_3gw": float(avg_mins_3gw)
        })
    df_rolling = pd.DataFrame(rolling_stats)

    # 3. Prior-season seed + Position-Price fallback + current-season blend.
    # ponytail: if archive data exists, use it as the seed source. If missing
    # (tests/sandbox), fallback to current-season pre-target history.
    archive_processed = _latest_archive_processed_dir(processed_dir)
    if archive_processed is not None:
        df_seed_perf = pd.read_parquet(archive_processed / "player_performances.parquet")
        df_seed_players = pd.read_parquet(archive_processed / "players.parquet")
    else:
        df_seed_perf = df_hist.copy()
        df_seed_players = df_players.rename(columns={"player_id": "id"}).copy()

    priors_by_band, priors_by_position = _compute_position_price_priors(df_seed_perf, df_seed_players)
    cold_start_disable_player_seed = target_gw <= 4

    seed_rows = []
    for _, player_row in df_players.iterrows():
        pid = int(player_row["player_id"])
        position_id = int(player_row["position_id"])
        band = _price_band(player_row.get("now_cost", 0))

        prior_rates, prior_avg_minutes, _ = _compute_player_rates(df_seed_perf, pid)
        has_player_prior = prior_avg_minutes > 0

        band_prior = priors_by_band.get((position_id, band))
        pos_prior = priors_by_position.get(position_id)
        fallback_prior = band_prior or pos_prior

        if has_player_prior and not cold_start_disable_player_seed:
            base_rates = prior_rates
            base_minutes = prior_avg_minutes
            has_seed = True
        elif fallback_prior is not None:
            base_rates = fallback_prior["rates"]
            base_minutes = float(fallback_prior["avg_minutes"])
            has_seed = True
        else:
            base_rates = {col: 0.0 for col in RATE_COLS}
            base_minutes = 0.0
            has_seed = False

        current_rates, current_avg_minutes, appearances = _compute_player_rates(df_hist, pid)
        if appearances < BLEND_START_APPEARANCES:
            current_weight = 0.0
        else:
            # ponytail: linear blend ramps to full current-season rates by ~8 apps.
            denom = max(1, BLEND_FULL_APPEARANCES - BLEND_START_APPEARANCES)
            current_weight = min(1.0, float(appearances - BLEND_START_APPEARANCES) / float(denom))
        prior_weight = 1.0 - current_weight

        row = {
            "player_id": pid,
            "has_prior_seed": has_seed,
            # Seed/backfill minutes for Cold-Start rows where rolling avg mins is 0.
            "seed_avg_mins": prior_weight * base_minutes + current_weight * current_avg_minutes,
        }
        for rate_col in RATE_COLS:
            row[rate_col] = prior_weight * float(base_rates.get(rate_col, 0.0)) + current_weight * float(current_rates.get(rate_col, 0.0))
        seed_rows.append(row)
    df_seed = pd.DataFrame(seed_rows)

    df_rolling = df_rolling.merge(df_seed, on="player_id", how="left")
    for rc in RATE_COLS:
        df_rolling[rc] = df_rolling[rc].fillna(0.0)
    # Keep recent rolling minutes when present; only backfill Cold-Start rows.
    df_rolling["avg_mins_3gw"] = (
        df_rolling["avg_mins_3gw"]
        .where(df_rolling["avg_mins_3gw"] > 0.0, df_rolling["seed_avg_mins"])
        .fillna(0.0)
    )
    df_rolling = df_rolling.drop(columns=["seed_avg_mins"], errors="ignore")
    df_rolling["has_prior_seed"] = df_rolling["has_prior_seed"].fillna(False)

    # 4. Merge player metadata
    df_feat = df_players.merge(df_rolling, on="player_id", how="left")
    
    # 5. Map strength from clubs
    df_clubs_sub = df_clubs[["id", "strength"]].rename(columns={"id": "club_id", "strength": "team_strength"})
    df_feat = df_feat.merge(df_clubs_sub, on="club_id", how="left")

    # 6. Extract upcoming fixtures for target_gw
    df_target_fixtures = df_fixtures[df_fixtures["gameweek_id"] == target_gw]
    
    # Build maps for home/away fixtures
    fixture_maps = []
    for _, f in df_target_fixtures.iterrows():
        # Home team perspective
        fixture_maps.append({
            "club_id": f["home_club_id"],
            "opponent_id": f["away_club_id"],
            "is_home": True,
            "difficulty": f["team_h_difficulty"]
        })
        # Away team perspective
        fixture_maps.append({
            "club_id": f["away_club_id"],
            "opponent_id": f["home_club_id"],
            "is_home": False,
            "difficulty": f["team_a_difficulty"]
        })
    df_fmap = pd.DataFrame(fixture_maps)
    
    df_feat = df_feat.merge(df_fmap, on="club_id", how="left")
    
    # Fill NAs
    df_feat["is_home"] = df_feat["is_home"].fillna(False)
    df_feat["difficulty"] = df_feat["difficulty"].fillna(3.0)
    df_feat["opponent_id"] = df_feat["opponent_id"].fillna(0).astype(int)
    
    # Define chance of playing
    df_feat["chance_of_playing"] = df_feat["chance_of_playing_next_round"].fillna(100.0)
    
    df_feat["gameweek_id"] = target_gw
    
    return df_feat
