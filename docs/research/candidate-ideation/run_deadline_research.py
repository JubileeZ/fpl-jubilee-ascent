"""Deadline-dated EXT-38 and EXT-39 development experiments."""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backtesting.empirical_mirrors import extract_prior_settled_df
from features.availability_snapshots import resolve_latest_snapshot
from features.builder import completed_performance_rows, history_before_target
import historical_replay_inputs as history_source
from models.scoring_matrix import event_points
from run_s1_replay import (
    SEASON,
    champion_factory,
    execute_replay,
    forecast,
    model_version_hash,
    reviewed_grid,
    s1_protocol_hash,
)

KEYS = ["player_id", "gameweek_id", "fixture_id"]
TOPIC = Path(__file__).parent
PROTOTYPE = TOPIC / "prototypes/ext_38/prototypes.py"
VARIANTS = ("ext_38_k08_d16", "ext_38_k16_d32")
ISSUES = range(1, 39)
TESTS = (("bps", "xp_bonus", "bonus"), ("ict_index", "xp_attack", "attack"))
ARCHIVE = history_source.REPO / "data/archive" / SEASON / "processed"
POSITION = {1: "GK", 2: "D", 3: "M", 4: "F"}


def asof_rows(
    rows: pd.DataFrame, fixtures: pd.DataFrame, gw: int, deadline: str
) -> pd.DataFrame:
    return completed_performance_rows(
        history_before_target(rows, gw, deadline, True), fixtures
    )


def stage_deadline_history(work: Path) -> tuple[dict[str, Any], Path, str]:
    """Replace reconstructed fit history before any forecaster can read it."""
    history_source.MIRROR_ROOT = work / "mirror"
    manifest, seed = history_source.stage_s1_inputs(work)
    outcomes = pd.read_parquet(ARCHIVE / "player_performances.parquet")
    receipts = manifest["origins"]
    sources: list[dict[str, Any]] = []
    for origin in receipts:
        gw = origin["gw"]
        deadline = origin["deadline_utc"]
        capture = datetime.fromisoformat(deadline)
        issue = work / "verified_inputs" / f"gw{gw:02d}"
        snapshot = resolve_latest_snapshot(issue / "snapshots", SEASON, gw, deadline)
        if snapshot is None:
            raise ValueError(f"Missing deadline market and fixtures at GW{gw}")
        possible = [
            prev["settled_outcomes"]
            for prev in receipts
            if prev["gw"] < gw
            and datetime.fromisoformat(prev["settled_outcomes"]["finalized_at_utc"])
            < capture
        ]
        if possible:
            receipt = max(
                possible,
                key=lambda item: datetime.fromisoformat(item["finalized_at_utc"]),
            )
            raw = history_source._checked_bytes(
                history_source.MIRROR_ROOT / receipt["local_relpath"],
                receipt["blob_sha256"],
            )
            prior = extract_prior_settled_df(raw, before_gw=gw).rename(
                columns=history_source._PERFORMANCE_NAMES
            )
            prior["was_home"] = (
                prior["was_home"]
                .astype(str)
                .str.lower()
                .map({"true": True, "false": False})
            )
            if prior["was_home"].isna().any():
                raise ValueError(f"Invalid prior fixture home flag at GW{gw}")
            prior = prior[list(outcomes.columns)].astype(outcomes.dtypes.to_dict())
        else:
            receipt = {}
            prior = outcomes.iloc[:0].copy()
        fixtures = snapshot["fixtures"]
        eligible = asof_rows(prior, fixtures, gw, deadline)
        poisoned = outcomes.loc[outcomes["gameweek_id"].ge(gw)].head(20).copy()
        for field in ("total_points", "bps", "ict_index", "expected_goals", "minutes"):
            poisoned[field] = (
                "999" if pd.api.types.is_string_dtype(outcomes[field]) else 999
            )
        pd.testing.assert_frame_equal(
            eligible,
            asof_rows(
                pd.concat([prior, poisoned], ignore_index=True), fixtures, gw, deadline
            ),
            check_dtype=False,
        )
        if eligible.duplicated(KEYS).any():
            raise ValueError(f"Duplicate training keys at GW{gw}")
        destination = issue / "player_performances.parquet"
        if gw <= 7:
            pd.testing.assert_frame_equal(
                pd.read_parquet(destination), eligible.reset_index(drop=True)
            )
        else:
            eligible.to_parquet(destination, index=False)
        sources.append(
            {
                "gameweek": gw,
                "deadline": deadline,
                "history_receipt": receipt.get("blob_sha256"),
                "history_available": receipt.get("finalized_at_utc"),
                "max_history_gw": None
                if eligible.empty
                else int(eligible["gameweek_id"].max()),
                "history_rows": len(eligible),
                "history_sha256": sha256(destination.read_bytes()).hexdigest(),
                "target_mutation_invariant": True,
            }
        )
    pd.DataFrame(sources).to_csv(work / "issue_provenance.csv", index=False)
    return manifest, seed, strict_protocol(work, seed)


def strict_protocol(work: Path, seed: Path) -> str:
    return sha256(
        s1_protocol_hash(seed).encode()
        + Path(__file__).read_bytes()
        + (work / "issue_provenance.csv").read_bytes()
    ).hexdigest()


def load_staged(work: Path) -> tuple[dict[str, Any], Path, str]:
    manifest_path = history_source.CONFIG_ROOT / "dev_mirror_2025_26_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    source = pd.read_csv(work / "issue_provenance.csv")
    if (
        source["gameweek"].to_list() != list(ISSUES)
        or not source["target_mutation_invariant"].all()
    ):
        raise ValueError("Staged history inventory incomplete")
    for row, origin in zip(
        source.itertuples(index=False), manifest["origins"], strict=True
    ):
        history = (
            work
            / "verified_inputs"
            / f"gw{row.gameweek:02d}"
            / "player_performances.parquet"
        )
        if (
            row.deadline != origin["deadline_utc"]
            or sha256(history.read_bytes()).hexdigest() != row.history_sha256
            or (
                pd.notna(row.history_available)
                and pd.Timestamp(row.history_available) >= pd.Timestamp(row.deadline)
            )
        ):
            raise ValueError(
                f"Staged history differs from verified pre-deadline input at GW{row.gameweek}"
            )
    seed = work / "seed" / "seed_2024-25"
    return manifest, seed, strict_protocol(work, seed)


def historical_signal(
    past: pd.DataFrame, position: pd.Series, signal: str
) -> pd.Series:
    event = pd.to_numeric(past[signal], errors="coerce")
    minutes = pd.to_numeric(past["minutes"], errors="coerce")
    valid = minutes.gt(0) & np.isfinite(minutes) & np.isfinite(event)
    player = (
        pd.DataFrame({"event": event[valid], "minutes": minutes[valid]})
        .groupby(past.loc[valid, "player_id"])
        .sum()
    )
    pooled = player.groupby(position).sum()
    prior = position.reindex(player.index).map(pooled["event"] / pooled["minutes"])
    return 90 * (player["event"] + 360 * prior) / (player["minutes"] + 360)


def matched_issue(
    rows: pd.DataFrame, signal: str, component: str, outcome: str
) -> dict[str, float | int]:
    subset = rows.dropna(subset=[signal, outcome]).copy()
    subset["minutes_band"] = np.floor(subset["projected_minutes"] / 15)
    subset["points_band"] = np.floor(subset["projected_points"])
    subset["component_band"] = np.floor(subset[component] / 0.25)
    subset["error"] = subset[outcome] - subset[component]
    deltas: list[pd.Series] = []
    for _, group in subset.groupby(
        ["position_id", "minutes_band", "points_band", "component_band"]
    ):
        n = len(group) // 4
        if n == 0:
            continue
        ordered = group.sort_values([signal, "player_id", "fixture_id"])
        if (
            ordered[signal].iloc[n - 1] == ordered[signal].iloc[n]
            or ordered[signal].iloc[-n - 1] == ordered[signal].iloc[-n]
        ):
            continue
        cols = ["error", "projected_minutes", "projected_points", component]
        high, low = ordered.tail(n)[cols], ordered.head(n)[cols]
        deltas.append(
            (high.reset_index(drop=True) - low.reset_index(drop=True)).mean().rename(n)
        )
    deltas_frame = pd.DataFrame(deltas)
    matched = int(deltas_frame.index.to_numpy().sum()) if not deltas_frame.empty else 0
    weights = deltas_frame.index.to_numpy() if matched else None
    means = {
        f"delta_{key}": float(np.average(deltas_frame[key], weights=weights))
        for key in deltas_frame
    }
    return {
        "eligible": len(subset),
        "pairs": matched,
        "delta_error": float("nan"),
        **means,
    }


def bounds(series: pd.Series) -> float:
    values = series.to_numpy(dtype=float)
    starts = np.random.default_rng(39001).integers(0, len(values) - 4, size=(20000, 7))
    draws = values[
        (starts[:, :, None] + np.arange(5)).reshape(20000, -1)[:, : len(values)]
    ]
    finite = np.isfinite(draws).sum(axis=1)
    estimates = np.nansum(draws, axis=1)[finite > 0] / finite[finite > 0]
    return float(np.quantile(estimates, 0.025)) if len(estimates) else float("nan")


def run_diagnostics(work: Path, manifest: dict[str, Any], seed: Path) -> None:
    name, factory, _ = champion_factory()
    archive = pd.read_parquet(ARCHIVE / "player_performances.parquet")
    if (
        archive.duplicated(KEYS).any()
        or not archive["gameweek_id"].between(1, 38).all()
    ):
        raise ValueError("Invalid historical evaluation keys")
    print(
        f"Evaluation input {len(archive)} rows",
        archive[KEYS + ["minutes", "bps", "ict_index"]].head(2).to_dict("records"),
        flush=True,
    )
    weekly: list[dict[str, Any]] = []
    for origin in manifest["origins"]:
        gw = origin["gw"]
        issue = work / "verified_inputs" / f"gw{gw:02d}"
        out = work / "diagnostic_forecasts" / name
        forecast(work, out, factory, seed, gw, origin["deadline_utc"])
        forecast_rows = pd.read_parquet(out / "projections" / f"gw{gw:02d}.parquet")
        position = pd.read_parquet(issue / "market.parquet").set_index("player_id")[
            "position_id"
        ]
        past = pd.read_parquet(issue / "player_performances.parquet")
        first = forecast_rows.loc[
            forecast_rows["gameweek_id"].eq(gw)
            & forecast_rows["fixture_id"].ge(0)
            & forecast_rows["projected_minutes"].gt(0)
        ].copy()
        first["position_id"] = first["player_id"].map(position)
        first["xp_attack"] = first["xp_goals"] + first["xp_assists"]
        for signal, _, _ in TESTS:
            first[signal] = first["player_id"].map(
                historical_signal(past, position, signal)
            )
        labels = archive.loc[
            archive["gameweek_id"].eq(gw), KEYS + ["bonus", "goals_scored", "assists"]
        ]
        merged = first.merge(
            labels, on=KEYS, how="left", validate="one_to_one", indicator=True
        )
        missed = int(merged["_merge"].ne("both").sum())
        merged["attack"] = [
            event_points("goals", POSITION[pos], goals, rules_version=SEASON)
            + 3 * assists
            for pos, goals, assists in zip(
                merged["position_id"],
                merged["goals_scored"],
                merged["assists"],
                strict=True,
            )
        ]
        for signal, component, actual in TESTS:
            weekly.append(
                {
                    "gameweek": gw,
                    "signal": signal,
                    "issued_rows": len(first),
                    "unmatched_results": missed,
                    **matched_issue(merged, signal, component, actual),
                }
            )
    by_issue = pd.DataFrame(weekly)
    by_issue.to_csv(work / "ext39_by_issue.csv", index=False)
    stats = []
    for signal, _, _ in TESTS:
        rows = (
            by_issue[by_issue["signal"].eq(signal)]
            .set_index("gameweek")
            .reindex(ISSUES)
        )
        spread = rows["delta_error"]
        lower = bounds(spread.loc[8:38])
        stats.append(
            {
                "signal": signal,
                "pairs": int(rows["pairs"].sum()),
                "eligible": int(rows["eligible"].sum()),
                "matched_gameweeks": int(spread.notna().sum()),
                "prefix_gw01_07": spread.loc[:7].mean(),
                "gw08_19": spread.loc[8:19].mean(),
                "gw20_38": spread.loc[20:38].mean(),
                "gw08_38": spread.loc[8:38].mean(),
                "one_sided_lower_97_5": lower,
                "candidate_signal": bool(
                    spread.loc[8:19].mean() > 0
                    and spread.loc[20:38].mean() > 0
                    and lower > 0
                ),
            }
        )
    pd.DataFrame(stats).to_csv(work / "ext39_summary.csv", index=False)
    print(json.dumps(stats, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("task", choices=("stage", "diagnostic", "champion", *VARIANTS))
    parser.add_argument("--through", type=int, choices=ISSUES, default=38)
    parser.add_argument("--reviewed-sha256")
    args = parser.parse_args()
    work = args.work.resolve()
    if args.task == "stage":
        stage_deadline_history(work)
        return
    manifest, seed, protocol = load_staged(work)
    if args.task == "diagnostic":
        run_diagnostics(work, manifest, seed)
        return
    if args.task == "champion":
        name, factory, source = champion_factory()
    else:
        if not args.reviewed_sha256:
            parser.error("Candidate replay requires --reviewed-sha256")
        source = args.reviewed_sha256
        name, factory = args.task, reviewed_grid(PROTOTYPE, source)[args.task]
    execute_replay(
        name,
        factory,
        source,
        work,
        SEASON,
        manifest,
        seed,
        args.through,
        model_version_hash(name, source),
        protocol,
    )


if __name__ == "__main__":
    main()
