from models import get_model, list_model_names
from models.schedule_congestion_challenger import ScheduleCongestionChallengerModel
from tests.test_learned_start_challenger import _features, _start_history


def test_catalog_discovers_schedule_congestion_challenger() -> None:
    assert "schedule_congestion_challenger" in list_model_names()
    assert get_model("schedule_congestion_challenger").name == "schedule_congestion_challenger"


def test_predict_reconciles_ledger() -> None:
    history = _start_history()
    frame = _features(13)
    candidate = ScheduleCongestionChallengerModel()
    candidate.fit(history)
    out = candidate.predict(frame, horizon=1)
    components = [col for col in out.columns if col.startswith("xp_")]
    assert (out["projected_points"] - out[components].sum(axis=1)).abs().max() < 1e-9
