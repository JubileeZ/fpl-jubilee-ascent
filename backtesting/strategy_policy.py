"""First-Half Transfer Plan Walk-Forward policy (ADR 0020)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd


class LockedStartingShape(StrEnum):
    THREE_FOUR_THREE = "3-4-3"
    THREE_FIVE_TWO = "3-5-2"
    FOUR_THREE_THREE = "4-3-3"
    FOUR_FOUR_TWO = "4-4-2"
    FOUR_FIVE_ONE = "4-5-1"


class TransferTarget(StrEnum):
    UNCONSTRAINED = "unconstrained"
    ATTACK = "attack"
    DEFENCE = "defence"


class Tilt(StrEnum):
    VANILLA = "vanilla"
    DEFCON_FLOOR = "defcon_floor"
    ATTACK_CEILING = "attack_ceiling"


_SHAPE_XI: dict[LockedStartingShape, dict[int, tuple[int, int]]] = {
    LockedStartingShape.THREE_FOUR_THREE: {1: (1, 1), 2: (3, 3), 3: (4, 4), 4: (3, 3)},
    LockedStartingShape.THREE_FIVE_TWO: {1: (1, 1), 2: (3, 3), 3: (5, 5), 4: (2, 2)},
    LockedStartingShape.FOUR_THREE_THREE: {1: (1, 1), 2: (4, 4), 3: (3, 3), 4: (3, 3)},
    LockedStartingShape.FOUR_FOUR_TWO: {1: (1, 1), 2: (4, 4), 3: (4, 4), 4: (2, 2)},
    LockedStartingShape.FOUR_FIVE_ONE: {1: (1, 1), 2: (4, 4), 3: (5, 5), 4: (1, 1)},
}

_ATTACK_LOCK_POSITIONS = frozenset({1, 2})
_DEFENCE_LOCK_POSITIONS = frozenset({3, 4})
_TILT_POSITIONS = frozenset({2, 3})
DNP_EXCEPTION_THRESHOLD = 0.5
FREE_TRANSFER_CAP = 5


@dataclass(frozen=True)
class WalkforwardArm:
    arm_id: str
    family: str
    locked_starting_shape: LockedStartingShape | None
    transfer_target: TransferTarget
    tilt: Tilt


def apply_tilt(xp: float, xp_defcon: float, position_id: int, tilt: Tilt) -> float:
    if tilt is Tilt.VANILLA or position_id not in _TILT_POSITIONS:
        return float(xp)
    if tilt is Tilt.DEFCON_FLOOR:
        return float(xp) + float(xp_defcon)
    return float(xp) - float(xp_defcon)


def meets_dnp_exception(p_dnp: float) -> bool:
    return float(p_dnp) >= DNP_EXCEPTION_THRESHOLD


def locked_player_ids(
    owned: Sequence[Mapping[str, object]],
    target: TransferTarget,
) -> tuple[int, ...]:
    if target is TransferTarget.UNCONSTRAINED:
        return ()
    lock_positions = _ATTACK_LOCK_POSITIONS if target is TransferTarget.ATTACK else _DEFENCE_LOCK_POSITIONS
    locked = [
        int(row["player_id"])
        for row in owned
        if int(row["position_id"]) in lock_positions and not meets_dnp_exception(float(row["p_dnp"]))
    ]
    return tuple(locked)


def locked_starting_shape_bounds(
    shape: LockedStartingShape | None,
) -> dict[int, tuple[int, int]] | None:
    if shape is None:
        return None
    return dict(_SHAPE_XI[shape])


def apply_shape_to_type_data(
    type_data: pd.DataFrame,
    shape: LockedStartingShape | None,
) -> pd.DataFrame:
    bounds = locked_starting_shape_bounds(shape)
    if bounds is None:
        return type_data
    out = type_data.copy()
    for type_id, (lo, hi) in bounds.items():
        if type_id in out.index:
            out.loc[type_id, "squad_min_play"] = lo
            out.loc[type_id, "squad_max_play"] = hi
    return out


def next_free_transfer_bank(current: int, spent: int) -> int:
    if spent < 0:
        raise ValueError("spent Free Transfers cannot be negative")
    if spent > current:
        raise ValueError(f"Hit forbidden: spent {spent} exceeds Free Transfer Bank {current}")
    return min(FREE_TRANSFER_CAP, current - spent + 1)


_SEED_ARCHIVE_MISSING = (
    "2024-25 processed archive missing (Prior-Season Seed Event Rates and seed-state minutes). "
    "Ingest via: uv run python -m commands.snapshot_season --season 2024-25 --from-vaastav-dir <vaastav-csv-dir> "
    "or --from-raw-dir <raw>"
)


def require_prior_season_seed(processed_dir: Path) -> Path:
    players = processed_dir / "players.parquet"
    performances = processed_dir / "player_performances.parquet"
    if not players.exists() or not performances.exists():
        raise FileNotFoundError(_SEED_ARCHIVE_MISSING)
    try:
        players_df = pd.read_parquet(players)
        performances_df = pd.read_parquet(performances)
    except Exception as exc:
        raise FileNotFoundError(_SEED_ARCHIVE_MISSING) from exc
    if players_df.empty or performances_df.empty:
        raise FileNotFoundError(_SEED_ARCHIVE_MISSING)
    return processed_dir


def oat_arm_catalog() -> tuple[WalkforwardArm, ...]:
    arms: list[WalkforwardArm] = [
        WalkforwardArm("baseline", "baseline", None, TransferTarget.UNCONSTRAINED, Tilt.VANILLA),
    ]
    for shape in LockedStartingShape:
        arms.append(
            WalkforwardArm(
                f"shape_{shape.value}",
                "shape",
                shape,
                TransferTarget.UNCONSTRAINED,
                Tilt.VANILLA,
            )
        )
    for target in (TransferTarget.ATTACK, TransferTarget.DEFENCE):
        arms.append(
            WalkforwardArm(
                f"ft_{target.value}",
                "ft",
                None,
                target,
                Tilt.VANILLA,
            )
        )
    for tilt in (Tilt.DEFCON_FLOOR, Tilt.ATTACK_CEILING):
        arms.append(
            WalkforwardArm(
                f"tilt_{tilt.value}",
                "tilt",
                None,
                TransferTarget.UNCONSTRAINED,
                tilt,
            )
        )
    return tuple(arms)


FIRST_HALF_OAT_ARMS: tuple[WalkforwardArm, ...] = oat_arm_catalog()


def _is_oat_arm(
    shape: LockedStartingShape | None,
    target: TransferTarget,
    tilt: Tilt,
) -> bool:
    for arm in FIRST_HALF_OAT_ARMS:
        if arm.locked_starting_shape == shape and arm.transfer_target == target and arm.tilt == tilt:
            return True
    return False


def winner_cross_arm(
    shape: LockedStartingShape | None,
    target: TransferTarget,
    tilt: Tilt,
) -> WalkforwardArm | None:
    if _is_oat_arm(shape, target, tilt):
        return None
    shape_key = "unconstrained" if shape is None else shape.value
    return WalkforwardArm(
        f"cross_{shape_key}_{target.value}_{tilt.value}",
        "cross",
        shape,
        target,
        tilt,
    )
