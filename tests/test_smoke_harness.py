import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".agents" / "skills" / "explore-candidate"))

from smoke import InertPrototypeError, check_inert_prototype, max_playable_pool_shift  # noqa: E402
from backtesting.walkforward import WalkforwardResult  # noqa: E402


def _make_result(name: str, df: pd.DataFrame) -> WalkforwardResult:
    return WalkforwardResult(
        model_name=name,
        data_dir=Path("data/archive/2025-26"),
        start_gw=1,
        end_gw=2,
        metrics={},
        df_eval=df,
        snapshot_ids={},
        snapshot_backed=False,
    )


def test_inert_prototype_raises_on_zero_active_gameweeks() -> None:
    df_ref = pd.DataFrame(
        {
            "gameweek": [1, 1, 2, 2],
            "player_id": [1, 2, 1, 2],
            "projected_points": [4.0, 1.5, 5.0, 1.0],
            "actual_minutes": [90.0, 0.0, 85.0, 10.0],
        }
    )
    df_cand = df_ref.copy()

    ref = _make_result("champ", df_ref)
    cand = _make_result("cand_noop", df_cand)

    with pytest.raises(InertPrototypeError, match="zero active gameweeks"):
        check_inert_prototype("cand_noop", ref, cand, combined_delta=0.0)


def test_inert_prototype_raises_on_unplayable_bench_fodder_only() -> None:
    df_ref = pd.DataFrame(
        {
            "gameweek": [1, 1, 2, 2],
            "player_id": [1, 2, 1, 2],
            "projected_points": [4.0, 0.2, 5.0, 0.3],
            "actual_minutes": [90.0, 0.0, 85.0, 0.0],
        }
    )
    df_cand = df_ref.copy()
    # Player 2 is unplayable (champ_xp < 2.0 and mins < 30).
    # Perturb player 2 by 0.05, but keep playable player 1 identical.
    df_cand.loc[df_cand["player_id"] == 2, "projected_points"] += 0.05

    ref = _make_result("champ", df_ref)
    cand = _make_result("cand_bench_fodder", df_cand)

    # Active GW exists because of player 2, but max_playable_pool_shift == 0.0 < 0.01
    assert max_playable_pool_shift(df_ref, df_cand) == 0.0
    with pytest.raises(InertPrototypeError, match="inert on Exogenous Playable Pool"):
        check_inert_prototype("cand_bench_fodder", ref, cand, combined_delta=0.0)


def test_inert_prototype_passes_on_playable_shift() -> None:
    df_ref = pd.DataFrame(
        {
            "gameweek": [1, 1, 2, 2],
            "player_id": [1, 2, 1, 2],
            "projected_points": [4.5, 0.2, 5.0, 0.3],
            "actual_minutes": [90.0, 0.0, 85.0, 0.0],
        }
    )
    df_cand = df_ref.copy()
    # Player 1 is playable (champ_xp >= 2.0 and mins >= 30).
    df_cand.loc[df_cand["player_id"] == 1, "projected_points"] += 0.15

    ref = _make_result("champ", df_ref)
    cand = _make_result("cand_playable", df_cand)

    assert max_playable_pool_shift(df_ref, df_cand) == pytest.approx(0.15)
    # Does not raise even if combined_delta == 0.0
    check_inert_prototype("cand_playable", ref, cand, combined_delta=0.0)
