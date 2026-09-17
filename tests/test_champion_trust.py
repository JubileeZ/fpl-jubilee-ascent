"""On-product Champion Trust payload."""

from pathlib import Path

from models.champion_trust import load_champion_trust


def test_load_champion_trust_reads_bias_walkforward_and_provisional(tmp_path: Path) -> None:
    selection = tmp_path / "model_selection.json"
    selection.write_text(
        '{"schema_version":1,"champion":"dual_vector_state_hybrid","candidates":[],"promotion_status":"provisional"}',
        encoding="utf-8",
    )
    bias = tmp_path / "bias.csv"
    bias.write_text(
        "model,evaluation_season,gw_start,gw_end,signed_bias,mae\n"
        "dual_vector_state_hybrid,2025-26,1,38,0.15,1.07\n"
        "dual_vector_state_hybrid,2026-27,1,3,0.21,1.40\n",
        encoding="utf-8",
    )
    walk = tmp_path / "walk.csv"
    walk.write_text(
        "arm_id,family,realized_points,status\n"
        "ft_attack,ft,1081,ok\n"
        "baseline,baseline,1051,ok\n",
        encoding="utf-8",
    )
    regret = tmp_path / "regret.csv"
    regret.write_text("model_regret\n1.5\n2.5\n", encoding="utf-8")
    payload = load_champion_trust(
        selection_path=selection,
        bias_path=bias,
        walkforward_path=walk,
        regret_path=regret,
    )
    assert payload["champion"] == "dual_vector_state_hybrid"
    assert payload["promotion_status"] == "provisional"
    assert payload["signed_bias"] == 0.15
    assert payload["bias_season"] == "2025-26"
    assert payload["walkforward_best_arm"] == "ft_attack"
    assert payload["walkforward_best_points"] == 1081.0
    assert payload["walkforward_ranking"][0]["arm_id"] == "ft_attack"
    assert payload["walkforward_ranking"][1]["arm_id"] == "baseline"
    assert payload["decision_regret_mean"] == 2.0
