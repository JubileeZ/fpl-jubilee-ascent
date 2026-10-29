"""Derive a strict synthetic solver CSV from a verified forecast ID."""

import os
import uuid
from pathlib import Path
from typing import Any

from backtesting.data_admission import AdmittedInput
from backtesting.forecast_export import strict_solver_table
from backtesting.forecast_inputs import verify_training_bundle
from backtesting.forecast_store import _bytes, _hash, load_forecast_verified


def export_solver_csv(store: Path, forecast_id: str, capability: AdmittedInput, request: dict[str, Any], catalog: dict[str, bytes], training_authority: str) -> tuple[Path, dict[str, Any]]:
    predictions, _ = load_forecast_verified(store, forecast_id, capability, request, catalog, training_authority)
    source = verify_training_bundle(capability, request, catalog, training_authority)
    table: Any = strict_solver_table(predictions, capability, request, catalog)
    names = {item["id"]: item["web_name"] for item in source["tables"]["player_metadata"]}
    clubs = {item["id"]: item["short_name"] for item in source["tables"]["clubs"]}
    table["Name"] = table["player_id"].map(names)
    table["Team"] = table["club"].map(clubs)
    table["Pos"] = table["position"].map({1: "G", 2: "D", 3: "M", 4: "F"})
    table["Price"] = table["price"] / 10.0
    table = table.rename(columns={"player_id": "ID"}).drop(columns=["club", "position", "price"])
    if bool(table[["Name", "Team", "Pos", "Price"]].isna().any().any()):
        raise ValueError("Solver metadata missing")
    data = table.to_csv(index=False, float_format="%.17g", lineterminator="\n").encode()
    manifest = {"version": 1, "forecast_id": forecast_id, "csv_sha256": _hash(data), "rows": len(table), "mode": "synthetic_diagnostic"}
    root = store.resolve() / "solver_csv"
    if any(part in {"archive", "2026-27", ".git", ".agents"} for part in root.parts):
        raise ValueError("Invalid export root")
    root.mkdir(parents=True, exist_ok=True)
    destination = root / forecast_id
    if not destination.exists():
        stage = root / (".stage-" + uuid.uuid4().hex)
        stage.mkdir()
        (stage / "solver.csv").write_bytes(data)
        (stage / "manifest.json").write_bytes(_bytes(manifest))
        try:
            os.rename(stage, destination)
        except FileExistsError:
            import shutil

            shutil.rmtree(stage)
    if (destination / "solver.csv").read_bytes() != data or (destination / "manifest.json").read_bytes() != _bytes(manifest):
        raise ValueError("Solver export corruption")
    return destination / "solver.csv", manifest
