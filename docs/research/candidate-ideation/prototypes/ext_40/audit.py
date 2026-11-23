"""Static feature and I/O boundary audit for staged EXT-40 composition."""

from __future__ import annotations

import ast
from hashlib import sha256
from pathlib import Path
import re

from backtesting.forecast_export import REQUIRED_COMPONENTS
from features.builder import TERMINAL_PLAYER_COLUMNS
from prototypes.ext_40.prototypes import (
    COUNT_COLUMNS,
    EVENT,
    FEATURES,
    KEYS,
    STATE_COLUMNS,
)

_STAGED = {
    "panel.py": {
        "_settled_source_rows",
        "_source_fixture_context",
        "load_source_panel",
    },
    "run.py": {
        "_issue_input",
        "_load_outcomes",
        "_staged_champion",
        "_experiment_identity",
        "run_forecasts",
        "run_replay",
        "main",
    },
    "prototypes.py": set(),
}
_PROCESS_LOCALS = {
    "rate",
    "form",
    "support",
    "identity",
    "opponent_form",
    "index_gw",
    "target",
    "weighted_minutes",
    "weighted_process",
    "valid_process",
    "xgc",
    "complete",
    "starts",
    "long_minutes",
    "long_process",
    "recent_minutes",
    "recent_process",
    "_process",
    "_minutes",
    "count",
    "sum",
    "static",
    "prior",
    "dynamic",
    "",
}
_SOURCE_FIXTURE_COLUMNS = {"id", "home_club_id", "away_club_id"}
_FILE_CALLS = {
    "open",
    "read_bytes",
    "read_text",
    "read_csv",
    "read_parquet",
    "read_json",
    "urlopen",
    "write_bytes",
    "write_text",
    "to_csv",
    "to_parquet",
    "mkdir",
    "glob",
    "_checked_bytes",
    "_bootstrap_players_and_clubs",
    "_admitted_history",
    "resolve_latest_snapshot",
}


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def _column_literals(node: ast.AST) -> set[str]:
    values = []
    if isinstance(node, ast.Subscript):
        values = [node.slice]
    if isinstance(node, ast.Call):
        values.extend(
            item.value
            for item in node.keywords
            if item.arg in {"columns", "subset", "on", "by"}
        )
        if _call_name(node) == "get" and node.args:
            values.append(node.args[0])
    return {
        str(item.value)
        for value in values
        for item in ast.walk(value)
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    }


def audit() -> str:
    manifest = {entry.partition(".")[2] for entry in FEATURES}
    forbidden = {
        entry.partition(".")[2] for entry in FEATURES if entry.startswith("features.")
    }.intersection(TERMINAL_PLAYER_COLUMNS)
    if forbidden:
        raise ValueError(
            f"EXT-40 manifest references terminal features: {sorted(forbidden)}"
        )
    allowed = (
        manifest
        | _PROCESS_LOCALS
        | _SOURCE_FIXTURE_COLUMNS
        | set(KEYS)
        | set(COUNT_COLUMNS)
        | set(EVENT)
        | set(STATE_COLUMNS)
        | set(REQUIRED_COMPONENTS)
        | {"projected_points", "projected_minutes", "club_id"}
    )
    digests = []
    for filename, allowed_readers in _STAGED.items():
        raw = Path(__file__).with_name(filename).read_bytes()
        digests.append(sha256(raw).digest())
        tree = ast.parse(raw, filename=filename)
        if filename != "run.py" and re.search(r"\b20\d{2}-\d{2}\b", raw.decode()):
            raise ValueError(
                f"Season literal in season-agnostic EXT-40 code: {filename}"
            )
        staged_nodes = {
            node
            for function in tree.body
            if isinstance(function, ast.FunctionDef)
            and function.name in allowed_readers
            for node in ast.walk(function)
        }
        for node in ast.walk(tree):
            if node in staged_nodes:
                continue
            if isinstance(node, ast.Call) and _call_name(node) in _FILE_CALLS:
                raise ValueError(f"Unstaged file I/O in {filename}:{node.lineno}")
            if filename != "run.py" and (extra := _column_literals(node) - allowed):
                raise ValueError(
                    f"Undeclared input or local column in {filename}: {sorted(extra)}"
                )
    return sha256(b"".join(digests)).hexdigest()


if __name__ == "__main__":
    print(f"EXT-40 staged source and feature audit passed: {audit()}")
