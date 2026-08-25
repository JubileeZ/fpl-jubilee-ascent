from pathlib import Path

from commands.transfer_plan_walkforward import main


def test_cli_writes_blocked_summary_without_seed(tmp_path: Path) -> None:
    output = tmp_path / "tp_walkforward_summary.csv"
    seed = tmp_path / "missing" / "processed"
    code = main(["--seed_dir", str(seed), "--output", str(output)])
    assert code == 1
    text = output.read_text(encoding="utf-8")
    assert "baseline" in text
    assert "blocked_missing_prior_season_seed" in text
