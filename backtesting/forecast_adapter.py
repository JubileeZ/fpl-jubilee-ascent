"""Synthetic, admitted inputs to one issue-wide model prediction."""

from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd

from backtesting.data_admission import AdmittedInput
from backtesting.forecast_inputs import validate_storage_path, verify_training_bundle
from backtesting.forecast_export import strict_solver_table, validate_components
from backtesting.season_rules import get_rules
from features.availability_snapshots import write_availability_snapshot
from features.builder import EVENT_RATE_MAP, build_features
from models import get_model
from models.base import BaseModel


def predict_synthetic_issue(
    capability: AdmittedInput,
    request: dict[str, Any],
    catalog: dict[str, bytes],
    training_authority: str,
    staging_root: Path,
    model_name: str = "def_xg_shrink_challenger",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Stage verified synthetic data and call the supported concrete model once.

    Result remains diagnostic until component reconciliation and storage exist.
    """
    source = verify_training_bundle(capability, request, catalog, training_authority)
    origin = next(o for o in request["origins"] if o["season"] == capability.season and o["gw"] == capability.gw)
    rules = get_rules(capability.season)
    if origin["native_rules"] != rules.rules_id:
        raise ValueError("Native rules do not match issue")
    tables = source["tables"]
    required_history = {"player_id", "fixture_id", "gameweek_id", "kickoff_time", "minutes", "total_points", "starts", "was_home", "opponent_club_id"} | {item[0] for item in EVENT_RATE_MAP}
    for name in ("history", "seed_history"):
        for row in tables[name]:
            if not required_history <= set(row) or type(row["was_home"]) is not bool:
                raise ValueError("Incomplete performance schema")
            for key in required_history - {"kickoff_time", "was_home"}:
                if type(row[key]) not in (int, float) or not pd.notna(row[key]) or not float("-inf") < float(row[key]) < float("inf"):
                    raise ValueError("Invalid performance value")
    for name in ("history_fixtures", "seed_fixtures"):
        if any(any(type(row.get(k)) is not int or row[k] <= 0 for k in ("home_club_id", "away_club_id")) or row["home_club_id"] == row["away_club_id"] for row in tables[name]):
            raise ValueError("Historical fixture clubs missing")
    current_fixture_ids = {row["id"] for row in tables["target_fixtures"]}
    if any(row["id"] in current_fixture_ids or row["gameweek_id"] >= capability.gw for row in tables["history_fixtures"]):
        raise ValueError("Historical fixture outside issue scope")
    if any(p["availability"] not in ("available", "unavailable") for p in origin["players"]):
        raise ValueError("Unsupported availability semantics")
    root = validate_storage_path(staging_root)
    root.mkdir(parents=True, exist_ok=True)
    current = [{"id": p["id"], "club_id": p["club"], "position_id": p["position"], "now_cost": p["price"], "code": source["seed_mapping"][str(p["id"])].removeprefix("absent:"), "status": "a" if p["availability"] == "available" else "u", "chance_of_playing_next_round": 100.0 if p["availability"] == "available" else 0.0} for p in origin["players"]]
    seed = [{**p, "code": p["seed_key"]} for p in tables["seed_players"]]
    fixtures = [{**f, "finished": False} for f in tables["target_fixtures"]] + tables["history_fixtures"]
    history_columns = sorted(required_history)
    history = pd.DataFrame(tables["history"], columns=history_columns)
    seed_history = pd.DataFrame(tables["seed_history"], columns=history_columns)
    with TemporaryDirectory(prefix="synthetic-issue-", dir=root) as temporary:
        stage = Path(temporary)
        processed, seed_dir, snapshots = stage / "current", stage / "seed", stage / "snapshots"
        processed.mkdir()
        seed_dir.mkdir()
        history.to_parquet(processed / "player_performances.parquet", index=False)
        pd.DataFrame(fixtures).to_parquet(processed / "fixtures.parquet", index=False)
        pd.DataFrame(seed).to_parquet(seed_dir / "players.parquet", index=False)
        seed_history.to_parquet(seed_dir / "player_performances.parquet", index=False)
        pd.DataFrame(tables["seed_fixtures"]).to_parquet(seed_dir / "fixtures.parquet", index=False)
        snapshot = write_availability_snapshot(snapshots, capability.season, capability.gw, origin["deadline"], source["captured_at"], pd.DataFrame(current), pd.DataFrame(tables["clubs"]), pd.DataFrame(fixtures), {"kind": "derived-synthetic"})
        if snapshot is None:
            raise ValueError("Source outside snapshot capture window")
        horizon = min(6, 39 - capability.gw)
        features = build_features(processed, capability.gw, horizon, seed_processed_dir=seed_dir, use_archive_seed=False, as_of_gw=capability.gw, history_before_gw=capability.gw, target_deadline=origin["deadline"], availability_snapshot_root=snapshots, season=capability.season, require_availability_snapshot=True, minutes_prior_source="seed_state")
        if "external_xmins" in features.columns or getattr(features, "oracle_minutes", False):
            raise ValueError("Oracle minutes prohibited in evidence forecasts")
        features["native_rules_version"] = rules.version
        features.attrs["issue_gameweek"] = capability.gw
        model = get_model(model_name)
        if not isinstance(model, BaseModel):
            raise ValueError("Unexpected model factory")
        fit_fn = getattr(model, "fit", None)
        if callable(fit_fn):
            fit_fn(history)
        predictions = model.predict(features, horizon)
        predictions["horizon_lead"] = predictions["gameweek_id"] - capability.gw
        predictions["issue_gameweek"] = capability.gw
        predictions["model"] = model.name
        predictions["rules_version"] = rules.version
        predictions["cutoff"] = origin["deadline"]
        predictions["training_cutoff"] = source["captured_at"]
        strict_solver_table(predictions, capability, request, catalog)
        validate_components(predictions, rules.version)
    return predictions, {"mode": "synthetic_diagnostic", "model": model.name, "issue_gameweek": capability.gw, "training_authority": training_authority, "fit_count": 1, "predict_count": 1, "fit_cache": "unavailable", "oracle_minutes": False, "raw_captured_at": source["captured_at"], "derived_created_at": datetime.now(UTC).isoformat()}
