"""Integration and verification tests for independent rolling transfer plan replay."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from backtesting.ownership_anchor import solve_ownership_anchor
from backtesting.replay_state import Decision, Lineup, Outcome, OutcomeBatch, Player, ReplayState, state_hash
from backtesting.rolling_replay import (
    IncompleteReplayOutcomeError,
    QualityPolicy,
    ReplayLegalityError,
    SolverCertificate,
    UncertifiedSolveError,
    clipped_replay_horizon,
    execute_replay_deadline,
    get_strategic_replay_options,
    record_from_dict,
    run_rolling_replay as _run_rolling_replay,
    heuristic_zero_transfer_solve,
    ReplayTrajectory,
    solve_lineup_milp,
    validate_decision_legality,
)


def _run_lineup_fixture_replay(*args: Any, **kwargs: Any) -> ReplayTrajectory:
    kwargs.setdefault("solve_fn", heuristic_zero_transfer_solve)
    kwargs.setdefault("model_version_hash", "synthetic-model-v1")
    kwargs.setdefault("protocol_hash", "synthetic-protocol-v1")
    return _run_rolling_replay(*args, **kwargs)


def _make_test_universe() -> pd.DataFrame:
    """Create a verified 24-player universe across 6 clubs."""
    players = []
    pid = 1
    # 4 GKP
    for i in range(4):
        players.append({"player_id": pid, "position_id": 1, "club_id": (i % 6) + 1, "now_cost": 45 + i * 5, "selected_by_percent": 15.0 + i * 5.0})
        pid += 1
    # 8 DEF
    for i in range(8):
        players.append({"player_id": pid, "position_id": 2, "club_id": (i % 6) + 1, "now_cost": 40 + i * 3, "selected_by_percent": 10.0 + i * 3.0})
        pid += 1
    # 8 MID
    for i in range(8):
        players.append({"player_id": pid, "position_id": 3, "club_id": (i % 6) + 1, "now_cost": 45 + i * 4, "selected_by_percent": 8.0 + i * 4.0})
        pid += 1
    # 4 FWD
    for i in range(4):
        players.append({"player_id": pid, "position_id": 4, "club_id": (i % 6) + 1, "now_cost": 55 + i * 8, "selected_by_percent": 12.0 + i * 5.0})
        pid += 1
    return pd.DataFrame(players)


def _make_test_certificate(opts: dict[str, Any], **overrides: Any) -> SolverCertificate:
    """Helper to instantiate a valid SolverCertificate with standard defaults."""
    kwargs: dict[str, Any] = {
        "feasible": True,
        "objective": 10.0,
        "objective_bound": 10.0,
        "absolute_gap": 0.0,
        "relative_gap": 0.0,
        "termination_status": "OPTIMAL",
        "runtime_seconds": 0.01,
        "threads": 1,
        "seed": 42,
        "solver_version": "highs",
        "quality_mode": "certified",
        "strategic_audit": opts,
    }
    kwargs.update(overrides)
    return SolverCertificate(**kwargs)


def _make_default_lineup(state: ReplayState) -> Lineup:
    """Helper to build a basic legal lineup for testing."""
    return Lineup(
        starters=tuple(p.player_id for p in state.squad[:11]),
        bench=tuple(p.player_id for p in state.squad[11:]),
        captain=state.squad[0].player_id,
        vice=state.squad[1].player_id,
    )


def test_strategic_replay_options_and_horizon_clipping() -> None:
    """Verify Strategic scenario parameters and horizon clipping at season boundaries."""
    opts_24 = get_strategic_replay_options(horizon=6, rules_version="2024-25")
    assert opts_24["arm"] == "strategic"
    assert opts_24["horizon"] == 6
    assert opts_24["starter_xmins_floor"] == 65.0
    assert opts_24["def_stack_cap"] == 2
    assert "ft_value_list" in opts_24
    assert set(opts_24["ft_value_list"].keys()) == {"2", "3", "4", "5"}

    # 2023-24 native rules capped at 2 FTs
    opts_23 = get_strategic_replay_options(horizon=6, rules_version="2023-24")
    assert set(opts_23["ft_value_list"].keys()) == {"2"}

    # Horizon clipping: at GW36 with last_gw=38, remaining = 3 -> clipped horizon = 3
    assert clipped_replay_horizon(36, last_gw=38, horizon=6) == 3
    assert clipped_replay_horizon(38, last_gw=38, horizon=6) == 1
    assert clipped_replay_horizon(1, last_gw=38, horizon=6) == 6


def test_multigw_independent_rolling_replay_and_score_reconstruction(tmp_path: Path) -> None:
    """Verify that multi-GW replay executes independently, tracks state, and reconstructs continuous score."""
    df_univ = _make_test_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")

    def fake_forecast_provider(gw: int, state: ReplayState) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "player_id": pid,
                "projected_points": float(10.0 + (pid % 5) * 2.0),
                f"xp_{gw}": float(8.0 + (pid % 7)),
            }
            for pid in range(1, 25)
        ])

    def fake_outcome_provider(gw: int) -> OutcomeBatch:
        return OutcomeBatch(
            rules_version="2024-25",
            deadline=gw,
            source_identity=f"synthetic-gw-{gw}",
            outcomes=tuple((pid, Outcome(points=4 + (gw + pid) % 6, minutes=90, appeared=True)) for pid in range(1, 25)),
        )

    cp_dir = tmp_path / "checkpoints"
    traj = _run_lineup_fixture_replay(
        model_name="test_model_alpha",
        season="2024-25",
        anchor=anchor,
        forecast_provider=fake_forecast_provider,
        outcome_provider=fake_outcome_provider,
        start_gw=1,
        end_gw=3,
        checkpoint_dir=cp_dir,
    )

    assert len(traj.records) == 3
    assert traj.deadlines == (1, 2, 3)
    assert traj.cumulative_gross > 0
    assert traj.cumulative_net > 0

    # In-memory audit recomputation without solver
    reconstructed = traj.audit_reconstructed_net_score()
    assert reconstructed == traj.cumulative_net

    # Offline audit recomputation directly from saved JSON checkpoint files
    saved_files = sorted(cp_dir.glob("checkpoint_gw_*.json"))
    assert len(saved_files) == 3
    disk_records = [record_from_dict(json.loads(f.read_text(encoding="utf-8"))) for f in saved_files]
    offline_net = sum(r.net_points for r in disk_records)
    assert offline_net == traj.cumulative_net


def test_checkpoint_crash_and_resume(tmp_path: Path) -> None:
    """Verify crash/restart resume loads previous state from checkpoints and continues cleanly."""
    df_univ = _make_test_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")

    def fake_forecast_provider(gw: int, state: ReplayState) -> pd.DataFrame:
        return pd.DataFrame([
            {"player_id": pid, "projected_points": float(10.0 + pid)}
            for pid in range(1, 25)
        ])

    def fake_outcome_provider(gw: int) -> OutcomeBatch:
        return OutcomeBatch(
            rules_version="2024-25",
            deadline=gw,
            source_identity=f"synth-{gw}",
            outcomes=tuple((pid, Outcome(points=6, minutes=90, appeared=True)) for pid in range(1, 25)),
        )

    cp_dir = tmp_path / "resume_cps"

    interrupted = True

    def interrupted_solve(state: ReplayState, horizon: int, forecasts: pd.DataFrame, options: dict[str, Any]) -> tuple[Decision, SolverCertificate]:
        if interrupted and state.deadline == 3:
            raise RuntimeError("simulated interruption")
        return heuristic_zero_transfer_solve(state, horizon, forecasts, options)

    with pytest.raises(RuntimeError, match="simulated interruption"):
        _run_lineup_fixture_replay(
        model_name="resume_model",
        season="2024-25",
        anchor=anchor,
        forecast_provider=fake_forecast_provider,
        outcome_provider=fake_outcome_provider,
        start_gw=1,
        end_gw=3,
        checkpoint_dir=cp_dir,
        solve_fn=interrupted_solve,
    )
    first_ids = [json.loads(p.read_text())["checkpoint_id"] for p in sorted(cp_dir.glob("checkpoint_gw_*.json"))]
    assert len(first_ids) == 2
    interrupted = False

    # Resume to GW3: should load GW1 and GW2 from disk and solve only GW3
    traj_resumed = _run_lineup_fixture_replay(
        model_name="resume_model",
        season="2024-25",
        anchor=anchor,
        forecast_provider=fake_forecast_provider,
        outcome_provider=fake_outcome_provider,
        start_gw=1,
        end_gw=3,
        checkpoint_dir=cp_dir,
        solve_fn=interrupted_solve,
    )
    assert len(traj_resumed.records) == 3
    assert traj_resumed.deadlines == (1, 2, 3)
    assert traj_resumed.records[0].checkpoint_id == first_ids[0]
    assert traj_resumed.records[1].checkpoint_id == first_ids[1]


def test_cache_changes_and_corruption_rejection(tmp_path: Path) -> None:
    """Verify that altered or corrupted checkpoint files on disk are detected and rejected."""
    df_univ = _make_test_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")

    def fake_forecast_provider(gw: int, state: ReplayState) -> pd.DataFrame:
        return pd.DataFrame([{"player_id": pid, "projected_points": 5.0} for pid in range(1, 25)])

    def fake_outcome_provider(gw: int) -> OutcomeBatch:
        return OutcomeBatch("2024-25", gw, f"s-{gw}", tuple((pid, Outcome(5, 90, True)) for pid in range(1, 25)))

    cp_dir = tmp_path / "corrupted_cps"
    _run_lineup_fixture_replay(
        model_name="model_corrupt",
        season="2024-25",
        anchor=anchor,
        forecast_provider=fake_forecast_provider,
        outcome_provider=fake_outcome_provider,
        start_gw=1,
        end_gw=1,
        checkpoint_dir=cp_dir,
    )

    # Corrupt the checkpoint pre_state_hash on disk
    cp_file = next(cp_dir.glob("checkpoint_gw_1_*.json"))
    data = json.loads(cp_file.read_text(encoding="utf-8"))
    data["pre_state_hash"] = "deadbeef" * 8
    cp_file.write_text(json.dumps(data), encoding="utf-8")

    # Resuming should detect corrupted pre-state hash and raise ValueError
    with pytest.raises(ValueError, match="Corrupted resume checkpoint state mismatch"):
        _run_lineup_fixture_replay(
            model_name="model_corrupt",
            season="2024-25",
            anchor=anchor,
            forecast_provider=fake_forecast_provider,
            outcome_provider=fake_outcome_provider,
            start_gw=1,
            end_gw=1,
            checkpoint_dir=cp_dir,
        )


def test_strict_outcome_coverage_partial_publication() -> None:
    """Verify that IncompleteReplayOutcomeError is raised if any squad player is omitted from outcomes."""
    df_univ = _make_test_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")
    state = anchor.to_replay_state("2024-25")

    forecast_df = pd.DataFrame([{"player_id": p.player_id, "projected_points": 5.0} for p in state.squad])
    omitted_pid = state.squad[0].player_id
    partial_outcomes = OutcomeBatch(
        rules_version="2024-25",
        deadline=1,
        source_identity="partial-report",
        outcomes=tuple((p.player_id, Outcome(5, 90, True)) for p in state.squad if p.player_id != omitted_pid),
    )

    with pytest.raises(IncompleteReplayOutcomeError, match="Missing required outcome coverage"):
        execute_replay_deadline(state, forecast_df, partial_outcomes)


def test_bench_boost_native_scoring() -> None:
    """Verify that Bench Boost scores all 15 squad players while preserving legal 11/4 lineup partition."""
    df_univ = _make_test_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")
    state = anchor.to_replay_state("2024-25")
    target_xp = {p.player_id: float(p.player_id) for p in state.squad}

    lineup = solve_lineup_milp(state.squad, target_xp)
    # Lineup retains strict 11 starters and 4 bench partition
    assert len(lineup.starters) == 11
    assert len(lineup.bench) == 4

    decision = Decision(
        transfers=(),
        lineup=lineup,
        expected_state_hash=state_hash(state),
        issued_deadline=1,
        chip="bench_boost",
    )
    forecast_df = pd.DataFrame([{"player_id": p.player_id, "projected_points": 5.0} for p in state.squad])
    # Every player scores 5 points; captain gets double
    outcomes = OutcomeBatch("2024-25", 1, "bb-test", tuple((p.player_id, Outcome(5, 90, True)) for p in state.squad))

    rec = execute_replay_deadline(
        state,
        forecast_df,
        outcomes,
        solve_fn=lambda s, h, f, o: (decision, _make_test_certificate(o)),
    )
    # 15 players * 5 points = 75 gross points + 5 captain increment = 80 net points!
    assert rec.gross_points == 75
    assert rec.net_points == 80


def test_policies_diverge_and_retain_consequences() -> None:
    """Verify that two distinct transfer policies diverge and retain downstream consequences."""
    df_univ = _make_test_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")

    def solver_a(
        state: ReplayState,
        horizon: int,
        forecast_df: pd.DataFrame,
        opts: dict[str, Any],
    ) -> tuple[Decision, SolverCertificate]:
        target_xp = {int(r["player_id"]): float(r["projected_points"]) for r in forecast_df.to_dict(orient="records")}
        if state.deadline == 1:
            lineup = solve_lineup_milp(state.squad, target_xp)
            dec = Decision(transfers=(), lineup=lineup, expected_state_hash=state_hash(state), issued_deadline=1)
        else:
            sold_player = next(p for p in state.squad if p.position == "D")
            owned_ids = {p.player_id for p in state.squad}
            unowned_d = next(pid for pid in range(5, 13) if pid not in owned_ids)
            bought_p = Player(player_id=unowned_d, position="D", club=6, purchase=45, market=45, purchase_eligible=True)
            transfers = ((sold_player.player_id, bought_p),)
            new_squad = tuple(p for p in state.squad if p.player_id != sold_player.player_id) + (bought_p,)
            lineup = solve_lineup_milp(new_squad, target_xp)
            dec = Decision(transfers=transfers, lineup=lineup, expected_state_hash=state_hash(state), issued_deadline=state.deadline)

        cert = _make_test_certificate(opts)
        return dec, cert

    def solver_b(
        state: ReplayState,
        horizon: int,
        forecast_df: pd.DataFrame,
        opts: dict[str, Any],
    ) -> tuple[Decision, SolverCertificate]:
        target_xp = {int(r["player_id"]): float(r["projected_points"]) for r in forecast_df.to_dict(orient="records")}
        lineup = solve_lineup_milp(state.squad, target_xp)
        dec = Decision(transfers=(), lineup=lineup, expected_state_hash=state_hash(state), issued_deadline=state.deadline)
        cert = _make_test_certificate(opts)
        return dec, cert

    def fake_forecast(gw: int, state: ReplayState) -> pd.DataFrame:
        return pd.DataFrame([
            {"player_id": pid, "projected_points": float(100.0 if pid in (5, 6, 8) else 10.0 + pid)}
            for pid in range(1, 25)
        ])

    def fake_outcomes(gw: int) -> OutcomeBatch:
        return OutcomeBatch(
            rules_version="2024-25",
            deadline=gw,
            source_identity=f"synth-{gw}",
            outcomes=tuple((pid, Outcome(points=15 if pid in (5, 6, 7, 8) else 5, minutes=90, appeared=True)) for pid in range(1, 25)),
        )

    traj_a = _run_lineup_fixture_replay("model_a", "2024-25", anchor, fake_forecast, fake_outcomes, start_gw=1, end_gw=2, solve_fn=solver_a)
    traj_b = _run_lineup_fixture_replay("model_b", "2024-25", anchor, fake_forecast, fake_outcomes, start_gw=1, end_gw=2, solve_fn=solver_b)

    # State diverged at GW2: Squad A and Squad B have different players
    assert traj_a.final_squad_ids != traj_b.final_squad_ids
    # Net points diverge due to player scoring differences
    assert traj_a.cumulative_net != traj_b.cumulative_net


def test_identical_policies_remain_identical() -> None:
    """Verify that identical models under identical policies produce 100% bit-for-bit identical trajectories."""
    df_univ = _make_test_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")

    def fake_forecast(gw: int, state: ReplayState) -> pd.DataFrame:
        return pd.DataFrame([
            {"player_id": pid, "projected_points": float(100.0 if pid in (5, 6, 8) else 10.0 + pid)}
            for pid in range(1, 25)
        ])

    def fake_outcomes(gw: int) -> OutcomeBatch:
        return OutcomeBatch("2024-25", gw, f"s-{gw}", tuple((pid, Outcome(5, 90, True)) for pid in range(1, 25)))

    traj_1 = _run_lineup_fixture_replay("champion", "2024-25", anchor, fake_forecast, fake_outcomes, start_gw=1, end_gw=2)
    traj_2 = _run_lineup_fixture_replay("champion", "2024-25", anchor, fake_forecast, fake_outcomes, start_gw=1, end_gw=2)

    assert traj_1.cumulative_net == traj_2.cumulative_net
    assert traj_1.final_squad_ids == traj_2.final_squad_ids
    assert traj_1.final_bank == traj_2.final_bank
    for r1, r2 in zip(traj_1.records, traj_2.records, strict=True):
        assert r1.checkpoint_id == r2.checkpoint_id
        assert r1.pre_state_hash == r2.pre_state_hash
        assert r1.post_state_hash == r2.post_state_hash


def test_invalid_decisions_rejected_before_transition() -> None:
    """Verify that illegal decisions fail with ReplayLegalityError before applying state transition."""
    df_univ = _make_test_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")
    state = anchor.to_replay_state("2024-25")

    # 1. GW1 transfer lock violation
    sold = state.squad[0]
    bought = Player(player_id=99, position="GK", club=1, purchase=45, market=45, purchase_eligible=True)
    illegal_gw1_transfer = Decision(
        transfers=((sold.player_id, bought),),
        lineup=_make_default_lineup(state),
        expected_state_hash=state_hash(state),
        issued_deadline=1,
    )
    with pytest.raises(ReplayLegalityError, match="GW1 transfers are locked"):
        validate_decision_legality(state, illegal_gw1_transfer)

    # 2. State hash mismatch (stale pre-state)
    stale_dec = Decision(
        transfers=(),
        lineup=_make_default_lineup(state),
        expected_state_hash="0" * 64,
        issued_deadline=1,
    )
    with pytest.raises(ReplayLegalityError, match="pre-state hash mismatch"):
        validate_decision_legality(state, stale_dec)


def test_certified_quality_policy_rejection() -> None:
    """Verify that uncertified solves with non-zero gap are rejected under certified policy."""
    df_univ = _make_test_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")
    state = anchor.to_replay_state("2024-25")

    def bad_gap_solver(
        state: ReplayState,
        horizon: int,
        forecast_df: pd.DataFrame,
        opts: dict[str, Any],
    ) -> tuple[Decision, SolverCertificate]:
        lineup = solve_lineup_milp(state.squad, {})
        dec = Decision(transfers=(), lineup=lineup, expected_state_hash=state_hash(state), issued_deadline=1)
        cert = _make_test_certificate(
            opts,
            relative_gap=0.10,
            objective_bound=11.0,
            absolute_gap=1.0,
            termination_status="TIME_LIMIT",
        )
        return dec, cert

    forecast_df = pd.DataFrame([{"player_id": p.player_id, "projected_points": 5.0} for p in state.squad])
    outcomes = OutcomeBatch("2024-25", 1, "test", tuple((p.player_id, Outcome(5, 90, True)) for p in state.squad))

    with pytest.raises(UncertifiedSolveError, match="failed certified quality policy"):
        execute_replay_deadline(
            state,
            forecast_df,
            outcomes,
            solve_fn=bad_gap_solver,
            policy=QualityPolicy(mode="certified", target_gap=0.0, require_proven_optimal=True),
        )


def test_uncertified_solve_trajectory_recording() -> None:
    """Verify that uncertified solves are recorded with explicit status without disappearing or counting as loss."""
    df_univ = _make_test_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")

    def non_optimal_solver(
        state: ReplayState,
        horizon: int,
        forecast_df: pd.DataFrame,
        opts: dict[str, Any],
    ) -> tuple[Decision, SolverCertificate]:
        lineup = solve_lineup_milp(state.squad, {})
        dec = Decision(transfers=(), lineup=lineup, expected_state_hash=state_hash(state), issued_deadline=state.deadline)
        cert = _make_test_certificate(
            opts,
            relative_gap=0.05,
            objective_bound=10.5,
            absolute_gap=0.5,
            termination_status="SUBOPTIMAL",
        )
        return dec, cert

    def fake_forecast(gw: int, state: ReplayState) -> pd.DataFrame:
        return pd.DataFrame([{"player_id": p.player_id, "projected_points": 5.0} for p in state.squad])

    def fake_outcomes(gw: int) -> OutcomeBatch:
        return OutcomeBatch("2024-25", gw, f"test-{gw}", tuple((pid, Outcome(5, 90, True)) for pid in anchor.player_ids))

    # Run with raise_on_failure=False: should record uncertified status explicitly
    traj = _run_lineup_fixture_replay(
        model_name="gap_model",
        season="2024-25",
        anchor=anchor,
        forecast_provider=fake_forecast,
        outcome_provider=fake_outcomes,
        start_gw=1,
        end_gw=2,
        solve_fn=non_optimal_solver,
        policy=QualityPolicy(mode="certified", target_gap=0.0, require_proven_optimal=True, raise_on_failure=False),
    )
    assert traj.deadlines == (1,)
    assert traj.records[0].execution_status == "UNCERTIFIED_GAP"


def test_time_capped_policy_timeout_rejection() -> None:
    """Verify that timeouts under time-capped policy are explicitly signaled."""
    df_univ = _make_test_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")
    state = anchor.to_replay_state("2024-25")

    def timed_out_solver(
        state: ReplayState,
        horizon: int,
        forecast_df: pd.DataFrame,
        opts: dict[str, Any],
    ) -> tuple[Decision, SolverCertificate]:
        lineup = solve_lineup_milp(state.squad, {})
        dec = Decision(transfers=(), lineup=lineup, expected_state_hash=state_hash(state), issued_deadline=1)
        cert = _make_test_certificate(
            opts,
            feasible=False,
            termination_status="TIMEOUT",
            runtime_seconds=60.0,
            quality_mode="time_capped",
        )
        return dec, cert

    forecast_df = pd.DataFrame([{"player_id": p.player_id, "projected_points": 5.0} for p in state.squad])
    outcomes = OutcomeBatch("2024-25", 1, "test", tuple((p.player_id, Outcome(5, 90, True)) for p in state.squad))

    with pytest.raises(UncertifiedSolveError, match="failed time-capped policy"):
        execute_replay_deadline(
            state,
            forecast_df,
            outcomes,
            solve_fn=timed_out_solver,
            policy=QualityPolicy(mode="time_capped", time_limit_seconds=30.0),
        )


@pytest.mark.parametrize("changed", ["model", "version", "protocol", "policy", "forecast", "outcome", "schedule"])
def test_resume_rejects_changed_evaluation_inputs(tmp_path: Path, changed: str) -> None:
    anchor = solve_ownership_anchor(_make_test_universe(), season="2024-25")
    forecasts = pd.DataFrame([{"player_id": pid, "projected_points": 5.0} for pid in range(1, 25)])
    point = 5

    def forecast_provider(gw: int, state: ReplayState) -> pd.DataFrame:
        return forecasts

    def outcome_provider(gw: int) -> OutcomeBatch:
        return OutcomeBatch("2024-25", gw, "synthetic-source", tuple((pid, Outcome(point, 90, True)) for pid in range(1, 25)))

    kwargs: dict[str, Any] = {"model_name": "candidate", "season": "2024-25", "anchor": anchor,
                              "forecast_provider": forecast_provider, "outcome_provider": outcome_provider,
                              "end_gw": 2, "checkpoint_dir": tmp_path}
    _run_lineup_fixture_replay(**kwargs)
    if changed == "model":
        kwargs["model_name"] = "different-candidate"
    elif changed == "version":
        kwargs["model_version_hash"] = "different-source"
    elif changed == "protocol":
        kwargs["protocol_hash"] = "different-protocol"
    elif changed == "policy":
        kwargs["policy"] = QualityPolicy(target_gap=0.01)
    elif changed == "schedule":
        kwargs["end_gw"] = 3
    elif changed == "forecast":
        forecasts.loc[0, "projected_points"] = 50.0
    else:
        point = 6
    with pytest.raises(ValueError, match="identity mismatch"):
        _run_lineup_fixture_replay(**kwargs)


def test_record_and_trajectory_audit_recompute_native_transition() -> None:
    anchor = solve_ownership_anchor(_make_test_universe(), season="2024-25")
    forecasts = pd.DataFrame([{"player_id": pid, "projected_points": 5.0} for pid in range(1, 25)])
    outcomes = OutcomeBatch("2024-25", 1, "synthetic", tuple((pid, Outcome(5, 90, True)) for pid in range(1, 25)))
    trajectory = _run_lineup_fixture_replay("fixture", "2024-25", anchor, lambda gw, state: forecasts, lambda gw: outcomes, end_gw=1)
    record = trajectory.records[0]
    corrupted = replace(record, gross_points=record.gross_points + 10, net_points=record.net_points + 10)
    with pytest.raises(ValueError, match="content"):
        replace(trajectory, records=(corrupted,), cumulative_net=trajectory.cumulative_net + 10).audit_reconstructed_net_score()
    data = record.to_dict()
    data["transition_result"]["state"]["bank"] += 10
    with pytest.raises(ValueError, match="content"):
        record_from_dict(data)


@pytest.mark.parametrize("bad", [{"relative_gap": float("nan")}, {"objective": float("inf")},
                                 {"quality_mode": "time_capped"}, {"termination_status": "TIME_LIMIT"}])
def test_bad_certificate_cannot_supply_successful_evidence(bad: dict[str, Any]) -> None:
    anchor = solve_ownership_anchor(_make_test_universe(), season="2024-25")
    state = anchor.to_replay_state("2024-25")
    forecasts = pd.DataFrame([{"player_id": p.player_id, "projected_points": 5.0} for p in state.squad])
    outcomes = OutcomeBatch("2024-25", 1, "synthetic", tuple((p.player_id, Outcome(5, 90, True)) for p in state.squad))

    def bad_solver(s: ReplayState, horizon: int, forecasts: pd.DataFrame, options: dict[str, Any]) -> tuple[Decision, SolverCertificate]:
        decision, cert = heuristic_zero_transfer_solve(s, horizon, forecasts, options)
        return decision, replace(cert, **bad)

    with pytest.raises(UncertifiedSolveError):
        execute_replay_deadline(state, forecasts, outcomes, solve_fn=bad_solver)


def test_scoring_window_does_not_clip_planning_horizon() -> None:
    anchor = solve_ownership_anchor(_make_test_universe(), season="2024-25")
    horizons: list[int] = []

    def solve(state: ReplayState, horizon: int, forecasts: pd.DataFrame, options: dict[str, Any]) -> tuple[Decision, SolverCertificate]:
        horizons.append(horizon)
        return heuristic_zero_transfer_solve(state, horizon, forecasts, options)

    _run_lineup_fixture_replay("fixture", "2024-25", anchor,
                              lambda gw, state: pd.DataFrame([{"player_id": pid, "projected_points": 5.0} for pid in range(1, 25)]),
                              lambda gw: OutcomeBatch("2024-25", gw, "synthetic", tuple((pid, Outcome(5, 90, True)) for pid in range(1, 25))),
                              end_gw=2, solve_fn=solve)
    assert horizons == [6, 6]
