"""Committed Comparison Slate configuration."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "model_selection.json"
_MAX_CANDIDATES = 2
FALLBACK_CHAMPION = "calibrated_matchup_hybrid"
FALLBACK_CANDIDATES: tuple[str, ...] = ("participation_state_hybrid",)


@dataclass(frozen=True)
class ModelSelection:
    champion: str
    candidates: tuple[str, ...]
    promotion_status: str = "provisional"
    schema_version: int = 1
    provisional_active: str | None = None
    podium_frozen_season: str | None = None
    podium_sealed: bool = False
    frozen_protocol_hash: str | None = None
    frozen_certification_digest: str | None = None

    def __post_init__(self) -> None:
        if len(self.candidates) > _MAX_CANDIDATES:
            raise ValueError("Comparison Slate allows at most two Model Candidates")
        if self.provisional_active is not None:
            if not self.provisional_active.strip():
                object.__setattr__(self, "provisional_active", None)
            elif self.provisional_active == self.champion:
                raise ValueError("Provisional Active model cannot equal Confirmed Champion")
            elif self.provisional_active not in self.candidates:
                raise ValueError("Provisional Active model must appear in Comparison Slate candidates")


def load_model_selection(path: Path | None = None) -> ModelSelection:
    config_path = path or DEFAULT_CONFIG_PATH
    if path is None and not config_path.exists():
        selection = ModelSelection(
            champion=FALLBACK_CHAMPION,
            candidates=FALLBACK_CANDIDATES,
            promotion_status="provisional",
            schema_version=1,
        )
        save_model_selection(selection, config_path)
        return selection
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    candidates = tuple(payload.get("candidates", ()))
    raw_prov = payload.get("provisional_active")
    prov = str(raw_prov).strip() if isinstance(raw_prov, str) and raw_prov.strip() else None
    raw_season = payload.get("podium_frozen_season")
    frozen_season = str(raw_season).strip() if isinstance(raw_season, str) and raw_season.strip() else None
    raw_proto = payload.get("frozen_protocol_hash")
    frozen_proto = str(raw_proto).strip() if isinstance(raw_proto, str) and raw_proto.strip() else None
    raw_cert = payload.get("frozen_certification_digest")
    frozen_cert = str(raw_cert).strip() if isinstance(raw_cert, str) and raw_cert.strip() else None
    return ModelSelection(
        champion=str(payload["champion"]),
        candidates=candidates,
        promotion_status=str(payload.get("promotion_status", "provisional")),
        schema_version=int(payload.get("schema_version", 1)),
        provisional_active=prov,
        podium_frozen_season=frozen_season,
        podium_sealed=bool(payload.get("podium_sealed", False)),
        frozen_protocol_hash=frozen_proto,
        frozen_certification_digest=frozen_cert,
    )


def save_model_selection(selection: ModelSelection, path: Path | None = None) -> None:
    if len(selection.candidates) > _MAX_CANDIDATES:
        raise ValueError("Comparison Slate allows at most two Model Candidates")
    config_path = path or DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema_version": selection.schema_version,
        "champion": selection.champion,
        "candidates": list(selection.candidates),
        "promotion_status": selection.promotion_status,
        "provisional_active": selection.provisional_active,
        "podium_frozen_season": selection.podium_frozen_season,
        "podium_sealed": selection.podium_sealed,
    }
    if selection.frozen_protocol_hash is not None:
        payload["frozen_protocol_hash"] = selection.frozen_protocol_hash
    if selection.frozen_certification_digest is not None:
        payload["frozen_certification_digest"] = selection.frozen_certification_digest
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def default_model_name(path: Path | None = None) -> str:
    return load_model_selection(path).champion


def active_transfer_plan_model_name(path: Path | None = None) -> str:
    selection = load_model_selection(path)
    return selection.provisional_active or selection.champion


def dual_tier_models(path: Path | None = None) -> list[str]:
    selection = load_model_selection(path)
    if selection.provisional_active:
        return list(dict.fromkeys([selection.champion, selection.provisional_active]))
    return [selection.champion]


def projection_model_names(
    model_name: str | None = None,
    model_names: Sequence[str] | None = None,
    *,
    config_path: Path | None = None,
) -> list[str]:
    """Models to project for Explorer/Dual-Tier serving. `--models` overrides slate."""
    if model_names:
        return list(dict.fromkeys(model_names))
    cleaned = (model_name or "").strip()
    try:
        serving_models = dual_tier_models(config_path)
    except (ValueError, KeyError, OSError):
        serving_models = [FALLBACK_CHAMPION]
    if cleaned.lower() in ("", "default", "champion") or cleaned in serving_models:
        return serving_models
    return [cleaned]

