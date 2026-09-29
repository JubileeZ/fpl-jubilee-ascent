
from models import get_model, list_model_names
from models.club_def_prior_challenger import ClubDefPriorChallengerModel
from models.cs_exposure_challenger import CsExposureChallengerModel
from tests.test_learned_start_challenger import _features, _start_history


def test_catalog_discovers_cs_exposure_challenger() -> None:
    assert "cs_exposure_challenger" in list_model_names()
    assert get_model("cs_exposure_challenger").name == "cs_exposure_challenger"


def test_predict_reconciles_ledger_and_adjusts_clean_sheet() -> None:
    history = _start_history()
    frame = _features(13).assign(position_id=2)
    candidate = CsExposureChallengerModel()
    champion = ClubDefPriorChallengerModel()
    candidate.fit(history)
    champion.fit(history)
    out = candidate.predict(frame, horizon=1)
    ref = champion.predict(frame, horizon=1)
    components = [col for col in out.columns if col.startswith("xp_")]
    assert (out["projected_points"] - out[components].sum(axis=1)).abs().max() < 1e-9
    # Def clean sheet points should differ when m60 replaces default start minutes
    assert not out["xp_clean_sheet"].equals(ref["xp_clean_sheet"])
