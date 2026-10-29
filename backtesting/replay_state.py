"""Immutable financial primitives for a native-season replay."""

from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from itertools import permutations
import re
from typing import cast

from backtesting.season_rules import Chip, chip_window, get_rules, next_free_transfers, selling_price
from models.scoring_matrix import Position


@dataclass(frozen=True)
class Player:
    player_id: int
    position: Position
    club: int
    purchase: int
    market: int
    purchase_eligible: bool = True


@dataclass(frozen=True)
class ReplayState:
    rules_version: str
    squad: tuple[Player, ...]
    bank: int
    rules_id: str
    deadline: int = 1
    free_transfers: int = 0
    chip_history: tuple[tuple[int, Chip, int], ...] = ()
    previous_transfers: int = 0
    previous_hits: int = 0
    parent_hash: str | None = None


@dataclass(frozen=True)
class Lineup:
    starters: tuple[int, ...]
    bench: tuple[int, ...]
    captain: int
    vice: int


@dataclass(frozen=True)
class Outcome:
    points: int
    minutes: int
    appeared: bool | None


@dataclass(frozen=True)
class OutcomeBatch:
    rules_version: str
    deadline: int
    source_identity: str
    outcomes: tuple[tuple[int, Outcome], ...]


@dataclass(frozen=True)
class Decision:
    transfers: tuple[tuple[int, Player], ...]
    lineup: Lineup
    expected_state_hash: str
    issued_deadline: int
    chip: Chip | None = None


@dataclass(frozen=True)
class Transition:
    state: ReplayState
    gross: int
    captain_increment: int
    hit: int
    net: int


def state_hash(state: ReplayState) -> str:
    return sha256(json.dumps(asdict(state), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_squad(squad: tuple[Player, ...]) -> None:
    if not isinstance(squad, tuple) or any(not isinstance(p, Player) for p in squad):
        raise ValueError("Squad must be immutable players")
    if len(squad) != 15 or len({p.player_id for p in squad}) != 15:
        raise ValueError("Squad must contain fifteen distinct players")
    if Counter(p.position for p in squad) != {"GK": 2, "D": 5, "M": 5, "F": 3}:
        raise ValueError("Invalid squad positions")
    if any(count > 3 for count in Counter(p.club for p in squad).values()):
        raise ValueError("More than three players from one club")
    if any(
        type(value) is not int or value <= 0
        for p in squad
        for value in (p.player_id, p.club, p.purchase, p.market)
    ):
        raise ValueError("Invalid player metadata")
    if any(type(p.purchase_eligible) is not bool for p in squad):
        raise ValueError("Invalid purchase eligibility")


def initial_state(rules_version: str, squad: tuple[Player, ...]) -> ReplayState:
    rules = get_rules(rules_version)
    validate_squad(squad)
    if any(p.purchase != p.market for p in squad):
        raise ValueError("Initial acquisition must use deadline market price")
    bank = 1000 - sum(p.purchase for p in squad)
    if type(bank) is not int or bank < 0:
        raise ValueError("Initial squad exceeds budget")
    return ReplayState(rules_version, squad, bank, rules.rules_id)


def refresh_owned(squad: tuple[Player, ...], refreshed: tuple[Player, ...]) -> tuple[Player, ...]:
    """Accept admitted deadline metadata without changing acquisition basis."""
    validate_squad(squad)
    validate_squad(refreshed)
    old = {player.player_id: player for player in squad}
    if set(old) != {player.player_id for player in refreshed}:
        raise ValueError("Refreshed ownership must match")
    if any(player.purchase != old[player.player_id].purchase for player in refreshed):
        raise ValueError("Refreshed metadata changed acquisition basis")
    return refreshed


def transfer_squad(
    squad: tuple[Player, ...], bank: int, transfers: tuple[tuple[int, Player], ...]
) -> tuple[tuple[Player, ...], int]:
    validate_squad(squad)
    if type(bank) is not int or bank < 0:
        raise ValueError("Negative bank")
    sold = [player_id for player_id, _ in transfers]
    if any(type(player_id) is not int or player_id <= 0 for player_id in sold):
        raise ValueError("Invalid sold player ID")
    bought = [player.player_id for _, player in transfers]
    owned = {p.player_id: p for p in squad}
    if len(set(sold)) != len(sold) or len(set(bought)) != len(bought):
        raise ValueError("Duplicate transfer")
    if not set(sold) <= owned.keys() or set(bought) & owned.keys():
        raise ValueError("Invalid sold or purchased player")
    if any(p.purchase != p.market or not p.purchase_eligible for _, p in transfers):
        raise ValueError("Acquisition price must equal market price")
    updated_bank = bank + sum(selling_price(owned[i].purchase, owned[i].market) for i in sold)
    updated_bank -= sum(p.market for _, p in transfers)
    if updated_bank < 0:
        raise ValueError("Unaffordable transfers")
    updated = tuple(p for p in squad if p.player_id not in sold) + tuple(p for _, p in transfers)
    validate_squad(updated)
    return updated, updated_bank


def _formation(ids: tuple[int, ...], players: dict[int, Player]) -> bool:
    positions = Counter(players[i].position for i in ids)
    return (len(ids) == 11 and positions["GK"] == 1 and 3 <= positions["D"] <= 5
            and 2 <= positions["M"] <= 5 and 1 <= positions["F"] <= 3)


def _validate_outcome(outcome: Outcome) -> None:
    if not isinstance(outcome, Outcome) or type(outcome.points) is not int or type(outcome.minutes) is not int or outcome.minutes < 0:
        raise ValueError("Incomplete outcome")
    if type(outcome.appeared) is not bool or (outcome.minutes > 0 and not outcome.appeared):
        raise ValueError("Unknown or inconsistent appearance")
    if outcome.minutes == 0 and (outcome.points != 0 or outcome.appeared):
        raise ValueError("Zero-minute scoring or appearance eligibility unsupported")


def score_lineup(
    squad: tuple[Player, ...], lineup: Lineup, outcomes: dict[int, Outcome], chip: Chip | None
) -> tuple[int, int]:
    validate_squad(squad)
    if chip not in (None, "wildcard", "free_hit", "bench_boost", "triple_captain"):
        raise ValueError("Unsupported chip")
    players = {p.player_id: p for p in squad}
    all_ids = lineup.starters + lineup.bench
    if any(type(player_id) is not int or player_id <= 0 for player_id in (*all_ids, lineup.captain, lineup.vice)):
        raise ValueError("Invalid lineup player ID")
    if len(lineup.starters) != 11 or len(lineup.bench) != 4 or set(all_ids) != set(players) or len(set(all_ids)) != 15:
        raise ValueError("Lineup must partition squad into eleven and four")
    if not _formation(lineup.starters, players) or players[lineup.bench[0]].position != "GK":
        raise ValueError("Invalid starting formation or bench order")
    if lineup.captain == lineup.vice or lineup.captain not in lineup.starters or lineup.vice not in lineup.starters:
        raise ValueError("Invalid captain or vice")
    if not set(players) <= set(outcomes):
        raise ValueError("Missing outcomes")
    outcomes = {player_id: outcomes[player_id] for player_id in players}
    for outcome in outcomes.values():
        _validate_outcome(outcome)
    if chip == "bench_boost":
        scoring = all_ids
    else:
        missing = tuple(i for i in lineup.starters if not outcomes[i].appeared)
        available = tuple(i for i in lineup.bench if outcomes[i].appeared)
        choices: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        for count in range(min(len(missing), len(available)) + 1):
            for replacements in permutations(available, count):
                if tuple(sorted(replacements, key=lineup.bench.index)) != replacements:
                    continue
                for removed in permutations(missing, count):
                    chosen = tuple(i for i in lineup.starters if i not in removed) + replacements
                    if _formation(chosen, players):
                        choices.append((replacements, removed))
        replacements, removed = min(choices, key=lambda item: (-len(item[0]), tuple(lineup.bench.index(i) for i in item[0])))
        scoring = tuple(i for i in lineup.starters if i not in removed) + replacements
    gross = sum(outcomes[i].points for i in scoring)
    captain = lineup.captain if outcomes[lineup.captain].minutes > 0 else lineup.vice
    increment = outcomes[captain].points * (2 if chip == "triple_captain" else 1) if outcomes[captain].minutes > 0 else 0
    return gross, increment


def transition(state: ReplayState, decision: Decision, batch: OutcomeBatch) -> Transition:
    rules = get_rules(state.rules_version)
    if state.rules_id != rules.rules_id:
        raise ValueError("Rules identity mismatch")
    if type(decision.issued_deadline) is not int or decision.expected_state_hash != state_hash(state) or decision.issued_deadline != state.deadline:
        raise ValueError("Decision does not bind to pre-state")
    if batch.rules_version != state.rules_version or type(batch.deadline) is not int or batch.deadline != state.deadline or not isinstance(batch.source_identity, str) or not batch.source_identity.strip():
        raise ValueError("Outcome batch scope mismatch")
    if not isinstance(batch.outcomes, tuple) or any(not isinstance(item, tuple) or len(item) != 2 for item in batch.outcomes):
        raise ValueError("Outcome batch must be immutable")
    if any(type(player_id) is not int or player_id <= 0 or not isinstance(outcome, Outcome) for player_id, outcome in batch.outcomes):
        raise ValueError("Invalid outcome payload")
    for _, outcome in batch.outcomes:
        _validate_outcome(outcome)
    outcomes = dict(batch.outcomes)
    if len(outcomes) != len(batch.outcomes):
        raise ValueError("Duplicate outcome player")
    if type(state.deadline) is not int or not 1 <= state.deadline <= 38:
        raise ValueError("Invalid deadline")
    validate_squad(state.squad)
    if type(state.bank) is not int or state.bank < 0:
        raise ValueError("Invalid bank")
    if type(state.free_transfers) is not int or (state.deadline > 1 and not 1 <= state.free_transfers <= rules.free_transfer_cap) or (state.deadline == 1 and state.free_transfers != 0):
        raise ValueError("Invalid free transfer balance")
    if any(type(x) is not int or x < 0 for x in (state.previous_transfers, state.previous_hits)) or state.previous_hits % 4 or state.previous_hits > 4 * state.previous_transfers:
        raise ValueError("Invalid previous action")
    if state.deadline == 1:
        if state.parent_hash is not None or state.previous_transfers or state.previous_hits or state.chip_history:
            raise ValueError("Invalid opening lineage")
    elif not isinstance(state.parent_hash, str) or re.fullmatch(r"[0-9a-f]{64}", state.parent_hash) is None:
        raise ValueError("Invalid parent hash")
    if not isinstance(state.chip_history, tuple) or any(not isinstance(item, tuple) or len(item) != 3 for item in state.chip_history):
        raise ValueError("Invalid chip history container")
    if any(type(gw) is not int or type(window) is not int or not isinstance(chip, str) for gw, chip, window in state.chip_history):
        raise ValueError("Invalid chip history values")
    if any(gw >= state.deadline or chip_window(rules, chip, gw) != window for gw, chip, window in state.chip_history):
        raise ValueError("Invalid chip history")
    if any(gw == 1 and chip not in ("bench_boost", "triple_captain") for gw, chip, _ in state.chip_history):
        raise ValueError("Invalid opening chip")
    if len({(chip, window) for _, chip, window in state.chip_history}) != len(state.chip_history):
        raise ValueError("Duplicate chip history")
    if len({gw for gw, _, _ in state.chip_history}) != len(state.chip_history):
        raise ValueError("Multiple chips in one deadline")
    if tuple(sorted(state.chip_history)) != state.chip_history:
        raise ValueError("Unordered chip history")
    free_hit_gws = {gw for gw, chip, _ in state.chip_history if chip == "free_hit"}
    if any(gw + 1 in free_hit_gws for gw in free_hit_gws):
        raise ValueError("Consecutive Free Hits unsupported")
    if any(gw == state.deadline - 1 and chip in ("wildcard", "free_hit") for gw, chip, _ in state.chip_history) and state.previous_hits:
        raise ValueError("Chip action cannot incur hits")
    if not isinstance(decision.transfers, tuple) or not isinstance(decision.lineup.starters, tuple) or not isinstance(decision.lineup.bench, tuple):
        raise ValueError("Decision must be immutable")
    if state.deadline == 1 and (decision.transfers or decision.chip not in (None, "bench_boost", "triple_captain")):
        raise ValueError("GW1 reference squad is locked")
    history = state.chip_history
    if decision.chip is not None:
        window = chip_window(rules, decision.chip, state.deadline)
        if any(chip == decision.chip and prior_window == window for _, chip, prior_window in history):
            raise ValueError("Chip already used in window")
        if decision.chip == "free_hit" and any(gw == state.deadline - 1 and chip == "free_hit" for gw, chip, _ in history):
            raise ValueError("Consecutive Free Hits are unsupported")
        chip_event: tuple[int, Chip, int] = (state.deadline, cast(Chip, decision.chip), window)
        history = (*history, chip_event)
    squad, bank = transfer_squad(state.squad, state.bank, decision.transfers)
    gross, captain_increment = score_lineup(squad, decision.lineup, outcomes, decision.chip)
    transfers = len(decision.transfers)
    hit = 0 if decision.chip in ("wildcard", "free_hit") else 4 * max(transfers - state.free_transfers, 0)
    next_ft = next_free_transfers(rules, state.free_transfers, transfers, decision.chip, state.deadline)
    next_squad, next_bank = (state.squad, state.bank) if decision.chip == "free_hit" else (squad, bank)
    next_state = ReplayState(state.rules_version, next_squad, next_bank, state.rules_id, state.deadline + 1, next_ft,
                             history, transfers, hit, state_hash(state))
    return Transition(next_state, gross, captain_increment, hit, gross + captain_increment - hit)
