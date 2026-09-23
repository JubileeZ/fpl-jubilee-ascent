import os
import importlib
import inspect
from pathlib import Path
from models.base import BaseModel
from models.selection import FALLBACK_CHAMPION

DEFAULT_MODEL_NAME = FALLBACK_CHAMPION
_SKIP_MODULES = frozenset({"base.py", "__init__.py"})


def get_default_model_name() -> str:
    try:
        from models.selection import default_model_name

        return default_model_name()
    except (FileNotFoundError, ValueError, KeyError):
        return DEFAULT_MODEL_NAME


def resolve_model_or_champion(model_name: str | None = None, *, validate: bool = False) -> str:
    """Return model name, resolving None, empty, or 'champion' to active Champion."""
    if model_name is None or not str(model_name).strip() or str(model_name).strip().lower() == "champion":
        return get_default_model_name()
    resolved = str(model_name).strip()
    if validate:
        return resolve_model_name(resolved)
    return resolved



def _iter_registered_models() -> list[BaseModel]:
    models_dir = Path(__file__).resolve().parent
    found: dict[str, BaseModel] = {}
    for file in os.listdir(models_dir):
        if not file.endswith(".py") or file in _SKIP_MODULES:
            continue
        try:
            module = importlib.import_module(f"models.{file[:-3]}")
        except Exception:
            continue
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, BaseModel) or obj is BaseModel:
                continue
            try:
                instance = obj()
            except Exception:
                continue
            if instance.name not in found:
                found[instance.name] = instance
    return list(found.values())


def list_model_names() -> list[str]:
    """Sorted CLI identifiers (`BaseModel.name`) discovered under `models/`."""
    return sorted(model.name for model in _iter_registered_models())


def resolve_model_name(model_name: str) -> str:
    """Return `model_name` when registered, else raise."""
    if model_name in list_model_names():
        return model_name
    raise ValueError(
        f"Model '{model_name}' not found. Please ensure it is implemented in the models/ directory."
    )


def get_model(model_name: str) -> BaseModel:
    """
    Auto-discovers and returns an instance of the requested model from the models/ folder.
    """
    resolved = resolve_model_name(model_name)
    for model in _iter_registered_models():
        if model.name == resolved:
            return model
    raise ValueError(
        f"Model '{model_name}' not found. Please ensure it is implemented in the models/ directory."
    )
