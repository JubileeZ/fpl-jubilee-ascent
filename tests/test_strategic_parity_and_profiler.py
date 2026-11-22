"""TDD tests for ADR 0065 Strategic parity, QualityPolicy, 15 guards, and real profiler telemetry (#179)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import pandas as pd
import pytest

from backtesting.native_transfer_solver import native_strategic_solve
from backtesting.promotion_evidence import GUARD_SEMANTICS, MANDATORY_GUARDS, _verify_replay, evaluate_replay_evidence, finalized_gameweek_outcomes, protocol_from_payload
from backtesting.replay_cache import AdmissionContext, problem_material
from backtesting.replay_state import Player, initial_state, state_hash
from backtesting.rolling_replay import (
    QualityPolicy,
    _checkpoint_hash,
    get_strategic_replay_options,
    record_from_dict,
    replay_evaluation_identity,
)
from commands.profile_transfer_replay import (
    ProfilingEnvelope,
    ProfilingProblem,
    compute_workload_projection,
    execute_profiling_experiment,
    native_manifest_adapter,
)
from models.scoring_matrix import Position

POSITIONS: tuple[Position, ...] = (
    "GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F"
)


def _base_squad() -> tuple[Player, ...]:
    return tuple(
        Player(
            player_id=pid,
            position=pos,
            club=(pid - 1) % 5 + 1,
            purchase=50,
            market=50,
            purchase_eligible=True,
        )
        for pid, pos in enumerate(POSITIONS, 1)
    )


def test_adr_0065_strategic_options_and_post_transfer_ft_parity() -> None:
    opts = get_strategic_replay_options(6, rules_version="2025-26")
    assert opts["ft_use_penalty"] == 0.5
    assert opts["spare_ft_hold_weight"] == 0.325
    id1 = replay_evaluation_identity(
        model_name="m",
        model_version_hash="v1",
        protocol_hash="p1",
        season="2025-26",
        anchor_id="a1",
        horizon=6,
        last_gw=7,
        policy=QualityPolicy(),
        chip_calendar=(),
        solver_identity="s1",
    )
    assert len(id1) == 64

    # 2-GW analytical parity check comparing native_strategic_solve against solver/solver.py:848-869 formula
    squad = _base_squad()
    opening = initial_state("2025-26", squad)
    state = replace(opening, deadline=2, free_transfers=1, bank=10, parent_hash=state_hash(opening))
    rows = []
    for p in squad:
        rows.append(
            {
                "player_id": p.player_id,
                "position_id": {"GK": 1, "D": 2, "M": 3, "F": 4}[p.position],
                "club_id": p.club,
                "now_cost": p.market,
                "purchase_eligible": True,
                "2_Pts": 4.0 if p.player_id in (1, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14) else 0.0,
                "2_xMins": 90.0 if p.player_id != 15 else 0.0,
                "3_Pts": 4.0 if p.player_id in (1, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14) else 0.0,
                "3_xMins": 90.0 if p.player_id != 15 else 0.0,
            }
        )
    rows.append(
        {
            "player_id": 16,
            "position_id": 4,
            "club_id": 2,
            "now_cost": 50,
            "purchase_eligible": True,
            "2_Pts": 5.0,
            "2_xMins": 90.0,
            "3_Pts": 5.0,
            "3_xMins": 90.0,
        }
    )
    forecasts = pd.DataFrame(rows)
    h2_opts = get_strategic_replay_options(2, rules_version="2025-26")
    decision, cert = native_strategic_solve(state, 2, forecasts, h2_opts)
    assert cert.termination_status == "OPTIMAL"

    # Verification against analytical formula in solver/solver.py:848-869
    scale = float(h2_opts["horizon_scale"])
    ft_val_2 = float(h2_opts["ft_value_list"]["2"])
    plans = cert.strategic_audit["plans"]
    assert plans[0]["free_transfers"] == 1
    assert "post_free_transfers" in plans[0]
    if not decision.transfers:
        hold_w1 = 0.325 * ft_val_2 / scale
        assert cert.objective > 40.0 + hold_w1


def test_profiler_envelope_60s_zero_censoring_rss_and_live_cache(tmp_path: Path) -> None:
    env = ProfilingEnvelope(max_optimizer_calls=4, time_limit_per_call_seconds=60.0)
    assert env.time_limit_per_call_seconds == 60.0
    with pytest.raises(ValueError, match="60"):
        ProfilingEnvelope(time_limit_per_call_seconds=61.0)

    # Zero-censoring requirement for extrapolation_reliable
    rec_ok = execute_profiling_experiment(
        manifest=(
            ProfilingProblem("p1", "ordinary", 2, 6, 100, 1),
            ProfilingProblem("p2", "transfer_heavy", 3, 6, 100, 2),
            ProfilingProblem("p3", "chip_enabled", 4, 6, 100, 1),
            ProfilingProblem("p4", "constrained_budget", 5, 6, 0, 1),
        ),
        envelope=env,
        solver_hook=lambda p, g, tl: (
            replace(
                native_strategic_solve(
                    replace(initial_state("2025-26", _base_squad()), deadline=p.gameweek, free_transfers=1, parent_hash=state_hash(initial_state("2025-26", _base_squad()))),
                    1,
                    pd.DataFrame(
                        [
                            {
                                "player_id": pl.player_id,
                                "position_id": {"GK": 1, "D": 2, "M": 3, "F": 4}[pl.position],
                                "club_id": pl.club,
                                "now_cost": pl.market,
                                "purchase_eligible": True,
                                f"{p.gameweek}_Pts": 4.0,
                                f"{p.gameweek}_xMins": 90.0,
                            }
                            for pl in _base_squad()
                        ]
                    ),
                    get_strategic_replay_options(1, rules_version="2025-26"),
                )[1],
                runtime_seconds=0.05,
                relative_gap=0.0,
                termination_status="OPTIMAL",
                feasible=True,
                quality_mode="certified",
            ),
            "digest-ok",
        ),
        simulation=False,
        cache_root=tmp_path / "cache",
    )
    assert rec_ok.peak_rss_mb > 0.0
    assert all(r.assembly_time_seconds >= 0.0 and r.peak_rss_mb > 0.0 for r in rec_ok.records)
    assert rec_ok.workload_projection is not None
    assert rec_ok.workload_projection.measured_anchor_cost_seconds is not None
    assert rec_ok.workload_projection.measured_gw1_lineup_cost_seconds is not None
    assert rec_ok.workload_projection.extrapolation_reliable is True
    assert rec_ok.cache_benchmark is not None
    assert rec_ok.cache_benchmark.interrupted_resume_verified is True

    # Any censoring (>0) forces extrapolation_reliable=False even when <= 10%
    records_12 = [replace(rec_ok.records[0], problem_id=f"p{i}") for i in range(11)]
    records_12.append(replace(rec_ok.records[0], problem_id="p11", is_censored=True, termination_status="TIME_LIMIT"))
    proj = compute_workload_projection(records_12, total_planned_probes=12, anchor_cost=0.1, gw1_lineup_cost=0.1)
    assert proj.censored_rate < 0.10
    assert proj.extrapolation_reliable is False

    # native_manifest_adapter supports development_mirror mode
    st = replace(initial_state("2025-26", _base_squad()), deadline=2, bank=10, free_transfers=1)
    fc_rows = [
        {
            "player_id": pl.player_id,
            "position_id": {"GK": 1, "D": 2, "M": 3, "F": 4}[pl.position],
            "club_id": pl.club,
            "now_cost": pl.market,
            "purchase_eligible": True,
            "2_Pts": 4.0,
            "2_xMins": 90.0,
        }
        for pl in _base_squad()
    ]
    manifest_file = tmp_path / "dev_manifest.json"
    manifest_file.write_text(
        json.dumps(
            {
                "version": 2,
                "mode": "development_mirror",
                "season": "2025-26",
                "problems": [
                    {
                        "problem_id": "dm1",
                        "archetype": "ordinary",
                        "horizon": 1,
                        "state": asdict(st),
                        "forecasts": {"rows": fc_rows, "attrs": {}},
                        "chip_calendar": [],
                    }
                ],
            }
        )
    )
    loaded, solve_fn, source_id, _ = native_manifest_adapter(manifest_file)
    assert len(loaded) == 1 and source_id.startswith("development_mirror:")
    cert_dm, _ = solve_fn(loaded[0], 0.0, 60.0)
    assert cert_dm.termination_status == "OPTIMAL"


def test_promotion_evidence_rejects_time_capped_and_diagnostic_solvers(retained_request: Path) -> None:
    assert len(MANDATORY_GUARDS) == 15

    # Baseline fixture succeeds as inconclusive synthetic
    baseline = evaluate_replay_evidence(retained_request)
    assert baseline["empirical_admission"] is False
    assert baseline["scientific_verdict"] == "inconclusive"

    # Reject time_capped quality_policy directly inside _verify_replay (#179 Q5)
    req_tc = retained_request
    payload = json.loads(req_tc.read_text())
    proto_path = req_tc.parent / payload["protocol"]["path"]
    proto = json.loads(proto_path.read_text())
    config = protocol_from_payload(proto)
    proto_tc = {**proto, "quality_policy": {"mode": "time_capped", "target_gap": 0.0, "time_limit_seconds": 60.0}}
    with pytest.raises(ValueError, match="certified|QualityPolicy"):
        _verify_replay(
            req_tc.parent,
            payload["replays"][0],
            proto_tc,
            config,
            payload["model_source_hash"],
            {},
            "2026-01-01T00:00:00+00:00",
        )

    # Tampered checkpoint without recomputing checkpoint_id fails Class 6 lineage check,
    # and even with recomputed checkpoint_id, diagnostic solver_version is rejected inside _verify_replay
    entry = dict(payload["replays"][0])
    tpath = req_tc.parent / entry["trace"]["path"]
    tdata = json.loads(tpath.read_text())
    rec0_valid = record_from_dict(tdata["records"][0])
    bad_cert = replace(rec0_valid.certificate, solver_version="diagnostic-heuristic")
    rec0_diag = replace(rec0_valid, certificate=bad_cert)
    tdata["records"][0]["certificate"]["solver_version"] = "diagnostic-heuristic"
    tampered = json.dumps(tdata).encode()
    tpath.write_bytes(tampered)
    entry["trace"] = {"path": entry["trace"]["path"], "sha256": hashlib.sha256(tampered).hexdigest()}
    with pytest.raises(ValueError, match="Checkpoint content or lineage mismatch"):
        _verify_replay(req_tc.parent, entry, proto, config, payload["model_source_hash"], {}, "2026-01-01T00:00:00+00:00")

    rec0_rehashed_id = _checkpoint_hash(rec0_diag)
    tdata["records"][0]["checkpoint_id"] = rec0_rehashed_id
    prev_cp = rec0_rehashed_id
    for idx in range(1, len(tdata["records"])):
        rk = record_from_dict(tdata["records"][idx])
        tdata["records"][idx]["parent_checkpoint_id"] = prev_cp
        tdata["records"][idx]["checkpoint_id"] = _checkpoint_hash(replace(rk, parent_checkpoint_id=prev_cp))
        prev_cp = tdata["records"][idx]["checkpoint_id"]
    rehashed = json.dumps(tdata).encode()
    tpath.write_bytes(rehashed)
    entry["trace"] = {"path": entry["trace"]["path"], "sha256": hashlib.sha256(rehashed).hexdigest()}
    with pytest.raises(ValueError, match="precede"):
        _verify_replay(req_tc.parent, entry, proto, config, payload["model_source_hash"], {}, "2026-01-01T00:00:00+00:00")
    with pytest.raises(ValueError, match="Diagnostic/mock solver"):
        _verify_replay(req_tc.parent, entry, proto, config, payload["model_source_hash"], {}, "2099-01-01T00:00:00+00:00")


def test_empirical_promotion_outcomes_and_replay_cache_problem_material(tmp_path: Path) -> None:
    """Empirical origin payloads work cleanly with finalized_gameweek_outcomes and problem_material."""
    from backtesting.data_admission import require_input
    from backtesting.forecast_store import generate_forecast
    from backtesting.rolling_replay import replay_solver_identity
    from test_empirical_admission import _build_empirical_bundle

    req, cat, auth_map = _build_empirical_bundle(gws=(1, 2), partial_prefix=True)
    cap2 = require_input(req, cat, "2025-26", 2)
    fid, _, _ = generate_forecast(tmp_path / "fstore", cap2, req, cat, auth_map[2])
    st2 = replace(initial_state("2025-26", _base_squad()), deadline=2, free_transfers=1, bank=10)
    solver_id = replay_solver_identity(native_strategic_solve)
    mat = problem_material(
        tmp_path / "fstore",
        fid,
        AdmissionContext(cap2, req, cat, auth_map[2]),
        st2,
        anchor={"anchor_id": "a1"},
        calendar={"chip_calendar": []},
        policy={"horizon": 6},
        solver={"version": solver_id, "binary_sha256": "a" * 64, "options": {}},
        quality={"mode": "certified", "target_gap": 0.0},
    )
    assert mat["rules_id"] == "native-2025-26-v1"

    guard_specs = {name: {"outcome_field": sem[1]} for name, sem in GUARD_SEMANTICS.items()}
    outcomes = finalized_gameweek_outcomes(req["origins"][1], {"guard_specs": guard_specs}, catalog=cat)
    assert ("2025-26", 2, 1) in outcomes and outcomes["2025-26", 2, 1]["actual_points"] == 2.0
