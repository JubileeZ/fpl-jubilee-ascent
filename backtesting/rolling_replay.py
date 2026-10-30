"""Independent rolling multi-deadline transfer plan replay engine.

Implements the continuous sustained-management evaluation benchmark:
1. Starts from a neutral GW1 ownership anchor with conserved £100m capital and locked GW1 squad.
2. Rolls deadline-by-deadline (GW1..38 or GW1..19), solving independent 6-GW Strategic transfer
   plans for Candidate and Champion models.
3. Executes immediate decisions only, discarding tentative future actions upon replanning.
4. Tracks independent player ownership, purchase prices, selling prices (native half-profit rounding),
   bank balance, free transfers, chip history, and official hit deductions.
5. Employs structured solver certificates and independent pre-transition legality validation.
6. Persists verifiable per-deadline checkpoints allowing offline net-score reconstruction without a solver.
"""

from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

from backtesting.ownership_anchor import OwnershipAnchor
from backtesting.replay_state import (
    Decision,
    Lineup,
    Outcome,
    OutcomeBatch,
    Player,
    ReplayState,
    Transition,
    state_hash,
    transfer_squad,
    transition,
    validate_squad,
)
from backtesting.season_rules import (
    Chip,
    chip_window,
    get_rules,
)
from models.scoring_matrix import Position
from solver.scenarios import effective_horizon_scale

DEFAULT_HORIZON: int = 6


class ReplayLegalityError(ValueError):
    """Raised when a proposed transfer decision violates squad, financial, or lineup rules."""


class UncertifiedSolveError(RuntimeError):
    """Raised when a solve fails to meet required optimality or feasibility tolerances."""


class IncompleteReplayOutcomeError(ValueError):
    """Raised when required outcome coverage is incomplete for scored players."""


@dataclass(frozen=True)
class SolverCertificate:
    """Mathematical certificate of solution quality and solver execution."""

    feasible: bool
    objective: float
    objective_bound: float
    absolute_gap: float
    relative_gap: float
    termination_status: str
    runtime_seconds: float
    threads: int
    seed: int | None
    solver_version: str
    quality_mode: Literal["certified", "time_capped"]
    strategic_audit: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SolverCertificate":
        return cls(
            feasible=bool(data["feasible"]),
            objective=float(data["objective"]),
            objective_bound=float(data["objective_bound"]),
            absolute_gap=float(data["absolute_gap"]),
            relative_gap=float(data["relative_gap"]),
            termination_status=str(data["termination_status"]),
            runtime_seconds=float(data["runtime_seconds"]),
            threads=int(data["threads"]),
            seed=int(data["seed"]) if data.get("seed") is not None else None,
            solver_version=str(data["solver_version"]),
            quality_mode=cast(Literal["certified", "time_capped"], str(data["quality_mode"])),
            strategic_audit=dict(data.get("strategic_audit", {})),
        )


@dataclass(frozen=True)
class QualityPolicy:
    """Requested solution quality and timeout policy."""

    mode: Literal["certified", "time_capped"] = "certified"
    target_gap: float = 0.0
    time_limit_seconds: float = 60.0
    require_proven_optimal: bool = True
    raise_on_failure: bool = True


@dataclass(frozen=True)
class ReplayDeadlineRecord:
    """Full execution, decision, outcome, and transition record for one deadline."""

    deadline: int
    model_name: str
    pre_state_hash: str
    post_state_hash: str
    decision: Decision
    certificate: SolverCertificate
    outcomes: OutcomeBatch
    transition_result: Transition
    gross_points: int
    captain_increment: int
    hit_penalty: int
    net_points: int
    checkpoint_id: str
    parent_checkpoint_id: str | None
    execution_status: Literal["SUCCESS", "UNCERTIFIED_GAP", "TIMEOUT", "INFEASIBLE", "LEGALITY_VIOLATION"] = "SUCCESS"
    pre_state: ReplayState | None = None
    evaluation_identity: str = ""
    model_version_hash: str = ""
    protocol_hash: str = ""
    forecast_hash: str = ""
    outcome_hash: str = ""

    @property
    def total_gross_points(self) -> int:
        """Total gross FPL points inclusive of captain increment before hits."""
        return int(self.gross_points + self.captain_increment)

    def to_dict(self) -> dict[str, Any]:
        """Serialize deadline record to JSON-compatible dictionary."""
        return record_to_dict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ReplayDeadlineRecord":
        """Deserialize deadline record from JSON-compatible dictionary."""
        return record_from_dict(d)


def record_to_dict(rec: ReplayDeadlineRecord) -> dict[str, Any]:
    """Serialize a complete deadline record into a JSON-compatible dictionary."""
    return {
        "pre_state": asdict(rec.pre_state) if rec.pre_state is not None else None,
        "evaluation_identity": rec.evaluation_identity,
        "model_version_hash": rec.model_version_hash,
        "protocol_hash": rec.protocol_hash,
        "forecast_hash": rec.forecast_hash,
        "outcome_hash": rec.outcome_hash,
        "checkpoint_id": rec.checkpoint_id,
        "parent_checkpoint_id": rec.parent_checkpoint_id,
        "deadline": rec.deadline,
        "model_name": rec.model_name,
        "execution_status": rec.execution_status,
        "pre_state_hash": rec.pre_state_hash,
        "post_state_hash": rec.post_state_hash,
        "decision": {
            "transfers": [
                [sold_id, asdict(bought_p)] for sold_id, bought_p in rec.decision.transfers
            ],
            "lineup": asdict(rec.decision.lineup),
            "expected_state_hash": rec.decision.expected_state_hash,
            "issued_deadline": rec.decision.issued_deadline,
            "chip": rec.decision.chip,
        },
        "certificate": rec.certificate.to_dict(),
        "outcomes": {
            "rules_version": rec.outcomes.rules_version,
            "deadline": rec.outcomes.deadline,
            "source_identity": rec.outcomes.source_identity,
            "outcomes": [[pid, asdict(out)] for pid, out in rec.outcomes.outcomes],
        },
        "transition_result": {
            "state": asdict(rec.transition_result.state),
            "gross": rec.transition_result.gross,
            "captain_increment": rec.transition_result.captain_increment,
            "hit": rec.transition_result.hit,
            "net": rec.transition_result.net,
        },
        "gross_points": rec.gross_points,
        "captain_increment": rec.captain_increment,
        "hit_penalty": rec.hit_penalty,
        "net_points": rec.net_points,
    }


def record_from_dict(d: dict[str, Any]) -> ReplayDeadlineRecord:
    """Deserialize a deadline record from a JSON-compatible dictionary."""
    dec_data = d["decision"]
    transfers = tuple(
        (int(item[0]), Player(
            player_id=int(item[1]["player_id"]),
            position=cast(Position, item[1]["position"]),
            club=int(item[1]["club"]),
            purchase=int(item[1]["purchase"]),
            market=int(item[1]["market"]),
            purchase_eligible=bool(item[1].get("purchase_eligible", True)),
        ))
        for item in dec_data["transfers"]
    )
    lineup = Lineup(
        starters=tuple(int(x) for x in dec_data["lineup"]["starters"]),
        bench=tuple(int(x) for x in dec_data["lineup"]["bench"]),
        captain=int(dec_data["lineup"]["captain"]),
        vice=int(dec_data["lineup"]["vice"]),
    )
    decision = Decision(
        transfers=transfers,
        lineup=lineup,
        expected_state_hash=str(dec_data["expected_state_hash"]),
        issued_deadline=int(dec_data["issued_deadline"]),
        chip=dec_data.get("chip"),
    )
    cert = SolverCertificate.from_dict(d["certificate"])

    out_data = d["outcomes"]
    outcomes_list = tuple(
        (
            int(item[0]),
            Outcome(
                points=int(item[1]["points"]),
                minutes=int(item[1]["minutes"]),
                appeared=item[1].get("appeared"),
            ),
        )
        for item in out_data["outcomes"]
    )
    outcomes = OutcomeBatch(
        rules_version=str(out_data["rules_version"]),
        deadline=int(out_data["deadline"]),
        source_identity=str(out_data["source_identity"]),
        outcomes=outcomes_list,
    )

    tr_data = d["transition_result"]
    st_data = tr_data["state"]
    squad = tuple(
        Player(
            player_id=int(p["player_id"]),
            position=cast(Position, p["position"]),
            club=int(p["club"]),
            purchase=int(p["purchase"]),
            market=int(p["market"]),
            purchase_eligible=bool(p.get("purchase_eligible", True)),
        )
        for p in st_data["squad"]
    )
    chip_history = cast(
        tuple[tuple[int, Chip, int], ...],
        tuple((int(item[0]), cast(Chip, str(item[1])), int(item[2])) for item in st_data.get("chip_history", ())),
    )
    state = ReplayState(
        rules_version=str(st_data["rules_version"]),
        squad=squad,
        bank=int(st_data["bank"]),
        rules_id=str(st_data["rules_id"]),
        deadline=int(st_data["deadline"]),
        free_transfers=int(st_data["free_transfers"]),
        chip_history=chip_history,
        previous_transfers=int(st_data["previous_transfers"]),
        previous_hits=int(st_data["previous_hits"]),
        parent_hash=st_data.get("parent_hash"),
    )
    t_result = Transition(
        state=state,
        gross=int(tr_data["gross"]),
        captain_increment=int(tr_data["captain_increment"]),
        hit=int(tr_data["hit"]),
        net=int(tr_data["net"]),
    )

    rec = ReplayDeadlineRecord(
        deadline=int(d["deadline"]),
        model_name=str(d["model_name"]),
        pre_state_hash=str(d["pre_state_hash"]),
        post_state_hash=str(d["post_state_hash"]),
        decision=decision,
        certificate=cert,
        outcomes=outcomes,
        transition_result=t_result,
        gross_points=int(d["gross_points"]),
        captain_increment=int(d["captain_increment"]),
        hit_penalty=int(d["hit_penalty"]),
        net_points=int(d["net_points"]),
        checkpoint_id=str(d["checkpoint_id"]),
        parent_checkpoint_id=d.get("parent_checkpoint_id"),
        execution_status=cast(
            Literal["SUCCESS", "UNCERTIFIED_GAP", "TIMEOUT", "INFEASIBLE", "LEGALITY_VIOLATION"],
            d.get("execution_status", "SUCCESS"),
        ),
        pre_state=replay_state_from_dict(d["pre_state"]) if d.get("pre_state") is not None else None,
        evaluation_identity=str(d.get("evaluation_identity", "")),
        model_version_hash=str(d.get("model_version_hash", "")),
        protocol_hash=str(d.get("protocol_hash", "")),
        forecast_hash=str(d.get("forecast_hash", "")),
        outcome_hash=str(d.get("outcome_hash", "")),
    )
    if rec.pre_state is not None:
        verify_replay_record(rec, rec.pre_state, parent_checkpoint_id=rec.parent_checkpoint_id)
    return rec


def replay_state_from_dict(data: dict[str, Any]) -> ReplayState:
    return ReplayState(
        rules_version=data["rules_version"], squad=tuple(Player(**p) for p in data["squad"]), bank=data["bank"],
        rules_id=data["rules_id"], deadline=data["deadline"], free_transfers=data["free_transfers"],
        chip_history=tuple(tuple(item) for item in data["chip_history"]), previous_transfers=data["previous_transfers"],
        previous_hits=data["previous_hits"], parent_hash=data["parent_hash"],
    )


def _content_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def forecast_content_hash(forecasts: pd.DataFrame) -> str:
    """Hash every issued value and provenance attribute, independent of row/column ordering."""
    if not forecasts.columns.is_unique or "player_id" not in forecasts or forecasts["player_id"].duplicated().any():
        raise ValueError("Forecast hash requires unique columns and player IDs")
    normalized = forecasts.sort_values("player_id").reindex(sorted(forecasts.columns), axis=1)
    return _content_hash({"columns": list(normalized.columns), "rows": normalized.to_dict(orient="records"), "attrs": forecasts.attrs})


def refresh_replay_market(state: ReplayState, forecasts: pd.DataFrame) -> ReplayState:
    """Refresh held issue metadata while preserving acquisition basis and action history."""
    required = {"player_id", "position_id", "club_id", "now_cost", "purchase_eligible"}
    if not required <= set(forecasts.columns) or forecasts["player_id"].duplicated().any():
        raise ValueError("Native replay requires complete unique issue metadata")
    rows = {row["player_id"]: row for row in forecasts.to_dict(orient="records")}
    positions: dict[int, Position] = {1: "GK", 2: "D", 3: "M", 4: "F"}
    refreshed: list[Player] = []
    for player in state.squad:
        if player.player_id not in rows:
            raise ValueError("Owned player absent from issue metadata")
        row = rows[player.player_id]
        if (any(type(row[key]) is not int or row[key] <= 0 for key in ("position_id", "club_id", "now_cost"))
                or row["position_id"] not in positions or type(row["purchase_eligible"]) is not bool):
            raise ValueError("Invalid owned issue metadata")
        refreshed.append(replace(player, position=positions[row["position_id"]], club=row["club_id"],
                                 market=row["now_cost"], purchase_eligible=row["purchase_eligible"]))
    validate_squad(tuple(refreshed))
    return replace(state, squad=tuple(refreshed))


def replay_evaluation_identity(*, model_name: str, model_version_hash: str, protocol_hash: str, season: str,
                               anchor_id: str, horizon: int, last_gw: int, policy: QualityPolicy,
                               chip_calendar: tuple[tuple[int, Chip], ...], solver_identity: str, scored_end_gw: int = 38) -> str:
    return _content_hash({"version": 2, "model_name": model_name, "model_version_hash": model_version_hash,
                          "protocol_hash": protocol_hash, "season": season, "anchor_id": anchor_id,
                          "horizon": horizon, "last_gw": last_gw, "scored_end_gw": scored_end_gw, "policy": asdict(policy),
                          "chip_calendar": chip_calendar, "solver_identity": solver_identity,
                          "strategic_options": get_strategic_replay_options(horizon, rules_version=season)})


def replay_solver_identity(solve_fn: Callable[..., Any]) -> str:
    import highspy
    from importlib.metadata import version
    from importlib.util import find_spec

    core = find_spec("highspy._core")
    if core is None or core.origin is None or not Path(core.origin).is_file():
        raise ValueError("Installed HiGHS binary identity unavailable")
    runtime = {"distribution_version": version("highspy"), "solver_version": highspy.Highs().version(),
               "binary_sha256": hashlib.sha256(Path(core.origin).read_bytes()).hexdigest()}
    return _content_hash({"module": solve_fn.__module__, "name": solve_fn.__qualname__,
                          "source": Path(inspect.getfile(solve_fn)).read_bytes().hex(), "runtime": runtime})


def validate_solver_certificate_consistency(cert: SolverCertificate) -> None:
    """Check reported HiGHS bounds/gaps; zero objective requires a closed absolute gap."""
    values = (cert.objective, cert.objective_bound, cert.absolute_gap, cert.relative_gap, cert.runtime_seconds)
    if (any(isinstance(value, bool) or not math.isfinite(value) for value in values)
            or min(cert.absolute_gap, cert.relative_gap, cert.runtime_seconds) < 0 or cert.threads != 1
            or cert.objective_bound + 1e-6 < cert.objective
            or not math.isclose(cert.absolute_gap, abs(cert.objective_bound - cert.objective), rel_tol=1e-6, abs_tol=1e-6)):
        raise UncertifiedSolveError("Malformed or nonfinite solver certificate")
    if abs(cert.objective) <= 1e-12:
        if cert.absolute_gap > 1e-6:
            raise UncertifiedSolveError("Zero-objective solver certificate has an unresolved absolute gap")
        expected_relative_gap = 0.0
    else:
        expected_relative_gap = cert.absolute_gap / abs(cert.objective)
    if not math.isclose(cert.relative_gap, expected_relative_gap, rel_tol=1e-5, abs_tol=1e-8):
        raise UncertifiedSolveError("Solver certificate relative gap contradicts objective bounds")


def _checkpoint_hash(rec: ReplayDeadlineRecord) -> str:
    data = record_to_dict(rec)
    data.pop("checkpoint_id")
    return _content_hash(data)


def verify_replay_record(rec: ReplayDeadlineRecord, pre_state: ReplayState, *, model_name: str | None = None,
                         parent_checkpoint_id: str | None = None) -> ReplayState:
    """Reconstruct native state and score from the stored action/outcomes, without optimizing."""
    if rec.pre_state != pre_state or rec.pre_state_hash != state_hash(pre_state) or rec.deadline != pre_state.deadline:
        raise ValueError("Corrupted resume checkpoint state mismatch")
    if model_name is not None and rec.model_name != model_name:
        raise ValueError("Checkpoint model mismatch")
    if rec.parent_checkpoint_id != parent_checkpoint_id or rec.checkpoint_id != _checkpoint_hash(rec):
        raise ValueError("Checkpoint content or lineage mismatch")
    if rec.outcome_hash != _content_hash(asdict(rec.outcomes)):
        raise ValueError("Checkpoint outcome hash mismatch")
    validate_decision_legality(pre_state, rec.decision)
    expected = transition(pre_state, rec.decision, rec.outcomes)
    if (expected != rec.transition_result or rec.post_state_hash != state_hash(expected.state)
            or (rec.gross_points, rec.captain_increment, rec.hit_penalty, rec.net_points) != (expected.gross, expected.captain_increment, expected.hit, expected.net)):
        raise ValueError("Checkpoint native transition or score mismatch")
    return expected.state


@dataclass(frozen=True)
class ReplayTrajectory:
    """Complete rolling season replay history for one evaluated model policy."""

    model_name: str
    season: str
    anchor_id: str
    deadlines: tuple[int, ...]
    records: tuple[ReplayDeadlineRecord, ...]
    cumulative_gross: int
    cumulative_hits: int
    cumulative_net: int
    final_squad_ids: tuple[int, ...]
    final_bank: int

    def audit_reconstructed_net_score(self) -> int:
        """Independently recompute total net points from stored decisions and outcomes without solver."""
        running_net = 0
        previous: ReplayState | None = None
        parent_id: str | None = None
        for rec in self.records:
            if rec.pre_state is None:
                raise ValueError("Replay audit requires stored native pre-state")
            if previous is not None:
                if ({p.player_id: p.purchase for p in previous.squad} != {p.player_id: p.purchase for p in rec.pre_state.squad}
                        or replace(previous, squad=rec.pre_state.squad) != rec.pre_state):
                    raise ValueError("Replay audit ownership or financial lineage mismatch")
            previous = verify_replay_record(rec, rec.pre_state, model_name=self.model_name, parent_checkpoint_id=parent_id)
            parent_id = rec.checkpoint_id
            if rec.execution_status != "SUCCESS":
                continue
            expected_net = rec.gross_points + rec.captain_increment - rec.hit_penalty
            if rec.net_points != expected_net:
                raise ValueError(
                    f"Deadline {rec.deadline} net mismatch: {rec.net_points} != {expected_net}"
                )
            running_net += expected_net
        if running_net != self.cumulative_net:
            raise ValueError(
                f"Trajectory cumulative net mismatch: {self.cumulative_net} != {running_net}"
            )
        return running_net


def get_strategic_replay_options(
    horizon: int = DEFAULT_HORIZON,
    decay_base: float = 0.85,
    rules_version: str = "2024-25",
) -> dict[str, Any]:
    """Compute frozen 6-GW Strategic scenario settings for replay solves under native season rules."""
    rules = get_rules(rules_version)
    scale = effective_horizon_scale(horizon, decay_base=decay_base)

    ft_values: dict[str, float] = {}
    if rules.free_transfer_cap >= 2:
        ft_values["2"] = round(2.0 * scale, 4)
    if rules.free_transfer_cap >= 3:
        ft_values["3"] = round(1.2 * scale, 4)
    if rules.free_transfer_cap >= 4:
        ft_values["4"] = round(0.6 * scale, 4)
    if rules.free_transfer_cap >= 5:
        ft_values["5"] = round(0.2 * scale, 4)

    return {
        "arm": "strategic",
        "horizon": horizon,
        "decay_base": decay_base,
        "rules_version": rules.version,
        "horizon_scale": round(scale, 4),
        "hit_hurdle": round(4.0 + 1.8 * scale, 4),
        "paid_hit_penalty": round(1.8 * scale, 4),
        "gk_transfer_friction": round(1.5 * scale, 4),
        "ft_use_penalty": 0.2,
        "starter_xmins_floor": 65.0,
        "starter_xmins_penalty": 10.0,
        "bench_cover_min": 12,
        "bench_cover_xmins": 65.0,
        "bench_cover_penalty": 1.5,
        "def_stack_cap": 2,
        "def_stack_penalty": 1.2,
        "weekly_hit_limit": 1,
        "ft_value_list": ft_values,
    }


def clipped_replay_horizon(
    deadline_gw: int,
    *,
    last_gw: int = 38,
    horizon: int = DEFAULT_HORIZON,
) -> int:
    """Compute planning horizon clipped at the season boundary without dropping scored deadlines."""
    remaining = int(last_gw) - int(deadline_gw) + 1
    return max(1, min(int(horizon), remaining))


def validate_decision_legality(
    state: ReplayState,
    decision: Decision,
) -> None:
    """Independently validate decision legality, finances, formation, and chip rules before transition."""
    rules = get_rules(state.rules_version)
    if decision.expected_state_hash != state_hash(state):
        raise ReplayLegalityError(
            f"Decision pre-state hash mismatch: {decision.expected_state_hash} != {state_hash(state)}"
        )
    if decision.issued_deadline != state.deadline:
        raise ReplayLegalityError(
            f"Decision issued deadline {decision.issued_deadline} != state deadline {state.deadline}"
        )

    # GW1 transfer lock
    if state.deadline == 1:
        if decision.transfers:
            raise ReplayLegalityError("GW1 transfers are locked; initial squad cannot be modified")
        if decision.chip not in (None, "bench_boost", "triple_captain"):
            raise ReplayLegalityError(f"Chip {decision.chip} unsupported at GW1")

    # Chip window validation
    if decision.chip is not None:
        window = chip_window(rules, decision.chip, state.deadline)
        if any(c == decision.chip and w == window for _, c, w in state.chip_history):
            raise ReplayLegalityError(f"Chip {decision.chip} already consumed in window {window}")
        if decision.chip == "free_hit" and any(
            gw == state.deadline - 1 and c == "free_hit" for gw, c, _ in state.chip_history
        ):
            raise ReplayLegalityError("Consecutive Free Hits unsupported")

    # Squad and financial transition validation
    try:
        updated_squad, updated_bank = transfer_squad(state.squad, state.bank, decision.transfers)
    except ValueError as e:
        raise ReplayLegalityError(f"Financial or transfer legality failure: {e}") from e

    # Lineup partition and formation validation (11 starters, 4 bench for all decisions)
    owned_ids = {p.player_id for p in updated_squad}
    all_lineup_ids = decision.lineup.starters + decision.lineup.bench
    if set(all_lineup_ids) != owned_ids or len(all_lineup_ids) != 15:
        raise ReplayLegalityError("Lineup does not partition updated 15-player squad")

    player_map = {p.player_id: p for p in updated_squad}
    starters_pos = Counter(player_map[pid].position for pid in decision.lineup.starters)
    if len(decision.lineup.starters) != 11:
        raise ReplayLegalityError(f"Starting XI has {len(decision.lineup.starters)} players, requires 11")
    if (
        starters_pos["GK"] != 1
        or not (3 <= starters_pos["D"] <= 5)
        or not (2 <= starters_pos["M"] <= 5)
        or not (1 <= starters_pos["F"] <= 3)
    ):
        raise ReplayLegalityError(f"Invalid starting formation positions: {starters_pos}")

    if player_map[decision.lineup.bench[0]].position != "GK":
        raise ReplayLegalityError("Bench slot 0 must be backup goalkeeper")

    if (
        decision.lineup.captain == decision.lineup.vice
        or decision.lineup.captain not in decision.lineup.starters
        or decision.lineup.vice not in decision.lineup.starters
    ):
        raise ReplayLegalityError("Captain and vice must be distinct starting players")


def solve_lineup_milp(
    squad: tuple[Player, ...],
    target_xp: dict[int, float],
) -> Lineup:
    """Select the optimal legal starting XI and bench order maximizing projected points."""
    validate_squad(squad)
    pids = [p.player_id for p in squad]
    xp_vals = [target_xp.get(pid, 0.0) for pid in pids]

    gk_indices = [i for i, p in enumerate(squad) if p.position == "GK"]
    def_indices = [i for i, p in enumerate(squad) if p.position == "D"]
    mid_indices = [i for i, p in enumerate(squad) if p.position == "M"]
    fwd_indices = [i for i, p in enumerate(squad) if p.position == "F"]

    # Pick best GK
    starter_gk = max(gk_indices, key=lambda i: (xp_vals[i], -pids[i]))
    bench_gk = min(gk_indices, key=lambda i: (xp_vals[i], -pids[i]))

    # Solve outfield lineup MILP (10 outfield starters, 3-5 DEF, 2-5 MID, 1-3 FWD)
    outfield_indices = def_indices + mid_indices + fwd_indices
    num_outfield = len(outfield_indices)

    c = np.array([-xp_vals[i] for i in outfield_indices], dtype=float)
    positions = [p.position for p in squad]
    A_rows = [
        np.ones(num_outfield, dtype=float),
        np.array([1.0 if positions[i] == "D" else 0.0 for i in outfield_indices], dtype=float),
        np.array([1.0 if positions[i] == "M" else 0.0 for i in outfield_indices], dtype=float),
        np.array([1.0 if positions[i] == "F" else 0.0 for i in outfield_indices], dtype=float),
    ]
    lb = [10.0, 3.0, 2.0, 1.0]
    ub = [10.0, 5.0, 5.0, 3.0]

    constraints = LinearConstraint(np.array(A_rows), cast(float, lb), cast(float, ub))
    integrality = np.ones(num_outfield, dtype=int)
    bounds = Bounds(cast(float, np.zeros(num_outfield)), cast(float, np.ones(num_outfield)))

    res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)
    if not res.success or res.status != 0:
        raise UncertifiedSolveError(f"Lineup optimization failed: {res.message}")

    starter_outfield = [outfield_indices[i] for i in np.where(res.x > 0.5)[0]]
    bench_outfield = [i for i in outfield_indices if i not in starter_outfield]
    bench_outfield.sort(key=lambda i: (-xp_vals[i], pids[i]))

    starters = tuple(pids[i] for i in [starter_gk] + starter_outfield)
    bench = tuple(pids[i] for i in [bench_gk] + bench_outfield)

    sorted_starters = sorted(starters, key=lambda pid: (-target_xp.get(pid, 0.0), pid))
    captain = sorted_starters[0]
    vice = sorted_starters[1]

    return Lineup(starters=starters, bench=bench, captain=captain, vice=vice)


def heuristic_zero_transfer_solve(
    state: ReplayState,
    horizon: int,
    forecast_df: pd.DataFrame,
    options: dict[str, Any],
) -> tuple[Decision, SolverCertificate]:
    """Explicit zero-transfer lineup solver for baseline replay and tests."""
    target_col = f"xp_{state.deadline}" if f"xp_{state.deadline}" in forecast_df.columns else "projected_points"
    target_xp = (
        {int(r["player_id"]): float(r[target_col]) for r in forecast_df.to_dict(orient="records")}
        if "player_id" in forecast_df.columns and target_col in forecast_df.columns
        else {}
    )

    lineup = solve_lineup_milp(state.squad, target_xp)
    decision = Decision(
        transfers=(),
        lineup=lineup,
        expected_state_hash=state_hash(state),
        issued_deadline=state.deadline,
        chip=None,
    )
    cert = SolverCertificate(
        feasible=True,
        objective=0.0,
        objective_bound=0.0,
        absolute_gap=0.0,
        relative_gap=0.0,
        termination_status="OPTIMAL",
        runtime_seconds=0.001,
        threads=1,
        seed=42,
        solver_version="internal_lineup_v1",
        quality_mode="certified",
        strategic_audit=options,
    )
    return decision, cert


def execute_replay_deadline(
    state: ReplayState,
    forecast_df: pd.DataFrame,
    outcomes: OutcomeBatch,
    *,
    solve_fn: Callable[
        [ReplayState, int, pd.DataFrame, dict[str, Any]],
        tuple[Decision, SolverCertificate],
    ] | None = None,
    horizon: int = DEFAULT_HORIZON,
    last_gw: int = 38,
    policy: QualityPolicy = QualityPolicy(),
    chip_calendar: tuple[tuple[int, Chip], ...] = (),
) -> ReplayDeadlineRecord:
    """Execute one full rolling replay deadline: solve -> legality check -> transition -> audit."""
    # Strict outcome coverage validation
    squad_pids = {p.player_id for p in state.squad}
    outcome_pids = {pid for pid, _ in outcomes.outcomes}
    missing_pids = squad_pids - outcome_pids
    if missing_pids:
        raise IncompleteReplayOutcomeError(
            f"Missing required outcome coverage for squad player(s): {sorted(missing_pids)}"
        )

    eff_horizon = clipped_replay_horizon(state.deadline, last_gw=last_gw, horizon=horizon)
    options = get_strategic_replay_options(eff_horizon, rules_version=state.rules_version)
    options.update(chip_calendar=chip_calendar, target_gap=policy.target_gap, time_limit_seconds=policy.time_limit_seconds)

    if solve_fn is None:
        from backtesting.native_transfer_solver import native_strategic_solve

        solve_fn = native_strategic_solve
    decision, cert = solve_fn(state, eff_horizon, forecast_df, options)

    exec_status: Literal["SUCCESS", "UNCERTIFIED_GAP", "TIMEOUT", "INFEASIBLE", "LEGALITY_VIOLATION"] = "SUCCESS"

    validate_solver_certificate_consistency(cert)
    if cert.termination_status == "OPTIMAL" and (not cert.feasible or cert.relative_gap > policy.target_gap + 1e-8):
        raise UncertifiedSolveError("False OPTIMAL solver certificate")

    # Validate certificate against policy
    if policy.mode == "certified":
        if not cert.feasible or (policy.require_proven_optimal and (cert.relative_gap > policy.target_gap + 1e-8
                or cert.termination_status != "OPTIMAL" or cert.quality_mode != "certified")):
            if policy.raise_on_failure:
                raise UncertifiedSolveError(
                    f"Solve at deadline {state.deadline} failed certified quality policy (status={cert.termination_status}, gap={cert.relative_gap})"
                )
            exec_status = "UNCERTIFIED_GAP" if cert.feasible else "INFEASIBLE"
    elif policy.mode == "time_capped":
        if cert.termination_status in ("TIMEOUT", "INFEASIBLE") or not cert.feasible:
            if policy.raise_on_failure:
                raise UncertifiedSolveError(
                    f"Solve at deadline {state.deadline} failed time-capped policy (status={cert.termination_status}, runtime={cert.runtime_seconds}s)"
                )
            exec_status = "TIMEOUT" if cert.termination_status == "TIMEOUT" else "INFEASIBLE"

    # Validate decision legality independently
    validate_decision_legality(state, decision)

    # Execute transition
    pre_hash = state_hash(state)
    t_result = transition(state, decision, outcomes)
    post_hash = state_hash(t_result.state)

    checkpoint_material = {
        "deadline": state.deadline,
        "decision": asdict(decision),
        "post_hash": post_hash,
        "pre_hash": pre_hash,
    }
    checkpoint_id = hashlib.sha256(
        json.dumps(checkpoint_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    rec = ReplayDeadlineRecord(
        deadline=state.deadline,
        model_name="unnamed_model",
        pre_state_hash=pre_hash,
        post_state_hash=post_hash,
        decision=decision,
        certificate=cert,
        outcomes=outcomes,
        transition_result=t_result,
        gross_points=t_result.gross,
        captain_increment=t_result.captain_increment,
        hit_penalty=t_result.hit,
        net_points=t_result.net,
        checkpoint_id=checkpoint_id,
        parent_checkpoint_id=state.parent_hash,
        execution_status=exec_status,
        pre_state=state,
        forecast_hash=forecast_content_hash(forecast_df),
        outcome_hash=_content_hash(asdict(outcomes)),
    )
    return replace(rec, checkpoint_id=_checkpoint_hash(rec))


def run_rolling_replay(
    model_name: str,
    season: str,
    anchor: OwnershipAnchor,
    forecast_provider: Callable[[int, ReplayState], pd.DataFrame],
    outcome_provider: Callable[[int], OutcomeBatch],
    *,
    start_gw: int = 1,
    end_gw: int = 38,
    horizon: int = DEFAULT_HORIZON,
    solve_fn: Callable[
        [ReplayState, int, pd.DataFrame, dict[str, Any]],
        tuple[Decision, SolverCertificate],
    ] | None = None,
    policy: QualityPolicy = QualityPolicy(),
    checkpoint_dir: Path | None = None,
    model_version_hash: str = "",
    protocol_hash: str = "",
    chip_calendar: tuple[tuple[int, Chip], ...] = (),
) -> ReplayTrajectory:
    """Execute complete independent multi-period rolling replay over the specified gameweeks."""
    rules = get_rules(season)
    current_state = anchor.to_replay_state(season, rules_id=rules.rules_id)
    if start_gw != 1 or not 1 <= end_gw <= 38:
        raise ValueError("Continuous replay must start at GW1 with a valid final deadline")
    if solve_fn is None:
        from backtesting.native_transfer_solver import native_strategic_solve

        solve_fn = native_strategic_solve
    solver_identity = replay_solver_identity(solve_fn)
    identity = replay_evaluation_identity(model_name=model_name, model_version_hash=model_version_hash, protocol_hash=protocol_hash,
                                          season=season, anchor_id=anchor.anchor_id, horizon=horizon, last_gw=38,
                                          policy=policy, chip_calendar=chip_calendar, solver_identity=solver_identity, scored_end_gw=end_gw)

    records: list[ReplayDeadlineRecord] = []
    parent_cp_id: str | None = None

    if checkpoint_dir is not None:
        if not model_version_hash.strip() or not protocol_hash.strip():
            raise ValueError("Persistent replay requires explicit model_version_hash and protocol_hash")
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = checkpoint_dir / "evaluation.json"
        manifest = {"evaluation_identity": identity, "initial_state_hash": state_hash(current_state)}
        if manifest_file.exists():
            if json.loads(manifest_file.read_text(encoding="utf-8")) != manifest:
                raise ValueError("Replay checkpoint evaluation identity mismatch")
        else:
            with manifest_file.open("x", encoding="utf-8") as stream:
                json.dump(manifest, stream, sort_keys=True)

    for gw in range(start_gw, end_gw + 1):
        if current_state.deadline != gw:
            raise ValueError(f"State deadline {current_state.deadline} != scheduled GW {gw}")

        forecast_df = forecast_provider(gw, current_state)
        if solve_fn.__module__ == "backtesting.native_transfer_solver":
            current_state = refresh_replay_market(current_state, forecast_df)
        outcomes = outcome_provider(gw)
        cp_file = checkpoint_dir / f"checkpoint_gw_{gw}_{state_hash(current_state)}.json" if checkpoint_dir else None
        if checkpoint_dir is not None and cp_file is not None and not cp_file.exists() and any(checkpoint_dir.glob(f"checkpoint_gw_{gw}_*.json")):
            raise ValueError("Replay checkpoint issue metadata changed")
        if cp_file and cp_file.is_file():
            data = json.loads(cp_file.read_text(encoding="utf-8"))
            if data["pre_state_hash"] != state_hash(current_state):
                raise ValueError("Corrupted resume checkpoint state mismatch")
            rec = record_from_dict(data)
            if (rec.evaluation_identity != identity or rec.model_version_hash != model_version_hash or rec.protocol_hash != protocol_hash
                    or rec.forecast_hash != forecast_content_hash(forecast_df) or rec.outcome_hash != _content_hash(asdict(outcomes))):
                raise ValueError("Replay checkpoint forecast, outcome or evaluation identity mismatch")
            verify_replay_record(rec, current_state, model_name=model_name, parent_checkpoint_id=parent_cp_id)
            records.append(rec)
            parent_cp_id = rec.checkpoint_id
            current_state = rec.transition_result.state
            if rec.execution_status != "SUCCESS":
                break
            continue

        rec = execute_replay_deadline(
            current_state,
            forecast_df,
            outcomes,
            solve_fn=solve_fn,
            horizon=horizon,
            last_gw=38,
            policy=policy,
            chip_calendar=chip_calendar,
        )
        rec = replace(rec, model_name=model_name, parent_checkpoint_id=parent_cp_id, evaluation_identity=identity,
                      model_version_hash=model_version_hash, protocol_hash=protocol_hash)
        rec = replace(rec, checkpoint_id=_checkpoint_hash(rec))

        if cp_file is not None:
            stage = cp_file.with_suffix(".tmp")
            with stage.open("w", encoding="utf-8") as stream:
                json.dump(record_to_dict(rec), stream, indent=2, sort_keys=True, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(stage, cp_file)

        records.append(rec)
        parent_cp_id = rec.checkpoint_id
        current_state = rec.transition_result.state
        if rec.execution_status != "SUCCESS":
            break

    cum_gross = sum(r.total_gross_points for r in records if r.execution_status == "SUCCESS")
    cum_hits = sum(r.hit_penalty for r in records if r.execution_status == "SUCCESS")
    cum_net = sum(r.net_points for r in records if r.execution_status == "SUCCESS")
    final_ids = tuple(sorted(p.player_id for p in current_state.squad))

    return ReplayTrajectory(
        model_name=model_name,
        season=season,
        anchor_id=anchor.anchor_id,
        deadlines=tuple(r.deadline for r in records),
        records=tuple(records),
        cumulative_gross=cum_gross,
        cumulative_hits=cum_hits,
        cumulative_net=cum_net,
        final_squad_ids=final_ids,
        final_bank=current_state.bank,
    )
