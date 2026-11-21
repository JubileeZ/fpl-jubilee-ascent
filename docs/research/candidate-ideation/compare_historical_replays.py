"""Compare complete paired historical replay traces and fixture projection guards."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from typing import Any

import pandas as pd

from backtesting.evidence_statistics import (
    StatisticalProtocolConfig,
    run_stored_score_bootstrap,
)
from backtesting.promotion_evidence import (
    GUARD_SEMANTICS,
    REQUIRED_MILP_SEGMENTS,
    _guards_from_rows,
    derive_s1_guard_margins,
    group_projection_gameweeks,
    milp_segment_regression_tolerance,
    pair_replay_score,
)
from backtesting.replay_state import state_hash
from backtesting.rolling_replay import (
    ReplayDeadlineRecord,
    ReplayTrajectory,
    validate_solver_certificate_consistency,
)
from backtesting.walkforward import LEDGER_COMPONENTS, _build_actual_components
from commands.run_stage_a_and_b import REPO
from run_s1_replay import SEASON as DEV_SEASON, champion_factory, s1_protocol_matches
from run_s2_filter import (
    DAYS,
    SEASON as FILTER_SEASON,
    _verified_selection,
    is_sha256,
    validate_prefix_parity,
    verified_s2_directories,
)


def _binding(scores: pd.DataFrame) -> dict[str, Any]:
    fields = (
        "model",
        "protocol_hash",
        "evaluation_identity",
        "model_version_hash",
        "source_sha256",
    )
    return {
        **{field: scores.at[0, field] for field in fields},
        "checkpoint_ids": {
            str(gw): checkpoint
            for gw, checkpoint in zip(
                scores["gameweek"], scores["checkpoint_id"], strict=True
            )
        },
        "forecast_hashes": {
            str(gw): forecast
            for gw, forecast in zip(
                scores["gameweek"], scores["forecast_hash"], strict=True
            )
        },
    }


def _actuals(
    season: str,
) -> tuple[set[int], dict[tuple[str, int, int], dict[str, Any]]]:
    archive = REPO / "data/archive" / season / "processed"
    raw = pd.read_parquet(archive / "player_performances.parquet")
    players = pd.read_parquet(archive / "players.parquet").rename(
        columns={"id": "player_id"}
    )
    players = players[players["position_id"].between(1, 4)]
    raw = raw[raw["player_id"].isin(players["player_id"])]
    if raw.duplicated(["player_id", "fixture_id"]).any():
        raise ValueError("Duplicate archive player-fixture outcomes")
    scored = _build_actual_components(
        raw, players[["player_id", "position_id"]].assign(native_rules_version=season)
    )
    sum_cols = [f"actual_{component}" for component in LEDGER_COMPONENTS]
    if not scored[sum_cols].sum(axis=1).eq(scored["total_points"]).all():
        raise ValueError(
            "Archived native scoring components do not reconcile to awarded points"
        )
    names = {"total_points": "actual_points", "minutes": "actual_minutes"}
    names.update(
        {
            f"actual_{row[0]}": row[1]
            for row in GUARD_SEMANTICS.values()
            if row[0].startswith("xp_")
        }
    )
    totals = (
        scored.groupby(["player_id", "gameweek_id"], as_index=False)[list(names)]
        .sum()
        .rename(columns=names)
    )
    outcomes = {
        (season, row["gameweek_id"], row["player_id"]): row
        for row in totals.to_dict(orient="records")
    }
    return set(players["player_id"]), outcomes


def _load_run(
    directory: Path,
    season: str,
    known_players: set[int],
    outcomes: dict[tuple[str, int, int], dict[str, Any]],
) -> tuple[str, pd.DataFrame, ReplayTrajectory, list[dict[str, Any]]]:
    scores = pd.read_csv(directory / "scores.csv")
    if scores["gameweek"].to_list() != DAYS or not scores["season"].eq(season).all():
        raise ValueError(f"Whole-season score inventory required: {directory}")
    columns = [
        "model",
        "anchor_id",
        "evaluation_identity",
        "model_version_hash",
        "protocol_hash",
        "source_sha256",
    ]
    if scores[columns].isna().any().any() or not scores[columns].nunique().eq(1).all():
        raise ValueError(f"Replay identities change inside {directory}")
    for field in (*columns[2:], "checkpoint_id", "forecast_hash", "projection_sha256"):
        if not scores[field].map(is_sha256).all():
            raise ValueError(f"Incomplete replay provenance {field}: {directory}")
    model = str(scores.at[0, "model"])
    anchor_id = str(scores.at[0, "anchor_id"])
    files = set(directory.glob("checkpoint_gw_*.json"))
    if len(files) != len(DAYS):
        raise ValueError(f"Exactly one checkpoint per deadline required: {directory}")
    forecasts: list[dict[str, Any]] = []
    records: list[ReplayDeadlineRecord] = []
    zero = {sem[1]: 0.0 for sem in GUARD_SEMANTICS.values()}
    for row in scores.itertuples(index=False):
        matches = list(directory.glob(f"checkpoint_gw_{row.gameweek}_*.json"))
        if len(matches) != 1:
            raise ValueError(
                f"Incomplete or duplicate checkpoint at GW{row.gameweek}: {directory}"
            )
        file = matches[0]
        record = ReplayDeadlineRecord.from_dict(json.loads(file.read_text()))
        cert = record.certificate
        validate_solver_certificate_consistency(cert)
        if (
            record.execution_status != "SUCCESS"
            or record.pre_state is None
            or record.pre_state.rules_version != season
            or record.deadline != row.gameweek
            or record.model_name != row.model
            or record.net_points != row.net_points
            or record.total_gross_points != row.gross_points
            or record.hit_penalty != row.hit_points
            or record.forecast_hash != row.forecast_hash
            or record.checkpoint_id != row.checkpoint_id
            or record.protocol_hash != row.protocol_hash
            or record.model_version_hash != row.model_version_hash
            or record.evaluation_identity != row.evaluation_identity
            or file.name != f"checkpoint_gw_{row.gameweek}_{record.pre_state_hash}.json"
            or not cert.feasible
            or cert.quality_mode != "certified"
            or cert.termination_status != "OPTIMAL"
            or cert.relative_gap > 1e-8
        ):
            raise ValueError(f"Checkpoint/score mismatch: {file}")
        records.append(record)
        path = directory / "projections" / f"gw{row.gameweek:02d}.parquet"
        if sha256(path.read_bytes()).hexdigest() != row.projection_sha256:
            raise ValueError(f"Fixture-grain projection checksum mismatch: {path}")
        prediction = pd.read_parquet(path)
        for pid, gw in (
            prediction[["player_id", "gameweek_id"]]
            .drop_duplicates()
            .itertuples(index=False, name=None)
        ):
            if pid not in known_players:
                raise ValueError(f"No season roster identity for forecast player {pid}")
            # Missing official performance row for a registered player implies no appearance this gameweek.
            outcomes.setdefault((season, gw, pid), zero)
        forecasts.extend(
            group_projection_gameweeks(prediction, season, row.gameweek, outcomes)
        )
    opening = records[0].pre_state
    manifest = json.loads((directory / "evaluation.json").read_bytes())
    if opening is None or manifest != {
        "evaluation_identity": scores.at[0, "evaluation_identity"],
        "initial_state_hash": state_hash(opening),
    }:
        raise ValueError(
            f"Replay manifest does not bind the opening state: {directory}"
        )
    final = records[-1].transition_result.state
    trajectory = ReplayTrajectory(
        model_name=model,
        season=season,
        anchor_id=anchor_id,
        deadlines=tuple(DAYS),
        records=tuple(records),
        cumulative_gross=int(scores["gross_points"].sum()),
        cumulative_hits=int(scores["hit_points"].sum()),
        cumulative_net=int(scores["net_points"].sum()),
        final_squad_ids=tuple(sorted(player.player_id for player in final.squad)),
        final_bank=final.bank,
    )
    trajectory.audit_reconstructed_net_score()
    return model, scores, trajectory, forecasts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--champion", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--season", choices=(DEV_SEASON, FILTER_SEASON), default=DEV_SEASON
    )
    parser.add_argument("--pin", type=Path)
    parser.add_argument("--prefix-parity", type=Path)
    args = parser.parse_args()
    season = args.season
    selection = None
    parity = None
    prefix_digest = None
    reserved_protocol = None
    if season == FILTER_SEASON:
        if not (args.pin and args.prefix_parity and len(args.candidate) == 1):
            parser.error(
                "S-2 requires --pin, --prefix-parity, and one frozen candidate"
            )
        selection = _verified_selection(args.pin)
        directories, reserved_protocol = verified_s2_directories(
            selection, require_both_input_inventories=True
        )
        if (
            args.champion.resolve() != directories["champion"]
            or args.candidate[0].resolve() != directories["candidate"]
        ):
            raise ValueError("S-2 comparison must use the two reserved replay arms")
        parity_bytes = args.prefix_parity.read_bytes()
        parity = pd.read_csv(BytesIO(parity_bytes))
        prefix_digest = sha256(parity_bytes).hexdigest()
        if set(parity["model"]) != {model.name for model in selection.arms.values()}:
            raise ValueError(
                "S-2 prefix parity must identify only the two reserved models"
            )
    elif args.pin or args.prefix_parity:
        parser.error("--pin and --prefix-parity apply only to the S-2 comparison")
    players, outcomes = _actuals(season)
    champion, champ_scores, champ_trace, champ_forecasts = _load_run(
        args.champion, season, players, outcomes
    )
    expected_champion, _, champion_source = champion_factory()
    if (
        champion != expected_champion
        or champ_scores.at[0, "source_sha256"] != champion_source
    ):
        raise ValueError("Comparison must use the confirmed Champion")
    champ_binding = _binding(champ_scores)
    if selection is not None:
        if (
            champ_binding["model_version_hash"] != selection.arms["champion"].version
            or champ_binding["protocol_hash"] != reserved_protocol
        ):
            raise ValueError(
                "S-2 Champion does not match the reserved model and protocol"
            )
        assert parity is not None
        validate_prefix_parity(parity, champ_binding, [1])
    elif not s1_protocol_matches(
        champ_binding["protocol_hash"],
        args.champion.resolve().parent.parent / "seed/seed_2024-25",
    ):
        raise ValueError(
            "Dev Champion protocol no longer matches the archive and staged seed"
        )
    inapplicable = {"defcon_points_mse"} if season == FILTER_SEASON else set()
    applicable = {
        name: semantics
        for name, semantics in GUARD_SEMANTICS.items()
        if name not in inapplicable
    }
    margins = (
        selection.margins
        if selection is not None
        else derive_s1_guard_margins(champ_forecasts)
    )
    margins_bytes = (
        json.dumps(margins, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()
    margins_digest = sha256(margins_bytes).hexdigest()
    protocol = {
        "guard_specs": {
            name: {
                "forecast_field": sem[0],
                "outcome_field": sem[1],
                "loss": sem[2],
                "margin": margins[name],
                "alpha": 0.05,
                "direction": "lower_is_better",
            }
            for name, sem in applicable.items()
        },
        "projection_evaluation": {
            "applicability": {season: dict.fromkeys(applicable, "required")},
            "leads": list(range(6)),
            "weights": [1.0] * 6,
        },
    }
    results, guard_rows, pairs = [], [], []
    compared = {champion}
    for directory in args.candidate:
        model, scores, trace, forecasts = _load_run(
            directory, season, players, outcomes
        )
        if (
            model in compared
            or trace.records[0].pre_state != champ_trace.records[0].pre_state
            or any(
                scores.at[0, name] != champ_scores.at[0, name]
                for name in ("anchor_id", "protocol_hash")
            )
        ):
            raise ValueError(
                "Candidate must use an independent trajectory with the same native opening state and protocol"
            )
        compared.add(model)
        binding = _binding(scores)
        if selection is not None:
            expected = selection.arms["candidate"]
            if (
                model != expected.name
                or binding["model_version_hash"] != expected.version
                or binding["source_sha256"] != expected.source_digest
            ):
                raise ValueError("S-2 candidate does not match the reserved variant")
            assert parity is not None
            validate_prefix_parity(parity, binding, [1])
        elif not s1_protocol_matches(
            binding["protocol_hash"],
            directory.resolve().parent.parent / "seed/seed_2024-25",
        ):
            raise ValueError(
                f"Dev {model} protocol no longer matches the archive and staged seed"
            )
        paired = [
            pair_replay_score(season, a, b)
            for a, b in zip(trace.records, champ_trace.records, strict=True)
        ]
        pairs.extend(
            {"model": model, **asdict(score), "delta_net": score.delta_net}
            for score in paired
        )
        guards = _guards_from_rows(
            {"candidate_name": model, "former_champion": champion},
            protocol,
            {(season, model): forecasts, (season, champion): champ_forecasts},
            cluster_by_gw=True,
        )
        guard_rows.extend(
            {"season": season, "model": model, **asdict(guard)} for guard in guards
        )
        segments = pd.DataFrame(
            {
                "segment": [row.segment for row in paired],
                "delta": [row.delta_net for row in paired],
            }
        )
        means = segments.groupby("segment")["delta"].mean().to_dict()
        if set(means) != set(REQUIRED_MILP_SEGMENTS):
            raise ValueError(
                f"Expected exact segments {REQUIRED_MILP_SEGMENTS}, got {tuple(sorted(means))}"
            )
        segment_pass = {
            name: float(value) >= -milp_segment_regression_tolerance(name)
            for name, value in means.items()
        }
        bootstrap = run_stored_score_bootstrap(paired, StatisticalProtocolConfig())
        delta = sum(row.delta_net for row in paired)
        results.append(
            {
                "season": season,
                "model": model,
                "champion": champion,
                "candidate_net": sum(row.candidate_net_points for row in paired),
                "champion_net": sum(row.champion_net_points for row in paired),
                "delta_net": delta,
                "projection_guards_ok": all(guard.passed for guard in guards),
                "segment_guards_ok": all(segment_pass.values()),
                "segment_mean_delta": means,
                "segment_pass": segment_pass,
                "historical_mbb": asdict(bootstrap),
                "anchor_id": scores.at[0, "anchor_id"],
                "opening_state_hash": trace.records[0].pre_state_hash,
                "guard_margins_sha256": margins_digest,
                **{key: value for key, value in binding.items() if key != "model"},
                **{
                    f"champion_{key}": value
                    for key, value in champ_binding.items()
                    if key != "model"
                },
                **(
                    {
                        "pin_sha256": selection.pin_digest,
                        "prefix_parity_sha256": prefix_digest,
                    }
                    if selection
                    else {}
                ),
            }
        )
    args.out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(pairs).to_csv(args.out / "paired_weekly_scores.csv", index=False)
    pd.DataFrame(guard_rows).to_csv(args.out / "projection_guards.csv", index=False)
    (args.out / "guard_margins.json").write_bytes(margins_bytes)
    (args.out / "summary.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
