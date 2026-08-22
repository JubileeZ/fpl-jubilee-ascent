from solver.planning import (
    CHIP_SET_1_END,
    MAX_PLANNING_HORIZON,
    MIN_PLANNING_HORIZON,
    available_chips,
    chip_set_for_gw,
    clamp_planning_horizon,
    planning_gameweeks,
    solver_options_from_plan,
    validate_enabled_chips,
)


def test_clamp_planning_horizon_is_one_to_five() -> None:
    assert MIN_PLANNING_HORIZON == 1
    assert MAX_PLANNING_HORIZON == 5
    assert clamp_planning_horizon(0) == 1
    assert clamp_planning_horizon(3) == 3
    assert clamp_planning_horizon(6) == 5
    assert clamp_planning_horizon(99) == 5


def test_planning_gameweeks_start_at_target_and_clip_at_38() -> None:
    assert planning_gameweeks(2, 5) == [2, 3, 4, 5, 6]
    assert planning_gameweeks(36, 5) == [36, 37, 38]
    assert CHIP_SET_1_END == 19


def test_chip_set_for_gw() -> None:
    assert chip_set_for_gw(1) == 1
    assert chip_set_for_gw(19) == 1
    assert chip_set_for_gw(20) == 2
    assert chip_set_for_gw(38) == 2


def test_available_chips_default_set_1_when_no_user_chips() -> None:
    chips = available_chips([2, 3, 4, 5, 6], [])
    keys = {(c["chip"], c["chip_set"]) for c in chips}
    assert keys == {("wc", 1), ("bb", 1), ("fh", 1), ("tc", 1)}
    bb = next(c for c in chips if c["chip"] == "bb")
    assert bb["gws"] == [2, 3, 4, 5, 6]


def test_available_chips_without_user_squad_are_set_1_only() -> None:
    chips = available_chips([16, 17, 18, 19, 20], [])
    keys = {(c["chip"], c["chip_set"]) for c in chips}
    assert keys == {("wc", 1), ("bb", 1), ("fh", 1), ("tc", 1)}
    bb = next(c for c in chips if c["chip"] == "bb")
    assert bb["gws"] == [16, 17, 18, 19]


def test_available_chips_omits_spent_set_1_and_offers_set_2() -> None:
    chips = available_chips(
        [16, 17, 18, 19, 20],
        [
            {"chip": "bb", "chip_set": 1, "status": "played"},
            {"chip": "wc", "chip_set": 1, "status": "available"},
            {"chip": "bb", "chip_set": 2, "status": "available"},
        ],
    )
    keys = {(c["chip"], c["chip_set"]) for c in chips}
    assert ("bb", 1) not in keys
    assert ("bb", 2) in keys
    assert ("wc", 1) in keys
    bb2 = next(c for c in chips if c["chip"] == "bb" and c["chip_set"] == 2)
    assert bb2["gws"] == [20]


def test_solver_options_maps_booked_enabled_keep_ban() -> None:
    available = available_chips([2, 3, 4, 5, 6], [])
    options = solver_options_from_plan(
        booked_chips={"use_wc": [4], "use_bb": [], "use_fh": [], "use_tc": []},
        enabled_chips=[{"chip": "bb", "chip_set": 1}],
        force_keep=[{"player_id": 10, "gw": 2}],
        force_ban=[{"player_id": 20, "gw": 3}],
        planning_gws=[2, 3, 4, 5, 6],
        available=available,
        horizon=5,
    )
    assert options["horizon"] == 5
    assert options["use_wc"] == [4]
    assert options["force_keep_gws"] == [[10, 2]]
    assert options["force_ban_gws"] == [[20, 3]]
    windows = options["enabled_chip_windows"]
    assert len(windows) == 1
    assert windows[0]["chip"] == "bb"
    assert 4 not in windows[0]["gws"]
    assert windows[0]["gws"] == [2, 3, 5, 6]


def test_straddle_horizon_can_enable_same_chip_twice() -> None:
    available = available_chips(
        [16, 17, 18, 19, 20],
        [
            {"chip": "bb", "chip_set": 1, "status": "available"},
            {"chip": "bb", "chip_set": 2, "status": "available"},
        ],
    )
    options = solver_options_from_plan(
        booked_chips={"use_wc": [], "use_bb": [], "use_fh": [], "use_tc": []},
        enabled_chips=[{"chip": "bb", "chip_set": 1}, {"chip": "bb", "chip_set": 2}],
        force_keep=[],
        force_ban=[],
        planning_gws=[16, 17, 18, 19, 20],
        available=available,
        horizon=5,
    )
    windows = options["enabled_chip_windows"]
    assert [w["chip_set"] for w in windows] == [1, 2]
    assert windows[0]["gws"] == [16, 17, 18, 19]
    assert windows[1]["gws"] == [20]


def test_validate_enabled_rejects_spent_and_too_many_chips() -> None:
    available = available_chips([2], [{"chip": "bb", "chip_set": 1, "status": "played"}])
    try:
        validate_enabled_chips(
            [{"chip": "bb", "chip_set": 1}],
            booked_chips={"use_wc": [], "use_bb": [], "use_fh": [], "use_tc": []},
            planning_gws=[2],
            available=available,
        )
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Available Chip" in str(exc)

    available_all = available_chips([2], [])
    try:
        validate_enabled_chips(
            [{"chip": "bb", "chip_set": 1}, {"chip": "fh", "chip_set": 1}],
            booked_chips={"use_wc": [], "use_bb": [], "use_fh": [], "use_tc": []},
            planning_gws=[2],
            available=available_all,
        )
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Enabled Chip" in str(exc)


def test_validate_rejects_enabling_chip_already_booked() -> None:
    available = available_chips([2, 3, 4, 5, 6], [])
    try:
        validate_enabled_chips(
            [{"chip": "bb", "chip_set": 1}],
            booked_chips={"use_wc": [], "use_bb": [3], "use_fh": [], "use_tc": []},
            planning_gws=[2, 3, 4, 5, 6],
            available=available,
        )
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "already a Booked Chip" in str(exc)
