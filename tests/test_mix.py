from projections.mix import (
    apply_mix_letter,
    mix_bundle,
    mix_comparable,
    move_mix_member,
    remove_mix_member,
)


def test_mix_bundle_sums_price_and_per_gw_xp() -> None:
    eze = {
        "price": 7.5,
        "projections": {"gw2": {"total_xp": 4.0}, "gw3": {"total_xp": 5.0}},
    }
    oreilly = {
        "price": 5.0,
        "projections": {"gw2": {"total_xp": 3.5}, "gw3": {"total_xp": 2.0}},
    }
    bundle = mix_bundle([eze, oreilly], [2, 3])
    assert bundle["price"] == 12.5
    assert bundle["per_gw"] == [7.5, 7.0]
    assert bundle["total"] == 14.5
    assert mix_comparable([eze, oreilly], [{}, {}]) is True
    assert mix_comparable([eze, oreilly], [{}]) is False


def test_apply_mix_letter_adds_unowned_player_to_mix_a() -> None:
    mix_a, mix_b, reason = apply_mix_letter([], [], 14, "a")
    assert mix_a == [14]
    assert mix_b == []
    assert reason is None


def test_apply_mix_letter_removes_mix_member_on_same_side() -> None:
    mix_a, mix_b, reason = apply_mix_letter([14], [], 14, "a")
    assert mix_a == []
    assert mix_b == []
    assert reason is None


def test_apply_mix_letter_moves_mix_member_to_the_other_mix() -> None:
    mix_a, mix_b, reason = apply_mix_letter([14], [], 14, "b")
    assert mix_a == []
    assert mix_b == [14]
    assert reason is None


def test_apply_mix_letter_leaves_mixes_unchanged_when_destination_is_full() -> None:
    full_a = [1, 2, 3, 4, 5]
    mix_a, mix_b, reason = apply_mix_letter(full_a, [14], 14, "a")
    assert mix_a == [1, 2, 3, 4, 5]
    assert mix_b == [14]
    assert reason == "Mix A is full (5)."


def test_apply_mix_letter_does_not_add_when_mix_is_full() -> None:
    mix_a, mix_b, reason = apply_mix_letter([1, 2, 3, 4, 5], [], 99, "a")
    assert mix_a == [1, 2, 3, 4, 5]
    assert mix_b == []
    assert reason == "Mix A is full (5)."


def test_remove_mix_member_drops_player_from_either_mix() -> None:
    mix_a, mix_b, reason = remove_mix_member([14, 22], [7], 14)
    assert mix_a == [22]
    assert mix_b == [7]
    assert reason is None


def test_move_mix_member_is_noop_on_same_mix() -> None:
    mix_a, mix_b, reason = move_mix_member([14, 22], [7], 14, "a")
    assert mix_a == [14, 22]
    assert mix_b == [7]
    assert reason is None


def test_move_mix_member_sends_player_to_the_other_mix() -> None:
    mix_a, mix_b, reason = move_mix_member([14, 22], [7], 14, "b")
    assert mix_a == [22]
    assert mix_b == [7, 14]
    assert reason is None


def test_move_mix_member_leaves_source_when_destination_is_full() -> None:
    mix_a, mix_b, reason = move_mix_member([14], [1, 2, 3, 4, 5], 14, "b")
    assert mix_a == [14]
    assert mix_b == [1, 2, 3, 4, 5]
    assert reason == "Mix B is full (5)."
