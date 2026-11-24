"""Unit tests for #229 Strategic FT calibration research runner."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest

from backtesting.native_transfer_solver import native_strategic_solve
from backtesting.replay_state import Player, initial_state, state_hash
from backtesting.rolling_replay import get_strategic_replay_options
from models.scoring_matrix import Position

REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO / "docs/research/strategic-ft-calibration/runner.py"
SPEC = importlib.util.spec_from_file_location("strategic_ft_calibration_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules["strategic_ft_calibration_runner"] = runner
SPEC.loader.exec_module(runner)

PROTO230_PATH = REPO / "docs/research/strategic-ft-calibration/prototype_230.py"
PROTO_SPEC = importlib.util.spec_from_file_location("strategic_ft_calibration_proto230", PROTO230_PATH)
assert PROTO_SPEC is not None and PROTO_SPEC.loader is not None
proto230 = importlib.util.module_from_spec(PROTO_SPEC)
sys.modules["strategic_ft_calibration_proto230"] = proto230
PROTO_SPEC.loader.exec_module(proto230)

POSITIONS: tuple[Position, ...] = (
    "GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F"
)


def _base_squad() -> tuple[Player, ...]:
    return tuple(
        Player(
            player_id=pid,
            position=pos,
            club=(pid - 1) % 5 + 1,
            purchase=50,
            market=50,
            purchase_eligible=True,
        )
        for pid, pos in enumerate(POSITIONS, 1)
    )


def _synthetic_forecasts(squad: tuple[Player, ...], weeks: list[int], *, bonus_pid16: float = 5.0) -> pd.DataFrame:
    rows = []
    for p in squad:
        row: dict[str, object] = {
            "player_id": p.player_id,
            "position_id": {"GK": 1, "D": 2, "M": 3, "F": 4}[p.position],
            "club_id": p.club,
            "now_cost": p.market,
            "purchase_eligible": True,
        }
        base_pt = 4.0 if p.player_id in (1, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14) else 0.0
        xmin = 90.0 if p.player_id != 15 else 0.0
        for gw in weeks:
            row[f"{gw}_Pts"] = base_pt
            row[f"{gw}_xMins"] = xmin
        rows.append(row)
    extra: dict[str, object] = {
        "player_id": 16,
        "position_id": 4,
        "club_id": 2,
        "now_cost": 50,
        "purchase_eligible": True,
    }
    for gw in weeks:
        extra[f"{gw}_Pts"] = bonus_pid16
        extra[f"{gw}_xMins"] = 90.0
    rows.append(extra)
    return pd.DataFrame(rows)


def test_analytical_hurdles() -> None:
    base = runner.compute_ft_hurdles(2.0, 0.325, 0.5, scale_ft_by_horizon=True)
    assert base["perm_hurdle_h6"] == pytest.approx(5.15, abs=0.02)
    assert base["perm_hurdle_h10"] == pytest.approx(6.72, abs=0.02)
    assert base["gate_hurdle_lt4"] is False

    cand = runner.compute_ft_hurdles(2.0, 0.08, 0.4, scale_ft_by_horizon=False)
    assert cand["perm_hurdle_h6"] == pytest.approx(2.99, abs=0.02)
    assert cand["perm_hurdle_h10"] == pytest.approx(3.22, abs=0.02)
    assert cand["gate_hurdle_lt4"] is True


def test_wasted_ft_and_4gw_gain_and_sealed_guard() -> None:
    assert runner.compute_wasted_ft("2025-26", 5, 5, 0, None) == 1
    assert runner.compute_wasted_ft("2025-26", 5, 5, 1, None) == 0
    assert runner.compute_wasted_ft("2025-26", 5, 4, 0, None) == 0
    assert runner.compute_wasted_ft("2025-26", 15, 5, 0, None) == 0
    assert runner.compute_wasted_ft("2025-26", 16, 5, 0, None) == 1
    assert runner.compute_wasted_ft("2025-26", 5, 5, 0, "wildcard") == 0
    assert runner.compute_wasted_ft("2025-26", 5, 5, 0, "free_hit") == 0
    assert runner.compute_wasted_ft("2025-26", 38, 5, 0, None) == 0

    bought_late = Player(16, "F", 2, 50, 50, True)
    bought_chip = Player(17, "M", 3, 50, 50, True)
    actual_points = {
        (36, 15): 2, (37, 15): 1, (38, 15): 3,
        (36, 16): 6, (37, 16): 2, (38, 16): 5,
        (10, 14): 0, (10, 17): 100,
    }
    res = runner.compute_realized_4gw_transfer_gain(
        [(10, "wildcard", ((14, bought_chip),)), (36, None, ((15, bought_late),))],
        actual_points,
        total_hit_points=4,
    )
    assert res["scored_non_chip_transfers"] == 1.0
    assert res["total_4gw_transfer_gain"] == 7.0
    assert res["mean_4gw_transfer_gain"] == 7.0
    assert res["net_4gw_transfer_gain_after_hits"] == 3.0

    with pytest.raises(ValueError, match="barred"):
        runner.validate_calibration_season("2026-27")
    with pytest.raises(ValueError, match="barred"):
        runner.prepare_season_cache("2026-27")


def test_experimental_solver_baseline_parity_unscaled_hold_and_chip_waiver() -> None:
    squad = _base_squad()
    opening = initial_state("2025-26", squad)
    state = replace(opening, deadline=2, free_transfers=1, bank=10, parent_hash=state_hash(opening))
    forecasts = _synthetic_forecasts(squad, [2, 3], bonus_pid16=0.0)

    # 1. Parity with native_strategic_solve and explicit frozen legacy ADR 0065 baseline
    base_spec = runner.FTConfigSpec("baseline_adr0065", 2.0, 0.325, 0.5, baseline_mode=True, waive_chip_ft_hold=False)
    legacy_opts = runner.build_experimental_options(base_spec, 2, "2025-26")
    assert legacy_opts["ft_use_penalty"] == 0.5
    assert legacy_opts["spare_ft_hold_weight"] > 0.325  # H=2 scale < 1
    current_opts = get_strategic_replay_options(2, rules_version="2025-26")
    dec_exp, cert_exp = runner.experimental_native_solve(
        state, 2, forecasts, current_opts, baseline_mode=True, require_optimal=True
    )
    dec_ref, cert_ref = native_strategic_solve(state, 2, forecasts, current_opts)
    assert dec_exp == dec_ref
    assert cert_exp.objective == pytest.approx(cert_ref.objective, abs=1e-9)

    # 2. Unscaled hold weight (no division by true_horizon_scale) and WC waiver
    exp_spec = runner.FTConfigSpec("exp_test", 2.0, 0.15, 0.4, baseline_mode=False, waive_chip_ft_hold=True)
    opts_no_chip = runner.build_experimental_options(exp_spec, 2, "2025-26")
    assert opts_no_chip["horizon_scale"] == 1.0
    assert opts_no_chip["ft_value_list"] == {"2": 2.0, "3": 1.2, "4": 0.6, "5": 0.2}
    assert opts_no_chip["hit_hurdle"] == get_strategic_replay_options(2, rules_version="2025-26")["hit_hurdle"]

    _, cert_hold_on = runner.experimental_native_solve(
        state, 2, forecasts, opts_no_chip, baseline_mode=False, require_optimal=True
    )
    state_2ft = replace(opening, deadline=2, free_transfers=2, bank=10, parent_hash=state_hash(opening))
    _, cert_wc_waived = runner.experimental_native_solve(
        state_2ft, 2, forecasts, {**opts_no_chip, "chip_calendar": ((2, "wildcard"),)}, baseline_mode=False, require_optimal=True
    )
    _, cert_wc_zero = runner.experimental_native_solve(
        state_2ft,
        2,
        forecasts,
        {**opts_no_chip, "chip_calendar": ((2, "wildcard"),), "spare_ft_hold_weight": 0.0},
        baseline_mode=False,
        require_optimal=True,
    )
    assert cert_wc_waived.objective == pytest.approx(cert_wc_zero.objective, abs=1e-6)
    assert cert_hold_on.objective > 0.0


def test_twophase_spec_switching_and_live_h10_options() -> None:
    two = runner.FTConfigSpec(
        config_id="two_phase_test",
        v2=2.0,
        spare_ft_hold_weight=0.08,
        ft_use_penalty=0.4,
        early_gw_end=8,
        early_v2=2.0,
        early_spare_ft_hold_weight=0.15,
        early_ft_use_penalty=0.4,
    )
    assert runner.spec_for_gw(two, 1).spare_ft_hold_weight == 0.15
    assert runner.spec_for_gw(two, 8).spare_ft_hold_weight == 0.15
    assert runner.spec_for_gw(two, 9).spare_ft_hold_weight == 0.08
    assert runner.build_experimental_options(runner.spec_for_gw(two, 8), 6, "2025-26")["spare_ft_hold_weight"] == 0.15
    assert runner.build_experimental_options(runner.spec_for_gw(two, 9), 6, "2025-26")["spare_ft_hold_weight"] == 0.08

    # Live H=10 options preserve scaled frictions, unscale FT schedule, and invert 0.325 / horizon_scale cleanly
    live_specs = {s.config_id: s for s in proto230.build_live_sensitivity_configs()}
    base_live = {"horizon": 10, "decay_base": 0.85, "ft_value": 1.5}
    base_opts = proto230.build_live_h10_options(
        base_live, live_specs["baseline_adr0065"], free_transfer_bank=2
    )
    opts_015 = proto230.build_live_h10_options(
        base_live, live_specs["v2_2p0_h_0p15_u_0p4"], free_transfer_bank=2
    )
    opts_008 = proto230.build_live_h10_options(
        base_live, live_specs["v2_2p4_h_0p08_u_0p6"], free_transfer_bank=2
    )
    opts_000 = proto230.build_live_h10_options(
        base_live, live_specs["v2_3p2_h_0p00_u_0p5"], free_transfer_bank=2
    )

    assert opts_015["hit_friction"] == base_opts["hit_friction"]
    assert opts_015["gk_transfer_friction"] == base_opts["gk_transfer_friction"]
    assert opts_015["ft_value_list"] == {"2": 2.0, "3": 1.2, "4": 0.6, "5": 0.2}
    assert opts_015["spare_ft_hold_weight"] == pytest.approx(0.15, abs=1e-9)
    assert opts_008["spare_ft_hold_weight"] == pytest.approx(0.08, abs=1e-9)
    assert opts_000["spare_ft_hold_weight"] == 0.0
    assert base_opts["ft_use_penalty"] == 0.5
