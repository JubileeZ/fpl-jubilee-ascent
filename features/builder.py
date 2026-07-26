from pathlib import Path

import pandas as pd

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
    ("defensive_contribution", "per90_defensive_contribution"),
    ("expected_goals", "per90_xg"),
    ("expected_assists", "per90_xa"),
    ("threat", "per90_threat"),
    ("creativity", "per90_creativity"),
]
RATE_COLS = [rate_col for _, rate_col in EVENT_RATE_MAP]
BLEND_START_APPEARANCES = 3
BLEND_FULL_APPEARANCES = 8
MIN_PRIOR_MINUTES = 450
MIN_PRIOR_APPEARANCES = 8
AVAILABILITY_OVERRIDE_COLUMNS = frozenset({"player_code", "xmins_cap", "source", "expires_after_gw"})


def _safe_number(value: object, default: float) -> float:
    return default if value is None or pd.isna(value) else float(value)


def _price_band(now_cost: float) -> int:
    return int(float(now_cost) // 10)


def _archive_processed_dir(processed_dir: Path, seed_season: str | None) -> Path | None:
    archive_root = processed_dir.parent / "archive"
    if not archive_root.exists():
        return None

    if seed_season:
        candidate = archive_root / seed_season / "processed"
        return (
            candidate
            if (candidate / "player_performances.parquet").exists()
            and (candidate / "players.parquet").exists()
            else None
        )

    candidates = [
        season_dir / "processed"
        for season_dir in archive_root.iterdir()
        if (season_dir / "processed" / "player_performances.parquet").exists()
        and (season_dir / "processed" / "players.parquet").exists()
    ]
    return sorted(candidates)[-1] if candidates else None


def _load_players_as_of(processed_dir: Path, as_of_gw: int | None) -> tuple[pd.DataFrame, bool]:
    """Load player metadata, preferring a point-in-time snapshot when present."""
    df_players = pd.read_parquet(processed_dir / "players.parquet")
    snapshot_path = processed_dir / "player_snapshots.parquet"
    if as_of_gw is None or not snapshot_path.exists():
        return df_players, False

    snapshots = pd.read_parquet(snapshot_path)
    player_id_col = "player_id" if "player_id" in snapshots.columns else "id"
    snapshot_gw_col = (
        "snapshot_gameweek_id"
        if "snapshot_gameweek_id" in snapshots.columns
        else "gameweek_id"
    )
    if player_id_col not in snapshots.columns or snapshot_gw_col not in snapshots.columns:
        return df_players, False

    snapshots = snapshots[snapshots[snapshot_gw_col] <= as_of_gw].sort_values(snapshot_gw_col)
    snapshots = snapshots.drop_duplicates(player_id_col, keep="last")
    has_availability_snapshot = "chance_of_playing_next_round" in snapshots.columns
    snapshot_values = snapshots.set_index(player_id_col)
    for column in snapshot_values.columns:
        if column == snapshot_gw_col:
            continue
        values = df_players["id"].map(snapshot_values[column])
        if column in {
            "chance_of_playing_next_round",
            "chance_of_playing_this_round",
            "club_id",
            "position_id",
            "now_cost",
            "status",
        }:
            df_players[column] = values
        elif column in df_players.columns:
            df_players[column] = values.combine_first(df_players[column])
        else:
            df_players[column] = values
    return df_players, has_availability_snapshot


def _club_strength(club_row: pd.Series, preferred: str, fallback: str) -> float:
    value = club_row.get(preferred)
    if value is None or pd.isna(value):
        value = club_row.get(fallback)
    return _safe_number(value, 0.0)


def _fixture_maps(df_fixtures: pd.DataFrame, df_clubs: pd.DataFrame, gameweeks: list[int]) -> pd.DataFrame:
    club_rows = df_clubs.set_index("id") if not df_clubs.empty else pd.DataFrame()
    fixture_maps = []
    for _, fixture in df_fixtures[df_fixtures["gameweek_id"].isin(gameweeks)].iterrows():
        home_id = int(fixture["home_club_id"])
        away_id = int(fixture["away_club_id"])
        home = club_rows.loc[home_id] if home_id in club_rows.index else pd.Series(dtype=float)
        away = club_rows.loc[away_id] if away_id in club_rows.index else pd.Series(dtype=float)
        difficulty_home = _safe_number(fixture.get("team_h_difficulty"), 3.0)
        difficulty_away = _safe_number(fixture.get("team_a_difficulty"), 3.0)
        home_attack = _club_strength(home, "strength_attack_home", "strength")
        home_defence = _club_strength(home, "strength_defence_home", "strength")
        away_attack = _club_strength(away, "strength_attack_away", "strength")
        away_defence = _club_strength(away, "strength_defence_away", "strength")

        for club_id, opponent_id, is_home, difficulty, team_attack, team_defence, opponent_attack, opponent_defence in [
            (home_id, away_id, True, difficulty_home, home_attack, home_defence, away_attack, away_defence),
            (away_id, home_id, False, difficulty_away, away_attack, away_defence, home_attack, home_defence),
        ]:
            attack_multiplier = (
                min(max(team_attack / opponent_defence, 0.4), 1.8)
                if team_attack > 0 and opponent_defence > 0
                else min(max((6.0 - difficulty) / 3.0, 0.4), 1.8)
            )
            defence_multiplier = (
                min(max(opponent_attack / team_defence, 0.4), 1.8)
                if opponent_attack > 0 and team_defence > 0
                else min(max((6.0 - difficulty) / 3.0, 0.4), 1.8)
            )

            fixture_maps.append({
                "club_id": club_id,
                "gameweek_id": int(fixture["gameweek_id"]),
                "fixture_id": int(fixture["id"]),
                "opponent_id": opponent_id,
                "is_home": is_home,
                "difficulty": difficulty,
                "team_attack_strength": team_attack,
                "team_defence_strength": team_defence,
                "opponent_attack_strength": opponent_attack,
                "opponent_defence_strength": opponent_defence,
                "attack_multiplier": attack_multiplier,
                "defence_multiplier": defence_multiplier,
            })

    columns = [
        "club_id",
        "gameweek_id",
        "fixture_id",
        "opponent_id",
        "is_home",
        "difficulty",
        "team_attack_strength",
        "team_defence_strength",
        "opponent_attack_strength",
        "opponent_defence_strength",
        "attack_multiplier",
        "defence_multiplier",
    ]
    return pd.DataFrame(fixture_maps, columns=columns)


def _load_availability_overrides(
    availability_overrides: Path | None,
    target_gw: int,
    player_codes: set[int],
) -> pd.DataFrame:
    if availability_overrides is None or not availability_overrides.exists():
        return pd.DataFrame(columns=["player_code", "xmins_cap", "expires_after_gw"])

    overrides = pd.read_csv(availability_overrides)
    missing = AVAILABILITY_OVERRIDE_COLUMNS.difference(overrides.columns)
    if missing:
        raise ValueError(f"Availability Overrides missing columns: {sorted(missing)}")

    overrides = overrides[list(AVAILABILITY_OVERRIDE_COLUMNS)].copy()
    for column in ("player_code", "xmins_cap", "expires_after_gw"):
        overrides[column] = pd.to_numeric(overrides[column], errors="coerce")
    if overrides[["player_code", "xmins_cap", "expires_after_gw"]].isna().any().any():
        raise ValueError("Availability Overrides require numeric player_code, xmins_cap, and expires_after_gw")
    if (overrides["player_code"] % 1 != 0).any() or (overrides["expires_after_gw"] % 1 != 0).any():
        raise ValueError("Availability Override player_code and expires_after_gw must be integers")
    overrides[["player_code", "expires_after_gw"]] = overrides[
        ["player_code", "expires_after_gw"]
    ].astype(int)
    if (~overrides["xmins_cap"].between(0.0, 90.0)).any():
        raise ValueError("Availability Override xmins_cap must be between 0 and 90")
    if overrides["source"].isna().any() or overrides["source"].astype(str).str.strip().eq("").any():
        raise ValueError("Availability Overrides require a non-empty source")
    if overrides["player_code"].duplicated().any():
        raise ValueError("Availability Overrides must not contain duplicate player_code values")
    if expired := overrides.loc[overrides["expires_after_gw"] < target_gw, "player_code"].tolist():
        raise ValueError(f"Availability Overrides expired before GW{target_gw}: {expired}")
    if unknown := sorted(set(overrides["player_code"]).difference(player_codes)):
        raise ValueError(f"Availability Overrides contain unknown player_code values: {unknown}")
    return overrides[["player_code", "xmins_cap", "expires_after_gw"]]


def _compute_player_rates(df_perf: pd.DataFrame, player_id: int) -> tuple[dict[str, float], float, float, int]:
    player_hist = df_perf[df_perf["player_id"] == player_id]
    if player_hist.empty:
        rates = {col: (1.45 if col == "per90_goals_conceded" else 0.0) for col in RATE_COLS}
        return (rates, 0.0, 0.0, 0)
    total_minutes = float(player_hist["minutes"].sum())
    appearances = int((player_hist["minutes"] > 0).sum())
    minutes_if_appearance = total_minutes / appearances if appearances else 0.0
    appearance_probability = appearances / len(player_hist)
    rates = {}
    for raw_col, rate_col in EVENT_RATE_MAP:
        if raw_col in player_hist.columns and total_minutes > 0:
            val_sum = float(pd.to_numeric(player_hist[raw_col], errors="coerce").fillna(0.0).sum())
            rates[rate_col] = val_sum / total_minutes * 90.0
        else:
            rates[rate_col] = 1.45 if rate_col == "per90_goals_conceded" else 0.0
    return rates, minutes_if_appearance, appearance_probability, appearances


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
        appearances = int((grp["minutes"] > 0).sum())
        rates = {}
        for raw_col, rate_col in EVENT_RATE_MAP:
            if raw_col in grp.columns and total_minutes > 0:
                val_sum = float(pd.to_numeric(grp[raw_col], errors="coerce").fillna(0.0).sum())
                rates[rate_col] = val_sum / total_minutes * 90.0
            else:
                rates[rate_col] = 0.0
        priors_by_band[(int(position_id), int(band))] = {
            "minutes_if_appearance": total_minutes / appearances if appearances else 0.0,
            "appearance_probability": appearances / len(grp) if len(grp) else 0.0,
            "rates": rates,
        }

    for position_id, grp in perf.groupby("position_id"):
        total_minutes = float(grp["minutes"].sum())
        appearances = int((grp["minutes"] > 0).sum())
        rates = {}
        for raw_col, rate_col in EVENT_RATE_MAP:
            if raw_col in grp.columns and total_minutes > 0:
                val_sum = float(pd.to_numeric(grp[raw_col], errors="coerce").fillna(0.0).sum())
                rates[rate_col] = val_sum / total_minutes * 90.0
            else:
                rates[rate_col] = 0.0
        priors_by_position[int(position_id)] = {
            "minutes_if_appearance": total_minutes / appearances if appearances else 0.0,
            "appearance_probability": appearances / len(grp) if len(grp) else 0.0,
            "rates": rates,
        }
    return priors_by_band, priors_by_position

def build_features(
    processed_dir: Path,
    target_gw: int,
    horizon: int = 1,
    seed_season: str | None = None,
    seed_processed_dir: Path | None = None,
    use_archive_seed: bool = True,
    as_of_gw: int | None = None,
    blend_start_appearances: int = BLEND_START_APPEARANCES,
    blend_full_appearances: int = BLEND_FULL_APPEARANCES,
    availability_overrides: Path | None = None,
) -> pd.DataFrame:
    """
    Compiles a FeatureContract DataFrame for a target gameweek.
    
    Contains historical rolling stats and upcoming fixture metadata.
    """
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    if blend_start_appearances < 0:
        raise ValueError("blend_start_appearances must be non-negative")
    if blend_full_appearances <= blend_start_appearances:
        raise ValueError("blend_full_appearances must be greater than blend_start_appearances")

    # 1. Load Parquet tables
    df_players, has_point_in_time_snapshot = _load_players_as_of(processed_dir, as_of_gw)
    df_fixtures = pd.read_parquet(processed_dir / "fixtures.parquet")
    df_clubs = pd.read_parquet(processed_dir / "clubs.parquet")
    
    perf_path = processed_dir / "player_performances.parquet"
    if perf_path.exists():
        df_perf = pd.read_parquet(perf_path)
    else:
        df_perf = pd.DataFrame(columns=["player_id", "gameweek_id", "total_points", "minutes"])

    df_players = df_players.rename(columns={"id": "player_id"})
    gameweeks = list(range(target_gw, target_gw + horizon))
    
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
    archive_processed = seed_processed_dir or (
        _archive_processed_dir(processed_dir, seed_season) if use_archive_seed else None
    )
    if seed_processed_dir is not None and not (
        (seed_processed_dir / "player_performances.parquet").exists()
        and (seed_processed_dir / "players.parquet").exists()
    ):
        raise FileNotFoundError(f"Prior-season archive not found: {seed_processed_dir}")
    if seed_season and archive_processed is None:
        raise FileNotFoundError(f"Prior-season archive not found: {seed_season}")
    if archive_processed is not None:
        df_seed_perf = pd.read_parquet(archive_processed / "player_performances.parquet")
        df_seed_players = pd.read_parquet(archive_processed / "players.parquet")
    else:
        df_seed_perf = df_hist.copy()
        df_seed_players = df_players.rename(columns={"player_id": "id"}).copy()

    priors_by_band, priors_by_position = _compute_position_price_priors(df_seed_perf, df_seed_players)
    # Build mapping from player code / name to seed player id
    # ponytail: FPL element IDs change between seasons; permanent `code` preserves identity.
    # Name fallback omits position_id to handle players whose position changed between seasons (e.g. MID -> FWD).
    code_to_seed_id = {}
    if "code" in df_seed_players.columns:
        code_to_seed_id = df_seed_players.set_index("code")["id"].to_dict()

    name_to_seed_id = {}
    if "first_name" in df_seed_players.columns and "second_name" in df_seed_players.columns:
        dedup_players = df_seed_players.drop_duplicates(subset=["first_name", "second_name"])
        name_to_seed_id = dedup_players.set_index(["first_name", "second_name"])["id"].to_dict()

    seed_rows = []
    for _, player_row in df_players.iterrows():
        pid = int(player_row["player_id"])
        position_id = int(player_row["position_id"])
        band = _price_band(player_row.get("now_cost", 0))

        code = player_row.get("code")
        seed_pid = code_to_seed_id.get(code) if code is not None else None
        if seed_pid is None:
            fn = player_row.get("first_name")
            sn = player_row.get("second_name")
            if fn and sn:
                seed_pid = name_to_seed_id.get((fn, sn))
        if seed_pid is not None:
            prior_rates, prior_minutes_if_appearance, prior_appearance_probability, prior_appearances = _compute_player_rates(
                df_seed_perf,
                seed_pid,
            )
        else:
            prior_rates, prior_minutes_if_appearance, prior_appearance_probability, prior_appearances = (
                {col: 0.0 for col in RATE_COLS},
                0.0,
                0.0,
                0,
            )
        has_player_prior = (
            prior_minutes_if_appearance > 0
            and prior_appearances >= MIN_PRIOR_APPEARANCES
            and prior_minutes_if_appearance * prior_appearances >= MIN_PRIOR_MINUTES
        )

        band_prior = priors_by_band.get((position_id, band))
        pos_prior = priors_by_position.get(position_id)
        fallback_prior = band_prior or pos_prior

        if has_player_prior:
            base_rates = prior_rates
            base_minutes_if_appearance = prior_minutes_if_appearance
            base_appearance_probability = prior_appearance_probability
            seed_source = "player_prior"
        elif fallback_prior is not None:
            base_rates = fallback_prior["rates"]
            base_minutes_if_appearance = float(fallback_prior["minutes_if_appearance"])
            base_appearance_probability = float(fallback_prior["appearance_probability"])
            seed_source = "position_price_prior"
        else:
            base_rates = {col: 0.0 for col in RATE_COLS}
            base_minutes_if_appearance = 0.0
            base_appearance_probability = 0.0
            seed_source = "none"

        current_rates, current_minutes_if_appearance, current_appearance_probability, current_appearances = _compute_player_rates(
            df_hist,
            pid,
        )
        if current_appearances < blend_start_appearances:
            current_weight = 0.0
        else:
            # ponytail: linear blend ramps to full current-season rates by ~8 apps.
            denom = max(1, blend_full_appearances - blend_start_appearances)
            current_weight = min(
                1.0,
                float(current_appearances - blend_start_appearances) / float(denom),
            )
        prior_weight = 1.0 - current_weight

        row = {
            "player_id": pid,
            "has_prior_seed": seed_source == "player_prior",
            "has_fallback_prior": seed_source == "position_price_prior",
            "has_seed": seed_source != "none",
            "seed_source": seed_source,
            "n_starts_historical": float(prior_appearances + current_appearances),
            "minutes_if_appearance": (
                prior_weight * base_minutes_if_appearance
                + current_weight * current_minutes_if_appearance
            ),
            "appearance_probability": (
                prior_weight * base_appearance_probability
                + current_weight * current_appearance_probability
            ),
        }
        for rate_col in RATE_COLS:
            row[rate_col] = prior_weight * float(base_rates.get(rate_col, 0.0)) + current_weight * float(current_rates.get(rate_col, 0.0))
        seed_rows.append(row)
    df_seed = pd.DataFrame(seed_rows)

    df_rolling = df_rolling.merge(df_seed, on="player_id", how="left")
    for rc in RATE_COLS:
        df_rolling[rc] = df_rolling[rc].fillna(1.45 if rc == "per90_goals_conceded" else 0.0)
    df_rolling["avg_mins_3gw"] = df_rolling["minutes_if_appearance"].fillna(0.0)
    df_rolling["has_prior_seed"] = df_rolling["has_prior_seed"].fillna(False)
    df_rolling["n_starts_historical"] = df_rolling["n_starts_historical"].fillna(0.0)
    df_rolling["appearance_probability"] = df_rolling["appearance_probability"].fillna(0.0)

    # 4. Merge player metadata and expand to one row per player/target gameweek.
    df_players["_feature_key"] = 1
    df_gameweeks = pd.DataFrame({"gameweek_id": gameweeks, "_feature_key": 1})
    df_base = df_players.merge(df_gameweeks, on="_feature_key", how="inner").drop(columns="_feature_key")
    df_feat = df_base.merge(df_rolling, on="player_id", how="left")
    
    # 5. Map strength from clubs
    df_clubs_sub = df_clubs[["id", "strength"]].rename(columns={"id": "club_id", "strength": "team_strength"})
    df_feat = df_feat.merge(df_clubs_sub, on="club_id", how="left")

    # 6. Attach each requested game's fixture rows. Double gameweeks remain
    # separate rows; blank gameweeks receive a sentinel fixture_id.
    df_fmap = _fixture_maps(df_fixtures, df_clubs, gameweeks)
    df_feat = df_feat.merge(df_fmap, on=["club_id", "gameweek_id"], how="left")
    
    # Fill NAs
    df_feat["fixture_id"] = df_feat["fixture_id"].fillna(-1).astype(int)
    df_feat["is_home"] = df_feat["is_home"].fillna(False)
    df_feat["difficulty"] = df_feat["difficulty"].fillna(3.0)
    df_feat["opponent_id"] = df_feat["opponent_id"].fillna(0).astype(int)
    
    # Define chance of playing
    chance_col = "chance_of_playing_next_round"
    if as_of_gw is not None and not has_point_in_time_snapshot:
        # No historical availability snapshot means current mutable injury data
        # cannot be used without look-ahead leakage.
        df_feat["chance_of_playing"] = 100.0
    else:
        api_chance = (
            pd.to_numeric(df_feat[chance_col], errors="coerce")
            if chance_col in df_feat.columns
            else pd.Series(float("nan"), index=df_feat.index)
        )
        df_feat["chance_of_playing"] = api_chance.where(
            api_chance.notna(),
            df_feat["appearance_probability"].fillna(1.0) * 100.0,
        )

    if "status" in df_feat.columns:
        unavailable_statuses = {"u", "n"}
        df_feat["chance_of_playing"] = df_feat["chance_of_playing"].where(
            ~df_feat["status"].isin(unavailable_statuses), 0.0
        )

    player_codes = (
        set(pd.to_numeric(df_players["code"], errors="coerce").dropna().astype(int))
        if "code" in df_players.columns
        else set()
    )
    overrides = _load_availability_overrides(availability_overrides, target_gw, player_codes)
    if not overrides.empty:
        df_feat = df_feat.merge(overrides, left_on="code", right_on="player_code", how="left")
        df_feat["xmins_cap"] = df_feat["xmins_cap"].where(
            df_feat["gameweek_id"] <= df_feat["expires_after_gw"],
        )
        df_feat = df_feat.drop(columns=["player_code", "expires_after_gw"])
    else:
        df_feat["xmins_cap"] = float("nan")
    
    return df_feat
