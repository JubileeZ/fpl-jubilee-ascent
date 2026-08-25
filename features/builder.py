from datetime import datetime
from pathlib import Path
from typing import Literal, TypedDict

import pandas as pd

from features.availability_snapshots import resolve_latest_snapshot
from features.expected_role_prior import (
    BLEND_FULL_APPEARANCES,
    BLEND_START_APPEARANCES,
    DEFAULT_EXPECTED_ROLE_TABLE,
    LIVE_SEASON,
    OUT_OF_CONTENTION,
    appearance_blend_weight,
    apply_availability_priors,
    fit_role_prior,
    load_expected_role_table,
    minutes_if_appearance,
)

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
MIN_PRIOR_MINUTES = 450
MIN_PRIOR_APPEARANCES = 8
AVAILABILITY_OVERRIDE_COLUMNS = frozenset({"player_code", "xmins_cap", "source", "expires_after_gw"})
PARTICIPATION_STATES = ("dnp", "start", "sub_in")
STATE_RECENCY_DECAY = 0.95
STATE_PRIOR_STRENGTH = 4.0


class StateStats(TypedDict):
    counts: dict[str, float]
    minutes_sum: dict[str, float]
    sixty_count: dict[str, float]


def _empty_state_stats() -> StateStats:
    return {
        "counts": dict.fromkeys(PARTICIPATION_STATES, 0.0),
        "minutes_sum": dict.fromkeys(PARTICIPATION_STATES, 0.0),
        "sixty_count": dict.fromkeys(PARTICIPATION_STATES, 0.0),
    }


def _minutes_prior_from_state(stats: StateStats) -> dict[str, object]:
    counts = stats["counts"]
    total = sum(counts.values())
    if total <= 0:
        return {
            "p_start": 1.0 / 3.0,
            "p_sub_in": 1.0 / 3.0,
            "p_dnp": 1.0 / 3.0,
            "xmins_if_start": 80.0,
            "xmins_if_sub_in": 20.0,
            "draft_availability": "eligible",
            "availability_override": "",
        }
    start_n = counts["start"]
    sub_n = counts["sub_in"]
    minutes_sum = stats["minutes_sum"]
    return {
        "p_start": start_n / total,
        "p_sub_in": sub_n / total,
        "p_dnp": counts["dnp"] / total,
        "xmins_if_start": minutes_sum["start"] / start_n if start_n else 80.0,
        "xmins_if_sub_in": minutes_sum["sub_in"] / sub_n if sub_n else 20.0,
        "draft_availability": "eligible",
        "availability_override": "",
    }


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


def _load_players(processed_dir: Path) -> pd.DataFrame:
    """Load terminal metadata for non-point-in-time exploratory projections."""
    return pd.read_parquet(processed_dir / "players.parquet")


def history_before_target(
    df_perf: pd.DataFrame,
    target_gw: int,
    target_deadline: datetime | str | None,
    require_kickoff_time: bool,
) -> pd.DataFrame:
    """Keep completed performances known before the target deadline."""
    history = df_perf[df_perf["gameweek_id"] < target_gw]
    if target_deadline is None:
        return history
    if "kickoff_time" not in history.columns:
        if require_kickoff_time and not history.empty:
            raise ValueError("Point-in-time evaluation requires kickoff_time for historical performances")
        return history
    deadline = pd.to_datetime(target_deadline, utc=True)
    kickoff_times = pd.to_datetime(history["kickoff_time"], utc=True, errors="coerce")
    if require_kickoff_time and kickoff_times.isna().any():
        raise ValueError("Point-in-time evaluation requires valid historical kickoff_time values")
    return history[kickoff_times.lt(deadline)]


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
                else min(max(difficulty / 3.0, 0.4), 1.8)
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


def _attach_fixture_clubs(df_perf: pd.DataFrame, df_fixtures: pd.DataFrame) -> pd.DataFrame:
    """Infer a player's Club from fixture identity and home/away status."""
    required_perf = {"fixture_id", "was_home"}
    required_fixtures = {"id", "home_club_id", "away_club_id"}
    if not required_perf.issubset(df_perf.columns) or not required_fixtures.issubset(df_fixtures.columns):
        return df_perf.copy()

    fixture_clubs = df_fixtures[list(required_fixtures)].rename(columns={"id": "_fixture_id"})
    enriched = df_perf.merge(fixture_clubs, left_on="fixture_id", right_on="_fixture_id", how="left")
    was_home = enriched["was_home"].fillna(False).astype(bool)
    enriched["club_id_at_fixture"] = enriched["home_club_id"].where(was_home, enriched["away_club_id"])
    return enriched.drop(columns=["_fixture_id", "home_club_id", "away_club_id"])


def _summarize_state_rows(rows: pd.DataFrame, recency_decay: float) -> StateStats:
    """Summarize DNP/start/sub-in outcomes using recency-weighted rows."""
    stats = _empty_state_stats()
    if rows.empty or "minutes" not in rows.columns:
        return stats

    minutes = pd.to_numeric(rows["minutes"], errors="coerce").fillna(0.0)
    starts_source = rows["starts"] if "starts" in rows.columns else pd.Series(0.0, index=rows.index)
    gameweeks_source = (
        rows["gameweek_id"]
        if "gameweek_id" in rows.columns
        else pd.Series(0.0, index=rows.index)
    )
    starts = pd.to_numeric(starts_source, errors="coerce").fillna(0.0)
    gameweeks = pd.to_numeric(gameweeks_source, errors="coerce").fillna(0.0)
    latest_gameweek = float(gameweeks.max())
    weights = recency_decay ** (latest_gameweek - gameweeks)
    states = pd.Series("dnp", index=rows.index)
    states = states.mask((minutes > 0) & (starts > 0), "start")
    states = states.mask((minutes > 0) & (starts <= 0), "sub_in")

    for state in PARTICIPATION_STATES:
        mask = states == state
        state_weights = weights[mask]
        stats["counts"][state] = float(state_weights.sum())
        stats["minutes_sum"][state] = float((minutes[mask] * state_weights).sum())
        stats["sixty_count"][state] = float(weights[mask & (minutes >= 60)].sum())
    return stats


def _state_stats_for_player(
    df_perf: pd.DataFrame,
    player_id: int,
    club_id: int | None,
    recency_decay: float,
) -> StateStats:
    rows = df_perf[df_perf["player_id"] == player_id]
    if club_id is not None and "club_id_at_fixture" in rows.columns:
        known_clubs = rows["club_id_at_fixture"].notna()
        if known_clubs.any():
            rows = rows[rows["club_id_at_fixture"] == club_id]
    return _summarize_state_rows(rows, recency_decay)


def _aggregate_state_priors(
    df_perf: pd.DataFrame,
    df_players: pd.DataFrame,
    recency_decay: float,
) -> tuple[dict[tuple[int, int], StateStats], dict[int, StateStats]]:
    """Build Position-Price and Position participation priors."""
    if (
        df_perf.empty
        or "player_id" not in df_perf.columns
        or "position_id" not in df_players.columns
    ):
        return {}, {}

    meta_columns = [column for column in ["id", "position_id", "now_cost", "club_id"] if column in df_players.columns]
    meta = df_players[meta_columns].rename(columns={"id": "player_id"})
    rows = df_perf.merge(meta, on="player_id", how="left")
    if "club_id_at_fixture" in rows.columns and "club_id" in rows.columns:
        known_clubs = rows["club_id_at_fixture"].notna()
        rows = rows[~known_clubs | (rows["club_id_at_fixture"] == rows["club_id"])]
    price_source = (
        rows["now_cost"]
        if "now_cost" in rows.columns
        else pd.Series(0.0, index=rows.index)
    )
    rows["price_band"] = pd.to_numeric(price_source, errors="coerce").fillna(0.0).map(_price_band)

    by_band: dict[tuple[int, int], StateStats] = {}
    by_position: dict[int, StateStats] = {}
    for key, group in rows.groupby(["position_id", "price_band"], dropna=True):
        by_band[(int(key[0]), int(key[1]))] = _summarize_state_rows(group, recency_decay)
    for position_id, group in rows.groupby("position_id", dropna=True):
        by_position[int(position_id)] = _summarize_state_rows(group, recency_decay)
    return by_band, by_position


def _state_probability_summary(
    current: StateStats,
    prior: StateStats,
    prior_strength: float,
) -> dict[str, float]:
    """Combine current observations with a prior and conditional minute means."""
    current_counts = current["counts"]
    prior_counts = prior["counts"]
    prior_total = sum(prior_counts.values())
    prior_probs = (
        {state: prior_counts[state] / prior_total for state in PARTICIPATION_STATES}
        if prior_total > 0
        else dict.fromkeys(PARTICIPATION_STATES, 1.0 / len(PARTICIPATION_STATES))
    )
    posterior_counts = {
        state: current_counts[state] + prior_strength * prior_probs[state]
        for state in PARTICIPATION_STATES
    }
    posterior_total = sum(posterior_counts.values())
    summary = {
        f"p_{state}": posterior_counts[state] / posterior_total
        for state in PARTICIPATION_STATES
    }
    for state in ("start", "sub_in"):
        prior_count = prior_counts[state]
        prior_minutes = (
            prior["minutes_sum"][state] / prior_count
            if prior_count > 0
            else (78.0 if state == "start" else 18.0)
        )
        denominator = current_counts[state] + prior_strength * prior_probs[state]
        current_minutes = (
            current["minutes_sum"][state] / current_counts[state]
            if current_counts[state] > 0
            else prior_minutes
        )
        summary[f"xmins_if_{state}"] = (
            (
                current_minutes * current_counts[state]
                + prior_minutes * prior_strength * prior_probs[state]
            )
            / denominator
            if denominator > 0
            else prior_minutes
        )
        prior_sixty = (
            prior["sixty_count"][state] / prior_count
            if prior_count > 0
            else (1.0 if state == "start" else 0.0)
        )
        current_sixty = (
            current["sixty_count"][state] / current_counts[state]
            if current_counts[state] > 0
            else prior_sixty
        )
        summary[f"p_60_if_{state}"] = (
            (
                current_sixty * current_counts[state]
                + prior_sixty * prior_strength * prior_probs[state]
            )
            / denominator
            if denominator > 0
            else prior_sixty
        )
    summary["state_observation_weight"] = sum(current_counts.values())
    for state in PARTICIPATION_STATES:
        summary[f"{state}_observation_weight"] = current_counts[state]
    return summary


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
    availability_snapshot_root: Path | None = None,
    season: str | None = None,
    expected_role_season: str | None = None,
    expected_role_table: Path | None = None,
    minutes_prior_source: Literal["expected_role", "seed_state"] = "expected_role",
    target_deadline: datetime | str | None = None,
    state_recency_decay: float = STATE_RECENCY_DECAY,
    state_prior_strength: float = STATE_PRIOR_STRENGTH,
    require_availability_snapshot: bool = False,
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
    if not 0 < state_recency_decay <= 1:
        raise ValueError("state_recency_decay must be greater than 0 and at most 1")
    if state_prior_strength < 0:
        raise ValueError("state_prior_strength must be non-negative")

    if minutes_prior_source not in {"expected_role", "seed_state"}:
        raise ValueError("minutes_prior_source must be expected_role or seed_state")
    role_table = None
    if minutes_prior_source == "expected_role":
        role_season = expected_role_season or LIVE_SEASON
        role_table_path = (
            Path(expected_role_table) if expected_role_table is not None else DEFAULT_EXPECTED_ROLE_TABLE
        )
        role_table = load_expected_role_table(role_table_path, role_season)

    # 1. Load Parquet tables, preferring a complete immutable snapshot package.
    snapshot = (
        resolve_latest_snapshot(
            availability_snapshot_root,
            season,
            target_gw,
            target_deadline,
        )
        if availability_snapshot_root is not None and season and target_deadline is not None
        else None
    )
    if require_availability_snapshot and snapshot is None:
        raise ValueError(
            f"Missing immutable availability snapshot for GW{target_gw}; "
            "point-in-time evaluation cannot use terminal metadata"
        )
    if snapshot is None:
        df_players = _load_players(processed_dir)
        has_point_in_time_snapshot = False
        df_fixtures = pd.read_parquet(processed_dir / "fixtures.parquet")
        df_clubs = pd.read_parquet(processed_dir / "clubs.parquet")
        snapshot_id = None
    else:
        df_players = snapshot["players"]
        df_fixtures = snapshot["fixtures"]
        df_clubs = snapshot["clubs"]
        has_point_in_time_snapshot = True
        snapshot_id = str(snapshot["metadata"]["snapshot_id"])
    
    perf_path = processed_dir / "player_performances.parquet"
    if perf_path.exists():
        df_perf = pd.read_parquet(perf_path)
    else:
        df_perf = pd.DataFrame(columns=["player_id", "gameweek_id", "total_points", "minutes"])

    df_players = df_players.rename(columns={"id": "player_id"})
    gameweeks = list(range(target_gw, target_gw + horizon))
    
    # 2. Compute current-season historical features (pre-target_gw)
    df_hist = history_before_target(
        df_perf,
        target_gw,
        target_deadline,
        require_availability_snapshot,
    )

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
    df_hist_context = _attach_fixture_clubs(df_hist, df_fixtures)

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
        seed_fixtures_path = archive_processed / "fixtures.parquet"
        df_seed_fixtures = (
            pd.read_parquet(seed_fixtures_path)
            if seed_fixtures_path.exists()
            else df_fixtures
        )
    else:
        df_seed_perf = df_hist.copy()
        df_seed_players = df_players.rename(columns={"player_id": "id"}).copy()
        df_seed_fixtures = df_fixtures

    df_seed_perf_context = _attach_fixture_clubs(df_seed_perf, df_seed_fixtures)
    priors_by_band, priors_by_position = _compute_position_price_priors(df_seed_perf, df_seed_players)
    state_priors_by_band, state_priors_by_position = _aggregate_state_priors(
        df_seed_perf_context,
        df_seed_players,
        state_recency_decay,
    )
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
    seed_club_by_id = (
        df_seed_players.set_index("id")["club_id"].to_dict()
        if {"id", "club_id"}.issubset(df_seed_players.columns)
        else {}
    )

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
            prior_rates, prior_minutes_if_appearance, _, prior_appearances = _compute_player_rates(
                df_seed_perf,
                seed_pid,
            )
        else:
            prior_rates, prior_minutes_if_appearance, _, prior_appearances = (
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
            seed_source = "player_prior"
        elif fallback_prior is not None:
            base_rates = fallback_prior["rates"]
            seed_source = "position_price_prior"
        else:
            base_rates = {col: 0.0 for col in RATE_COLS}
            seed_source = "none"

        current_rates, current_minutes_if_appearance, current_appearance_probability, current_appearances = _compute_player_rates(
            df_hist,
            pid,
        )
        current_state = _state_stats_for_player(
            df_hist_context,
            pid,
            int(player_row["club_id"]) if pd.notna(player_row.get("club_id")) else None,
            state_recency_decay,
        )
        prior_state = (
            _state_stats_for_player(
                df_seed_perf_context,
                seed_pid,
                int(seed_club_by_id[seed_pid]) if seed_pid in seed_club_by_id else None,
                state_recency_decay,
            )
            if seed_pid is not None
            else _empty_state_stats()
        )
        prior_state_total = sum(prior_state["counts"].values())
        state_prior = (
            prior_state
            if prior_state_total >= MIN_PRIOR_APPEARANCES
            else state_priors_by_band.get((position_id, band))
            or state_priors_by_position.get(position_id)
            or _empty_state_stats()
        )
        state_summary = _state_probability_summary(
            current_state,
            state_prior,
            state_prior_strength,
        )
        current_weight = appearance_blend_weight(
            current_appearances,
            blend_start_appearances,
            blend_full_appearances,
        )
        prior_weight = 1.0 - current_weight
        if minutes_prior_source == "seed_state":
            src = prior_state if prior_state_total > 0 else state_prior
            minutes_prior = _minutes_prior_from_state(src)
        else:
            if role_table is None:
                raise ValueError("Expected Role Table is required when minutes_prior_source is expected_role")
            minutes_prior = fit_role_prior(role_table, pid)
        current_state_total = sum(current_state["counts"].values())
        if current_state_total > 0:
            current_p_start = current_state["counts"]["start"] / current_state_total
            current_p_sub = current_state["counts"]["sub_in"] / current_state_total
            current_p_dnp = current_state["counts"]["dnp"] / current_state_total
        else:
            current_p_start = minutes_prior["p_start"]
            current_p_sub = minutes_prior["p_sub_in"]
            current_p_dnp = minutes_prior["p_dnp"]
        current_xmins_start = (
            current_state["minutes_sum"]["start"] / current_state["counts"]["start"]
            if current_state["counts"]["start"] > 0
            else minutes_prior["xmins_if_start"]
        )
        current_xmins_sub = (
            current_state["minutes_sum"]["sub_in"] / current_state["counts"]["sub_in"]
            if current_state["counts"]["sub_in"] > 0
            else minutes_prior["xmins_if_sub_in"]
        )
        p_start = prior_weight * minutes_prior["p_start"] + current_weight * current_p_start
        p_sub_in = prior_weight * minutes_prior["p_sub_in"] + current_weight * current_p_sub
        p_dnp = prior_weight * minutes_prior["p_dnp"] + current_weight * current_p_dnp
        xmins_if_start = prior_weight * minutes_prior["xmins_if_start"] + current_weight * current_xmins_start
        xmins_if_sub_in = prior_weight * minutes_prior["xmins_if_sub_in"] + current_weight * current_xmins_sub
        p_60_if_start = min(1.0, max(0.0, (xmins_if_start - 45.0) / 30.0))
        p_60_if_sub_in = min(1.0, max(0.0, (xmins_if_sub_in - 45.0) / 30.0))
        role_appearance_probability = 1.0 - minutes_prior["p_dnp"]
        blended_appearance_probability = (
            prior_weight * role_appearance_probability + current_weight * current_appearance_probability
        )
        blended_minutes_if_appearance = minutes_if_appearance(
            p_start, p_sub_in, xmins_if_start, xmins_if_sub_in
        )

        row = {
            "player_id": pid,
            "has_prior_seed": seed_source == "player_prior",
            "has_fallback_prior": seed_source == "position_price_prior",
            "has_seed": seed_source != "none",
            "seed_source": seed_source,
            "n_starts_historical": float(prior_appearances + current_appearances),
            "minutes_if_appearance": blended_minutes_if_appearance,
            "appearance_probability": blended_appearance_probability,
            "p_dnp": p_dnp,
            "p_start": p_start,
            "p_sub_in": p_sub_in,
            "xmins_if_start": xmins_if_start,
            "xmins_if_sub_in": xmins_if_sub_in,
            "p_60_if_start": p_60_if_start,
            "p_60_if_sub_in": p_60_if_sub_in,
            "draft_availability": minutes_prior["draft_availability"],
            "availability_override": minutes_prior["availability_override"],
        }
        row.update({key: state_summary[key] for key in state_summary if key.startswith("state_") or key.endswith("_observation_weight")})
        row["p_dnp_prior"] = minutes_prior["p_dnp"]
        row["p_start_prior"] = minutes_prior["p_start"]
        row["p_sub_in_prior"] = minutes_prior["p_sub_in"]
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
    df_rolling["draft_availability"] = df_rolling["draft_availability"].fillna("eligible")
    df_rolling["availability_override"] = df_rolling["availability_override"].fillna("")
    for state in PARTICIPATION_STATES:
        df_rolling[f"p_{state}"] = df_rolling[f"p_{state}"].fillna(1.0 / len(PARTICIPATION_STATES))
        df_rolling[f"p_{state}_prior"] = df_rolling[f"p_{state}_prior"].fillna(
            df_rolling[f"p_{state}"]
        )
    for column, default in (
        ("xmins_if_start", OUT_OF_CONTENTION[3]),
        ("xmins_if_sub_in", OUT_OF_CONTENTION[4]),
        ("p_60_if_start", 1.0),
        ("p_60_if_sub_in", 0.0),
        ("state_observation_weight", 0.0),
        ("dnp_observation_weight", 0.0),
        ("start_observation_weight", 0.0),
        ("sub_in_observation_weight", 0.0),
    ):
        df_rolling[column] = df_rolling[column].fillna(default)

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

    overlays = [
        apply_availability_priors(
            float(row.p_start),
            float(row.p_sub_in),
            float(row.p_dnp),
            str(row.draft_availability) if pd.notna(row.draft_availability) else "eligible",
            str(row.availability_override) if pd.notna(row.availability_override) else "",
            int(row.gameweek_id),
        )
        for row in df_feat.itertuples()
    ]
    if overlays:
        df_feat["p_start"] = [item[0] for item in overlays]
        df_feat["p_sub_in"] = [item[1] for item in overlays]
        df_feat["p_dnp"] = [item[2] for item in overlays]
        df_feat["appearance_probability"] = 1.0 - df_feat["p_dnp"]

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

    if has_point_in_time_snapshot and "status" in df_feat.columns:
        unavailable_statuses = {"u", "n"}
        df_feat["chance_of_playing"] = df_feat["chance_of_playing"].where(
            ~df_feat["status"].isin(unavailable_statuses), 0.0
        )

    df_feat["is_immediate_next_gw"] = df_feat["gameweek_id"].eq(target_gw)
    df_feat["has_availability_snapshot"] = has_point_in_time_snapshot
    df_feat["availability_snapshot_id"] = snapshot_id

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
