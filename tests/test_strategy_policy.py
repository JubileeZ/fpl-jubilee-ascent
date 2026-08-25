from pathlib import Path

import pandas as pd

from backtesting.strategy_policy import (
    FIRST_HALF_OAT_ARMS,
    LockedStartingShape,
    Tilt,
    TransferTarget,
    apply_shape_to_type_data,
    apply_tilt,
    locked_player_ids,
    locked_starting_shape_bounds,
    meets_dnp_exception,
    next_free_transfer_bank,
    oat_arm_catalog,
    require_prior_season_seed,
    winner_cross_arm,
)


def test_defcon_floor_doubles_defcon_for_def_and_mid_only() -> None:
    assert apply_tilt(4.0, 0.5, position_id=2, tilt=Tilt.DEFCON_FLOOR) == 4.5
    assert apply_tilt(4.0, 0.5, position_id=3, tilt=Tilt.DEFCON_FLOOR) == 4.5
    assert apply_tilt(4.0, 0.5, position_id=4, tilt=Tilt.DEFCON_FLOOR) == 4.0
    assert apply_tilt(4.0, 0.5, position_id=1, tilt=Tilt.DEFCON_FLOOR) == 4.0


def test_attack_ceiling_strips_defcon_for_def_and_mid_only() -> None:
    assert apply_tilt(4.0, 0.5, position_id=2, tilt=Tilt.ATTACK_CEILING) == 3.5
    assert apply_tilt(4.0, 0.5, position_id=4, tilt=Tilt.ATTACK_CEILING) == 4.0
    assert apply_tilt(4.0, 0.5, position_id=2, tilt=Tilt.VANILLA) == 4.0


def test_dnp_exception_is_deadline_p_dnp_at_least_half() -> None:
    assert meets_dnp_exception(0.5) is True
    assert meets_dnp_exception(0.49) is False
    assert meets_dnp_exception(1.0) is True


def test_attack_targeted_locks_backline_except_dnp() -> None:
    owned = [
        {"player_id": 1, "position_id": 1, "p_dnp": 0.1},
        {"player_id": 2, "position_id": 2, "p_dnp": 0.2},
        {"player_id": 3, "position_id": 2, "p_dnp": 0.8},
        {"player_id": 4, "position_id": 3, "p_dnp": 0.0},
    ]
    assert locked_player_ids(owned, TransferTarget.ATTACK) == (1, 2)


def test_defence_targeted_locks_mid_and_fwd_except_dnp() -> None:
    owned = [
        {"player_id": 2, "position_id": 2, "p_dnp": 0.0},
        {"player_id": 7, "position_id": 3, "p_dnp": 0.1},
        {"player_id": 12, "position_id": 4, "p_dnp": 0.9},
    ]
    assert locked_player_ids(owned, TransferTarget.DEFENCE) == (7,)


def test_unconstrained_target_locks_nobody() -> None:
    owned = [{"player_id": 2, "position_id": 2, "p_dnp": 0.0}]
    assert locked_player_ids(owned, TransferTarget.UNCONSTRAINED) == ()


def test_apply_shape_to_type_data_locks_min_and_max_play() -> None:
    type_data = pd.DataFrame(
        {"squad_min_play": [1, 3, 2, 1], "squad_max_play": [1, 5, 5, 3]},
        index=[1, 2, 3, 4],
    )
    locked = apply_shape_to_type_data(type_data, LockedStartingShape.FOUR_FOUR_TWO)
    assert int(locked.loc[2, "squad_min_play"]) == 4
    assert int(locked.loc[2, "squad_max_play"]) == 4
    assert int(locked.loc[3, "squad_min_play"]) == 4
    assert int(locked.loc[4, "squad_max_play"]) == 2


def test_locked_starting_shape_sets_exact_xi_counts() -> None:
    assert locked_starting_shape_bounds(LockedStartingShape.FOUR_FOUR_TWO) == {
        1: (1, 1),
        2: (4, 4),
        3: (4, 4),
        4: (2, 2),
    }
    assert locked_starting_shape_bounds(LockedStartingShape.THREE_FIVE_TWO)[2] == (3, 3)
    assert locked_starting_shape_bounds(None) is None


def test_free_transfer_bank_caps_at_five_and_forbids_hits() -> None:
    assert next_free_transfer_bank(3, spent=2) == 2
    assert next_free_transfer_bank(5, spent=0) == 5
    assert next_free_transfer_bank(1, spent=0) == 2
    assert next_free_transfer_bank(1, spent=1) == 1


def test_free_transfer_bank_rejects_a_hit() -> None:
    try:
        next_free_transfer_bank(1, spent=2)
    except ValueError as exc:
        assert "Hit" in str(exc)
    else:
        raise AssertionError("expected Hit rejection")


def test_oat_catalog_is_baseline_plus_five_shapes_plus_two_ft_plus_two_tilts() -> None:
    arms = oat_arm_catalog()
    assert len(arms) == 10
    assert arms[0].arm_id == "baseline"
    shapes = [arm.locked_starting_shape for arm in arms if arm.family == "shape"]
    assert shapes == [
        LockedStartingShape.THREE_FOUR_THREE,
        LockedStartingShape.THREE_FIVE_TWO,
        LockedStartingShape.FOUR_THREE_THREE,
        LockedStartingShape.FOUR_FOUR_TWO,
        LockedStartingShape.FOUR_FIVE_ONE,
    ]
    assert FIRST_HALF_OAT_ARMS == arms


def test_winner_cross_skips_when_combo_already_ran() -> None:
    assert winner_cross_arm(
        LockedStartingShape.FOUR_FOUR_TWO,
        TransferTarget.UNCONSTRAINED,
        Tilt.VANILLA,
    ) is None
    cross = winner_cross_arm(
        LockedStartingShape.THREE_FIVE_TWO,
        TransferTarget.ATTACK,
        Tilt.DEFCON_FLOOR,
    )
    assert cross is not None
    assert cross.family == "cross"
    assert cross.locked_starting_shape == LockedStartingShape.THREE_FIVE_TWO
    assert cross.transfer_target == TransferTarget.ATTACK
    assert cross.tilt == Tilt.DEFCON_FLOOR


def test_require_prior_season_seed_needs_readable_nonempty_parquets(tmp_path: Path) -> None:
    missing = tmp_path / "archive" / "2024-25" / "processed"
    missing.mkdir(parents=True)
    try:
        require_prior_season_seed(missing)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected missing seed")
    (missing / "players.parquet").write_bytes(b"")
    (missing / "player_performances.parquet").write_bytes(b"")
    try:
        require_prior_season_seed(missing)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected unreadable empty parquet")
    pd.DataFrame({"id": [1]}).to_parquet(missing / "players.parquet")
    pd.DataFrame({"element": [1], "round": [1]}).to_parquet(missing / "player_performances.parquet")
    assert require_prior_season_seed(missing) == missing
