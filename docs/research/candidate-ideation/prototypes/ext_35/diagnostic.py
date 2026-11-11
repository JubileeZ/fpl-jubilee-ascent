"""Retain EXT-35 event-on/off × native/oracle cells before development smoke.

Run as a module with --output under data/reports or this research topic.
Season data is read only inside run(); importing or requesting --help reads none.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Protocol, cast

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from backtesting.walkforward import LEDGER_COMPONENTS, PLAYER_POSITIONS, inject_oracle_minutes, load_gameweek_deadlines
from features.builder import build_features, history_before_target
from features.contracts import assert_projection_contract
from models import get_model
from models.base import BaseModel
from models.selection import DEFAULT_CONFIG_PATH, load_model_selection

KEYS = ["player_id", "gameweek_id", "fixture_id"]
STATES = ["p_dnp", "p_start", "p_sub_in", "xmins_if_start", "xmins_if_sub_in",
          "p_60_if_start", "p_60_if_sub_in", "projected_minutes", "xp_minutes"]
SMOKE_PATH = ROOT / ".agents/skills/explore-candidate/smoke.py"
PROTOTYPE_PATH = Path(__file__).with_name("prototypes.py")
ATOL = 1e-10


class EventProjector(Protocol):
    def __call__(
        self, row: pd.Series, position: str, expected_minutes: float,
        *, clean_sheet_minutes: float, p_sixty_mins: float,
    ) -> dict[str, float]: ...


@dataclass
class Cell:
    projections: pd.DataFrame
    events: pd.DataFrame
    rates: pd.DataFrame


def _module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _ordered(frame: pd.DataFrame, keys: list[str] = KEYS) -> pd.DataFrame:
    if not set(keys).issubset(frame.columns):
        raise ValueError(f"Missing diagnostic keys: {keys}")
    out = frame.copy()
    for column in keys:
        values = np.asarray(pd.to_numeric(out[column], errors="raise"), dtype=np.float64)
        if not np.isfinite(values).all() or (values % 1.0 != 0.0).any():
            raise ValueError(f"Invalid integral diagnostic key: {column}")
        out[column] = values.astype(np.int64)
    if out.duplicated(keys).any():
        raise ValueError(f"Duplicate diagnostic keys: {keys}")
    return out.sort_values(keys, kind="stable").reset_index(drop=True)


def _finite(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    if not set(columns).issubset(frame.columns):
        raise ValueError(f"{label}: missing numeric fields")
    if not np.isfinite(frame[columns].to_numpy(dtype=float)).all():
        raise ValueError(f"{label}: non-finite values")


def _same(left: pd.DataFrame, right: pd.DataFrame, columns: list[str], label: str,
          keys: list[str] = KEYS) -> None:
    left, right = _ordered(left, keys), _ordered(right, keys)
    if not left[keys].equals(right[keys]):
        raise ValueError(f"{label}: populations differ")
    _finite(left, columns, label)
    _finite(right, columns, label)
    if not np.allclose(left[columns].to_numpy(dtype=float), right[columns].to_numpy(dtype=float), atol=ATOL, rtol=0.0):
        raise ValueError(f"{label}: values differ beyond {ATOL}")


def _frame_hash(frame: pd.DataFrame, columns: list[str]) -> str:
    ordered = _ordered(frame)[[*KEYS, *columns]].copy()
    payload = np.asarray(ordered[KEYS], dtype=np.int64).tobytes() + np.asarray(ordered[columns], dtype=np.float64).tobytes()
    return hashlib.sha256(json.dumps(list(ordered.columns)).encode() + payload).hexdigest()


def _write_frame(frame: pd.DataFrame, path: Path) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    out.attrs = {}
    out.to_parquet(path, index=False)
    return {"path": str(path), "rows": len(out), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def capture_prediction(model: BaseModel, features: pd.DataFrame) -> Cell:
    """Trace the bound scorer without changing its inputs or returned dictionary."""
    original = cast(EventProjector, getattr(model, "_project_event_components"))
    owned = "_project_event_components" in vars(model)
    records: list[dict[str, object]] = []
    calls: dict[tuple[int, int, int], int] = {}

    def capture(
        row: pd.Series, position: str, expected_minutes: float,
        *, clean_sheet_minutes: float, p_sixty_mins: float,
    ) -> dict[str, float]:
        key = (int(cast(float, row["player_id"])), int(cast(float, row["gameweek_id"])),
               int(cast(float, row["fixture_id"])))
        state_call = calls.get(key, 0)
        calls[key] = state_call + 1
        record: dict[str, object] = {
            **dict(zip(KEYS, key, strict=True)), "state_call": state_call,
            "position": position, "conditional_minutes": float(expected_minutes),
            "clean_sheet_minutes": float(clean_sheet_minutes), "p_sixty_mins": float(p_sixty_mins),
            **{f"prepared_{column}": value for column, value in row.items()},
        }
        components = original(row, position, expected_minutes, clean_sheet_minutes=clean_sheet_minutes,
                              p_sixty_mins=p_sixty_mins)
        record.update({f"event_{column}": value for column, value in components.items()})
        records.append(record)
        return components

    setattr(model, "_project_event_components", capture)
    try:
        projections = _ordered(model.predict(features.copy(deep=True), horizon=1))
    finally:
        if owned:
            setattr(model, "_project_event_components", original)
        else:
            delattr(model, "_project_event_components")

    assert_projection_contract(projections)
    _same(features, projections, [], "Feature/projection population")
    _finite(projections, ["projected_points", *STATES, *LEDGER_COMPONENTS], model.name)
    probabilities = projections[["p_dnp", "p_start", "p_sub_in"]].to_numpy(dtype=float)
    bounded = projections[["p_dnp", "p_start", "p_sub_in", "p_60_if_start", "p_60_if_sub_in"]].to_numpy(dtype=float)
    if (bounded < -ATOL).any() or (bounded > 1.0 + ATOL).any() or not np.allclose(probabilities.sum(axis=1), 1.0, atol=ATOL, rtol=0.0):
        raise ValueError(f"{model.name}: invalid participation distribution")
    if (projections["projected_minutes"] < -ATOL).any():
        raise ValueError(f"{model.name}: negative projected minutes")
    if not np.allclose(projections[list(LEDGER_COMPONENTS)].sum(axis=1), projections["projected_points"], atol=ATOL, rtol=0.0):
        raise ValueError(f"{model.name}: component accounting mismatch")

    if records:
        events = _ordered(pd.DataFrame(records), [*KEYS, "state_call"])
        if set(calls.values()) != {2}:
            raise ValueError(f"{model.name}: expected one start and one substitute scorer call")
        rate_columns = sorted(column for column in events if column.startswith("prepared_per90_")
                              or column in {"prepared_attack_multiplier", "prepared_defence_multiplier"})
        if not rate_columns:
            raise ValueError(f"{model.name}: prepared rate trace missing")
        event_numeric = [column for column in events if column.startswith("event_")]
        _finite(events, [*rate_columns, *event_numeric, "conditional_minutes", "clean_sheet_minutes", "p_sixty_mins"], model.name)
        if (events[[*rate_columns, "conditional_minutes", "clean_sheet_minutes"]].to_numpy(dtype=float) < -ATOL).any():
            raise ValueError(f"{model.name}: negative prepared rates or durations")
        if not events["p_sixty_mins"].between(-ATOL, 1.0 + ATOL).all():
            raise ValueError(f"{model.name}: invalid scorer P(60)")
        rates = _ordered(events.loc[events["state_call"] == 0, [*KEYS, *rate_columns]])
        second = events.loc[events["state_call"] == 1, [*KEYS, *rate_columns]]
        _same(rates, second, rate_columns, "Start/sub prepared rate identity")
        traced = projections.loc[projections["fixture_id"] >= 0]
        _same(traced, rates, [], "Nonblank scorer coverage")
    else:
        if (projections["fixture_id"] >= 0).any():
            raise ValueError(f"{model.name}: scorer trace empty")
        events, rates = pd.DataFrame(columns=[*KEYS, "state_call"]), pd.DataFrame(columns=KEYS)

    blank = projections.loc[projections["fixture_id"] < 0]
    if not np.allclose(blank[["projected_points", "projected_minutes"]].to_numpy(dtype=float), 0.0, atol=ATOL, rtol=0.0):
        raise ValueError(f"{model.name}: nonzero blank forecast")
    return Cell(projections, events, rates)


def _source_hashes() -> dict[str, str]:
    paths = [Path(__file__), PROTOTYPE_PATH, SMOKE_PATH, DEFAULT_CONFIG_PATH,
             ROOT / "backtesting/walkforward.py", *ROOT.glob("models/*.py"), *ROOT.glob("features/*.py")]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(set(paths))}


def run(output: Path) -> Path:
    output = output.resolve()
    allowed = [ROOT / "data/reports", ROOT / "docs/research/candidate-ideation"]
    if not any(output.is_relative_to(root) and output != root for root in allowed):
        raise ValueError("Output must be a new directory under data/reports or this research topic")
    if output.exists():
        raise ValueError("Output directory already exists; retain prior diagnostic artifacts")

    smoke = _module(SMOKE_PATH, "ext35_diagnostic_smoke")
    prototypes = _module(PROTOTYPE_PATH, "ext35_diagnostic_prototypes")
    issues = smoke.audit(PROTOTYPE_PATH, prototypes)
    if issues:
        raise ValueError(f"Prototype audit failed: {issues}")
    factories = cast(dict[str, Callable[[], BaseModel]], prototypes.PROTOTYPES)
    if len(factories) != 4 or any(not name.startswith("ext_35_") for name in factories):
        raise ValueError("Diagnostic requires the four preregistered EXT-35 variants")
    roles, _ = smoke.resolve_seasons()
    if "dev" not in roles:
        raise ValueError("No complete development season resolved")
    season = roles["dev"]
    champion = load_model_selection(DEFAULT_CONFIG_PATH).champion
    if champion in factories:
        raise ValueError("Champion/prototype name collision")
    sources = _source_hashes()
    performance_path = season.data_dir / "player_performances.parquet"
    performances = pd.read_parquet(performance_path)
    if performances.duplicated(KEYS).any():
        raise ValueError("Actual outcomes have duplicate fixture keys")
    deadlines = load_gameweek_deadlines(season.data_dir)
    output.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 1, "status": "running", "evidence_kind": "four_cell_projection_diagnostic",
        "promotion_authority": False, "started_utc": datetime.now(timezone.utc).isoformat(),
        "role": "dev", "season": season.name, "seed_dir": str(season.seed_dir),
        "gw_range": [1, season.last_gw], "champion": champion, "variants": list(factories),
        "source_sha256": sources, "feature_builds_per_gw": 1, "fit_scope": "current-season history_before_target",
        "oracle": "inject_oracle_minutes then unchanged target_to_states; not observed categorical states",
        "invariants": {"native_state_parity": True, "rate_regime_identity": True,
                       "component_accounting": True, "blank_identity": True, "finite": True, "atol": ATOL},
        "cells": [], "completed_gameweeks": [],
        "actual_outcomes": _write_frame(performances, output / "outcomes.parquet"),
        "actual_source_sha256": hashlib.sha256(performance_path.read_bytes()).hexdigest(),
    }
    manifest_path = output / "manifest.json"

    def checkpoint() -> None:
        manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    checkpoint()
    try:
        for gw in range(1, season.last_gw + 1):
            features = build_features(season.data_dir, target_gw=gw, horizon=1,
                                      seed_processed_dir=season.seed_dir, use_archive_seed=False,
                                      as_of_gw=gw, target_deadline=deadlines.get(gw))
            features = features.loc[features["position_id"].isin(PLAYER_POSITIONS)].copy()
            if features.empty:
                raise ValueError(f"GW{gw}: empty feature population")
            _ordered(features)
            history = history_before_target(performances, gw, deadlines.get(gw), False)
            oracle = inject_oracle_minutes(features, performances, gw)
            cells: dict[tuple[str, str], Cell] = {}
            model_factories = {champion: lambda: get_model(champion), **factories}
            diagnostics: dict[str, pd.DataFrame] = {}
            for name, factory in model_factories.items():
                model = cast(BaseModel, smoke.guard(factory()))
                cast(Callable[[pd.DataFrame], None], getattr(model, "fit"))(history.copy(deep=True))
                cells[(name, "native")] = capture_prediction(model, features)
                cells[(name, "oracle")] = capture_prediction(model, oracle)
                native, external = cells[(name, "native")], cells[(name, "oracle")]
                rate_columns = [column for column in native.rates if column not in KEYS]
                if set(native.rates.columns) != set(external.rates.columns):
                    raise ValueError(f"{name}: rate trace schema changes between regimes")
                _same(native.rates, external.rates, rate_columns, f"{name}: native/oracle rate identity")
                rate_diagnostics = getattr(model, "rate_diagnostics", None)
                if isinstance(rate_diagnostics, pd.DataFrame):
                    diagnostics[name] = rate_diagnostics.reset_index()

            for name in factories:
                _same(cells[(champion, "native")].projections, cells[(name, "native")].projections,
                      STATES, f"{name}: native event-on/off state parity")
                for regime in ("native", "oracle"):
                    _same(cells[(champion, regime)].projections, cells[(name, regime)].projections,
                          STATES, f"{name}: {regime} shared-state parity")
                    delta = diagnostics.get(name, pd.DataFrame()).get("prior_delta")
                    if history.empty or delta is None or delta.empty or delta.eq(0.0).all():
                        _same(cells[(champion, regime)].projections, cells[(name, regime)].projections,
                              ["projected_points", *LEDGER_COMPONENTS], f"{name}: zero-correction identity")

            gw_dir = output / f"gw{gw:02d}"
            _write_frame(features, gw_dir / "features.parquet")
            for (name, regime), cell in cells.items():
                cell_dir = gw_dir / name / regime
                rate_columns = [column for column in cell.rates if column not in KEYS]
                cast(list[dict[str, object]], manifest["cells"]).append({
                    "model": name, "regime": regime, "gameweek_id": gw,
                    "state_hash": _frame_hash(cell.projections, STATES),
                    "rate_hash": _frame_hash(cell.rates, rate_columns),
                    "projections": _write_frame(cell.projections, cell_dir / "projections.parquet"),
                    "prepared_events": _write_frame(cell.events, cell_dir / "prepared_events.parquet"),
                    "prepared_rates": _write_frame(cell.rates, cell_dir / "prepared_rates.parquet"),
                })
            for name, frame in diagnostics.items():
                _write_frame(frame, gw_dir / name / "rate_diagnostics.parquet")
            cast(list[int], manifest["completed_gameweeks"]).append(gw)
            checkpoint()
            print(f"Retained GW{gw:02d}: Champion and four variants, native/oracle; invariants passed", flush=True)
        if _source_hashes() != sources:
            raise ValueError("Diagnostic source/configuration changed during execution")
        manifest["status"] = "complete"
    except Exception as error:
        manifest.update(status="invalid", error=f"{type(error).__name__}: {error}")
        checkpoint()
        raise
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    checkpoint()
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New durable directory; full development season only")
    args = parser.parse_args()
    print(run(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
