"""Replay eligible EXT-41 arms through Dev GW4 under the paired certified policy."""

from __future__ import annotations

import argparse
from functools import partial
from hashlib import sha256
import json
from pathlib import Path
from typing import cast

import pandas as pd

from backtesting.ownership_anchor import UniverseSchema, solve_ownership_anchor
from backtesting.rolling_replay import (
    DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS,
    QualityPolicy,
    run_rolling_replay,
)
from backtesting.season_rules import Chip, load_season_lifecycle
from commands.run_stage_a_and_b import CONFIG_ROOT, _outcomes_for_gw
from historical_replay_inputs import SEASON, _checked_bytes
from prototypes.ext_40.prototypes import KEYS
from prototypes.ext_40.run import (
    HORIZON,
    ISSUES,
    STRATEGY_MARKET_COLUMNS,
    _experiment_identity,
)
from run_s1_replay import model_version_hash

REPLAY_ARMS = ("goals_a", "assists_a", "goals_c", "assists_c")


def replay(work: Path, arm: str) -> int:
    """Verify the eligible forecast bundle and retain a certified trajectory."""
    if arm not in (*REPLAY_ARMS, "champion"):
        raise ValueError(f"Unknown EXT-41 replay arm {arm}")
    lifecycle = load_season_lifecycle()
    dev = lifecycle.season_for_role("development")
    manifest_bytes = (
        CONFIG_ROOT / f"dev_mirror_{dev.replace('-', '_')}_manifest.json"
    ).read_bytes()
    manifest = json.loads(manifest_bytes)
    if SEASON != dev or manifest["season"] != dev:
        raise ValueError("EXT-41 requires its admitted development season")

    results = work / "ext41"
    raw_identity = (results / "run_identity.json").read_bytes()
    identity = json.loads(raw_identity)
    reports = identity["bound_reports"]
    for report in ("summary.csv", "by_issue.csv"):
        _checked_bytes(results / report, reports[report])
    summary = pd.read_csv(results / "summary.csv").set_index(
        ["component", "arm"], verify_integrity=True
    )
    if arm != "champion":
        component, feature_block = arm.split("_")
        eligible = summary.at[(component, feature_block), "forecast_eligible"]
        if summary["forecast_eligible"].dtype != bool or not eligible:
            raise ValueError(f"{arm} did not clear its declared forecast comparison")

    recorded = pd.read_csv(results / "by_issue.csv").set_index(
        ["component", "arm", "gameweek"], verify_integrity=True
    )
    baseline = work / "ext41_champion"
    current = _experiment_identity(work, baseline)
    bound = {**identity, "recipe": identity["ext40_recipe"]}
    if any(bound[key] != value for key, value in current.items()):
        raise ValueError(
            "EXT-41 replay inputs or Champion forecasts differ from issuance"
        )
    forecasts: dict[int, pd.DataFrame] = {}
    market_hashes = []
    for gw in ISSUES:
        name = f"gw{gw:02d}.parquet"
        champion_hash = recorded.at[("goals", "champion", gw), "forecast_sha256"]
        if recorded.at[("assists", "champion", gw), "forecast_sha256"] != champion_hash:
            raise ValueError(f"Champion forecast diverges between components at GW{gw}")
        _checked_bytes(baseline / "projections" / name, champion_hash)
        champion = pd.read_parquet(baseline / "projections" / name)
        projection = champion
        if arm != "champion":
            candidate_path = results / arm / name
            _checked_bytes(
                candidate_path,
                recorded.at[(component, feature_block, gw), "forecast_sha256"],
            )
            projection = pd.read_parquet(candidate_path)
            pd.testing.assert_frame_equal(
                projection[KEYS + ["projected_minutes"]],
                champion[KEYS + ["projected_minutes"]],
                check_exact=True,
            )
        by_player_gw = projection.groupby(["player_id", "gameweek_id"])[
            ["projected_points", "projected_minutes"]
        ].sum()
        market_path = work / "verified_inputs" / f"gw{gw:02d}" / "market.parquet"
        market_digest = recorded.at[("goals", "champion", gw), "market_sha256"]
        _checked_bytes(market_path, market_digest)
        market = pd.read_parquet(market_path, columns=STRATEGY_MARKET_COLUMNS)
        market_hashes.append(bytes.fromhex(market_digest))
        for target in range(gw, gw + HORIZON):
            aggregate = by_player_gw.xs(target, level="gameweek_id")
            market[f"{target}_Pts"] = market["player_id"].map(
                aggregate["projected_points"]
            )
            market[f"{target}_xMins"] = market["player_id"].map(
                aggregate["projected_minutes"]
            )
        forecasts[gw] = market

    anchor = solve_ownership_anchor(
        pd.read_parquet(work / "verified_inputs/gw01/market.parquet"),
        dev,
        gameweek=1,
        anchor_type="opening",
        schema=UniverseSchema(eligibility_col="purchase_eligible"),
    )
    calendar = tuple(
        (row["gameweek"], cast(Chip, row["chip"]))
        for row in manifest["shared_chip_calendar"]
    )
    protocol = sha256(
        raw_identity
        + manifest_bytes
        + b"".join(market_hashes)
        + Path(__file__).read_bytes()
        + current["s1"].encode()
    ).hexdigest()
    model_digest = model_version_hash(arm, sha256(raw_identity).hexdigest())
    out = results / "replays" / f"{arm}-{model_digest[:8]}-{protocol[:8]}"
    trajectory = run_rolling_replay(
        arm,
        dev,
        anchor,
        lambda gw, _state: forecasts[gw].copy(),
        partial(_outcomes_for_gw, dev),
        horizon=HORIZON,
        end_gw=ISSUES.stop - 1,
        chip_calendar=calendar,
        policy=QualityPolicy(
            mode="certified",
            target_gap=0.0,
            time_limit_seconds=DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS,
        ),
        checkpoint_dir=out,
        model_version_hash=model_digest,
        protocol_hash=protocol,
    )
    total = trajectory.audit_reconstructed_net_score()
    if [record.deadline for record in trajectory.records] != list(ISSUES) or any(
        record.execution_status != "SUCCESS" or record.decision is None
        for record in trajectory.records
    ):
        raise ValueError(f"{arm} did not complete the certified prefix")
    rows = []
    for record in trajectory.records:
        decision = record.decision
        assert decision is not None
        rows.append(
            {
                "arm": arm,
                "gameweek": record.deadline,
                "gross": record.total_gross_points,
                "hits": record.hit_penalty,
                "net": record.net_points,
                "anchor_id": anchor.anchor_id,
                "captain": decision.lineup.captain,
                "starters": json.dumps(decision.lineup.starters),
                "bench": json.dumps(decision.lineup.bench),
                "transfers": json.dumps(
                    [(sold, bought.player_id) for sold, bought in decision.transfers]
                ),
                "forecast_hash": record.forecast_hash,
                "checkpoint_id": record.checkpoint_id,
                "protocol_hash": protocol,
            }
        )
    pd.DataFrame(rows).to_csv(out / "decisions.csv", index=False)
    print(f"{arm} certified GW1–4 net {total} in {out}", flush=True)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("arm", choices=("champion", *REPLAY_ARMS))
    args = parser.parse_args()
    replay(args.work.resolve(), args.arm)


if __name__ == "__main__":
    main()
