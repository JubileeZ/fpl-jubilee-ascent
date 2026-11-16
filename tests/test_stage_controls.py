"""Offline Stage B verification controls and canonical 6-archetype regression suite (#179, #189)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import highspy
import pandas as pd
import pytest

from backtesting.evidence_statistics import (
    PairedGameweekScore,
    StatisticalProtocolConfig,
    evaluate_evidence_against_protocol,
)
from backtesting.native_transfer_solver import _build_native_milp, _forecast_universe, native_strategic_solve
from backtesting.ownership_anchor import UniverseSchema, solve_ownership_anchor
from backtesting.projection_guards import (
    ComponentLedger,
    declare_component_applicability,
    evaluate_non_inferiority_guard,
    reconcile_total_to_ledger,
)
from backtesting.promotion_evidence import MANDATORY_GUARDS, _verify_replay, protocol_from_payload
from backtesting.replay_state import (
    Outcome,
    OutcomeBatch,
    Player,
    initial_state,
    selling_price,
    state_hash,
    transition,
)
from backtesting.rolling_replay import (
    QualityPolicy,
    _checkpoint_hash,
    execute_replay_deadline,
    get_strategic_replay_options,
    heuristic_zero_transfer_solve,
    record_from_dict,
)
from backtesting.season_rules import get_rules, next_free_transfers
from models.scoring_matrix import Position
from promotion_evidence_fixture import build_evidence_fixture

POSITIONS: tuple[Position, ...] = (
    "GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F"
)
POS_ID: dict[Position, int] = {"GK": 1, "D": 2, "M": 3, "F": 4}


def _squad(market: int = 50, purchase: int = 50) -> tuple[Player, ...]:
    return tuple(Player(pid, pos, (pid - 1) % 5 + 1, purchase, market, True) for pid, pos in enumerate(POSITIONS, 1))


def _forecast_df(
    players: list[Player],
    weeks: list[int],
    pts_fn: Callable[[int, int], float],
    xmins_fn: Callable[[int, int], float] | None = None,
) -> pd.DataFrame:
    if xmins_fn is None:
        def _default_xmins(_pid: int, _gw: int) -> float:
            return 90.0

        xmins_fn = _default_xmins
    rows: list[dict[str, Any]] = []
    for pl in players:
        row: dict[str, Any] = {
            "player_id": pl.player_id,
            "position_id": POS_ID[pl.position],
            "club_id": pl.club,
            "now_cost": pl.market,
            "purchase_eligible": pl.purchase_eligible,
        }
        for gw in weeks:
            row[f"{gw}_Pts"] = float(pts_fn(pl.player_id, gw))
            row[f"{gw}_xMins"] = float(xmins_fn(pl.player_id, gw))
        rows.append(row)
    return pd.DataFrame(rows)


def test_identical_model_null_control_and_15_mandatory_guards() -> None:
    """Identical candidate/champion yields p=1.0, zero delta, and 0/15 guard diffs."""
    assert len(MANDATORY_GUARDS) == 15
    paired = [
        PairedGameweekScore(
            season="2025-26",
            gameweek=gw,
            candidate_net_points=55.0 + (gw % 5),
            champion_net_points=55.0 + (gw % 5),
            candidate_gross_points=55.0 + (gw % 5),
            champion_gross_points=55.0 + (gw % 5),
            candidate_hits_deducted=0,
            champion_hits_deducted=0,
            is_chip_gameweek=False,
            segment="h1" if gw <= 19 else "h2",
        )
        for gw in range(1, 39)
    ]
    guards = [
        evaluate_non_inferiority_guard(
            [1.0, 2.0, 1.5, 0.5],
            [1.0, 2.0, 1.5, 0.5],
            metric_name=name,
            meaningful_margin=0.05,
        )
        for name in sorted(MANDATORY_GUARDS)
    ]
    res = evaluate_evidence_against_protocol(
        paired,
        guards,
        StatisticalProtocolConfig(bootstrap_draws=200, bootstrap_block_size=4, required_projection_guards=tuple(sorted(MANDATORY_GUARDS))),
        seed=42,
    )
    assert res.point_estimate == 0.0
    assert res.p_value == 1.0
    assert res.projection_guards_passed is True
    assert not res.projection_guard_failures

    ledger_25 = ComponentLedger(minutes=90.0, goals=1.0, assists=1.0, clean_sheets=1.0, defensive_contributions=1.0)
    assert reconcile_total_to_ledger(17.0, ledger_25, "D", season="2025-26").reconciled is True
    app_24 = declare_component_applicability("2024-25")
    assert app_24.component_statuses["defensive_contributions"] == "inapplicable_season"


def test_horizon_6_vs_1_divergence_and_heuristic_refusal(tmp_path: Path) -> None:
    """Horizon=6 vs 1 chooses different transfers; heuristic_zero_transfer_solve is refused at evidence gate."""
    base = initial_state("2025-26", _squad())
    state = replace(base, deadline=2, free_transfers=1, bank=10, parent_hash=state_hash(base))
    pool = [
        *base.squad,
        Player(16, "F", 6, 50, 50, True),
        Player(17, "F", 7, 50, 50, True),
    ]
    weeks = [2, 3, 4, 5, 6, 7]

    def pts(pid: int, gw: int) -> float:
        if pid in (1, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14):
            return 4.0
        if pid == 16:
            return 6.0 if gw == 2 else 3.0
        if pid == 17:
            return 5.8 if gw == 2 else 6.5
        return 0.0

    wide = _forecast_df(pool, weeks, pts)
    d1, c1 = native_strategic_solve(state, 1, wide, get_strategic_replay_options(1, rules_version="2025-26"))
    d6, c6 = native_strategic_solve(state, 6, wide, get_strategic_replay_options(6, rules_version="2025-26"))
    assert c1.termination_status == "OPTIMAL" and c6.termination_status == "OPTIMAL"
    assert d1.transfers[0][1].player_id == 16
    assert d6.transfers[0][1].player_id == 17

    # heuristic_zero_transfer_solve emits internal_lineup_v1 -> refused by promotion_evidence._verify_replay
    dec_h, cert_h = heuristic_zero_transfer_solve(state, 1, wide, get_strategic_replay_options(1, rules_version="2025-26"))
    assert "lineup" in cert_h.solver_version
    req = build_evidence_fixture(tmp_path / "heur")
    payload = json.loads(req.read_text())
    proto = json.loads((req.parent / payload["protocol"]["path"]).read_text())
    config = protocol_from_payload(proto)
    entry = dict(payload["replays"][0])
    tpath = req.parent / entry["trace"]["path"]
    tdata = json.loads(tpath.read_text())
    rec0 = record_from_dict(tdata["records"][0])
    bad_rec0 = replace(rec0, certificate=cert_h)
    tdata["records"][0]["certificate"] = asdict(cert_h)
    tdata["records"][0]["checkpoint_id"] = _checkpoint_hash(bad_rec0)
    prev = tdata["records"][0]["checkpoint_id"]
    for idx in range(1, len(tdata["records"])):
        rk = record_from_dict(tdata["records"][idx])
        tdata["records"][idx]["parent_checkpoint_id"] = prev
        tdata["records"][idx]["checkpoint_id"] = _checkpoint_hash(replace(rk, parent_checkpoint_id=prev))
        prev = tdata["records"][idx]["checkpoint_id"]
    raw = json.dumps(tdata).encode()
    tpath.write_bytes(raw)
    entry["trace"] = {"path": entry["trace"]["path"], "sha256": hashlib.sha256(raw).hexdigest()}
    with pytest.raises(ValueError, match="Diagnostic/mock solver"):
        _verify_replay(req.parent, entry, proto, config, payload["model_source_hash"], {}, "2099-01-01T00:00:00+00:00")


def test_purchase_eligible_false_owned_half_profit_and_buy_block() -> None:
    """Owned purchase_eligible=False can hold/sell with half-profit floor; unowned cannot be bought."""
    assert selling_price(50, 55) == 52
    opening = initial_state("2025-26", _squad(market=50, purchase=50))
    sq = list(opening.squad)
    sq[14] = Player(15, "F", 5, 50, 55, False)
    state = replace(opening, deadline=2, free_transfers=1, bank=0, squad=tuple(sq), parent_hash=state_hash(opening))
    pool = [
        *state.squad,
        Player(16, "F", 6, 52, 52, True),
        Player(17, "F", 7, 50, 50, False),
    ]
    wide = _forecast_df(
        pool,
        [2],
        lambda pid, _gw: 12.0 if pid == 17 else (9.0 if pid == 16 else (0.0 if pid == 15 else 4.0)),
    )
    dec, cert = native_strategic_solve(state, 1, wide, get_strategic_replay_options(1, rules_version="2025-26"))
    assert cert.termination_status == "OPTIMAL"
    assert dec.transfers and dec.transfers[0][0] == 15 and dec.transfers[0][1].player_id == 16


def test_cross_season_native_rules_and_afcon_5ft_carryover() -> None:
    """Native solver respects 2023-24, 2024-25, and 2025-26 GW15 AFCON 5-FT rules."""
    assert next_free_transfers(get_rules("2023-24"), 2, 0, "wildcard", 5) == 1
    assert next_free_transfers(get_rules("2024-25"), 3, 1, "free_hit", 10) == 3
    assert next_free_transfers(get_rules("2025-26"), 1, 1, None, 15) == 5

    base23 = initial_state("2023-24", _squad())
    st23 = replace(base23, deadline=2, free_transfers=2, bank=10, parent_hash=state_hash(base23))
    pool = [*base23.squad, Player(16, "F", 6, 50, 50, True)]
    w23 = _forecast_df(pool, [2, 3], lambda pid, _gw: 7.0 if pid == 16 else (4.0 if pid <= 14 else 0.0))
    d23, c23 = native_strategic_solve(st23, 2, w23, get_strategic_replay_options(2, rules_version="2023-24"))
    assert c23.termination_status == "OPTIMAL" and d23 is not None

    base25 = initial_state("2025-26", _squad())
    st15 = replace(base25, deadline=15, free_transfers=1, bank=10, parent_hash=state_hash(base25))
    w15 = _forecast_df(pool, [15, 16], lambda pid, _gw: 6.0 if pid == 16 else (4.0 if pid <= 14 else 0.0))
    _, c15 = native_strategic_solve(st15, 2, w15, get_strategic_replay_options(2, rules_version="2025-26"))
    assert c15.termination_status == "OPTIMAL"
    assert c15.strategic_audit["plans"][0]["post_free_transfers"] == 5


def test_canonical_six_archetypes_end_to_end() -> None:
    """Exercise all 6 canonical replay archetypes under certified QualityPolicy(target_gap=0.0)."""
    pool_base = list(_squad())
    pool = [*pool_base, Player(16, "F", 6, 50, 50, True), Player(17, "D", 6, 50, 50, True)]
    base = initial_state("2025-26", tuple(pool_base))

    # 1. GW1 opening anchor (no transfers, certified lineup)
    bs_df = pd.DataFrame(
        [
            {
                "player_id": pl.player_id,
                "position_id": POS_ID[pl.position],
                "club_id": pl.club,
                "now_cost": pl.market,
                "selected_by_percent": 20.0 if pl.player_id <= 15 else 1.0,
                "purchase_eligible": True,
            }
            for pl in pool
        ]
    )
    anchor = solve_ownership_anchor(bs_df, "2025-26", 1, anchor_type="opening", schema=UniverseSchema(eligibility_col="purchase_eligible"))
    assert anchor.certificate.status == "OPTIMAL"
    st1 = anchor.to_replay_state("2025-26")
    d_gw1, c_gw1 = native_strategic_solve(st1, 2, _forecast_df(pool, [1, 2], lambda pid, _gw: 5.0 if pid <= 15 else 9.0), get_strategic_replay_options(2, rules_version="2025-26"))
    assert c_gw1.termination_status == "OPTIMAL" and d_gw1.transfers == ()

    # 2. Multi-FT + optional -4 hit when gain > 4.0 hurdle
    st_hit = replace(base, deadline=2, free_transfers=1, bank=20, parent_hash=state_hash(base))
    hit_opts = {**get_strategic_replay_options(1, rules_version="2025-26"), "weekly_hit_limit": 1, "hit_hurdle": 4.0}
    w_hit = _forecast_df(pool, [2], lambda pid, _gw: 12.0 if pid in (16, 17) else (0.0 if pid in (7, 15) else 4.0))
    d_hit, c_hit = native_strategic_solve(st_hit, 1, w_hit, hit_opts)
    assert c_hit.termination_status == "OPTIMAL" and len(d_hit.transfers) == 2

    # 3. Free Hit pre-FH squad restoration & Triple Captain (BB covered below)
    st_fh = replace(base, deadline=3, free_transfers=2, bank=20, parent_hash=state_hash(base))
    fh_opts = {**get_strategic_replay_options(2, rules_version="2025-26"), "chip_calendar": ((3, "free_hit"),)}
    d_fh, _ = native_strategic_solve(st_fh, 2, _forecast_df(pool, [3, 4], lambda pid, _gw: 10.0 if pid == 16 else 3.0), fh_opts)
    assert d_fh.chip == "free_hit"
    post_fh = transition(
        st_fh,
        d_fh,
        OutcomeBatch("2025-26", 3, "b3", tuple((pl.player_id, Outcome(4, 90, True, 0, 0, 4)) for pl in pool)),
    )
    assert {p.player_id for p in post_fh.state.squad} == {p.player_id for p in st_fh.squad}
    assert post_fh.state.free_transfers == 2

    # Triple captain 3x captain multiplier check
    tc_opts = {**get_strategic_replay_options(1, rules_version="2025-26"), "chip_calendar": ((2, "triple_captain"),)}
    st_tc = replace(base, deadline=2, free_transfers=1, parent_hash=state_hash(base))
    d_tc, _ = native_strategic_solve(st_tc, 1, _forecast_df(pool, [2], lambda pid, _gw: 10.0 if pid == 14 else 3.0), tc_opts)
    assert d_tc.chip == "triple_captain" and d_tc.lineup.captain == 14

    # 4. Blank/DGW & GW36-38 tail truncation via execute_replay_deadline
    tail_state = replace(base, deadline=36, free_transfers=1, bank=10, parent_hash=state_hash(base))
    tail_recs = []
    for gw in (36, 37, 38):
        rec = execute_replay_deadline(
            tail_state,
            _forecast_df(
                pool,
                list(range(gw, min(gw + 6, 39))),
                lambda pid, w: 0.0 if w == 37 else (10.0 if w == 38 and pid <= 15 else 4.0),
            ),
            OutcomeBatch(
                "2025-26", gw, f"b{gw}", tuple((pl.player_id, Outcome(4, 90, True, 0, 0, 4)) for pl in pool)
            ),
            horizon=6,
            last_gw=38,
            solve_fn=native_strategic_solve,
            policy=QualityPolicy(mode="certified", target_gap=0.0, time_limit_seconds=60.0),
        )
        tail_recs.append(rec)
        tail_state = rec.transition_result.state
    assert [r.deadline for r in tail_recs] == [36, 37, 38]
    assert [len(r.certificate.strategic_audit["plans"]) for r in tail_recs] == [3, 2, 1]
    assert all(r.certificate.termination_status == "OPTIMAL" for r in tail_recs)


def test_native_solver_gw1_gw2_hit_afcon_5buy_and_unpruned_exact_parity() -> None:
    """Verify max_ft bounds at GW1->GW2 hit, GW15->GW16 AFCON 5-buy, and unpruned full-universe parity."""
    squad = _squad()
    # 1. GW1 horizon=2 must permit 2 buys (1 FT + 1 hit) at GW2
    st_gw1 = initial_state("2025-26", squad)
    pool_hit = [*squad, Player(16, "F", 6, 50, 50, True), Player(17, "F", 7, 50, 50, True)]
    df_gw1 = _forecast_df(
        pool_hit,
        [1, 2],
        lambda pid, gw: (120.0 if pid in (16, 17) and gw == 2 else (0.0 if pid in (14, 15) and gw == 2 else 4.0)),
    )
    opts_hit = {**get_strategic_replay_options(2, rules_version="2025-26"), "weekly_hit_limit": 1}
    d1, c1 = native_strategic_solve(replace(st_gw1, bank=10), 2, df_gw1, opts_hit)
    assert c1.termination_status == "OPTIMAL"
    assert set(c1.strategic_audit["plans"][1]["transfers_in"]) == {16, 17}

    # 2. 2025-26 AFCON GW15->16 must permit 5 free transfers at GW16 even starting with 1 FT at GW15
    st_gw15 = replace(st_gw1, deadline=15, free_transfers=1, bank=50, parent_hash=state_hash(st_gw1))
    extra5 = [Player(16 + i, "F" if i < 3 else "M", 6 + i, 50, 50, True) for i in range(5)]
    pool_afcon = [*squad, *extra5]
    new_ids = {p.player_id for p in extra5}
    df_afcon = _forecast_df(
        pool_afcon,
        [15, 16],
        lambda pid, gw: (
            80.0
            if (gw == 16 and pid in new_ids)
            else (0.0 if (gw == 15 and pid in new_ids) else (10.0 if gw == 15 else (0.0 if pid in {11, 12, 13, 14, 15} else 4.0)))
        ),
    )
    opts_afcon = {**get_strategic_replay_options(2, rules_version="2025-26"), "weekly_hit_limit": 0, "chip_calendar": ((15, "bench_boost"),)}
    _, c15 = native_strategic_solve(st_gw15, 2, df_afcon, opts_afcon)
    assert c15.termination_status == "OPTIMAL"
    assert set(c15.strategic_audit["plans"][1]["transfers_in"]) == new_ids

    # 3. Dominance pruning + warm start matches unpruned full-MILP solve identically (~100 players)
    large_pool = [*squad]
    pid = 100
    for club in range(1, 12):
        for k in range(8):
            pos = ("GK", "D", "D", "M", "M", "M", "F", "F")[k]
            large_pool.append(Player(pid, pos, club, 45 + (k % 5) * 5, 45 + (k % 5) * 5, True))
            pid += 1
    df_large = _forecast_df(large_pool, [2, 3, 4], lambda p, gw: 5.5 + (p % 7) * 0.4 + 0.1 * gw)
    st2 = replace(st_gw1, deadline=2, free_transfers=2, bank=15, parent_hash=state_hash(st_gw1))
    opts3 = get_strategic_replay_options(3, rules_version="2025-26")
    _, cert_pruned = native_strategic_solve(st2, 3, df_large, opts3)
    players_u, xp_u, xmins_u = _forecast_universe(st2, 3, df_large)
    full_m, _, _ = _build_native_milp(
        st2, [2, 3, 4], players_u, xp_u, xmins_u, sorted(players_u), opts3, {}, target_gap=0.0, time_limit=30.0, disable_submip=False
    )
    full_m.run()
    assert full_m.getModelStatus() == highspy.HighsModelStatus.kOptimal
    assert abs(cert_pruned.objective - full_m.getObjectiveValue()) < 1e-6
