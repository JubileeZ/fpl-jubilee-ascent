"""Construct EXT-40 process predictors from a source panel and deadline receipts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backtesting.empirical_mirrors import extract_gw_df_from_merged_csv
from commands.run_stage_a_and_b import _bootstrap_players_and_clubs
from historical_replay_inputs import _PERFORMANCE_NAMES, _checked_bytes
from prototypes.ext_40.prototypes import (
    Component,
    EVENT,
    FloatArray,
    KEYS,
    OUTFIELD,
    poisson_categories,
)

PERFORMANCE = [
    *KEYS,
    "kickoff_time",
    "opponent_club_id",
    "was_home",
    "minutes",
    "starts",
    "expected_goals",
    "expected_assists",
    "goals_scored",
    "assists",
]
ROSTER = ["player_id", "code", "position_id", "club_id"]
SIGNALS = ["rate", "form", "support"]
REQUIRED_ISSUE = [*KEYS, *ROSTER[1:], "is_home", "opponent_id"]


@dataclass(frozen=True)
class SourcePanel:
    season: str
    digest: str
    last_available: datetime
    training: dict[Component, pd.DataFrame]
    carry: pd.DataFrame
    inventory: pd.DataFrame


@dataclass(frozen=True)
class IssueContext:
    season: str
    gameweek: int
    cutoff: datetime
    source_digest: str
    receipt_digest: str
    fixtures: pd.DataFrame
    current_history: pd.DataFrame
    previous_issues: dict[int, dict[Component, pd.DataFrame]]


def performance_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if len(frame) == 0:
        return pd.DataFrame(columns=PERFORMANCE)
    data = frame.loc[:, PERFORMANCE].copy()
    if data.duplicated(KEYS).any():
        raise ValueError("Duplicate settled player-fixture rows")
    for col in [
        *KEYS,
        "opponent_club_id",
        "minutes",
        "starts",
        "expected_goals",
        "expected_assists",
        "goals_scored",
        "assists",
    ]:
        data[col] = pd.to_numeric(data[col].replace("", np.nan), errors="raise")
        present = data[col].dropna()
        if not np.isfinite(present).all() or not present.ge(0).all():
            raise ValueError(f"Invalid settled {col}")
    for col in [*KEYS, "opponent_club_id"]:
        if not data[col].gt(0).all() or not data[col].eq(np.floor(data[col])).all():
            raise ValueError(f"Invalid settled {col} key")
        data[col] = data[col].astype(int)
    if not data["gameweek_id"].between(1, 38).all():
        raise ValueError("Out-of-season settled Gameweek")
    data["was_home"] = (
        data["was_home"].astype(str).str.lower().map({"true": True, "false": False})
    )
    data["kickoff_time"] = pd.to_datetime(
        data["kickoff_time"], utc=True, errors="raise"
    )
    if data[["was_home", "kickoff_time"]].isna().any().any():
        raise ValueError("Settled fixture context is missing")
    return data


def roster_identity(frame: pd.DataFrame) -> pd.DataFrame:
    roster = frame.loc[:, ROSTER].copy()
    if roster["player_id"].duplicated().any():
        raise ValueError("Duplicate issue roster player IDs")
    code = pd.to_numeric(roster["code"], errors="coerce")
    valid = (
        code.gt(0)
        & code.eq(np.floor(code))
        & np.isfinite(code)
        & ~code.duplicated(keep=False)
    )
    roster["identity"] = code.where(valid)
    return roster


def unique_season_identity(dated: pd.DataFrame) -> pd.DataFrame:
    """Discard a code link if the roster prefix gives ambiguous season mappings."""
    dated = dated.copy()
    observed = dated[["player_id", "identity"]].dropna().drop_duplicates()
    ambiguous = observed.loc[
        observed["player_id"].duplicated(keep=False)
        | observed["identity"].duplicated(keep=False)
    ]
    dated["identity"] = dated["identity"].where(
        ~dated["player_id"].isin(ambiguous["player_id"])
        & ~dated["identity"].isin(ambiguous["identity"])
    )
    return dated


def issue_fixture_rows(
    market: pd.DataFrame, schedule: pd.DataFrame, gw: int, horizon: int
) -> pd.DataFrame:
    fixtures = schedule.loc[schedule["gameweek_id"].between(gw, gw + horizon - 1)]
    if not fixtures["id"].is_unique:
        raise ValueError("Duplicate issued fixture IDs")
    sides = pd.concat(
        [
            fixtures.rename(
                columns={"id": "fixture_id", club: "club_id", opponent: "opponent_id"}
            )[["fixture_id", "gameweek_id", "club_id", "opponent_id"]].assign(
                is_home=home
            )
            for club, opponent, home in (
                ("home_club_id", "away_club_id", True),
                ("away_club_id", "home_club_id", False),
            )
        ],
        ignore_index=True,
    )
    roster = (
        market[ROSTER + ["identity"]]
        if "identity" in market
        else roster_identity(market)
    )
    player_weeks = roster.merge(
        pd.DataFrame({"gameweek_id": range(gw, gw + horizon)}), how="cross"
    )
    issued = player_weeks.merge(sides, on=["club_id", "gameweek_id"], how="left")
    issued["fixture_id"] = issued["fixture_id"].fillna(-1).astype(int)
    issued["opponent_id"] = issued["opponent_id"].fillna(0).astype(int)
    issued["is_home"] = issued["is_home"].eq(True)
    return issued


def annotate_history(
    history: pd.DataFrame, roster_by_gw: pd.DataFrame, offset: int
) -> pd.DataFrame:
    dated = roster_by_gw[["gameweek_id", "player_id", "position_id", "identity"]]
    if dated.duplicated(["gameweek_id", "player_id"]).any():
        raise ValueError("Ambiguous dated roster player position")
    df = history.merge(
        dated, on=["gameweek_id", "player_id"], how="left", validate="many_to_one"
    )
    df["index_gw"] = df["gameweek_id"] + offset
    return df


def _process_totals(
    history: pd.DataFrame, process: str, issue_index: int
) -> pd.DataFrame:
    if not history["index_gw"].lt(issue_index).all():
        raise ValueError("Target or later Gameweek entered process predictors")
    good = history.loc[
        history["minutes"].gt(0)
        & history[process].notna()
        & history["position_id"].isin(OUTFIELD)
    ].copy()
    weight = 0.95 ** (issue_index - 1 - good["index_gw"].to_numpy(dtype=float))
    good["weighted_process"] = weight * good[process]
    good["weighted_minutes"] = weight * good["minutes"]
    return good


def _opponent_form(history: pd.DataFrame) -> pd.Series:
    if history.empty:
        return pd.Series(dtype=float)
    active = history.loc[history["minutes"].gt(0)].copy()
    # A side with any missing active-player xG or fewer than 11 recorded starts
    # cannot supply a complete opponent-facing chance volume for that fixture.
    active["valid_process"] = active["expected_goals"].notna()
    groups = active.groupby(["fixture_id", "opponent_club_id"], as_index=False).agg(
        xgc=("expected_goals", "sum"),
        complete=("valid_process", "all"),
        starts=("starts", "sum"),
    )
    complete = groups.loc[groups["complete"] & groups["starts"].eq(11)]
    both_sides = (
        complete.groupby("fixture_id")["opponent_club_id"].transform("size").eq(2)
    )
    complete = complete.loc[both_sides]
    if complete.empty:
        return pd.Series(dtype=float)
    league = complete["xgc"].mean()
    opponent = complete.groupby("opponent_club_id")["xgc"].agg(["sum", "count"])
    shrunk = (opponent["sum"] + 8 * league) / (opponent["count"] + 8)
    return np.log((0.1 + shrunk) / (0.1 + league)).clip(-0.5, 0.5)


def build_predictors(
    issued: pd.DataFrame,
    seed: pd.DataFrame,
    current: pd.DataFrame,
    issue_index: int,
    component: Component,
) -> pd.DataFrame:
    """Use one information set for all leads; source and current club IDs stay separate."""
    if issued.duplicated(KEYS).any():
        raise ValueError("Duplicate issued player-fixture predictor keys")
    process, _ = EVENT[component]
    if seed.empty:
        history = current
    elif current.empty:
        history = seed
    else:
        history = pd.concat([seed, current], ignore_index=True)
    good = _process_totals(history, process, issue_index)
    measures = ["weighted_process", "weighted_minutes"]
    position = good.groupby("position_id")[[process, "minutes"]].sum()
    pooled = 90 * position[process] / position["minutes"]
    source = (
        good.loc[good["index_gw"].le(38)]
        .groupby("position_id")[[process, "minutes"]]
        .sum()
    )
    source_pool = 90 * source[process] / source["minutes"]
    home = issued.loc[:, REQUIRED_ISSUE + ["identity"]].copy()
    for prefix, eligible in (
        ("long", good),
        ("recent", good.loc[good["index_gw"].ge(issue_index - 4)]),
    ):
        counts = eligible.groupby("identity")[measures].sum()
        home[f"{prefix}_process"] = (
            home["identity"].map(counts["weighted_process"]).fillna(0.0)
        )
        home[f"{prefix}_minutes"] = (
            home["identity"].map(counts["weighted_minutes"]).fillna(0.0)
        )
    linked = home["long_minutes"].gt(0)
    base = (
        home["position_id"]
        .map(pooled)
        .where(linked, home["position_id"].map(source_pool))
    )
    home["rate"] = (90 * home["long_process"] + 450 * base) / (
        home["long_minutes"] + 450
    )
    short = (90 * home["recent_process"] + 450 * home["rate"]) / (
        home["recent_minutes"] + 450
    )
    home["form"] = (
        np.log((0.05 + short) / (0.05 + home["rate"]))
        .clip(-1.0, 1.0)
        .where(home["recent_minutes"].gt(0), 0.0)
    )
    home["opponent_form"] = home["opponent_id"].map(_opponent_form(current)).fillna(0.0)
    home["support"] = np.where(linked, "own_history", "position_pool")
    linked_seed = source_identity(seed, process)
    home.loc[linked & home["identity"].isin(linked_seed), "support"] = "linked_source"
    return home[[*KEYS, "position_id", "is_home", "opponent_form", *SIGNALS]]


def source_identity(seed: pd.DataFrame, process: str) -> set[int]:
    if seed.empty:
        return set()
    return set(
        seed.loc[seed["minutes"].gt(0) & seed[process].notna(), "identity"]
        .dropna()
        .astype(int)
    )


def training_examples(
    issued: pd.DataFrame, settled: pd.DataFrame, component: Component, *, soft: bool
) -> pd.DataFrame:
    process, event = EVENT[component]
    rows = issued.merge(
        settled[[*KEYS, "minutes", process, event]], on=KEYS, validate="one_to_one"
    )
    rows = rows.loc[
        rows["position_id"].isin(OUTFIELD)
        & rows["minutes"].gt(0)
        & rows[process].notna()
    ].copy()
    rows["target"] = rows[process if soft else event]
    return rows.dropna(subset=["target"])


def count_targets(rows: pd.DataFrame, *, soft: bool) -> FloatArray:
    target = rows["target"].to_numpy(dtype=float)
    if soft:
        return poisson_categories(target)[0]
    if (
        not np.isfinite(target).all()
        or (target < 0).any()
        or not np.equal(target, np.floor(target)).all()
    ):
        raise ValueError("Native scoring counts must be nonnegative integers")
    return np.eye(4)[np.minimum(target, 3).astype(int)]


def eligible_issue_history(context: IssueContext) -> pd.DataFrame:
    history = context.current_history
    if not history["gameweek_id"].lt(context.gameweek).all():
        raise ValueError("Current-season labels include target or future Gameweek")
    if not history["kickoff_time"].lt(context.cutoff).all():
        raise ValueError("Current-season label fixture starts after issue deadline")
    return history


def _settled_source_rows(mirror: Path, origin: dict[str, Any]) -> pd.DataFrame:
    receipt = origin["settled_outcomes"]
    if not receipt["zero_diff_verified"] or receipt["ledger_mismatch_rows"] != 0:
        raise ValueError(f"Unverified native source ledger at GW{origin['gw']}")
    raw = _checked_bytes(mirror / receipt["local_relpath"], receipt["blob_sha256"])
    frame = extract_gw_df_from_merged_csv(raw, origin["gw"]).rename(
        columns=_PERFORMANCE_NAMES
    )
    # The source mirror includes Assistant Manager rows that do not belong to
    # the player-component data. Their starts/minutes fields may be absent.
    frame = frame.loc[
        frame["minutes"].astype(str).ne(""), PERFORMANCE
    ].drop_duplicates()
    return performance_rows(frame)


def _source_fixture_context(
    history: pd.DataFrame, market: pd.DataFrame, fixture_source: bytes, gw: int
) -> pd.DataFrame:
    fixtures = pd.read_csv(
        BytesIO(fixture_source), usecols=["id", "event", "team_h", "team_a"]
    )
    schedule = fixtures.rename(
        columns={
            "event": "gameweek_id",
            "team_h": "home_club_id",
            "team_a": "away_club_id",
        }
    )
    issued = issue_fixture_rows(market, schedule, gw, 1)
    matched = issued.merge(
        history[[*KEYS, "was_home", "opponent_club_id"]], on=KEYS, validate="one_to_one"
    )
    return matched.loc[
        matched["is_home"].eq(matched["was_home"])
        & matched["opponent_id"].eq(matched["opponent_club_id"])
    ].copy()


def load_source_panel(
    mirror: Path,
    manifest_path: Path,
    archive: Path,
    seed_manifest_path: Path,
    *,
    soft_assists: bool,
) -> SourcePanel:
    """Verify source outcomes and use dated context and publication cutoffs at all origins."""
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    seed_raw = seed_manifest_path.read_bytes()
    seed_manifest = json.loads(seed_raw)
    if manifest["season"] != seed_manifest["season"]:
        raise ValueError("Inconsistent source-season identities")
    origins = manifest["origins"]
    if [origin["gw"] for origin in origins] != list(range(1, 39)):
        raise ValueError("Expected one source origin per Gameweek")
    filename = "player_performances.parquet"
    _checked_bytes(
        archive / filename, seed_manifest["processed_digests"][filename]["sha256"]
    )
    archived_raw = pd.read_parquet(archive / filename, columns=PERFORMANCE)
    settled: dict[int, pd.DataFrame] = {}
    rosters: dict[int, pd.DataFrame] = {}
    deadlines: dict[int, datetime] = {}
    for origin in origins:
        gw = int(origin["gw"])
        settled[gw] = _settled_source_rows(mirror, origin)
        deadlines[gw] = deadline = datetime.fromisoformat(origin["deadline_utc"])
        bootstrap = origin["bootstrap"]
        capture = datetime.fromisoformat(bootstrap["capture_upper_utc"])
        if bootstrap["status"] != "supported" or capture >= deadline:
            raise ValueError(f"No dated source player classification at GW{gw}")
        bootstrap_path = mirror / bootstrap["local_relpath"]
        _checked_bytes(bootstrap_path, bootstrap["blob_sha256"])
        market, _ = _bootstrap_players_and_clubs(bootstrap_path, capture_upper=capture)
        rosters[gw] = roster_identity(
            market.loc[market["position_id"].between(1, 4)]
        ).assign(gameweek_id=gw)
    dated = pd.concat(rosters.values(), ignore_index=True)
    final = performance_rows(
        archived_raw.merge(
            dated[["player_id", "gameweek_id"]],
            on=["player_id", "gameweek_id"],
            validate="many_to_one",
        )
    )
    carry = annotate_history(final, unique_season_identity(dated), 0)
    carry = carry.loc[carry["position_id"].isin(OUTFIELD)].copy()
    examples: dict[Component, list[pd.DataFrame]] = {
        component: [] for component in EVENT
    }
    inventory = []
    for origin in origins:
        gw = int(origin["gw"])
        deadline = deadlines[gw]
        fixture_receipt = origin["fixtures"]
        possible = [
            prev["gw"]
            for prev in origins[: gw - 1]
            if datetime.fromisoformat(prev["settled_outcomes"]["finalized_at_utc"])
            < deadline
        ]
        past = (
            pd.concat([settled[week] for week in possible], ignore_index=True)
            if possible
            else final.iloc[:0].copy()
        )
        roster_prefix = unique_season_identity(dated.loc[dated["gameweek_id"].le(gw)])
        past = annotate_history(
            past.loc[past["kickoff_time"].lt(deadline)], roster_prefix, 0
        )
        info = {
            "gameweek": gw,
            "deadline": deadline.isoformat(),
            "eligible_history_rows": len(past),
            "published_prior_gameweeks": len(possible),
            "omitted_unsettled_gameweeks": gw - 1 - len(possible),
            "fixture_status": fixture_receipt["status"],
            "goal_training_rows": 0,
            "assist_training_rows": 0,
        }
        if (
            fixture_receipt["status"] == "supported"
            and datetime.fromisoformat(fixture_receipt["capture_upper_utc"]) < deadline
        ):
            fixture_source = _checked_bytes(
                mirror / fixture_receipt["local_relpath"],
                fixture_receipt["blob_sha256"],
            )
            labels = final.loc[final["gameweek_id"].eq(gw)]
            issued = _source_fixture_context(
                labels,
                roster_prefix.loc[roster_prefix["gameweek_id"].eq(gw)],
                fixture_source,
                gw,
            )
            # The historic opening issue has no earlier observations to estimate a
            # position pool. Leave it out of the fitted source loss for both designs.
            for component in EVENT:
                x = build_predictors(issued, past.iloc[:0], past, gw, component)
                matched = training_examples(
                    x.dropna(subset=["rate"]),
                    labels,
                    component,
                    soft=(component == "assists" and soft_assists),
                )
                examples[component].append(matched)
                info[f"{component.removesuffix('s')}_training_rows"] = len(matched)
        inventory.append(info)
    training = {
        component: pd.concat(examples[component], ignore_index=True)
        for component in EVENT
    }
    for component, rows in training.items():
        if rows.empty or rows["target"].gt(0).sum() == 0:
            raise ValueError(f"No positive admitted source targets for {component}")
    digest = sha256(manifest_raw + seed_raw + bytes([soft_assists])).hexdigest()
    last_available = max(
        datetime.fromisoformat(origin["settled_outcomes"]["finalized_at_utc"])
        for origin in origins
    )
    return SourcePanel(
        manifest["season"],
        digest,
        last_available,
        training,
        carry,
        pd.DataFrame(inventory),
    )
