import sys

import pandas as pd

from commands.fdr_report import build_fdr_report, main


def _fixtures() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "id": 10,
            "gameweek_id": 2,
            "home_club_id": 1,
            "away_club_id": 2,
            "team_h_difficulty": 2,
            "team_a_difficulty": 4,
        },
        {
            "id": 11,
            "gameweek_id": 2,
            "home_club_id": 3,
            "away_club_id": 1,
            "team_h_difficulty": 1,
            "team_a_difficulty": 5,
        },
        {
            "id": 12,
            "gameweek_id": 3,
            "home_club_id": 2,
            "away_club_id": 1,
            "team_h_difficulty": 2,
            "team_a_difficulty": 3,
        },
    ])


def _clubs() -> pd.DataFrame:
    return pd.DataFrame([
        {"id": 1, "name": "Club A"},
        {"id": 2, "name": "Club B"},
        {"id": 3, "name": "Club C"},
    ])


def test_fdr_report_preserves_home_away_double_gameweeks_and_average():
    report = build_fdr_report(_fixtures(), _clubs(), start_gw=2, horizon=2)

    assert list(report["club"]) == ["Club C", "Club B", "Club A"]
    club_a = report[report["club"] == "Club A"].iloc[0]
    assert club_a["GW2"] == "H:1.75 vs Club B | A:5.25 @ Club C"
    assert club_a["GW3"] == "A:3.25 @ Club B"
    assert club_a["Average FDR"] == 10.25 / 3
    assert club_a["Fixtures"] == 3


def test_fdr_report_cli_reads_processed_parquet_and_sorts_by_club(tmp_path, monkeypatch, capsys):
    processed = tmp_path / "processed"
    processed.mkdir()
    _fixtures().to_parquet(processed / "fixtures.parquet", index=False)
    _clubs().to_parquet(processed / "clubs.parquet", index=False)
    pd.DataFrame([{"id": 2, "is_next": True, "finished": False}]).to_parquet(
        processed / "gameweeks.parquet",
        index=False,
    )
    output = tmp_path / "reports" / "fdr.csv"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fdr_report",
            "--data_dir",
            str(processed),
            "--horizon",
            "2",
            "--sort_by",
            "club",
            "--output",
            str(output),
        ],
    )
    main()

    captured = capsys.readouterr().out
    assert "MODIFIED FDR REPORT: GW2-GW3" in captured
    assert "Club A" in captured
    assert "A:5.25 @ Club C" in captured
    assert output.exists()
    saved = pd.read_csv(output)
    assert list(saved["club"]) == ["Club A", "Club B", "Club C"]
