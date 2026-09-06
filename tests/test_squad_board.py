"""Squad Board What-If scoring: Auto Captain, Squad xP, ITB, Rule Breach."""

from projections.squad_board import (
    SquadSlot,
    auto_captain_id,
    auto_vice_captain_id,
    hit_count,
    itb_after_transfers,
    rule_breaches,
    squad_xp,
)


def _slot(
    player_id: int,
    pos: str,
    club_id: int,
    lineup_index: int,
    xp: float,
    *,
    price: float = 4.5,
    selling_price: float | None = None,
) -> SquadSlot:
    return SquadSlot(
        player_id=player_id,
        pos=pos,
        club_id=club_id,
        lineup_index=lineup_index,
        price=price,
        selling_price=0.0 if selling_price is None else selling_price,
        gw_xp={1: xp, 2: xp / 2.0},
    )


def _legal_15(*, xp_by_id: dict[int, float] | None = None) -> list[SquadSlot]:
    layout = (
        (1, "G", 1),
        (2, "D", 2),
        (3, "D", 3),
        (4, "D", 4),
        (5, "D", 5),
        (6, "M", 6),
        (7, "M", 7),
        (8, "M", 8),
        (9, "F", 9),
        (10, "F", 10),
        (11, "F", 11),
        (12, "G", 1),
        (13, "D", 12),
        (14, "M", 13),
        (15, "M", 14),
    )
    xp_by_id = xp_by_id or {}
    return [
        _slot(pid, pos, club, pid, xp_by_id.get(pid, 2.0))
        for pid, pos, club in layout
    ]


def test_auto_captain_is_highest_xmin_weighted_xp_in_xi_not_bench() -> None:
    slots = _legal_15(xp_by_id={11: 9.0, 10: 8.0, 15: 20.0})
    assert auto_captain_id(slots, 1) == 11
    assert auto_vice_captain_id(slots, 1) == 10


def test_auto_captain_uses_that_gameweek_xp() -> None:
    slots = _legal_15(xp_by_id={11: 9.0})
    slots[5] = SquadSlot(
        player_id=6,
        pos="M",
        club_id=6,
        lineup_index=6,
        price=4.5,
        selling_price=4.5,
        gw_xp={1: 3.0, 2: 12.0},
    )
    assert auto_captain_id(slots, 1) == 11
    assert auto_captain_id(slots, 2) == 6


def test_squad_xp_sums_15_plus_extra_auto_captain() -> None:
    slots = _legal_15(xp_by_id={11: 9.0, 10: 8.0})
    # 13 players at 2.0 + 8 + 9 = 43; extra 1x C (11) = 52
    assert squad_xp(slots, 1) == 52.0


def test_squad_xp_delta_uses_auto_captain_on_both_sides() -> None:
    owned = _legal_15(xp_by_id={11: 9.0})
    what_if = _legal_15(xp_by_id={11: 9.0, 9: 7.0})
    assert squad_xp(what_if, 1) - squad_xp(owned, 1) == 5.0


def test_itb_after_same_position_replace_uses_selling_price_out_and_price_in() -> None:
    owned = _legal_15()
    owned[10] = _slot(11, "F", 11, 11, 2.0, selling_price=10.0)
    what_if = list(owned)
    what_if[10] = _slot(99, "F", 15, 11, 2.0, price=10.5, selling_price=10.5)
    assert itb_after_transfers(0.5, owned, what_if) == 0.0


def test_itb_missing_selling_price_does_not_fall_back_to_price() -> None:
    owned = _legal_15()
    owned[10] = _slot(11, "F", 11, 11, 2.0, price=10.0, selling_price=0.0)
    what_if = list(owned)
    what_if[10] = _slot(99, "F", 15, 11, 2.0, price=10.5, selling_price=10.5)
    assert itb_after_transfers(0.5, owned, what_if) == -10.0


def test_hit_count_is_transfers_beyond_free_transfer_bank() -> None:
    owned_ids = list(range(1, 16))
    what_if_ids = [99, *list(range(2, 16))]
    assert hit_count(owned_ids, what_if_ids, free_transfers=2) == 0
    what_if_ids = [97, 98, 99, *list(range(4, 16))]
    assert hit_count(owned_ids, what_if_ids, free_transfers=2) == 1


def test_rule_breach_club_cap_and_itb_and_starting_shape() -> None:
    slots = _legal_15()
    assert rule_breaches(slots, itb=0.5) == []
    stacked = _legal_15()
    for i in range(4):
        stacked[i] = _slot(stacked[i].player_id, stacked[i].pos, 1, stacked[i].lineup_index, 2.0)
    assert "club_cap" in rule_breaches(stacked, itb=0.5)
    assert "itb" in rule_breaches(slots, itb=-0.1)
    bad_xi = _legal_15()
    d4 = next(s for s in bad_xi if s.lineup_index == 4)
    d5 = next(s for s in bad_xi if s.lineup_index == 5)
    m14 = next(s for s in bad_xi if s.lineup_index == 14)
    m15 = next(s for s in bad_xi if s.lineup_index == 15)
    swapped: list[SquadSlot] = []
    for s in bad_xi:
        if s.player_id == d4.player_id:
            swapped.append(_slot(s.player_id, s.pos, s.club_id, 14, 2.0))
        elif s.player_id == d5.player_id:
            swapped.append(_slot(s.player_id, s.pos, s.club_id, 15, 2.0))
        elif s.player_id == m14.player_id:
            swapped.append(_slot(s.player_id, s.pos, s.club_id, 4, 2.0))
        elif s.player_id == m15.player_id:
            swapped.append(_slot(s.player_id, s.pos, s.club_id, 5, 2.0))
        else:
            swapped.append(s)
    assert "starting_shape" in rule_breaches(swapped, itb=0.5)
