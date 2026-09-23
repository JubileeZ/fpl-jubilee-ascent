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
    if len(candidates) > _MAX_CANDIDATES:
        raise ValueError("Comparison Slate allows at most two Model Candidates")
    return ModelSelection(
        champion=str(payload["champion"]),
        candidates=candidates,
        promotion_status=str(payload.get("promotion_status", "provisional")),
        schema_version=int(payload.get("schema_version", 1)),
    )



def save_model_selection(selection: ModelSelection, path: Path | None = None) -> None:
    if len(selection.candidates) > _MAX_CANDIDATES:
        raise ValueError("Comparison Slate allows at most two Model Candidates")
    config_path = path or DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": selection.schema_version,
        "champion": selection.champion,
        "candidates": list(selection.candidates),
        "promotion_status": selection.promotion_status,
    }
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def default_model_name(path: Path | None = None) -> str:
    return load_model_selection(path).champion


def projection_model_names(
    model_name: str | None = None,
    model_names: Sequence[str] | None = None,
    *,
    config_path: Path | None = None,
) -> list[str]:
    """Models to project for Explorer. Default Champion only. `--models` keeps the slate."""
    if model_names:
        return list(dict.fromkeys(model_names))
    if model_name and model_name.strip().lower() != "champion":
        return [model_name.strip()]
    try:
        return [default_model_name(config_path)]
    except (FileNotFoundError, ValueError, KeyError, OSError, json.JSONDecodeError):
        return [FALLBACK_CHAMPION]

