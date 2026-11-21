"""Compare stored historical replay forecasts and outcomes against admitted prefix inputs."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd

from backtesting.empirical_mirrors import (
    extract_gw_df_from_merged_csv,
    load_empirical_manifest_bundle,
)
from backtesting.rolling_replay import ReplayDeadlineRecord, forecast_content_hash
from backtesting.walkforward import LEDGER_COMPONENTS
from commands.run_stage_a_and_b import (
    CONFIG_ROOT,
    MIRROR_ROOT,
    REPO,
    _prepare_filtered_seed,
    _stage_causal_gw_inputs,
)
from features.builder import (
    build_features,
    completed_performance_rows,
    history_before_target,
)
from models.base import BaseModel
from run_s1_replay import _factory

_HISTORY_COLUMNS = {
    "element": "player_id",
    "fixture": "fixture_id",
    "GW": "gameweek_id",
    "opponent_team": "opponent_club_id",
    "value": "price",
}
_KEYS = ["player_id", "gameweek_id", "fixture_id"]
_PROJECTIONS = ["projected_points", "projected_minutes", *LEDGER_COMPONENTS]
_OUTCOME_FIELDS = ["total_points", "minutes", "yellow_cards", "red_cards"]


def _history(manifest: dict[str, Any], gw: int, schema: pd.DataFrame) -> pd.DataFrame:
    if gw == 1:
        return schema.copy()
    receipt = manifest["origins"][gw - 2]["settled_outcomes"]
    path = MIRROR_ROOT / receipt["local_relpath"]
    if sha256(path.read_bytes()).hexdigest() != receipt["blob_sha256"]:
        raise ValueError("Prior admitted receipt differs from its manifest")
    parsed = pd.read_csv(path, low_memory=False).rename(columns=_HISTORY_COLUMNS)
    parsed["was_home"] = (
        parsed["was_home"].astype(str).str.lower().map({"true": True, "false": False})
    )
    if parsed["was_home"].isna().any():
        raise ValueError("Invalid admitted history home/away flags")
    return parsed.loc[parsed["gameweek_id"].lt(gw), schema.columns].astype(
        schema.dtypes.to_dict()
    )


def _solver_reference(
    projected: pd.DataFrame, players: pd.DataFrame, targets: range
) -> pd.DataFrame:
    wide = players[
        ["player_id", "position_id", "club_id", "now_cost", "purchase_eligible"]
    ].copy()
    grouped = projected.groupby(["player_id", "gameweek_id"])[
        ["projected_points", "projected_minutes"]
    ].sum()
    for target in targets:
        player_scores = grouped.xs(target, level="gameweek_id")
        wide[f"{target}_Pts"] = wide["player_id"].map(player_scores["projected_points"])
        wide[f"{target}_xMins"] = wide["player_id"].map(
            player_scores["projected_minutes"]
        )
    return wide


def _matches_settlement(
    record: ReplayDeadlineRecord, origin: dict[str, Any], players: set[int]
) -> bool:
    receipt = origin["settled_outcomes"]
    raw = (MIRROR_ROOT / receipt["local_relpath"]).read_bytes()
    if sha256(raw).hexdigest() != receipt["blob_sha256"]:
        raise ValueError(f"Invalid admitted settlement checksum at GW{record.deadline}")
    rows = extract_gw_df_from_merged_csv(raw, record.deadline)
    rows["element"] = pd.to_numeric(rows["element"])
    rows = rows.loc[rows["element"].isin(players)]
    stats = rows[_OUTCOME_FIELDS].apply(pd.to_numeric).groupby(rows["element"]).sum()
    reference = {pid: tuple(row) for pid, row in stats.iterrows() if any(row)}
    actual = {
        pid: (o.points, o.minutes, o.yellow_cards, o.red_cards)
        for pid, o in record.outcomes.outcomes
        if o.points or o.minutes or o.yellow_cards or o.red_cards
    }
    return reference == actual


def audit_prefix(
    season: str,
    prefix_end: int,
    inputs: Sequence[tuple[str, Callable[[], BaseModel], Path]],
    work: Path,
    *,
    expected_protocol: str | None = None,
) -> pd.DataFrame:
    manifest_path = CONFIG_ROOT / f"dev_mirror_{season.replace('-', '_')}_manifest.json"
    load_empirical_manifest_bundle(
        manifest_path,
        quarantine_root=MIRROR_ROOT,
        prefix_end_gw=prefix_end,
        require_admitted=True,
    )
    manifest = json.loads(manifest_path.read_text())
    archive = REPO / "data/archive" / season / "processed"
    schema = pd.read_parquet(archive / "player_performances.parquet").iloc[:0]
    roster = pd.read_parquet(archive / "players.parquet", columns=["id", "position_id"])
    native_players = set(roster.loc[roster["position_id"].between(1, 4), "id"])
    seed_name = "2024-25" if season == "2025-26" else "2023-24"
    seed = _prepare_filtered_seed(seed_name, work)
    reports: list[dict[str, Any]] = []
    for origin in manifest["origins"][:prefix_end]:
        gw = int(origin["gw"])
        proc, snapshots, players = _stage_causal_gw_inputs(
            season=season, origin_entry=origin, manifest=manifest, work_dir=work
        )
        players = players[players["position_id"].between(1, 4)].copy()
        fixtures = pd.read_parquet(proc / "fixtures.parquet")
        deadline = origin["deadline_utc"]
        history = completed_performance_rows(
            history_before_target(_history(manifest, gw, schema), gw, deadline, True),
            fixtures,
        )
        history.to_parquet(proc / "player_performances.parquet", index=False)
        features = build_features(
            proc,
            gw,
            6,
            seed_processed_dir=seed,
            use_archive_seed=False,
            as_of_gw=gw,
            history_before_gw=gw,
            target_deadline=deadline,
            availability_snapshot_root=snapshots,
            season=season,
            require_availability_snapshot=True,
            minutes_prior_source="seed_state",
        )
        features.attrs["issue_gameweek"] = gw
        features["native_rules_version"] = season
        for name, factory, run in inputs:
            model = factory()
            model.fit(history)
            reference = model.predict(features.copy(), 6)
            observed = pd.read_parquet(run / "projections" / f"gw{gw:02d}.parquet")
            left, right = (
                table.set_index(_KEYS)[_PROJECTIONS].sort_index()
                for table in (reference, observed)
            )
            pd.testing.assert_frame_equal(
                left, right, check_exact=False, atol=1e-10, rtol=0
            )
            [checkpoint] = list(run.glob(f"checkpoint_gw_{gw}_*.json"))
            record = ReplayDeadlineRecord.from_dict(json.loads(checkpoint.read_text()))
            if (
                record.execution_status != "SUCCESS"
                or record.model_name != name
                or (
                    expected_protocol is not None
                    and record.protocol_hash != expected_protocol
                )
            ):
                raise ValueError(f"Invalid replay checkpoint for {name}, GW{gw}")
            digest = forecast_content_hash(
                _solver_reference(reference, players, range(gw, gw + 6))
            )
            outcome_match = _matches_settlement(record, origin, native_players)
            if digest != record.forecast_hash or not outcome_match:
                raise ValueError(f"Admitted prefix mismatch for {name}, GW{gw}")
            reports.append(
                {
                    "season": season,
                    "model": name,
                    "origin_gw": gw,
                    "fixture_projection_rows": len(left),
                    "maximum_absolute_component_diff": float(
                        (left - right).abs().max().max()
                    ),
                    "solver_input_sha256": digest,
                    "checkpoint_forecast_sha256": record.forecast_hash,
                    "solver_forecast_hash_match": True,
                    "settled_outcome_match": True,
                    "evaluation_identity": record.evaluation_identity,
                    "checkpoint_id": record.checkpoint_id,
                    "protocol_hash": record.protocol_hash,
                    "model_version_hash": record.model_version_hash,
                }
            )
    return pd.DataFrame(reports)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--champion", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, action="append", required=True)
    parser.add_argument("--prototype", type=Path, required=True)
    parser.add_argument("--reviewed-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pin", type=Path)
    args = parser.parse_args()
    season, prefix_end = ("2025-26", 7) if args.pin is None else ("2024-25", 1)
    name, factory, _ = _factory(argparse.Namespace(prototype=None))
    definitions = [(name, factory, args.champion)]
    reserved_protocol = None
    if args.pin is not None:
        from run_s2_filter import _verified_selection, verified_s2_directories

        selection = _verified_selection(args.pin)
        pinned_model = selection.arms["candidate"]
        pin = json.loads(args.pin.read_text())
        source = (REPO / pin["prototype_path"]).resolve()
        if (
            len(args.candidate) != 1
            or source != args.prototype.resolve()
            or pinned_model.source_digest != args.reviewed_sha256
        ):
            raise ValueError("S-2 prefix audit requires the exact S-1 pin")
        reserved, reserved_protocol = verified_s2_directories(
            selection,
            require_both_input_inventories=True,
        )
        if (
            args.champion.resolve() != reserved["champion"]
            or args.candidate[0].resolve() != reserved["candidate"]
        ):
            raise ValueError(
                "S-2 prefix audit requires both canonically reserved replay arms"
            )
    for candidate in args.candidate:
        [opening] = list(candidate.glob("checkpoint_gw_1_*.json"))
        model_name = json.loads(opening.read_text())["model_name"]
        if args.pin is not None and model_name != pinned_model.name:
            raise ValueError("S-2 prefix audit would inspect an unpinned candidate")
        name, factory, _ = _factory(
            argparse.Namespace(
                prototype=args.prototype,
                variant=model_name,
                reviewed_sha256=args.reviewed_sha256,
            )
        )
        definitions.append((name, factory, candidate))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="parity-", dir=args.out.parent) as temporary:
        audit_prefix(
            season,
            prefix_end,
            definitions,
            Path(temporary),
            expected_protocol=reserved_protocol,
        ).to_csv(args.out, index=False)


if __name__ == "__main__":
    main()
