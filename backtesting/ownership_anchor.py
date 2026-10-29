r"""Neutral GW1 ownership anchor construction and freezing.

Mathematical Rationale & Ownership-Overlap Interpretation:
---------------------------------------------------------
For planning origin g (e.g., GW1 opening lock), let p_{i,g} represent the parsed
reported ownership fraction of player i, and x_i in {0, 1} represent binary squad
membership.

By linearity of expectation:
    E[|S \cap M|] = sum_{i in S} P(i in M) = sum_{i in S} p_{i,g}

where S is the selected 15-player anchor squad and M is the squad of a randomly
sampled FPL manager from the game's playing population.
Maximizing sum(p_{i,g} * x_i) subject to official FPL squad rules (15 players,
2 GKP / 5 DEF / 5 MID / 3 FWD, £100.0m budget cap, max 3 players per club)
maximizes the expected number of shared players between the anchor squad and a
random manager's squad.

Population Disclaimer:
----------------------
This mathematical property does NOT identify the modal, median, or most probable
complete 15-player squad across the manager population, nor does it make an empirical
claim of representative manager behavior or template coverage. It provides a
standardized, neutral, market-informed benchmark starting state from which independent
transfer planning policies can be evaluated over continuous seasons.
"""

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Literal, cast

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

from backtesting.replay_state import Player, ReplayState, validate_squad
from backtesting.season_rules import get_rules
from models.scoring_matrix import Position

SQUAD_SIZE: int = 15
POSITION_BOUNDS: dict[int, int] = {1: 2, 2: 5, 3: 5, 4: 3}
MAX_PER_CLUB: int = 3
INITIAL_BUDGET_TENTHS: int = 1000
TIE_BREAK_VERSION: str = "two_stage_log_id_v2"

_INT_TO_POS: dict[int, Position] = {1: "GK", 2: "D", 3: "M", 4: "F"}
_POS_NAME_TO_INT: dict[str, int] = {
    "GK": 1,
    "GKP": 1,
    "D": 2,
    "DEF": 2,
    "M": 3,
    "MID": 3,
    "F": 4,
    "FWD": 4,
}


class InfeasibleAnchorError(ValueError):
    """Raised when the admitted universe cannot form a legal 15-player squad."""


class UncertifiedAnchorError(RuntimeError):
    """Raised when the solver fails to certify the highest-owned optimum."""


class InvalidAnchorInputError(ValueError):
    """Raised when the input universe metadata is malformed or invalid."""


@dataclass(frozen=True)
class UniverseSchema:
    """Column name mapping for player universe DataFrames."""

    id_col: str = "player_id"
    pos_col: str = "position_id"
    club_col: str = "club_id"
    cost_col: str = "now_cost"
    ownership_col: str = "selected_by_percent"
    eligibility_col: str | None = None


@dataclass(frozen=True)
class CanonicalUniverse:
    """Extracted, validated, and canonically sorted player universe arrays."""

    player_ids: list[int]
    positions: list[int]
    clubs: list[int]
    costs: list[int]
    ownership: list[float]
    eligible: list[bool]
    source_df: pd.DataFrame


@dataclass(frozen=True)
class AnchorCertificate:
    """Mathematical certificate of optimality and feasibility for the anchor."""

    status: str
    anchor_type: Literal["opening", "diagnostic"]
    objective_value: float
    total_cost: int
    bank: int
    budget: int
    solver: str
    tie_break_version: str
    num_variables: int
    constraints_checked: dict[str, Any]
    wall_time_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnchorCertificate":
        return cls(
            status=str(data["status"]),
            anchor_type=cast(Literal["opening", "diagnostic"], str(data["anchor_type"])),
            objective_value=float(data["objective_value"]),
            total_cost=int(data["total_cost"]),
            bank=int(data["bank"]),
            budget=int(data["budget"]),
            solver=str(data["solver"]),
            tie_break_version=str(data["tie_break_version"]),
            num_variables=int(data["num_variables"]),
            constraints_checked=dict(data["constraints_checked"]),
            wall_time_seconds=float(data["wall_time_seconds"]),
        )


@dataclass(frozen=True)
class OwnershipAnchor:
    """Frozen neutral GW1 ownership squad anchor."""

    anchor_id: str
    anchor_type: Literal["opening", "diagnostic"]
    season: str
    gameweek: int
    player_ids: tuple[int, ...]
    player_positions: dict[int, Position]
    player_clubs: dict[int, int]
    player_eligible: dict[int, bool]
    acquisition_prices: dict[int, int]
    bank: int
    total_budget: int
    objective_value: float
    certificate: AnchorCertificate
    source_digest: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "acquisition_prices": {str(k): v for k, v in self.acquisition_prices.items()},
            "anchor_id": self.anchor_id,
            "anchor_type": self.anchor_type,
            "bank": self.bank,
            "certificate": self.certificate.to_dict(),
            "created_at": self.created_at,
            "gameweek": self.gameweek,
            "objective_value": self.objective_value,
            "player_clubs": {str(k): v for k, v in self.player_clubs.items()},
            "player_eligible": {str(k): v for k, v in self.player_eligible.items()},
            "player_ids": list(self.player_ids),
            "player_positions": {str(k): v for k, v in self.player_positions.items()},
            "season": self.season,
            "source_digest": self.source_digest,
            "total_budget": self.total_budget,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OwnershipAnchor":
        return cls(
            acquisition_prices={int(k): int(v) for k, v in data["acquisition_prices"].items()},
            anchor_id=str(data["anchor_id"]),
            anchor_type=cast(Literal["opening", "diagnostic"], str(data["anchor_type"])),
            bank=int(data["bank"]),
            certificate=AnchorCertificate.from_dict(data["certificate"]),
            created_at=str(data["created_at"]),
            gameweek=int(data["gameweek"]),
            objective_value=float(data["objective_value"]),
            player_clubs={int(k): int(v) for k, v in data["player_clubs"].items()},
            player_eligible={int(k): bool(v) for k, v in data.get("player_eligible", {}).items()},
            player_ids=tuple(int(x) for x in data["player_ids"]),
            player_positions={int(k): cast(Position, v) for k, v in data["player_positions"].items()},
            season=str(data["season"]),
            source_digest=str(data["source_digest"]),
            total_budget=int(data["total_budget"]),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str) -> "OwnershipAnchor":
        return cls.from_dict(json.loads(json_str))

    def to_replay_state(self, rules_version: str, rules_id: str | None = None) -> ReplayState:
        """Construct an initial ReplayState for GW1 from this frozen anchor."""
        rules = get_rules(rules_version)
        players = tuple(
            Player(
                player_id=pid,
                position=self.player_positions[pid],
                club=self.player_clubs[pid],
                purchase=self.acquisition_prices[pid],
                market=self.acquisition_prices[pid],
                purchase_eligible=bool(self.player_eligible.get(pid, True)),
            )
            for pid in sorted(self.player_ids)
        )
        validate_squad(players)
        total_spending = sum(p.purchase for p in players)
        if total_spending + self.bank != self.total_budget:
            raise ValueError(
                f"Initial capital not conserved: {total_spending} + {self.bank} != {self.total_budget}"
            )
        state = ReplayState(
            rules_version=rules_version,
            squad=players,
            bank=self.bank,
            rules_id=rules_id or rules.rules_id,
            deadline=self.gameweek,
            free_transfers=0,
            chip_history=(),
            previous_transfers=0,
            previous_hits=0,
            parent_hash=None,
        )
        return state


def _normalize_cost_tenths(raw_cost: int | float | str) -> int:
    """Normalize price/cost to integer tenths (e.g. £10.0m -> 100 tenths)."""
    val = float(raw_cost)
    if val <= 20.0 and val > 0:
        return int(round(val * 10.0))
    return int(round(val))


def _normalize_position_int(raw_pos: int | str) -> int:
    """Normalize position to integer 1..4."""
    if isinstance(raw_pos, (int, np.integer)):
        pos_int = int(raw_pos)
        if pos_int in (1, 2, 3, 4):
            return pos_int
        raise InvalidAnchorInputError(f"Position int must be 1..4, got {pos_int}")
    if isinstance(raw_pos, str):
        pos_upper = raw_pos.strip().upper()
        if pos_upper in _POS_NAME_TO_INT:
            return _POS_NAME_TO_INT[pos_upper]
        raise InvalidAnchorInputError(f"Unknown position string: '{raw_pos}'")
    raise InvalidAnchorInputError(f"Unsupported position type: {type(raw_pos)}")


def _extract_canonical_universe(df: pd.DataFrame, schema: UniverseSchema) -> CanonicalUniverse:
    """Strictly validate, sort by ID, and extract canonical universe arrays."""
    required_cols = [schema.id_col, schema.pos_col, schema.club_col, schema.cost_col, schema.ownership_col]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise InvalidAnchorInputError(f"Universe missing required columns: {missing}")

    if df.empty or len(df) < SQUAD_SIZE:
        raise InfeasibleAnchorError(
            f"Admitted universe has {len(df)} players, requires at least {SQUAD_SIZE}"
        )

    for col in required_cols:
        if bool(df[col].isna().any()):
            raise InvalidAnchorInputError(f"Universe contains NaN/null values in column '{col}'")

    # Sort strictly by player_id to eliminate row order sensitivity
    df_sorted = df.sort_values(by=schema.id_col, ascending=True).reset_index(drop=True)
    raw_ids: list[int] = [int(x) for x in df_sorted[schema.id_col]]
    if len(raw_ids) != len(set(raw_ids)):
        duplicates = [pid for pid, count in Counter(raw_ids).items() if count > 1]
        raise InvalidAnchorInputError(f"Duplicate player IDs found in universe: {duplicates}")

    raw_clubs: list[int] = [int(x) for x in df_sorted[schema.club_col]]
    raw_costs: list[int] = [_normalize_cost_tenths(x) for x in df_sorted[schema.cost_col]]
    raw_pos: list[int] = [_normalize_position_int(x) for x in df_sorted[schema.pos_col]]
    raw_own: list[float] = [float(x) for x in df_sorted[schema.ownership_col]]

    raw_elig: list[bool] = []
    if schema.eligibility_col and schema.eligibility_col in df_sorted.columns:
        raw_elig = [bool(x) for x in df_sorted[schema.eligibility_col]]
    elif "is_eligible" in df_sorted.columns:
        raw_elig = [bool(x) for x in df_sorted["is_eligible"]]
    else:
        raw_elig = [True] * len(raw_ids)

    for i in range(len(raw_ids)):
        if raw_ids[i] <= 0:
            raise InvalidAnchorInputError(f"Player ID must be positive integer, got {raw_ids[i]}")
        if raw_clubs[i] <= 0:
            raise InvalidAnchorInputError(f"Club ID must be positive integer, got {raw_clubs[i]}")
        if raw_costs[i] <= 0:
            raise InvalidAnchorInputError(f"Cost must be positive, got {raw_costs[i]}")
        if raw_own[i] < 0.0:
            raise InvalidAnchorInputError(f"Ownership cannot be negative, got {raw_own[i]}")

    return CanonicalUniverse(
        player_ids=raw_ids,
        positions=raw_pos,
        clubs=raw_clubs,
        costs=raw_costs,
        ownership=raw_own,
        eligible=raw_elig,
        source_df=df_sorted,
    )


def compute_universe_digest(
    universe: pd.DataFrame | CanonicalUniverse,
    schema: UniverseSchema = UniverseSchema(),
) -> str:
    """Compute deterministic SHA256 digest of input player universe rows."""
    if isinstance(universe, CanonicalUniverse):
        cu = universe
    else:
        cu = _extract_canonical_universe(universe, schema)

    canonical_rows: list[dict[str, Any]] = []
    for i in range(len(cu.player_ids)):
        canonical_rows.append({
            "club_id": cu.clubs[i],
            "cost": cu.costs[i],
            "eligible": cu.eligible[i],
            "ownership": round(cu.ownership[i], 6),
            "player_id": cu.player_ids[i],
            "position_id": cu.positions[i],
        })
    raw_bytes = json.dumps(canonical_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()


def solve_ownership_anchor(
    universe: pd.DataFrame,
    season: str,
    gameweek: int = 1,
    *,
    anchor_type: Literal["opening", "diagnostic"] | None = None,
    budget_tenths: int = INITIAL_BUDGET_TENTHS,
    schema: UniverseSchema = UniverseSchema(),
) -> OwnershipAnchor:
    """Solve binary ownership maximization over the admitted GW1 universe.

    Guarantees:
    1. Full 15-player squad (2 GKP, 5 DEF, 5 MID, 3 FWD).
    2. Sum of acquisition prices <= budget_tenths.
    3. Max 3 players per club.
    4. Deterministic secondary lexicographic tie-breaking without sacrificing primary ownership.
    5. Invariant to input row ordering.
    """
    start_time = time.perf_counter()
    effective_anchor_type: Literal["opening", "diagnostic"] = (
        anchor_type if anchor_type is not None else ("opening" if gameweek == 1 else "diagnostic")
    )
    cu = _extract_canonical_universe(universe, schema)
    n = len(cu.player_ids)

    player_ids = np.array(cu.player_ids, dtype=int)
    positions = np.array(cu.positions, dtype=int)
    clubs = np.array(cu.clubs, dtype=int)
    costs = np.array(cu.costs, dtype=int)
    ownership = np.array(cu.ownership, dtype=float)
    eligible = np.array(cu.eligible, dtype=bool)

    # Positional feasibility check on eligible players
    pos_counts = Counter(positions[eligible])
    for pos_code, req_count in POSITION_BOUNDS.items():
        if pos_counts[pos_code] < req_count:
            raise InfeasibleAnchorError(
                f"Position {pos_code} ({_INT_TO_POS[pos_code]}) has only {pos_counts[pos_code]} "
                f"eligible players, requires {req_count}"
            )

    # Minimum possible cost for 15 eligible players
    min_cost = 0
    for p, req in POSITION_BOUNDS.items():
        pos_costs = sorted(int(costs[i]) for i in range(n) if positions[i] == p and eligible[i])
        min_cost += sum(pos_costs[:req])
    if min_cost > budget_tenths:
        raise InfeasibleAnchorError(
            f"Minimum possible squad cost ({min_cost}) exceeds budget ({budget_tenths})"
        )

    # Assemble linear constraints
    unique_clubs = np.unique(clubs)
    A_rows: list[np.ndarray] = [
        np.ones(n, dtype=float),  # Total squad = 15
        (positions == 1).astype(float),  # GKP = 2
        (positions == 2).astype(float),  # DEF = 5
        (positions == 3).astype(float),  # MID = 5
        (positions == 4).astype(float),  # FWD = 3
        costs.astype(float),  # Budget constraint <= budget_tenths
    ]
    lb: list[float] = [float(SQUAD_SIZE), 2.0, 5.0, 5.0, 3.0, 0.0]
    ub: list[float] = [float(SQUAD_SIZE), 2.0, 5.0, 5.0, 3.0, float(budget_tenths)]

    for cl in unique_clubs:
        A_rows.append((clubs == cl).astype(float))
        lb.append(0.0)
        ub.append(float(MAX_PER_CLUB))

    A_stage1 = np.array(A_rows, dtype=float)
    constraints_stage1 = LinearConstraint(A_stage1, cast(float, lb), cast(float, ub))
    integrality = np.ones(n, dtype=int)
    # Upper bound = 1 if eligible else 0
    upper_bounds = np.where(eligible, 1.0, 0.0)
    bounds = Bounds(cast(float, np.zeros(n)), cast(float, upper_bounds))

    # Stage 1: Maximize sum(ownership * x) <=> Minimize -sum(ownership * x)
    c_stage1 = -ownership
    res_stage1 = milp(c=c_stage1, integrality=integrality, bounds=bounds, constraints=constraints_stage1)

    if not res_stage1.success or res_stage1.status != 0:
        raise InfeasibleAnchorError(
            f"Stage 1 ownership optimization failed: {res_stage1.message} (status: {res_stage1.status})"
        )

    z_star: float = -float(res_stage1.fun)

    # Stage 2: Secondary deterministic lexicographic tie-breaking.
    # Mathematical non-sacrifice guarantee:
    # We enforce sum(ownership * x) >= z_star - 1e-7 so the primary objective cannot be compromised.
    # Objective: Minimize sum(log(1 + player_id) * x).
    # Since log is strictly concave and strictly increasing, for any subset of players with identical
    # total ownership, this deterministically prefers smaller player IDs.
    A_stage2 = np.vstack([A_stage1, ownership])
    lb_stage2: list[float] = list(lb) + [z_star - 1e-7]
    ub_stage2: list[float] = list(ub) + [float("inf")]

    c_stage2 = np.log1p(player_ids.astype(float))

    constraints_stage2 = LinearConstraint(A_stage2, cast(float, lb_stage2), cast(float, ub_stage2))
    res_stage2 = milp(c=c_stage2, integrality=integrality, bounds=bounds, constraints=constraints_stage2)

    if not res_stage2.success or res_stage2.status != 0:
        raise UncertifiedAnchorError(
            f"Stage 2 tie-breaking failed: {res_stage2.message} (status: {res_stage2.status})"
        )

    selected_idx = np.where(res_stage2.x > 0.5)[0]
    if len(selected_idx) != SQUAD_SIZE:
        raise UncertifiedAnchorError(
            f"Selected squad size {len(selected_idx)} != {SQUAD_SIZE}"
        )

    selected_ids = tuple(sorted(int(player_ids[i]) for i in selected_idx))
    selected_pos: dict[int, Position] = {
        int(player_ids[i]): _INT_TO_POS[int(positions[i])] for i in selected_idx
    }
    selected_clubs: dict[int, int] = {
        int(player_ids[i]): int(clubs[i]) for i in selected_idx
    }
    selected_prices: dict[int, int] = {
        int(player_ids[i]): int(costs[i]) for i in selected_idx
    }
    selected_elig: dict[int, bool] = {
        int(player_ids[i]): bool(eligible[i]) for i in selected_idx
    }

    total_cost = sum(selected_prices.values())
    bank = budget_tenths - total_cost
    if bank < 0:
        raise UncertifiedAnchorError(f"Negative bank: {bank}")

    actual_obj = float(sum(ownership[i] for i in selected_idx))
    if abs(actual_obj - z_star) > 1e-5:
        raise UncertifiedAnchorError(
            f"Secondary tie-break sacrificed primary objective: {actual_obj} vs {z_star}"
        )

    # Verify positions and club constraints explicitly
    pos_counter = Counter(selected_pos.values())
    if pos_counter != {"GK": 2, "D": 5, "M": 5, "F": 3}:
        raise UncertifiedAnchorError(f"Positional breakdown violated: {pos_counter}")

    club_counter = Counter(selected_clubs.values())
    if any(c > MAX_PER_CLUB for c in club_counter.values()):
        raise UncertifiedAnchorError(f"Club quota violated: {club_counter}")

    wall_time = time.perf_counter() - start_time
    certificate = AnchorCertificate(
        status="OPTIMAL",
        anchor_type=effective_anchor_type,
        objective_value=round(actual_obj, 6),
        total_cost=total_cost,
        bank=bank,
        budget=budget_tenths,
        solver="scipy.optimize.milp(HiGHS)",
        tie_break_version=TIE_BREAK_VERSION,
        num_variables=n,
        constraints_checked={
            "budget_cap_tenths": budget_tenths,
            "max_per_club": MAX_PER_CLUB,
            "position_counts": {"GK": 2, "D": 5, "M": 5, "F": 3},
            "squad_size": SQUAD_SIZE,
        },
        wall_time_seconds=round(wall_time, 4),
    )

    source_digest = compute_universe_digest(cu, schema=schema)

    id_payload = {
        "anchor_type": effective_anchor_type,
        "budget": budget_tenths,
        "gameweek": gameweek,
        "objective_value": round(actual_obj, 6),
        "player_ids": list(selected_ids),
        "season": season,
        "source_digest": source_digest,
        "tie_break_version": TIE_BREAK_VERSION,
    }
    raw_hash = hashlib.sha256(
        json.dumps(id_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    prefix = "diagnostic-anchor" if effective_anchor_type == "diagnostic" else "opening-anchor"
    anchor_id = f"{prefix}-{raw_hash[:16]}"
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return OwnershipAnchor(
        anchor_id=anchor_id,
        anchor_type=effective_anchor_type,
        season=season,
        gameweek=gameweek,
        player_ids=selected_ids,
        player_positions=selected_pos,
        player_clubs=selected_clubs,
        player_eligible=selected_elig,
        acquisition_prices=selected_prices,
        bank=bank,
        total_budget=budget_tenths,
        objective_value=round(actual_obj, 6),
        certificate=certificate,
        source_digest=source_digest,
        created_at=created_at,
    )


def save_ownership_anchor(anchor: OwnershipAnchor, output_path: str | Path) -> Path:
    """Save ownership anchor to disk atomically."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(anchor.to_json())
    temp_path.replace(path)
    return path


def load_ownership_anchor(
    path: str | Path,
    expected_digest: str | None = None,
) -> OwnershipAnchor:
    """Load and verify an ownership anchor from disk."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Anchor file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        anchor = OwnershipAnchor.from_json(f.read())

    if expected_digest is not None and anchor.source_digest != expected_digest:
        raise ValueError(
            f"Source digest mismatch: expected {expected_digest}, found {anchor.source_digest}"
        )
    return anchor
