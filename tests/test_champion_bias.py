from pathlib import Path

import pandas as pd

from backtesting.champion_bias import champion_bias_row, signed_bias, write_champion_bias_csv
from backtesting.walkforward import WalkforwardResult


def test_signed_bias_is_mean_projected_minus_actual() -> None:
    frame = pd.DataFrame({"projected_points": [3.0, 3.0], "actual_points": [1.0, 1.0]})
    assert signed_bias(frame) == 2.0


def test_champion_bias_row_uses_eval_frame_not_metrics_bias() -> None:
    result = WalkforwardResult(
        model_name="participation_penalty_hybrid",
        data_dir=Path("data/archive/2025-26/processed"),
        start_gw=1,
        end_gw=2,
        metrics={"sample_count": 99, "bias": 99.0, "mae": 99.0, "minutes_forecast_metrics": {"bias": 10.0}},
        df_eval=pd.DataFrame(
            {
                "player_id": [1, 2],
                "gameweek": [1, 1],
                "projected_points": [3.0, 3.0],
                "actual_points": [1.0, 1.0],
            }
        ),
        snapshot_ids={},
        snapshot_backed=False,
    )
    row = champion_bias_row(result, evaluation_season="2025-26", seed_season="2024-25")
    assert row["signed_bias"] == 2.0
    assert row["mae"] == 2.0
    assert row["sample_count"] == 2
    assert row["minutes_bias"] == 10.0
    assert row["model"] == "participation_penalty_hybrid"
    assert row["evaluation_season"] == "2025-26"
    assert row["seed_season"] == "2024-25"


def test_write_champion_bias_csv(tmp_path: Path) -> None:
    path = tmp_path / "champion_bias_summary.csv"
    write_champion_bias_csv(
        path,
        [
            {
                "model": "participation_penalty_hybrid",
                "evaluation_season": "2025-26",
                "gw_start": 1,
                "gw_end": 2,
                "seed_season": "2024-25",
                "sample_count": 4,
                "signed_bias": 0.25,
                "mae": 1.0,
                "minutes_bias": 0.0,
                "snapshot_backed": "false",
            }
        ],
    )
    text = path.read_text(encoding="utf-8")
    assert "signed_bias" in text
    assert "0.25" in text
