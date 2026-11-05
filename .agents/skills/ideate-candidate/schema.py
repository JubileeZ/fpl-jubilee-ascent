"""Authoritative Operational Data Catalog and Input Validation for Candidate Ideation.

Defines the exact observed data schema available in fpl-jubilee-ascent, including
Target Gameweek features (features.<col>) and Historical Performance primitives (history.<col>).
Prohibits unobserved telemetry (tracking, passing networks, possession %, betting spreads).
"""

from __future__ import annotations

import re

# Canonical Pre-Match Target Gameweek Feature Schema (features.<col>)
# Produced by features/builder.py: build_features(processed_dir, target_gw, horizon)
FEATURE_SCHEMA: dict[str, dict[str, str]] = {
    "Player Identity & Position": {
        "player_id": "Unique integer player ID in FPL API",
        "web_name": "Display name on shirt (e.g. 'Haaland')",
        "first_name": "Player first name",
        "second_name": "Player surname",
        "code": "Immutable official player code across seasons",
        "club_id": "Club ID (1-20)",
        "position_id": "Position (1=GKP, 2=DEF, 3=MID, 4=FWD)",
        "now_cost": "Cost in £0.1m units (e.g. 140 = £14.0m, 45 = £4.5m)",
        "status": "Availability flag: 'a' (available), 'd' (doubtful), 'i' (injured), 's' (suspended), 'u' (unavailable)",
    },
    "Participation & Availability Priors": {
        "chance_of_playing": "Official reported playing chance % (0-100 or null)",
        "chance_of_playing_this_round": "Playing chance for immediate round (0-100 or null)",
        "chance_of_playing_next_round": "Playing chance for subsequent round (0-100 or null)",
        "news": "Official injury/suspension news string",
        "news_added": "Timestamp when news was reported",
        "p_start": "Learned probability of starting match [0.0, 1.0]",
        "p_sub_in": "Learned probability of appearing as substitute [0.0, 1.0]",
        "p_dnp": "Learned probability of Did Not Play [0.0, 1.0] (sum to 1.0)",
        "p_start_prior": "Empirical Bayes prior probability of starting",
        "p_sub_in_prior": "Empirical Bayes prior probability of subbing in",
        "p_dnp_prior": "Empirical Bayes prior probability of DNP",
        "p_60_if_start": "Probability of playing 60+ minutes if starting (clip((mins-45)/30, 0, 1))",
        "p_60_if_sub_in": "Probability of playing 60+ minutes if substitute (typically 0.0)",
        "xmins_if_start": "Expected minutes conditioned on starting (~78.0 outfield)",
        "xmins_if_sub_in": "Expected minutes conditioned on substitute cameo (~18.0)",
        "xmins_cap": "Hard ceiling on expected minutes",
        "n_starts_historical": "Number of starts in historical window",
        "starts": "Cumulative observed starts in season",
        "minutes": "Cumulative observed minutes in season",
        "appearance_probability": "Total appearance probability p_start + p_sub_in",
    },
    "Club Strength & Fixture Context": {
        "fixture_id": "Unique fixture ID",
        "gameweek_id": "Target Gameweek ID (1-38)",
        "opponent_id": "Opponent Club ID (1-20)",
        "is_home": "Boolean flag: True if home fixture, False if away",
        "kickoff_time": "Scheduled match kickoff timestamp",
        "difficulty": "Official FPL Fixture Difficulty Rating (FDR 1-5)",
        "team_strength": "Official FPL team overall strength rating",
        "team_attack_strength": "Official home/away attack strength",
        "team_defence_strength": "Official home/away defence strength",
        "opponent_attack_strength": "Opponent home/away attack strength",
        "opponent_defence_strength": "Opponent home/away defence strength",
        "attack_multiplier": "Calibrated attacking matchup multiplier (ADR 0040 s=0.40)",
        "defence_multiplier": "Calibrated defensive matchup multiplier (ADR 0040 s=0.40)",
        "is_immediate_next_gw": "Boolean flag: True if target GW is immediate deadline",
    },
    "Per-90 Rate Baseline Covariates": {
        "per90_xg": "Empirical Bayes shrunk expected goals per 90 (K_DEF=2400, attack K=360)",
        "per90_xa": "Empirical Bayes shrunk expected assists per 90",
        "per90_goals": "Observed goals scored per 90 minutes",
        "per90_assists": "Observed assists per 90 minutes",
        "per90_clean_sheets": "Observed clean sheets per 90 minutes",
        "per90_goals_conceded": "Observed goals conceded per 90 minutes",
        "per90_saves": "Observed goalkeeper saves per 90 minutes",
        "per90_bonus": "Observed bonus points per 90 minutes",
        "per90_defensive_contribution": "Observed Defcon actions (tackles+CBI) per 90 minutes",
        "per90_threat": "FPL ICT Threat index per 90 minutes",
        "per90_creativity": "FPL ICT Creativity index per 90 minutes",
        "per90_influence": "FPL ICT Influence index per 90 minutes",
        "per90_yellow_cards": "Observed yellow cards per 90 minutes",
        "per90_red_cards": "Observed red cards per 90 minutes",
        "per90_penalties_saved": "Goalkeeper penalty saves per 90 minutes",
        "per90_penalties_missed": "Attacker penalties missed per 90 minutes",
        "per90_own_goals": "Own goals per 90 minutes",
    },
    "Set-Piece Hierarchies": {
        "penalties_order": "Penalty taker rank order (1=primary taker, 2=secondary)",
        "direct_freekicks_order": "Direct free kick taker rank order (1=primary)",
        "corners_and_indirect_freekicks_order": "Corner and indirect free kick taker rank order",
    },
    "Aggregated Season Totals (Point-in-Time)": {
        "expected_goals": "Cumulative Opta expected goals (xG)",
        "expected_assists": "Cumulative Opta expected assists (xA)",
        "expected_goal_involvements": "Cumulative Opta expected goal involvements (xGI)",
        "expected_goals_conceded": "Cumulative Opta expected goals conceded (xGC)",
        "goals_scored": "Cumulative goals scored",
        "assists": "Cumulative official FPL assists",
        "clean_sheets": "Cumulative clean sheets",
        "goals_conceded": "Cumulative goals conceded",
        "saves": "Cumulative goalkeeper saves",
        "bonus": "Cumulative FPL bonus points awarded (1-3)",
        "bps": "Cumulative Bonus Points System raw performance score",
        "total_points": "Cumulative FPL fantasy points",
        "influence": "Cumulative FPL ICT Influence",
        "creativity": "Cumulative FPL ICT Creativity",
        "threat": "Cumulative FPL ICT Threat",
        "ict_index": "Cumulative FPL ICT Index",
        "selected_by_percent": "Current FPL manager ownership %",
    },
}

# Canonical Pre-Deadline Historical Performance Schema (history.<col>)
# Sourced strictly from player_performances.parquet prior to target deadline H_{<g}
HISTORY_SCHEMA: dict[str, dict[str, str]] = {
    "Match Context": {
        "player_id": "Unique player ID",
        "fixture_id": "Unique fixture ID",
        "gameweek_id": "Gameweek when match was played (1-38)",
        "opponent_club_id": "Opposing club ID (1-20)",
        "was_home": "Boolean flag: True if player played at home",
        "kickoff_time": "Exact kickoff timestamp",
        "team_h_score": "Home club final score",
        "team_a_score": "Away club final score",
    },
    "Participation & Points": {
        "minutes": "Actual minutes played in match (0-90+)",
        "starts": "Integer indicator: 1 if started match, 0 if substitute/benched",
        "total_points": "Official FPL points earned in match",
    },
    "Attacking Production (Opta & FPL)": {
        "goals_scored": "Actual goals scored in match",
        "assists": "Actual official assists in match",
        "expected_goals": "Opta expected goals (xG) generated in match",
        "expected_assists": "Opta expected assists (xA) generated in match",
        "expected_goal_involvements": "Opta xGI in match (xG + xA)",
    },
    "Defensive & Goalkeeping Production": {
        "clean_sheets": "Clean sheet awarded: 1 if >=60 mins played and 0 conceded, else 0",
        "goals_conceded": "Goals conceded while player was on the pitch",
        "expected_goals_conceded": "Opta xGC while player was on the pitch",
        "defensive_contribution": "Defcon volume: tackles won + clearances + blocks + interceptions",
        "saves": "Goalkeeper saves made in match",
        "penalties_saved": "Penalties saved by goalkeeper",
        "penalties_missed": "Penalties missed by penalty taker",
        "own_goals": "Own goals scored",
        "yellow_cards": "Yellow cards received (0 or 1)",
        "red_cards": "Red cards received (0 or 1)",
    },
    "Bonus & Underlying Performance": {
        "bonus": "FPL bonus points awarded in match (0, 1, 2, or 3)",
        "bps": "Official raw BPS score accumulated in match",
        "influence": "FPL Influence index in match",
        "creativity": "FPL Creativity index in match",
        "threat": "FPL Threat index in match",
        "ict_index": "FPL ICT Composite Index in match",
    },
    "Financial & Ownership Dynamics": {
        "price": "Player price in £0.1m increments at kickoff",
        "selected": "Total ownership count at kickoff",
        "transfers_balance": "Net transfers in - out for the gameweek",
        "transfers_in": "Transfers in for the gameweek",
        "transfers_out": "Transfers out for the gameweek",
    },
}

# Explicitly Unobserved / Forbidden Telemetry
FORBIDDEN_TELEMETRY: list[tuple[str, str]] = [
    (
        "Tracking & Spatial Data",
        "No player XY coordinates, sprint speeds, distance covered, pressing events, or positional heatmaps.",
    ),
    (
        "Passing Sequences & Tactical Maps",
        "No pass completion %, progressive passes, pass networks, aerial duels, or tackle success rates.",
    ),
    (
        "Possession & Game Flow Telemetry",
        "No in-match possession %, field tilt %, territory dominance, or PPDA (passes per defensive action).",
    ),
    (
        "Betting Markets & Odds",
        "No bookmaker odds, Asian handicaps, betting exchange spreads, or market-implied goal totals.",
    ),
    (
        "External Environmental Factors",
        "No weather conditions, pitch dimensions, referee card rates, or manager press-conference transcripts.",
    ),
    (
        "Minute-Level Event Streams",
        "No timestamped match event feeds; all performance history is recorded strictly as post-match aggregates per player-fixture.",
    ),
]

# Aliases mapping common alternative names to canonical columns
COLUMN_ALIASES: dict[str, str] = {
    "team_id": "club_id",
    "opponent_team_id": "opponent_id",
    "position": "position_id",
    "element_type": "position_id",
    "cost": "now_cost",
    "price": "now_cost",
    "value": "now_cost",
    "xg": "expected_goals",
    "xa": "expected_assists",
    "xgi": "expected_goal_involvements",
    "xgc": "expected_goals_conceded",
    "cs": "clean_sheets",
    "gc": "goals_conceded",
    "mins": "minutes",
    "opponent_club": "opponent_club_id",
}

# Flattened sets of allowed base column names
ALL_ALLOWED_FEATURE_COLS: frozenset[str] = frozenset(
    col for cat in FEATURE_SCHEMA.values() for col in cat
) | frozenset(COLUMN_ALIASES.keys())

ALL_ALLOWED_HISTORY_COLS: frozenset[str] = frozenset(
    col for cat in HISTORY_SCHEMA.values() for col in cat
) | frozenset(COLUMN_ALIASES.keys())

# High-risk unsupported covariate keywords for heuristic catches
FORBIDDEN_KEYWORDS: tuple[str, ...] = (
    "pace", "tempo", "odds", "betting", "spread", "possession", "tilt",
    "tracking", "sprint", "speed", "distance", "press", "ppda", "weather",
    "referee", "aerial", "duel", "pass_map", "pass_acc", "pass_pct",
    "progressive", "carry", "heat_map", "turnover", "recovery_speed",
)


def validate_input_token(token: str) -> tuple[bool, str]:
    """Validate a single input token.

    Returns (is_valid, reason_or_normalized).
    """
    clean = token.strip().strip("`*\"'").strip()
    if not clean:
        return True, ""

    # Remove trailing parenthetical descriptions like '(rolling 5-GW EWM)' or '(EB shrunk)'
    clean = re.sub(r"\(.*?\)", "", clean).strip()

    # Check for forbidden keywords anywhere in token
    lower = clean.lower()
    for kw in FORBIDDEN_KEYWORDS:
        if kw in lower:
            return False, f"unsupported telemetry: '{clean}' (matches unobserved keyword '{kw}')"

    # Match prefix.column
    match = re.match(r"^(features|history)\.([a-zA-Z0-9_]+)$", clean, re.IGNORECASE)
    if match:
        pfx = match.group(1).lower()
        col = match.group(2).lower()
        canonical_col = COLUMN_ALIASES.get(col, col)

        if pfx == "features":
            if canonical_col in ALL_ALLOWED_FEATURE_COLS:
                return True, f"features.{canonical_col}"
            return False, f"unknown features column: '{col}' (not in FeatureContract)"
        else:  # history
            if canonical_col in ALL_ALLOWED_HISTORY_COLS:
                return True, f"history.{canonical_col}"
            return False, f"unknown history column: '{col}' (not in player_performances)"

    # If un-prefixed, check if it matches a known canonical column in either schema
    canonical = COLUMN_ALIASES.get(lower, lower)
    if canonical in ALL_ALLOWED_FEATURE_COLS or canonical in ALL_ALLOWED_HISTORY_COLS:
        return True, canonical

    # If token contains math operators, check if all sub-tokens are valid
    if any(op in clean for op in ("+", "*", "/", "-")):
        sub_tokens = [t.strip() for t in re.split(r"[\+\*\/\-\s]+", clean) if t.strip()]
        for sub in sub_tokens:
            if not sub or sub.replace(".", "", 1).isdigit():
                continue
            sub_valid, sub_msg = validate_input_token(sub)
            if not sub_valid:
                return False, sub_msg
        return True, clean

    return False, f"unrecognized input: '{clean}' (requires features.<col> or history.<col>)"


def validate_inputs_manifest(raw_inputs: str) -> tuple[list[str], list[str]]:
    """Validate complete Section 8 inputs string.

    Returns (valid_list, invalid_list).
    """
    if not raw_inputs or not raw_inputs.strip():
        return [], []

    # Split by semicolon, comma, or newline
    raw_tokens = [t.strip() for t in re.split(r"[;\n,]+", raw_inputs) if t.strip()]
    valid_list: list[str] = []
    invalid_list: list[str] = []

    for token in raw_tokens:
        is_valid, msg = validate_input_token(token)
        if is_valid:
            if msg:
                valid_list.append(msg)
        else:
            invalid_list.append(msg)

    return valid_list, invalid_list
