"""Reproduce the early static control and run a single certified development lane."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

import audit_historical_prefix as prefix_audit
from backtesting.forecast_export import REQUIRED_COMPONENTS
import commands.run_stage_a_and_b as stages
from historical_replay_inputs import _checked_bytes
from prototypes.ext_40.prototypes import KEYS
from run_s1_replay import (
    champion_factory,
    execute_replay,
    forecast,
    model_version_hash,
    replay_directory,
    reviewed_grid,
    s1_protocol_hash,
)

_ARMS = ("goals_a", "assists_a")
_PROTOTYPES = Path(__file__).resolve().parent / "prototypes"
_FORECAST_COLUMNS = ["projected_points", "projected_minutes", *REQUIRED_COMPONENTS]


def replay_development(work: Path, arm: str, reviewed_sha256: str) -> None:
    mirror = work / "mirror"
    os.environ["STATIC_ATTACK_MIRROR_ROOT"] = str(mirror)
    model = f"static_{arm}"
    path = _PROTOTYPES / model / "prototypes.py"
    grid = reviewed_grid(path, reviewed_sha256)
    if set(grid) != {model}:
        raise ValueError("Each static lane must contain exactly one frozen variant")
    factory = grid[model]
    manifest_path = stages.CONFIG_ROOT / "dev_mirror_2025_26_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    season = manifest["season"]
    seed = work / "seed/seed_2024-25"
    protocol = s1_protocol_hash(seed)
    version = model_version_hash(model, reviewed_sha256)
    champion, champion_constructor, champion_digest = champion_factory()
    if champion != "def_xg_shrink_challenger":
        raise ValueError(
            "The frozen static variant requires its original Model Champion"
        )
    champion_run = replay_directory(
        work, champion, 38, model_version_hash(champion, champion_digest), protocol
    )
    incumbent_scores = pd.read_csv(champion_run / "scores.csv")
    if incumbent_scores["gameweek"].tolist() != list(range(1, 39)):
        raise ValueError("Qualification requires a complete Champion trajectory")

    output = work / arm
    output.mkdir(exist_ok=True)
    replay = replay_directory(work, model, 38, version, protocol)
    early = work / "ext41"
    early_identity = json.loads((early / "run_identity.json").read_bytes())
    _checked_bytes(
        early / "by_issue.csv", early_identity["bound_reports"]["by_issue.csv"]
    )
    early_by_issue = pd.read_csv(early / "by_issue.csv").set_index(
        ["component", "arm", "gameweek"]
    )
    if not early_by_issue.index.is_unique:
        raise ValueError("Early reference contains duplicate issue records")
    component, _ = arm.split("_")
    prior: list[tuple[int, pd.DataFrame]] = []
    rows = []
    for origin in manifest["origins"][:4]:
        gw = origin["gw"]
        path = early / arm / f"gw{gw:02d}.parquet"
        reference_hash = early_by_issue.at[(component, "a", gw), "forecast_sha256"]
        _checked_bytes(path, reference_hash)
        forecast(
            work,
            replay,
            factory,
            seed,
            gw,
            origin["deadline_utc"],
            prior_forecasts=prior,
        )
        stored = replay / "projections" / f"gw{gw:02d}.parquet"
        reference, observed = (
            pd.read_parquet(source).set_index(KEYS)[_FORECAST_COLUMNS].sort_index()
            for source in (path, stored)
        )
        pd.testing.assert_frame_equal(observed, reference, check_exact=True)
        rows.append(
            {
                "model": model,
                "gameweek": gw,
                "fixture_rows": len(reference),
                "reference_sha256": reference_hash,
                "qualification_sha256": sha256(stored.read_bytes()).hexdigest(),
                "exact_score_and_minutes_parity": True,
            }
        )
    pd.DataFrame(rows).to_csv(output / "early_forecast_parity.csv", index=False)

    execute_replay(
        model,
        factory,
        reviewed_sha256,
        work,
        season,
        manifest,
        seed,
        38,
        version,
        protocol,
    )
    reference_scores = pd.read_csv(
        _PROTOTYPES / "ext_41/evidence/rolling_decisions.csv"
    )
    candidate_scores = pd.read_csv(replay / "scores.csv")
    early_scores = []
    for old_name, scores in (("champion", incumbent_scores), (arm, candidate_scores)):
        reference = reference_scores.loc[
            reference_scores["arm"].eq(old_name), ["gameweek", "net", "hits"]
        ].reset_index(drop=True)
        observed = scores.loc[
            scores["gameweek"].between(1, 4), ["gameweek", "net_points", "hit_points"]
        ].rename(columns={"net_points": "net", "hit_points": "hits"})
        pd.testing.assert_frame_equal(observed.reset_index(drop=True), reference)
        early_scores.append(reference.assign(arm=old_name))
    pd.concat(early_scores, ignore_index=True).to_csv(
        output / "early_rolling_parity.csv", index=False
    )
    stages.MIRROR_ROOT = mirror
    prefix_audit.MIRROR_ROOT = mirror
    with TemporaryDirectory(prefix="parity-", dir=output) as temporary:
        parity = prefix_audit.audit_prefix(
            season,
            7,
            (
                (champion, champion_constructor, champion_run),
                (model, factory, replay),
            ),
            Path(temporary),
            expected_protocol=protocol,
        )
    parity.to_csv(output / "s1_prefix_parity.csv", index=False)
    print(f"Champion replay: {champion_run}\nCandidate replay: {replay}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--arm", choices=_ARMS, required=True)
    parser.add_argument("--reviewed-sha256", required=True)
    args = parser.parse_args()
    replay_development(args.work.resolve(), args.arm, args.reviewed_sha256)


if __name__ == "__main__":
    main()
