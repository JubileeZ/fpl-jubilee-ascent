"""One-Gameweek lineup decision and hindsight-regret evaluation."""

from dataclasses import dataclass
from itertools import combinations, permutations
from typing import Mapping


@dataclass(frozen=True)
class PlayerOutcome:
    player_id: int
    position_id: int
    points: float
    minutes: float


@dataclass(frozen=True)
class LineupDecision:
    starters: tuple[int, ...]
    bench: tuple[int, ...]
    captain: int
    vice_captain: int


@dataclass(frozen=True)
class ScoredLineup:
    points: float
    final_starters: tuple[int, ...]


def is_legal_formation(starters: tuple[int, ...], outcomes: Mapping[int, PlayerOutcome]) -> bool:
    """Validate the FPL 1-GK, 3-5-2-5-3 starting-XI formation bounds."""
    if len(starters) != 11:
        return False
    positions = [outcomes[player_id].position_id for player_id in starters]
    counts = {position: positions.count(position) for position in range(1, 5)}
    return (
        counts[1] == 1
        and 3 <= counts[2] <= 5
        and 2 <= counts[3] <= 5
        and 1 <= counts[4] <= 3
    )


def resolve_autosubs(
    decision: LineupDecision,
    outcomes: Mapping[int, PlayerOutcome],
) -> tuple[int, ...]:
    """Apply bench order while preserving a legal formation."""
    starters = list(decision.starters)
    used_bench: set[int] = set()
    for bench_player in decision.bench:
        if outcomes.get(
            bench_player,
            PlayerOutcome(bench_player, 0, 0.0, 0.0),
        ).minutes <= 0:
            continue
        for starter in decision.starters:
            if starter not in starters:
                continue
            if outcomes.get(starter, PlayerOutcome(starter, 0, 0.0, 0.0)).minutes > 0:
                continue
            if bench_player in used_bench:
                continue
            candidate = tuple(bench_player if player == starter else player for player in starters)
            if is_legal_formation(candidate, outcomes):
                starters = list(candidate)
                used_bench.add(bench_player)
                break
    return tuple(starters)


def score_lineup(
    decision: LineupDecision,
    outcomes: Mapping[int, PlayerOutcome],
) -> ScoredLineup:
    final_starters = resolve_autosubs(decision, outcomes)
    points = sum(outcomes.get(player_id, PlayerOutcome(player_id, 0, 0.0, 0.0)).points for player_id in final_starters)
    captain = outcomes.get(decision.captain, PlayerOutcome(decision.captain, 0, 0.0, 0.0))
    vice_captain = outcomes.get(
        decision.vice_captain,
        PlayerOutcome(decision.vice_captain, 0, 0.0, 0.0),
    )
    if decision.captain in final_starters and captain.minutes > 0:
        points += captain.points
    elif decision.vice_captain in final_starters and vice_captain.minutes > 0:
        points += vice_captain.points
    return ScoredLineup(float(points), final_starters)


def _best_captain_pair(
    starters: tuple[int, ...],
    decision: LineupDecision,
    outcomes: Mapping[int, PlayerOutcome],
) -> tuple[int, int]:
    active = [
        player_id
        for player_id in resolve_autosubs(decision, outcomes)
        if player_id in starters and outcomes.get(
            player_id,
            PlayerOutcome(player_id, 0, 0.0, 0.0),
        ).minutes > 0
    ]
    ranked = sorted(
        active,
        key=lambda player_id: (
            outcomes[player_id].points,
            -player_id,
        ),
        reverse=True,
    )
    if len(ranked) >= 2:
        return ranked[0], ranked[1]
    if ranked:
        vice = next(player_id for player_id in starters if player_id != ranked[0])
        return ranked[0], vice
    return starters[0], starters[1]


def optimize_model_lineup(
    squad: tuple[int, ...],
    outcomes: Mapping[int, PlayerOutcome],
) -> LineupDecision:
    """Choose a legal lineup using projected points and bench coverage."""
    best: tuple[float, LineupDecision] | None = None
    for starters in combinations(squad, 11):
        if not is_legal_formation(starters, outcomes):
            continue
        bench = tuple(
            sorted(
                (player_id for player_id in squad if player_id not in starters),
                key=lambda player_id: (-outcomes[player_id].points, player_id),
            )
        )
        captain, vice_captain = sorted(
            starters,
            key=lambda player_id: (-outcomes[player_id].points, player_id),
        )[:2]
        decision = LineupDecision(starters, bench, captain, vice_captain)
        score = score_lineup(decision, outcomes).points
        if best is None or score > best[0]:
            best = (score, decision)
    if best is None:
        raise ValueError("Squad has no legal FPL formation")
    return best[1]


def optimize_oracle_lineup(
    squad: tuple[int, ...],
    outcomes: Mapping[int, PlayerOutcome],
) -> LineupDecision:
    """Choose the best legal lineup using hindsight outcomes only."""
    best: tuple[float, LineupDecision] | None = None
    for starters in combinations(squad, 11):
        if not is_legal_formation(starters, outcomes):
            continue
        bench_players = tuple(player_id for player_id in squad if player_id not in starters)
        for bench in permutations(bench_players):
            provisional = LineupDecision(starters, bench, starters[0], starters[1])
            captain, vice_captain = _best_captain_pair(starters, provisional, outcomes)
            decision = LineupDecision(starters, bench, captain, vice_captain)
            score = score_lineup(decision, outcomes).points
            if best is None or score > best[0]:
                best = (score, decision)
    if best is None:
        raise ValueError("Squad has no legal FPL formation")
    return best[1]


def evaluate_decision_regret(
    actual_decision: LineupDecision,
    model_decision: LineupDecision,
    squad: tuple[int, ...],
    outcomes: Mapping[int, PlayerOutcome],
) -> dict[str, object]:
    """Return actual, model, oracle, lift, and regret for one Gameweek."""
    actual_points = score_lineup(actual_decision, outcomes).points
    model_points = score_lineup(model_decision, outcomes).points
    oracle_decision = optimize_oracle_lineup(squad, outcomes)
    oracle_points = score_lineup(oracle_decision, outcomes).points
    return {
        "actual_points": actual_points,
        "model_points": model_points,
        "oracle_points": oracle_points,
        "model_lift": model_points - actual_points,
        "model_regret": oracle_points - model_points,
        "actual_decision": actual_decision,
        "model_decision": model_decision,
        "oracle_decision": oracle_decision,
    }
