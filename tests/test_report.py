from pathlib import Path
from unittest.mock import patch

import pandas as pd

from commands.report import main, recommend_captain_vice


def test_recommend_captain_vice_uses_next_gameweek_points():
    projections = pd.DataFrame([
        {"ID": 1, "Name": "Captain", "1_Pts": 8.0},
        {"ID": 2, "Name": "Vice", "1_Pts": 7.0},
        {"ID": 3, "Name": "Third", "1_Pts": 6.0},
    ])

    captain, vice_captain = recommend_captain_vice(projections, "1_Pts")

    assert captain is not None
    assert vice_captain is not None
    assert captain["ID"] == 1
    assert vice_captain["ID"] == 2


def test_report_prints_and_exports_captaincy_recommendations(tmp_path: Path, capsys) -> None:
    projections = pd.DataFrame([
        {
            "ID": 1,
            "Name": "Captain",
            "Pos": "M",
            "Price": 10.0,
            "Team": "AAA",
            "1_Pts": 8.0,
            "1_xMins": 90.0,
            "2_Pts": 6.0,
            "2_xMins": 90.0,
        },
        {
            "ID": 2,
            "Name": "Vice",
            "Pos": "F",
            "Price": 9.0,
            "Team": "BBB",
            "1_Pts": 7.0,
            "1_xMins": 90.0,
            "2_Pts": 5.0,
            "2_xMins": 90.0,
        },
    ])
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    projections.to_csv(data_dir / "linear_baseline.csv", index=False)

    with patch("commands.report.PROJECT_ROOT", tmp_path), \
        patch("commands.report.load_settings", return_value={"datasource": "linear_baseline", "horizon": 2}), \
        patch("sys.argv", ["commands.report", "--model", "linear_baseline", "--horizon", "2"]):
        main()

    output = capsys.readouterr().out
    assert "Captain      : Captain" in output
    assert "Vice-Captain : Vice" in output
    report = pd.read_csv(tmp_path / "data" / "reports" / "top_picks_linear_baseline.csv")
    assert {"Captain", "Vice_Captain"}.issubset(report.columns)
    assert bool(report.loc[report["ID"] == 1, "Captain"].iloc[0])
    assert bool(report.loc[report["ID"] == 2, "Vice_Captain"].iloc[0])
