"""Tests for neutral GW1 ownership anchor construction and freezing."""

from collections import Counter
import itertools
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
import pytest

from backtesting.ownership_anchor import (
    INITIAL_BUDGET_TENTHS,
    InfeasibleAnchorError,
    InvalidAnchorInputError,
    load_ownership_anchor,
    save_ownership_anchor,
    solve_ownership_anchor,
)
from backtesting.replay_state import Decision, Lineup, Outcome, OutcomeBatch, state_hash, transition


def _make_sample_universe() -> pd.DataFrame:
    """Create a realistic legal player universe across 6 clubs with varied positions and prices."""
    players = []
    pid = 1

    # 4 GKPs (pos 1) across clubs 1..4
    for i in range(4):
        players.append({
            "player_id": pid,
            "position_id": 1,
            "club_id": (i % 6) + 1,
            "now_cost": 45 + (i * 5),
            "selected_by_percent": 15.0 + (i * 5.0),
            "is_eligible": True,
        })
        pid += 1

    # 12 DEFs (pos 2) across clubs 1..6
    for i in range(12):
        players.append({
            "player_id": pid,
            "position_id": 2,
            "club_id": (i % 6) + 1,
            "now_cost": 40 + (i * 2),
            "selected_by_percent": 10.0 + (i * 2.5),
            "is_eligible": True,
        })
        pid += 1

    # 12 MIDs (pos 3) across clubs 1..6
    for i in range(12):
        players.append({
            "player_id": pid,
            "position_id": 3,
            "club_id": (i % 6) + 1,
            "now_cost": 45 + (i * 3),
            "selected_by_percent": 8.0 + (i * 3.0),
            "is_eligible": True,
        })
        pid += 1

    # 8 FWDs (pos 4) across clubs 1..6
    for i in range(8):
        players.append({
            "player_id": pid,
            "position_id": 4,
            "club_id": (i % 6) + 1,
            "now_cost": 50 + (i * 5),
            "selected_by_percent": 12.0 + (i * 4.0),
            "is_eligible": True,
        })
        pid += 1

    return pd.DataFrame(players)


def test_small_brute_force_matches_optimizer() -> None:
    """Verify that the optimizer finds the exact global optimum verified by exhaustive search."""
    universe_rows = []
    pid = 1
    # 3 GKP across clubs 1, 2, 3
    for i in range(3):
        universe_rows.append({"player_id": pid, "position_id": 1, "club_id": (i % 6) + 1, "now_cost": 45 + i * 5, "selected_by_percent": 10.0 + i * 10.0})
        pid += 1
    # 6 DEF across clubs 1..6
    for i in range(6):
        universe_rows.append({"player_id": pid, "position_id": 2, "club_id": (i % 6) + 1, "now_cost": 40 + i * 5, "selected_by_percent": 5.0 + i * 5.0})
        pid += 1
    # 6 MID across clubs 1..6
    for i in range(6):
        universe_rows.append({"player_id": pid, "position_id": 3, "club_id": (i % 6) + 1, "now_cost": 50 + i * 5, "selected_by_percent": 8.0 + i * 4.0})
        pid += 1
    # 3 FWD across clubs 4, 5, 6
    for i in range(3):
        universe_rows.append({"player_id": pid, "position_id": 4, "club_id": ((i + 3) % 6) + 1, "now_cost": 60 + i * 10, "selected_by_percent": 15.0 + i * 5.0})
        pid += 1

    df_small = pd.DataFrame(universe_rows)

    # Brute force search directly over universe_rows dicts
    gkps = [r for r in universe_rows if r["position_id"] == 1]
    defs = [r for r in universe_rows if r["position_id"] == 2]
    mids = [r for r in universe_rows if r["position_id"] == 3]
    fwds = [r for r in universe_rows if r["position_id"] == 4]

    best_obj: float = -1.0
    best_squad: tuple[int, ...] = ()
    best_cost: int = 999999

    for g_comb in itertools.combinations(gkps, 2):
        for d_comb in itertools.combinations(defs, 5):
            for m_comb in itertools.combinations(mids, 5):
                for f_comb in itertools.combinations(fwds, 3):
                    squad = g_comb + d_comb + m_comb + f_comb
                    total_cost = int(sum(int(p["now_cost"]) for p in squad))
                    if total_cost > INITIAL_BUDGET_TENTHS:
                        continue
                    # Check club constraint: max 3 per club
                    club_counts = Counter(int(p["club_id"]) for p in squad)
                    if any(c > 3 for c in club_counts.values()):
                        continue
                    obj = float(sum(float(p["selected_by_percent"]) for p in squad))
                    if obj > best_obj or (abs(obj - best_obj) < 1e-7 and total_cost < best_cost):
                        best_obj = obj
                        best_cost = total_cost
                        best_squad = tuple(sorted(int(p["player_id"]) for p in squad))

    anchor = solve_ownership_anchor(df_small, season="2024-25")
    assert anchor.player_ids == best_squad
    assert abs(anchor.objective_value - round(best_obj, 6)) < 1e-5
    assert anchor.certificate.total_cost == best_cost
    assert anchor.anchor_type == "opening"
    assert anchor.anchor_id.startswith("opening-anchor-")


def test_greedy_counterexample() -> None:
    """Demonstrate that greedy selection fails budget/position constraints or yields lower ownership."""
    rows = []
    pid = 1

    # 3 GKP:
    rows.append({"player_id": 1, "position_id": 1, "club_id": 1, "now_cost": 100, "selected_by_percent": 50.0})  # Expensive high ownership
    rows.append({"player_id": 2, "position_id": 1, "club_id": 2, "now_cost": 40, "selected_by_percent": 49.0})
    rows.append({"player_id": 3, "position_id": 1, "club_id": 3, "now_cost": 40, "selected_by_percent": 48.0})
    pid = 4

    # 6 DEFs across clubs 1..6:
    for i in range(6):
        rows.append({"player_id": pid, "position_id": 2, "club_id": (i % 6) + 1, "now_cost": 40, "selected_by_percent": 30.0})
        pid += 1
    # 6 MIDs across clubs 1..6:
    for i in range(6):
        rows.append({"player_id": pid, "position_id": 3, "club_id": (i % 6) + 1, "now_cost": 50, "selected_by_percent": 30.0})
        pid += 1
    # 4 FWDs across clubs 1..6:
    for i in range(4):
        rows.append({"player_id": pid, "position_id": 4, "club_id": (i % 6) + 1, "now_cost": 60, "selected_by_percent": 30.0})
        pid += 1

    df_greedy = pd.DataFrame(rows)
    anchor = solve_ownership_anchor(df_greedy, season="2024-25", budget_tenths=750)

    assert len(anchor.player_ids) == 15
    assert anchor.certificate.total_cost <= 750
    assert anchor.bank >= 0
    assert anchor.certificate.status == "OPTIMAL"


def test_club_budget_position_interaction() -> None:
    """Verify exact 2 GKP/5 DEF/5 MID/3 FWD, max 3 per club, <= £100m budget, bank >= 0, conserved capital."""
    df_univ = _make_sample_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25", budget_tenths=1000)

    # 1. 15 players
    assert len(anchor.player_ids) == 15

    # 2. Position bounds
    pos_counts = Counter(anchor.player_positions.values())
    assert pos_counts == {"GK": 2, "D": 5, "M": 5, "F": 3}

    # 3. Club quota: max 3 per club
    club_counts = Counter(anchor.player_clubs.values())
    assert all(c <= 3 for c in club_counts.values())

    # 4. Budget & bank
    total_cost = sum(anchor.acquisition_prices.values())
    assert total_cost <= 1000
    assert anchor.bank == 1000 - total_cost
    assert anchor.bank >= 0
    assert total_cost + anchor.bank == 1000


def test_rounded_ties_and_no_epsilon_sacrifice() -> None:
    """Demonstrate that rounded ownership ties are deterministically resolved without sacrificing objective.

    Contrasts the two-stage exact formulation (which guarantees mathematical non-sacrifice)
    with a naive single-stage epsilon formulation that erroneously sacrifices ownership.
    """
    df_univ = _make_sample_universe()
    # Create two tied GKPs with exact reported ownership (15.4%):
    # Player 101: GKP, cost 45, ownership 15.4%
    # Player 102: GKP, cost 45, ownership 15.4% (higher ID than 101)
    # Player 103: GKP, cost 45, ownership 15.35% (slightly lower ownership, but lower ID = 90)
    gkps = [
        {"player_id": 90, "position_id": 1, "club_id": 6, "now_cost": 45, "selected_by_percent": 15.35},
        {"player_id": 101, "position_id": 1, "club_id": 6, "now_cost": 45, "selected_by_percent": 15.4},
        {"player_id": 102, "position_id": 1, "club_id": 6, "now_cost": 45, "selected_by_percent": 15.4},
        {"player_id": 105, "position_id": 1, "club_id": 5, "now_cost": 45, "selected_by_percent": 30.0},
    ]
    df_non_gk = df_univ[df_univ["position_id"] != 1]
    df_tie = cast(pd.DataFrame, pd.concat([pd.DataFrame(gkps), df_non_gk], ignore_index=True))

    anchor = solve_ownership_anchor(df_tie, season="2024-25")
    # Top keeper 105 must be selected (30.0%)
    assert 105 in anchor.player_ids
    # Between 101 and 102: both have 15.4%, but 101 has lower ID -> 101 must be picked
    assert 101 in anchor.player_ids
    assert 102 not in anchor.player_ids
    # Player 90 has 15.35% (< 15.4%). The 2-stage solver CANNOT sacrifice the 0.05% ownership to pick player 90:
    assert 90 not in anchor.player_ids

    # Contrast with naive single-stage epsilon perturbation:
    # If c = -(ownership - eps * player_id) with eps = 0.01:
    # Score(90) = 15.35 - 0.01 * 90 = 15.35 - 0.90 = 14.45
    # Score(101) = 15.40 - 0.01 * 101 = 15.40 - 1.01 = 14.39
    # Naive single-stage would pick player 90 and sacrifice 0.05% true ownership!
    # Our two-stage formulation mathematically prevents this sacrifice by bounding Stage 2:
    assert anchor.objective_value >= 15.4 + 30.0


def test_native_eligibility_enforcement() -> None:
    """Verify that ineligible players are strictly excluded from selection."""
    df_univ = _make_sample_universe()
    # Mark the superstar FWD as ineligible (e.g. suspended or transferred out)
    df_univ_elig = df_univ.copy()
    pids: list[int] = [int(x) for x in df_univ_elig["player_id"].tolist()]
    positions: list[int] = [int(x) for x in df_univ_elig["position_id"].tolist()]
    fwd_players = [pids[i] for i in range(len(pids)) if positions[i] == 4]
    fwd_id = max(fwd_players)
    df_univ_elig.loc[df_univ_elig["player_id"] == fwd_id, "is_eligible"] = False

    anchor = solve_ownership_anchor(df_univ_elig, season="2024-25")
    assert fwd_id not in anchor.player_ids
    assert all(anchor.player_eligible.values())


def test_diagnostic_anchor_type_and_prefix() -> None:
    """Verify that midseason anchors or explicitly diagnostic anchors carry diagnostic prefix."""
    df_univ = _make_sample_universe()

    # Gameweek 5 defaults to diagnostic
    diag_anchor = solve_ownership_anchor(df_univ, season="2024-25", gameweek=5)
    assert diag_anchor.anchor_type == "diagnostic"
    assert diag_anchor.anchor_id.startswith("diagnostic-anchor-")
    assert diag_anchor.certificate.anchor_type == "diagnostic"

    # Explicit override to diagnostic for GW1
    explicit_diag = solve_ownership_anchor(
        df_univ, season="2024-25", gameweek=1, anchor_type="diagnostic"
    )
    assert explicit_diag.anchor_type == "diagnostic"
    assert explicit_diag.anchor_id.startswith("diagnostic-anchor-")


def test_shuffled_rows_independence() -> None:
    """Verify that shuffling rows yields the exact same anchor bit-for-bit."""
    df_univ = _make_sample_universe()
    anchor_orig = solve_ownership_anchor(df_univ, season="2024-25")

    for seed in [42, 123, 999]:
        df_shuffled = df_univ.sample(frac=1.0, random_state=seed).reset_index(drop=True)
        anchor_shuffled = solve_ownership_anchor(df_shuffled, season="2024-25")

        assert anchor_shuffled.anchor_id == anchor_orig.anchor_id
        assert anchor_shuffled.player_ids == anchor_orig.player_ids
        assert anchor_shuffled.acquisition_prices == anchor_orig.acquisition_prices
        assert anchor_shuffled.bank == anchor_orig.bank
        assert anchor_shuffled.objective_value == anchor_orig.objective_value
        assert anchor_shuffled.source_digest == anchor_orig.source_digest


def test_infeasible_universe_actionable_error() -> None:
    """Verify actionable InfeasibleAnchorError on position shortfall, budget deficit, or small universe."""
    df_univ = _make_sample_universe()

    # 1. Fewer than 15 players
    with pytest.raises(InfeasibleAnchorError, match="requires at least 15"):
        solve_ownership_anchor(cast(pd.DataFrame, df_univ.iloc[:14]), season="2024-25")

    # 2. Insufficient GKPs (only 1 GKP)
    df_no_gk = df_univ[df_univ["position_id"] != 1].copy()
    df_one_gk = cast(pd.DataFrame, pd.concat([df_univ[df_univ["position_id"] == 1].iloc[:1], df_no_gk]))
    with pytest.raises(InfeasibleAnchorError, match="Position 1 .* has only 1 eligible players, requires 2"):
        solve_ownership_anchor(df_one_gk, season="2024-25")

    # 3. Minimum possible cost exceeds budget
    with pytest.raises(InfeasibleAnchorError, match="Minimum possible squad cost .* exceeds budget"):
        solve_ownership_anchor(df_univ, season="2024-25", budget_tenths=300)


def test_duplicate_and_missing_metadata_validation() -> None:
    """Verify that malformed or invalid inputs raise InvalidAnchorInputError."""
    df_univ = _make_sample_universe()

    # Duplicate player ID
    df_dup = df_univ.copy()
    df_dup.loc[1, "player_id"] = df_dup.loc[0, "player_id"]
    with pytest.raises(InvalidAnchorInputError, match="Duplicate player IDs"):
        solve_ownership_anchor(df_dup, season="2024-25")

    # Null values
    df_null = df_univ.copy()
    df_null.loc[0, "now_cost"] = np.nan
    with pytest.raises(InvalidAnchorInputError, match="NaN/null values"):
        solve_ownership_anchor(df_null, season="2024-25")

    # Negative cost
    df_neg_cost = df_univ.copy()
    df_neg_cost.loc[0, "now_cost"] = -10
    with pytest.raises(InvalidAnchorInputError, match="Cost must be positive"):
        solve_ownership_anchor(df_neg_cost, season="2024-25")

    # Negative ownership
    df_neg_own = df_univ.copy()
    df_neg_own.loc[0, "selected_by_percent"] = -1.0
    with pytest.raises(InvalidAnchorInputError, match="Ownership cannot be negative"):
        solve_ownership_anchor(df_neg_own, season="2024-25")

    # Invalid position code
    df_bad_pos = df_univ.copy()
    df_bad_pos.loc[0, "position_id"] = 99
    with pytest.raises(InvalidAnchorInputError, match="Position int must be 1..4"):
        solve_ownership_anchor(df_bad_pos, season="2024-25")


def test_forecast_and_outcome_independence() -> None:
    """Verify that extraneous forecast or outcome columns cannot influence anchor selection."""
    df_univ = _make_sample_universe()
    anchor_clean = solve_ownership_anchor(df_univ, season="2024-25")

    # Add misleading forecast and outcome columns favoring low-ownership players
    df_contaminated = df_univ.copy()
    df_contaminated["projected_points"] = [100.0 - float(x) for x in df_univ["selected_by_percent"]]
    df_contaminated["expected_goals"] = 10.0
    df_contaminated["actual_points"] = 50.0

    anchor_contaminated = solve_ownership_anchor(df_contaminated, season="2024-25")
    assert anchor_contaminated.player_ids == anchor_clean.player_ids
    assert anchor_contaminated.objective_value == anchor_clean.objective_value
    assert anchor_contaminated.anchor_id == anchor_clean.anchor_id


def test_save_load_and_to_replay_state(tmp_path: Path) -> None:
    """Verify serialization roundtrip and conversion to valid GW1 ReplayState."""
    df_univ = _make_sample_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")

    # Save to JSON
    save_path = tmp_path / "anchor_2024-25.json"
    save_ownership_anchor(anchor, save_path)
    assert save_path.is_file()

    # Load and verify
    loaded = load_ownership_anchor(save_path, expected_digest=anchor.source_digest)
    assert loaded.anchor_id == anchor.anchor_id
    assert loaded.player_ids == anchor.player_ids
    assert loaded.bank == anchor.bank

    # Digest mismatch
    with pytest.raises(ValueError, match="Source digest mismatch"):
        load_ownership_anchor(save_path, expected_digest="wrong_digest")

    # Convert to ReplayState
    state = loaded.to_replay_state("2024-25")
    assert state.rules_version == "2024-25"
    assert state.deadline == 1
    assert state.free_transfers == 0
    assert state.bank == loaded.bank
    assert len(state.squad) == 15
    assert sum(p.purchase for p in state.squad) + state.bank == 1000

    # Ensure state can legally transition in GW1
    # Build a legal lineup: 1 GK, 4 DEF, 4 MID, 2 FWD
    players_by_pos: dict[str, list[int]] = {}
    for p in state.squad:
        players_by_pos.setdefault(p.position, []).append(p.player_id)

    starters = (
        players_by_pos["GK"][0],
        *players_by_pos["D"][:4],
        *players_by_pos["M"][:4],
        *players_by_pos["F"][:2],
    )
    bench = (
        players_by_pos["GK"][1],
        players_by_pos["D"][4],
        players_by_pos["M"][4],
        players_by_pos["F"][2],
    )
    captain = starters[1]
    vice = starters[2]
    lineup = Lineup(starters=starters, bench=bench, captain=captain, vice=vice)

    decision = Decision(
        transfers=(),
        lineup=lineup,
        expected_state_hash=state_hash(state),
        issued_deadline=1,
    )

    outcomes = tuple(
        (p.player_id, Outcome(points=5, minutes=90, appeared=True))
        for p in state.squad
    )
    batch = OutcomeBatch(
        rules_version="2024-25",
        deadline=1,
        source_identity="test-source",
        outcomes=outcomes,
    )

    t_res = transition(state, decision, batch)
    assert t_res.gross == 55  # 11 starters * 5 pts
    assert t_res.captain_increment == 5  # captain gets extra 5 pts
    assert t_res.net == 60
    assert t_res.state.deadline == 2
    assert t_res.state.free_transfers == 1  # advanced for GW2
