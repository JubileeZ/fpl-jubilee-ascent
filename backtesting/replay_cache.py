"""Synthetic replay problem identities and verified transition checkpoints."""

import json
import os
import uuid
from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple, cast

from backtesting.data_admission import AdmittedInput
from backtesting.forecast_store import _canonical_json_bytes, _sha256_hex, load_forecast_verified, validate_storage_path
from backtesting.replay_state import Decision, Lineup, Outcome, OutcomeBatch, Player, ReplayState, Transition, state_hash, transition
from backtesting.season_rules import Chip, get_rules
from models.scoring_matrix import Position


class AdmissionContext(NamedTuple):
    capability: AdmittedInput
    request: dict[str, Any]
    catalog: dict[str, bytes]
    training_authority: str


def problem_material(forecast_store: Path, forecast_id: str, context: AdmissionContext, state: ReplayState, anchor: dict[str, Any], calendar: dict[str, Any], policy: dict[str, Any], solver: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    forecasts, forecast_material = load_forecast_verified(forecast_store, forecast_id, *context)
    issue = forecast_material["issue"]
    rules = get_rules(state.rules_version)
    if issue["gw"] != state.deadline or issue["season"] != state.rules_version or state.rules_id != rules.rules_id or issue["native_rules"] != rules.rules_id:
        raise ValueError("Forecast and replay scope mismatch")
    if "player_id" not in forecasts or not {player.player_id for player in state.squad} <= set(forecasts["player_id"]):
        raise ValueError("Forecast does not cover owned squad")
    origin = next((o for o in context.request.get("origins", []) if o.get("season") == state.rules_version and o.get("gw") == state.deadline), None)
    if origin and "universe" in origin and not set(origin["universe"]) <= set(forecasts["player_id"]):
        raise ValueError("Forecast does not cover admitted universe")
    if any(not isinstance(value, dict) or not value for value in (anchor, calendar, policy, solver, quality)) or set(solver) != {"version", "binary_sha256", "options"}:
        raise ValueError("Incomplete problem policy")
    if not isinstance(solver["version"], str) or not solver["version"] or not isinstance(solver["binary_sha256"], str) or len(solver["binary_sha256"]) != 64 or any(c not in "0123456789abcdef" for c in solver["binary_sha256"]) or not isinstance(solver["options"], dict):
        raise ValueError("Invalid solver identity")
    return {"version": 1, "forecast_id": forecast_id, "state": asdict(state), "state_hash": state_hash(state), "anchor": anchor, "calendar": calendar, "policy": policy, "rules_id": rules.rules_id, "solver": solver, "quality": quality}


def problem_id(material: dict[str, Any]) -> str:
    return _sha256_hex(_canonical_json_bytes(material))


def _player(value: dict[str, Any]) -> Player:
    return Player(value["player_id"], cast(Position, value["position"]), value["club"], value["purchase"], value["market"], value["purchase_eligible"])


def _state(value: dict[str, Any]) -> ReplayState:
    return ReplayState(value["rules_version"], tuple(_player(p) for p in value["squad"]), value["bank"], value["rules_id"], value["deadline"], value["free_transfers"], tuple((item[0], cast(Chip, item[1]), item[2]) for item in value["chip_history"]), value["previous_transfers"], value["previous_hits"], value["parent_hash"])


def _decision(value: dict[str, Any]) -> Decision:
    lineup = value["lineup"]
    return Decision(tuple((item[0], _player(item[1])) for item in value["transfers"]), Lineup(tuple(lineup["starters"]), tuple(lineup["bench"]), lineup["captain"], lineup["vice"]), value["expected_state_hash"], value["issued_deadline"], cast(Chip | None, value["chip"]))


def _batch(value: dict[str, Any]) -> OutcomeBatch:
    return OutcomeBatch(value["rules_version"], value["deadline"], value["source_identity"], tuple((p, Outcome(item["points"], item["minutes"], item["appeared"])) for p, item in value["outcomes"]))


def _verify_checkpoint(root: Path, forecast_store: Path, contexts: Mapping[str, AdmissionContext], checkpoint_id: str, seen: set[str]) -> dict[str, Any]:
    if len(checkpoint_id) != 64 or any(c not in "0123456789abcdef" for c in checkpoint_id) or checkpoint_id in seen:
        raise ValueError("Invalid checkpoint chain")
    seen.add(checkpoint_id)
    raw = (root / f"{checkpoint_id}.json").read_bytes()
    if _sha256_hex(raw) != checkpoint_id:
        raise ValueError("Checkpoint hash mismatch")
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {"version", "problem", "problem_id", "decision", "outcomes", "result", "parent_checkpoint"} or value["version"] != 1 or problem_id(value["problem"]) != value["problem_id"]:
        raise ValueError("Checkpoint scope mismatch")
    state = _state(value["problem"]["state"])
    if state_hash(state) != value["problem"]["state_hash"]:
        raise ValueError("Checkpoint state mismatch")
    forecast_id = value["problem"]["forecast_id"]
    if not isinstance(forecast_id, str) or len(forecast_id) != 64 or any(c not in "0123456789abcdef" for c in forecast_id):
        raise ValueError("Invalid checkpoint forecast")
    if forecast_id not in contexts:
        raise ValueError("Missing retained forecast admission")
    problem = value["problem"]
    rebuilt = problem_material(forecast_store, forecast_id, contexts[forecast_id], state, problem["anchor"], problem["calendar"], problem["policy"], problem["solver"], problem["quality"])
    if _canonical_json_bytes(rebuilt) != _canonical_json_bytes(problem):
        raise ValueError("Checkpoint problem mismatch")
    actual = transition(state, _decision(value["decision"]), _batch(value["outcomes"]))
    if _canonical_json_bytes(asdict(actual)) != _canonical_json_bytes(value["result"]):
        raise ValueError("Checkpoint transition mismatch")
    parent = value["parent_checkpoint"]
    if parent is None:
        if state.deadline != 1:
            raise ValueError("Missing parent checkpoint")
    else:
        previous = _verify_checkpoint(root, forecast_store, contexts, parent, seen)
        if _canonical_json_bytes(previous["result"]["state"]) != _canonical_json_bytes(asdict(state)) or state.parent_hash != previous["problem"]["state_hash"]:
            raise ValueError("Checkpoint parent state mismatch")
        for key in ("anchor", "calendar", "policy", "rules_id", "solver", "quality"):
            if previous["problem"][key] != value["problem"][key]:
                raise ValueError("Checkpoint parent scope mismatch")
    return value


def checkpoint_transition(root: Path, forecast_store: Path, contexts: Mapping[str, AdmissionContext], problem: dict[str, Any], state: ReplayState, decision: Decision, outcomes: OutcomeBatch, parent_checkpoint: str | None) -> tuple[str, Transition, bool]:
    if _canonical_json_bytes(problem.get("state")) != _canonical_json_bytes(asdict(state)) or problem.get("state_hash") != state_hash(state):
        raise ValueError("Problem pre-state mismatch")
    forecast_id = problem.get("forecast_id")
    if not isinstance(forecast_id, str) or len(forecast_id) != 64 or any(c not in "0123456789abcdef" for c in forecast_id):
        raise ValueError("Invalid problem forecast")
    if forecast_id not in contexts:
        raise ValueError("Missing retained forecast admission")
    rebuilt = problem_material(forecast_store, forecast_id, contexts[forecast_id], state, problem["anchor"], problem["calendar"], problem["policy"], problem["solver"], problem["quality"])
    if _canonical_json_bytes(rebuilt) != _canonical_json_bytes(problem):
        raise ValueError("Problem identity mismatch")
    result = transition(state, decision, outcomes)
    payload = {"version": 1, "problem": problem, "problem_id": problem_id(problem), "decision": asdict(decision), "outcomes": asdict(outcomes), "result": asdict(result), "parent_checkpoint": parent_checkpoint}
    raw = _canonical_json_bytes(payload)
    checkpoint_id = _sha256_hex(raw)
    resolved = validate_storage_path(root)
    resolved.mkdir(parents=True, exist_ok=True)
    attempts = resolved / "attempts"
    attempts.mkdir(parents=True, exist_ok=True)
    attempt = attempts / uuid.uuid4().hex
    attempt.mkdir()
    (attempt / "started.json").write_bytes(_canonical_json_bytes({"version": 1, "started_at": datetime.now(UTC).isoformat(), "deadline": state.deadline, "problem_id": problem_id(problem)}))
    try:
        if parent_checkpoint is None:
            if state.deadline != 1:
                raise ValueError("Missing parent checkpoint")
        else:
            parent = _verify_checkpoint(resolved, forecast_store, contexts, parent_checkpoint, set())
            if _canonical_json_bytes(parent["result"]["state"]) != _canonical_json_bytes(asdict(state)) or state.parent_hash != parent["problem"]["state_hash"]:
                raise ValueError("Checkpoint parent state mismatch")
            if any(parent["problem"][key] != problem[key] for key in ("anchor", "calendar", "policy", "rules_id", "solver", "quality")):
                raise ValueError("Checkpoint parent scope mismatch")
        destination = resolved / f"{checkpoint_id}.json"
        hit = destination.exists()
        if not hit:
            temporary = resolved / (".stage-" + uuid.uuid4().hex)
            temporary.write_bytes(raw)
            try:
                os.rename(temporary, destination)
            except FileExistsError:
                temporary.unlink()
        _verify_checkpoint(resolved, forecast_store, contexts, checkpoint_id, set())
        (attempt / "complete.json").write_bytes(_canonical_json_bytes({"checkpoint_id": checkpoint_id, "cache_hit": hit, "completed_at": datetime.now(UTC).isoformat()}))
        return checkpoint_id, result, hit
    except Exception as exc:
        (attempt / "failed.json").write_bytes(_canonical_json_bytes({"type": type(exc).__name__, "failed_at": datetime.now(UTC).isoformat()}))
        raise
