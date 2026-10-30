"""Known-answer lifecycle uses actual outputs and preserves empirical barriers."""

from pathlib import Path

from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.promotion_evidence import verify_recommendation_bundle, write_recommendation_bundle
from commands.evaluate_model_promotion import adopt_champion
from models.selection import ModelSelection, load_model_selection, save_model_selection
from promotion_evidence_fixture import CANDIDATE, CHAMPION, build_evidence_fixture
import pytest


def test_complete_foundation_lifecycle_end_to_end(tmp_path: Path) -> None:
    request = build_evidence_fixture(tmp_path / "retained")
    bundle_path = request.with_name("recommendation_bundle.json")
    bundle = write_recommendation_bundle(request, bundle_path)
    assert verify_recommendation_bundle(bundle_path, require_finalized=True) == bundle
    assert bundle["scientific_verdict"] == "inconclusive"
    assert bundle["empirical_admission"] is False
    assert bundle["assessment"]["is_confirmation_available"] is True
    registry = ConfirmationRegistry(request.parent / "registry.jsonl")
    attempt = registry.get_attempt("fixture-attempt")
    assert attempt is not None and attempt.status == "completed"
    assert attempt.scientific_verdict == bundle["scientific_verdict"]
    config = request.parent / "selection.json"
    original = ModelSelection(CHAMPION, (CANDIDATE,))
    save_model_selection(original, config)
    with pytest.raises(ValueError, match="complete empirical scientific pass"):
        adopt_champion(bundle_path, config_path=config, approval_ref="fixture-human-approval", expected_current_champion=CHAMPION, approved_bundle_hash=bundle["bundle_hash"])
    assert load_model_selection(config) == original
