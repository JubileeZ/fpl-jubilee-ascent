"""Run a certified S-1 Strategic trajectory from recovered historical inputs."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from functools import partial
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import subprocess
from typing import cast

import numpy as np
import pandas as pd

from backtesting.ownership_anchor import UniverseSchema, solve_ownership_anchor
from backtesting.rolling_replay import QualityPolicy, run_rolling_replay
from backtesting.season_rules import Chip
from backtesting.walkforward import LEDGER_COMPONENTS
from commands.run_stage_a_and_b import (
    CONFIG_ROOT,
    REPO,
    _champion_model_name,
    _outcomes_for_gw,
)
from features.builder import TERMINAL_PLAYER_COLUMNS, build_features
from features.availability_snapshots import resolve_latest_snapshot
from historical_replay_inputs import SEASON, SOURCE_PATH, stage_s1_inputs
from models import get_model
from models.base import BaseModel


def _expected_fixture_keys(
    market: pd.DataFrame, fixtures: pd.DataFrame, targets: range
) -> pd.MultiIndex:
    schedule = fixtures[["id", "gameweek_id", "home_club_id", "away_club_id"]]
    teams = schedule.melt(id_vars=["id", "gameweek_id"], value_name="club_id").drop(
        columns="variable"
    )
    player_weeks = market[["player_id", "club_id"]].merge(
        pd.DataFrame({"gameweek_id": targets}), how="cross"
    )
    expected = player_weeks.merge(teams, on=["club_id", "gameweek_id"], how="left")
    expected["fixture_id"] = expected["id"].fillna(-1).astype(int)
    return pd.MultiIndex.from_frame(
        expected[["player_id", "gameweek_id", "fixture_id"]]
    ).sort_values()


def forecast(
    work: Path,
    out: Path,
    factory: Callable[[], BaseModel],
    seed: Path,
    gw: int,
    deadline: str,
) -> pd.DataFrame:
    path = work / "verified_inputs" / f"gw{gw:02d}"
    horizon = min(6, 39 - gw)
    features = build_features(
        path,
        gw,
        horizon,
        use_archive_seed=False,
        seed_processed_dir=seed,
        as_of_gw=gw,
        history_before_gw=gw,
        target_deadline=deadline,
        availability_snapshot_root=path / "snapshots",
        season=SEASON,
        require_availability_snapshot=True,
        minutes_prior_source="seed_state",
    )
    history = pd.read_parquet(path / "player_performances.parquet")
    # These two columns come from the verified issue-time availability package.
    timed_availability = {"status", "chance_of_playing_next_round"}
    terminal = set(features).intersection(TERMINAL_PLAYER_COLUMNS) - timed_availability
    if (not history.empty and history["gameweek_id"].max() >= gw) or terminal:
        raise ValueError(f"Point-in-time forecast invariant failed at GW{gw}")
    features.attrs["issue_gameweek"] = gw
    features["native_rules_version"] = SEASON
    model = factory()
    model.fit(history)
    projections = model.predict(features, horizon)
    wide = pd.read_parquet(
        path / "market.parquet",
        columns=[
            "player_id",
            "position_id",
            "club_id",
            "now_cost",
            "purchase_eligible",
        ],
    )
    snapshot = resolve_latest_snapshot(path / "snapshots", SEASON, gw, deadline)
    if snapshot is None:
        raise ValueError(f"Missing source-bound snapshots at GW{gw}")
    targets = range(gw, gw + horizon)
    expected = _expected_fixture_keys(
        wide, cast(pd.DataFrame, snapshot["fixtures"]), targets
    )
    actual = pd.MultiIndex.from_frame(
        projections[["player_id", "gameweek_id", "fixture_id"]]
    ).sort_values()
    if not actual.is_unique or not actual.equals(expected):
        raise ValueError(
            f"Incomplete, duplicate or unexpected forecast fixtures at GW{gw}"
        )
    scoring = projections[["projected_points", "projected_minutes", *LEDGER_COMPONENTS]]
    blank = projections["fixture_id"].eq(-1)
    if (
        not np.isfinite(scoring.to_numpy()).all()
        or not scoring["projected_minutes"].between(0, 90).all()
        or not scoring.loc[blank, ["projected_points", "projected_minutes"]]
        .eq(0)
        .all()
        .all()
        or not np.allclose(
            scoring[list(LEDGER_COMPONENTS)].sum(axis=1),
            scoring["projected_points"],
            atol=1e-4,
            rtol=0,
        )
    ):
        raise ValueError(
            f"Unreconciled projection components or invalid minutes at GW{gw}"
        )
    dest = out / "projections"
    dest.mkdir(parents=True, exist_ok=True)
    long_path = dest / f"gw{gw:02d}.parquet"
    if long_path.is_file():
        pd.testing.assert_frame_equal(
            pd.read_parquet(long_path), projections, check_exact=True
        )
    else:
        projections.to_parquet(long_path, index=False)

    by_player_gw = projections.groupby(["player_id", "gameweek_id"])[
        ["projected_points", "projected_minutes"]
    ].sum()
    for target in targets:
        aggregated = by_player_gw.xs(target, level="gameweek_id")
        wide[f"{target}_Pts"] = wide["player_id"].map(aggregated["projected_points"])
        wide[f"{target}_xMins"] = wide["player_id"].map(aggregated["projected_minutes"])
    print(f"{model.name} forecast GW{gw}", flush=True)
    return wide


def _factory(args: argparse.Namespace) -> tuple[str, Callable[[], BaseModel], str]:
    if args.prototype is None:
        champion = _champion_model_name()
        source = REPO / "models" / f"{champion}.py"
        return (
            champion,
            partial(get_model, champion),
            sha256(source.read_bytes()).hexdigest(),
        )
    digest = sha256(args.prototype.read_bytes()).hexdigest()
    if digest != args.reviewed_sha256:
        raise ValueError("Prototype bytes differ from dual review sign-off")
    spec = spec_from_file_location("reviewed_prototype", args.prototype)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot import {args.prototype}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return args.variant, module.PROTOTYPES[args.variant], digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--prototype", type=Path)
    parser.add_argument("--variant")
    parser.add_argument("--reviewed-sha256")
    parser.add_argument("--through", type=int, choices=range(1, 39), default=38)
    args = parser.parse_args()
    if (args.prototype is None and (args.variant or args.reviewed_sha256)) or (
        args.prototype is not None and not (args.variant and args.reviewed_sha256)
    ):
        parser.error("Use --prototype, --variant and --reviewed-sha256 together")

    name, factory, source_digest = _factory(args)
    work = args.work.resolve()
    manifest, seed = stage_s1_inputs(work)
    deadlines = {origin["gw"]: origin["deadline_utc"] for origin in manifest["origins"]}
    calendar = tuple(
        (row["gameweek"], cast(Chip, row["chip"]))
        for row in manifest["shared_chip_calendar"]
    )
    anchor = solve_ownership_anchor(
        pd.read_parquet(work / "verified_inputs/gw01/market.parquet"),
        SEASON,
        gameweek=1,
        anchor_type="opening",
        schema=UniverseSchema(eligibility_col="purchase_eligible"),
    )
    tracked = subprocess.check_output(
        [
            "git",
            "ls-files",
            "-z",
            "models",
            "backtesting",
            "features",
            "solver",
            "projections",
        ],
        cwd=REPO,
        text=True,
    ).split("\0")
    base = sha256(
        b"".join(
            sha256((REPO / path).read_bytes()).digest()
            for path in tracked
            if path.endswith(".py")
        )
    ).hexdigest()
    model_digest = sha256(f"{base}\n{name}\n{source_digest}".encode()).hexdigest()
    archive = REPO / "data/archive" / SEASON / "processed"
    paths = [
        Path(__file__),
        Path(__file__).with_name("historical_replay_inputs.py"),
        REPO / "commands/run_stage_a_and_b.py",
        REPO / "uv.lock",
        SOURCE_PATH,
        CONFIG_ROOT / "dev_mirror_2025_26_manifest.json",
        CONFIG_ROOT / "season_lifecycle.json",
        *sorted(archive.glob("*.parquet")),
        *sorted(seed.glob("*.parquet")),
    ]
    protocol = sha256(
        b"".join(sha256(path.read_bytes()).digest() for path in paths)
    ).hexdigest()
    out = (
        work
        / "replays"
        / f"{name}-gw01-{args.through:02d}-{model_digest[:8]}-{protocol[:8]}"
    )
    trajectory = run_rolling_replay(
        name,
        SEASON,
        anchor,
        lambda gw, _state: forecast(work, out, factory, seed, gw, deadlines[gw]),
        partial(_outcomes_for_gw, SEASON),
        horizon=6,
        end_gw=args.through,
        chip_calendar=calendar,
        policy=QualityPolicy(
            mode="certified", target_gap=0.0, time_limit_seconds=180.0
        ),
        checkpoint_dir=out,
        model_version_hash=model_digest,
        protocol_hash=protocol,
    )
    total = trajectory.audit_reconstructed_net_score()
    if len(trajectory.records) != args.through or any(
        record.execution_status != "SUCCESS" for record in trajectory.records
    ):
        raise ValueError("Replay stopped before its declared last deadline")
    rows = [
        {
            "season": SEASON,
            "model": name,
            "gameweek": record.deadline,
            "net_points": record.net_points,
            "gross_points": record.total_gross_points,
            "hit_points": record.hit_penalty,
            "anchor_id": anchor.anchor_id,
            "checkpoint_id": record.checkpoint_id,
            "forecast_hash": record.forecast_hash,
            "evaluation_identity": record.evaluation_identity,
            "model_version_hash": model_digest,
            "protocol_hash": protocol,
            "source_sha256": source_digest,
            "projection_sha256": sha256(
                (out / "projections" / f"gw{record.deadline:02d}.parquet").read_bytes()
            ).hexdigest(),
        }
        for record in trajectory.records
    ]
    pd.DataFrame(rows).to_csv(out / "scores.csv", index=False)
    print(
        json.dumps(
            {
                "model": name,
                "through_gw": args.through,
                "net_points": total,
                "anchor_id": anchor.anchor_id,
                "protocol_sha256": protocol,
                "replay_dir": str(out),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
