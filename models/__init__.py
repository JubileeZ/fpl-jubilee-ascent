import os
import importlib
import inspect
from pathlib import Path
from models.base import BaseModel

DEFAULT_MODEL_NAME = "participation_state_hybrid"
_SKIP_MODULES = frozenset({"base.py", "__init__.py"})


def get_default_model_name() -> str:
    try:
        from models.selection import default_model_name

        return default_model_name()
    except (FileNotFoundError, ValueError, KeyError):
        return DEFAULT_MODEL_NAME


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


def get_model(model_name: str) -> BaseModel:
    """
    Auto-discovers and returns an instance of the requested model from the models/ folder.
    """
    for model in _iter_registered_models():
        if model.name == model_name:
            return model
    raise ValueError(
        f"Model '{model_name}' not found. Please ensure it is implemented in the models/ directory."
    )
