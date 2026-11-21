"""Compare two frozen S-2 models under a shared solver budget for research only."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import fcntl
from functools import partial, wraps
from hashlib import sha256
import json
from pathlib import Path
from socket import gethostname
from tempfile import TemporaryDirectory
from typing import Any, cast

import pandas as pd

from audit_historical_prefix import audit_prefix
from backtesting.native_transfer_solver import native_strategic_solve
from backtesting.ownership_anchor import UniverseSchema, solve_ownership_anchor
from backtesting.promotion_evidence import pair_replay_score
from backtesting.replay_state import Decision, ReplayState
from backtesting.rolling_replay import (
    QualityPolicy,
    ReplayDeadlineRecord,
    ReplayTrajectory,
    SolverCertificate,
    UncertifiedSolveError,
    replay_solver_binary_sha256,
    run_rolling_replay,
    validate_solver_certificate_consistency,
)
from backtesting.season_rules import Chip
from commands.run_stage_a_and_b import REPO, _outcomes_for_gw
from run_s1_replay import forecast, replay_directory
from run_s2_filter import (
    DAYS,
    SEASON,
    ReviewedModel,
    _canonical_bytes,
    _protocol_hash,
    _reserve_json,
    _verified_selection,
    verified_s2_directories,
)
from s2_historical_replay_inputs import stage_s2_inputs

METHOD = "best_feasible_at_180s"
# Reuse legality, settlement and checkpoint verification without requiring a proof.
# The production gate rejects this non-proven policy.
POLICY = QualityPolicy(time_limit_seconds=180.0, require_proven_optimal=False)
_ROOT = REPO / ".tmp/agent/explore-candidate/pre-slate/s2_incumbent_diagnostic"


@wraps(native_strategic_solve)
def solve_with_incumbent(
    state: ReplayState, horizon: int, forecasts: pd.DataFrame, options: dict[str, Any]
) -> tuple[Decision, SolverCertificate]:
    # Preserve native adapter metadata so rolling replay refreshes the issue market.
    try:
        decision, cert = native_strategic_solve(state, horizon, forecasts, options)
        verify_diagnostic_certificate(cert)
    except UncertifiedSolveError as exc:
        raise UncertifiedSolveError(f"Diagnostic GW{state.deadline}: {exc}") from exc
    return decision, cert


def verify_diagnostic_certificate(cert: SolverCertificate) -> None:
    validate_solver_certificate_consistency(cert)
    status = (cert.termination_status, cert.quality_mode)
    if not cert.feasible or status not in {
        ("OPTIMAL", "certified"),
        ("TIME_LIMIT", "time_capped"),
    }:
        raise UncertifiedSolveError(
            f"Diagnostic solve has no usable incumbent: {status[0]}"
        )
    if status[0] == "OPTIMAL" and cert.relative_gap > 1e-8:
        raise UncertifiedSolveError(
            "Diagnostic solve reported OPTIMAL with an open gap"
        )
    if (
        cert.strategic_audit.get("time_limit_seconds") != POLICY.time_limit_seconds
        or cert.strategic_audit.get("target_gap") != POLICY.target_gap
        or cert.seed != 42
    ):
        raise UncertifiedSolveError(
            "Diagnostic solve differs from the declared solver policy"
        )


def run_arm(
    model: ReviewedModel,
    work: Path,
    protocol: str,
    certified_protocol: str,
    certified_attempt_digest: str,
) -> tuple[Path, ReplayTrajectory]:
    if work.resolve() != work or (work / "replays").resolve() != work / "replays":
        raise ValueError("Diagnostic arm must use its own replay directory")
    manifest, seed = stage_s2_inputs(work)
    if _protocol_hash(certified_attempt_digest, seed) != certified_protocol:
        raise ValueError("Diagnostic inputs differ from the reserved S-2 inputs")
    deadlines = {row["gw"]: row["deadline_utc"] for row in manifest["origins"]}
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
    replay = replay_directory(work, model.name, len(DAYS), model.version, protocol)
    if replay.resolve() != replay:
        raise ValueError("Diagnostic checkpoint directory must be canonical")
    trace = run_rolling_replay(
        model.name,
        SEASON,
        anchor,
        lambda gw, _state: forecast(
            work, replay, model.factory, seed, gw, deadlines[gw], season=SEASON
        ),
        partial(_outcomes_for_gw, SEASON),
        horizon=6,
        end_gw=len(DAYS),
        solve_fn=solve_with_incumbent,
        policy=POLICY,
        checkpoint_dir=replay,
        model_version_hash=model.version,
        protocol_hash=protocol,
        chip_calendar=calendar,
    )
    if trace.deadlines != tuple(DAYS) or any(
        record.execution_status != "SUCCESS" for record in trace.records
    ):
        raise ValueError("Diagnostic requires a complete GW1–38 trajectory")
    for record in trace.records:
        verify_diagnostic_certificate(record.certificate)
        if (
            record.decision.chip != dict(calendar).get(record.deadline)
            or record.hit_penalty > 4
        ):
            raise ValueError(
                f"Diagnostic GW{record.deadline} differs from the frozen Strategic policy"
            )
    trace.audit_reconstructed_net_score()
    return replay, trace


def weekly_solver_report(
    record: ReplayDeadlineRecord,
    certified_replay: Path,
    certified_protocol: str,
    inventory: dict[str, str],
) -> dict[str, Any]:
    cert = record.certificate
    reference = (
        certified_replay
        / f"checkpoint_gw_{record.deadline}_{record.pre_state_hash}.json"
    )
    optimal = None
    if reference.name in inventory:
        payload = reference.read_bytes()
        if sha256(payload).hexdigest() != inventory[reference.name]:
            raise ValueError(f"Certified reference checkpoint changed: {reference}")
        optimal = ReplayDeadlineRecord.from_dict(json.loads(payload))
        verify_diagnostic_certificate(optimal.certificate)
        if (
            optimal.protocol_hash != certified_protocol
            or optimal.model_version_hash != record.model_version_hash
            or optimal.model_name != record.model_name
            or optimal.pre_state_hash != record.pre_state_hash
            or optimal.deadline != record.deadline
            or optimal.execution_status != "SUCCESS"
            or optimal.certificate.termination_status != "OPTIMAL"
        ):
            raise ValueError(f"Invalid certified reference checkpoint: {reference}")
        if optimal.forecast_hash != record.forecast_hash:
            optimal = None
    return {
        "status": cert.termination_status,
        "runtime_seconds": cert.runtime_seconds,
        "objective": cert.objective,
        "objective_bound": cert.objective_bound,
        "absolute_gap": cert.absolute_gap,
        "relative_gap": cert.relative_gap,
        "checkpoint_id": record.checkpoint_id,
        "certified_reference_same_inputs": optimal is not None,
        "certified_reference_checkpoint_id": optimal.checkpoint_id
        if optimal is not None
        else None,
        "matches_certified_transfers": (
            record.decision.transfers == optimal.decision.transfers
            if optimal is not None
            else None
        ),
        "matches_certified_lineup": (
            record.decision.lineup == optimal.decision.lineup
            if optimal is not None
            else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pin", type=Path, required=True)
    args = parser.parse_args()
    selection = _verified_selection(args.pin)
    if (
        selection.lane != "ext_01_1"
        or selection.arms["candidate"].name != "ext_01_1_a10"
    ):
        parser.error("This diagnostic is reserved for the pinned EXT-01_1 candidate")
    certified, certified_protocol = verified_s2_directories(
        selection, require_both_input_inventories=True
    )
    certified_attempt = sha256(
        (selection.attempt_dir / "attempt.json").read_bytes()
    ).hexdigest()
    work = _ROOT / selection.lane
    if work.resolve() != work or any(path.is_symlink() for path in work.rglob("*")):
        raise ValueError(
            "Diagnostic output must stay outside the certified reservation"
        )
    work.mkdir(parents=True, exist_ok=True)
    with (work / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        reference_path = work / "certified_references.json"
        if not reference_path.exists():
            _reserve_json(
                reference_path,
                {
                    arm: {
                        path.name: sha256(path.read_bytes()).hexdigest()
                        for path in directory.glob("checkpoint_gw_*.json")
                    }
                    for arm, directory in certified.items()
                },
            )
        reference_bytes = reference_path.read_bytes()
        references = json.loads(reference_bytes)
        diagnostic = {
            "purpose": "historical_diagnostic",
            "method": METHOD,
            "season": SEASON,
            "policy": asdict(POLICY),
            "certified_protocol_hash": certified_protocol,
            "certified_references_sha256": sha256(reference_bytes).hexdigest(),
            "pin_sha256": selection.pin_digest,
            "runner_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "solver_binary_sha256": replay_solver_binary_sha256(),
            "host_sha256": sha256(gethostname().encode()).hexdigest(),
        }
        protocol = sha256(_canonical_bytes(diagnostic)).hexdigest()
        _reserve_json(work / "diagnostic_protocol.json", diagnostic)
        runs = {
            arm: run_arm(
                model, work / arm, protocol, certified_protocol, certified_attempt
            )
            for arm, model in selection.arms.items()
        }
        champion, candidate = runs["champion"][1], runs["candidate"][1]
        if (
            champion.anchor_id != candidate.anchor_id
            or champion.records[0].pre_state != candidate.records[0].pre_state
        ):
            raise ValueError(
                "Diagnostic arms require the same neutral GW1 opening state"
            )
        with TemporaryDirectory(prefix="parity-", dir=work) as temporary:
            parity = audit_prefix(
                SEASON,
                1,
                [
                    (model.name, model.factory, runs[arm][0])
                    for arm, model in selection.arms.items()
                ],
                Path(temporary),
                expected_protocol=protocol,
            )
        weekly = []
        for a, b in zip(candidate.records, champion.records, strict=True):
            score = pair_replay_score(SEASON, a, b)
            weekly.append(
                {
                    "gameweek": score.gameweek,
                    "segment": score.segment,
                    "delta_net": score.delta_net,
                    "candidate_net_points": score.candidate_net_points,
                    "champion_net_points": score.champion_net_points,
                    "candidate_solver": weekly_solver_report(
                        a,
                        certified["candidate"],
                        certified_protocol,
                        references["candidate"],
                    ),
                    "champion_solver": weekly_solver_report(
                        b,
                        certified["champion"],
                        certified_protocol,
                        references["champion"],
                    ),
                }
            )
        report = {
            "method": METHOD,
            "qualification_eligible": False,
            "season": SEASON,
            "protocol_hash": protocol,
            "candidate": candidate.model_name,
            "champion": champion.model_name,
            "candidate_evaluation_identity": candidate.records[0].evaluation_identity,
            "champion_evaluation_identity": champion.records[0].evaluation_identity,
            "anchor_id": candidate.anchor_id,
            "candidate_net_points": candidate.cumulative_net,
            "champion_net_points": champion.cumulative_net,
            "net_delta": candidate.cumulative_net - champion.cumulative_net,
            "gw1_parity": parity.to_dict(orient="records"),
            "weekly": weekly,
        }
        path = work / "diagnostic_report.json"
        _reserve_json(path, report)
        print(path)


if __name__ == "__main__":
    main()
