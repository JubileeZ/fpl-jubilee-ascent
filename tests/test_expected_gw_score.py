"""Expected GW Score: probabilistic Official-style GW points minus Hits."""

from projections.expected_gw_score import PlayerGw, auto_captain_alternatives, expected_gw_score


def _xi() -> list[PlayerGw]:
    # Legal 1-4-4-2
    players: list[PlayerGw] = [PlayerGw(1, 1, xp=2.0, p_appear=1.0)]
    players.extend(PlayerGw(10 + i, 2, xp=2.0, p_appear=1.0) for i in range(4))
    players.extend(PlayerGw(20 + i, 3, xp=2.0, p_appear=1.0) for i in range(4))
    players.extend(PlayerGw(30 + i, 4, xp=2.0, p_appear=1.0) for i in range(2))
    return players


def test_expected_gw_score_is_xi_plus_captain_minus_hits() -> None:
    players = {p.player_id: p for p in _xi()}
    lineup = tuple(players)
    score = expected_gw_score(
        lineup_ids=lineup,
        bench_ids=(),
        captain_id=1,
        vice_id=10,
        players=players,
        hits=1,
        hit_cost=4.0,
    )
    # 11 × 2 + extra 2 − 4
    assert score == 20.0


def test_expected_gw_score_autosubs_dnp_starter_from_bench() -> None:
    players = {p.player_id: p for p in _xi()}
    players[1] = PlayerGw(1, 1, xp=6.0, p_appear=0.0)
    bench_gk = PlayerGw(2, 1, xp=4.0, p_appear=1.0)
    players[2] = bench_gk
    score = expected_gw_score(
        lineup_ids=tuple(p.player_id for p in _xi()),
        bench_ids=(2,),
        captain_id=10,
        vice_id=11,
        players=players,
        hits=0,
    )
    # GK replaced: 10 outfield × 2 + bench GK 4 + captain extra 2
    assert score == 26.0


def test_expected_gw_score_chains_captain_to_vice_when_captain_dnps() -> None:
    players = {p.player_id: p for p in _xi()}
    players[1] = PlayerGw(1, 1, xp=8.0, p_appear=0.0)
    players[2] = PlayerGw(2, 1, xp=3.0, p_appear=1.0)
    score = expected_gw_score(
        lineup_ids=tuple(p.player_id for p in _xi()),
        bench_ids=(2,),
        captain_id=1,
        vice_id=10,
        players=players,
        hits=0,
    )
    # XI: bench GK 3 + 10 × 2 = 23; C DNP so VC extra 2
    assert score == 25.0


def test_expected_gw_score_bench_boost_includes_appearing_bench() -> None:
    players = {p.player_id: p for p in _xi()}
    players[99] = PlayerGw(99, 4, xp=5.0, p_appear=1.0)
    score = expected_gw_score(
        lineup_ids=tuple(p.player_id for p in _xi()),
        bench_ids=(99,),
        captain_id=1,
        vice_id=10,
        players=players,
        hits=0,
        chip="bb",
    )
    # XI 22 + C extra 2 + bench 5
    assert score == 29.0


def test_expected_gw_score_triple_captain_is_three_times_when_captain_plays() -> None:
    players = {p.player_id: p for p in _xi()}
    score = expected_gw_score(
        lineup_ids=tuple(players),
        bench_ids=(),
        captain_id=1,
        vice_id=10,
        players=players,
        hits=0,
        chip="tc",
    )
    # XI 22 + extra 4 (3× captain)
    assert score == 26.0


def test_auto_captain_alternatives_are_top_xi_xp_without_ownership() -> None:
    players = {p.player_id: p for p in _xi()}
    players[30] = PlayerGw(30, 4, xp=9.0, p_appear=1.0)
    players[31] = PlayerGw(31, 4, xp=8.0, p_appear=1.0)
    players[20] = PlayerGw(20, 3, xp=7.0, p_appear=1.0)
    alt = auto_captain_alternatives(tuple(players), players, next_best=2)
    assert alt["auto_captain_id"] == 30
    assert alt["auto_vice_id"] == 31
    assert [row["id"] for row in alt["next_best"]] == [20, 1]
    assert "ownership" not in alt["next_best"][0]
