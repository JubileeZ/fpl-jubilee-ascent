
from models import get_model, list_model_names
from models.calibrated_rate_challenger import CalibratedRateChallengerModel
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from tests.test_learned_start_challenger import _features, _start_history


def test_catalog_discovers_calibrated_rate_challenger() -> None:
    assert "calibrated_rate_challenger" in list_model_names()
    assert get_model("calibrated_rate_challenger").name == "calibrated_rate_challenger"


def test_calibrated_rate_reconciles_ledger() -> None:
    history, frame = _start_history(), _features(13)
    candidate = CalibratedRateChallengerModel()
    candidate.fit(history)
    out = candidate.predict(frame, horizon=1)
    components = [col for col in out.columns if col.startswith("xp_")]
    assert (out["projected_points"] - out[components].sum(axis=1)).abs().max() < 1e-9


def test_unsharp_and_mins_clamp_deflates_elite_and_protects_budget() -> None:
    history, frame = _start_history(), _features(13)
    # Set high xG and xA for player 1000 (elite)
    frame.loc[frame["player_id"] == 1000, "per90_xg"] = 0.90
    frame.loc[frame["player_id"] == 1000, "per90_xa"] = 0.30
    frame.loc[frame["player_id"] == 1000, "xmins_if_start"] = 90.0
    # Set low xG for player 1001 (budget)
    frame.loc[frame["player_id"] == 1001, "per90_xg"] = 0.05
    frame.loc[frame["player_id"] == 1001, "per90_xa"] = 0.05

    candidate = CalibratedRateChallengerModel()
    champion = DefXgShrinkChallengerModel()
    candidate.fit(history)
    champion.fit(history)

    out_cand = candidate.predict(frame, horizon=1)
    out_champ = champion.predict(frame, horizon=1)

    # Elite attacker (player 1000) projects lower goals under candidate (no +25% sharp slope)
    p1_cand = out_cand[out_cand["player_id"] == 1000].iloc[0]
    p1_champ = out_champ[out_champ["player_id"] == 1000].iloc[0]
    assert p1_cand["xp_goals"] < p1_champ["xp_goals"]

    # Budget asset (player 1001) with xG < 0.10 has higher/equal xG goals under candidate (no 5% down-trim)
    p2_cand = out_cand[out_cand["player_id"] == 1001].iloc[0]
    p2_champ = out_champ[out_champ["player_id"] == 1001].iloc[0]
    assert p2_cand["xp_goals"] >= p2_champ["xp_goals"]
