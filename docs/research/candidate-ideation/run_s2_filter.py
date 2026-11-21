"""Run the untuned S-2 look for an exact S-1-selected, prefix-verified variant."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
import fcntl
from hashlib import sha256
from io import BytesIO
import json
import math
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Any

import pandas as pd

from backtesting.promotion_evidence import GUARD_SEMANTICS
from commands.run_stage_a_and_b import CONFIG_ROOT, REPO
from models.base import BaseModel
from run_s1_replay import (
    SEASON as DEV_SEASON,
    champion_factory,
    core_closure_hash,
    execute_replay,
    model_version_hash,
    protocol_data_files,
    protocol_source_files,
    replay_directory,
    reviewed_grid,
)
from s2_historical_replay_inputs import AMENDMENTS, SEASON, stage_s2_inputs

DAYS = list(range(1, 39))
_PROTOTYPES = REPO / "docs/research/candidate-ideation/prototypes"
_LOOKS = REPO / ".tmp/agent/explore-candidate/pre-slate/s2_filter"
_SHA256 = re.compile(r"[a-f0-9]{64}")


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def validate_prefix_parity(
    parity: pd.DataFrame, binding: dict[str, Any], prefix: list[int]
) -> None:
    model = binding["model"]
    scope = parity.loc[parity["model"].eq(model)].sort_values("origin_gw")
    if scope["origin_gw"].to_list() != prefix:
        raise ValueError(f"Missing or duplicate admitted prefix rows for {model}")
    for row in scope.itertuples(index=False):
        gw = str(row.origin_gw)
        if (
            row.solver_forecast_hash_match is not True
            or row.settled_outcome_match is not True
            or not 0 <= row.maximum_absolute_component_diff <= 1e-10
            or row.evaluation_identity != binding["evaluation_identity"]
            or row.protocol_hash != binding["protocol_hash"]
            or row.model_version_hash != binding["model_version_hash"]
            or row.checkpoint_id != binding["checkpoint_ids"][gw]
            or row.solver_input_sha256 != row.checkpoint_forecast_sha256
            or row.checkpoint_forecast_sha256 != binding["forecast_hashes"][gw]
        ):
            raise ValueError(f"Admitted prefix evidence mismatch for {model} GW{gw}")


@dataclass(frozen=True)
class ReviewedModel:
    name: str
    factory: Callable[[], BaseModel]
    source_digest: str
    version: str


@dataclass(frozen=True)
class FrozenSelection:
    pin_digest: str
    core_hash: str
    lane: str
    arms: dict[str, ReviewedModel]
    margins: dict[str, float]

    @property
    def attempt_dir(self) -> Path:
        directory = _LOOKS / self.lane
        if directory.resolve() != directory:
            raise ValueError(f"S-2 reservation path must be canonical: {directory}")
        return directory


def champion_binding(row: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "evaluation_identity",
        "model_version_hash",
        "protocol_hash",
        "source_sha256",
        "checkpoint_ids",
        "forecast_hashes",
    )
    return {"model": row["champion"], **{key: row[f"champion_{key}"] for key in fields}}


def _validate_run_provenance(run: dict[str, Any]) -> None:
    fields = (
        "evaluation_identity",
        "model_version_hash",
        "protocol_hash",
        "source_sha256",
    )
    if not all(is_sha256(run[key]) for key in fields):
        raise ValueError(f"Missing replay provenance digest for {run['model']}")
    for field in ("checkpoint_ids", "forecast_hashes"):
        evidence = run[field]
        if (
            not isinstance(evidence, dict)
            or set(evidence) != {str(day) for day in DAYS}
            or not all(is_sha256(digest) for digest in evidence.values())
        ):
            raise ValueError(f"Incomplete {field} for {run['model']}")


def _verified_selection(path: Path) -> FrozenSelection:
    path = path.resolve()
    raw_pin = path.read_bytes()
    pin = json.loads(raw_pin)
    champion, champion_constructor, champion_source = champion_factory()
    if pin["schema_version"] != 1 or pin["champion"] != champion:
        raise ValueError("Stale or incompatible Dev selection")
    source = (REPO / pin["prototype_path"]).resolve()
    if (
        not source.is_relative_to(_PROTOTYPES)
        or source.name != "prototypes.py"
        or source.parent.parent != _PROTOTYPES
    ):
        raise ValueError(
            "Pinned candidate source must identify a canonical prototype lane"
        )
    grid = reviewed_grid(source, pin["source_sha256"])
    if champion in grid:
        raise ValueError("Reviewed grid collides with the confirmed Champion")

    evidence: dict[str, bytes] = {}
    for name in (
        "development_summary",
        "development_guard_margins",
        "development_prefix_parity",
    ):
        ref = pin[name]
        payload = (path.parent / ref["path"]).read_bytes()
        if sha256(payload).hexdigest() != ref["sha256"]:
            raise ValueError(f"Pinned evidence mismatch: {name}")
        evidence[name] = payload

    results = json.loads(evidence["development_summary"])
    names = [row["model"] for row in results]
    if len(names) != len(grid) or set(names) != set(grid):
        raise ValueError(
            "Dev summary must include exactly one row per reviewed constructor"
        )
    core_hash = core_closure_hash()
    champion_version = model_version_hash(champion, champion_source, core_hash)
    champ_run = champion_binding(results[0])
    _validate_run_provenance(champ_run)
    if (
        champ_run["source_sha256"] != champion_source
        or champ_run["model_version_hash"] != champion_version
    ):
        raise ValueError("Confirmed Champion model closure differs from its S-1 run")
    anchor_id = results[0]["anchor_id"]
    opening_hash = results[0]["opening_state_hash"]
    margins_digest = sha256(evidence["development_guard_margins"]).hexdigest()
    if not isinstance(anchor_id, str) or not anchor_id or not is_sha256(opening_hash):
        raise ValueError("Missing Dev opening anchor identity")
    identities = {champ_run["evaluation_identity"]}
    for row in results:
        _validate_run_provenance(row)
        if (
            row["season"] != DEV_SEASON
            or champion_binding(row) != champ_run
            or row["champion"] != champion
            or row["anchor_id"] != anchor_id
            or row["opening_state_hash"] != opening_hash
            or row["protocol_hash"] != champ_run["protocol_hash"]
            or row["evaluation_identity"] in identities
        ):
            raise ValueError(
                "Dev comparison requires a common opening anchor and exactly one Champion run"
            )
        identities.add(row["evaluation_identity"])
        if row["guard_margins_sha256"] != margins_digest:
            raise ValueError(
                "Pinned guard margins differ from the retained Dev comparison"
            )
        if row["source_sha256"] != pin["source_sha256"] or row[
            "model_version_hash"
        ] != model_version_hash(row["model"], row["source_sha256"], core_hash):
            raise ValueError(f"{row['model']} model closure differs from its S-1 run")
        if (
            type(row["delta_net"]) not in (int, float)
            or not math.isfinite(row["delta_net"])
            or row["candidate_net"] - row["champion_net"] != row["delta_net"]
            or row["champion_net"] != results[0]["champion_net"]
            or any(
                type(row[key]) is not bool
                for key in ("projection_guards_ok", "segment_guards_ok")
            )
        ):
            raise ValueError(f"Invalid Dev gate result for {row['model']}")

    qualifies = [
        row
        for row in results
        if row["delta_net"] > 0
        and row["projection_guards_ok"]
        and row["segment_guards_ok"]
    ]
    if not qualifies:
        raise ValueError("No S-1 grid variant passed the Dev gate")
    chosen = min(qualifies, key=lambda row: (-row["delta_net"], row["model"]))
    if any(
        pin[key] != chosen[key]
        for key in (
            "model",
            "source_sha256",
            "evaluation_identity",
            "protocol_hash",
            "model_version_hash",
            "champion_evaluation_identity",
            "champion_model_version_hash",
        )
    ):
        raise ValueError(
            "Pin must identify the best eligible S-1 variant and its exact evidence"
        )

    parity = pd.read_csv(BytesIO(evidence["development_prefix_parity"]))
    for binding in (chosen, champ_run):
        validate_prefix_parity(parity, binding, list(range(1, 8)))
    margins = json.loads(evidence["development_guard_margins"])
    if set(margins) != set(GUARD_SEMANTICS) or not all(
        type(value) in (int, float) and math.isfinite(value) and value >= 0
        for value in margins.values()
    ):
        raise ValueError("Incomplete or invalid pinned Development guard margins")
    constructor = grid[pin["model"]]
    instance = constructor()
    if not pin["parameters"] or any(
        getattr(instance, param, None) != value
        for param, value in pin["parameters"].items()
    ):
        raise ValueError(
            "Pinned candidate parameters differ from the reviewed constructor"
        )
    return FrozenSelection(
        sha256(raw_pin).hexdigest(),
        core_hash,
        source.parent.name,
        {
            "champion": ReviewedModel(
                champion, champion_constructor, champion_source, champion_version
            ),
            "candidate": ReviewedModel(
                pin["model"],
                constructor,
                pin["source_sha256"],
                pin["model_version_hash"],
            ),
        },
        margins,
    )


def _file_digests(paths: list[Path]) -> dict[str, str]:
    return {path.name: sha256(path.read_bytes()).hexdigest() for path in paths}


def attempt_identity(selection: FrozenSelection) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "season": SEASON,
        "lane": selection.lane,
        "pin_sha256": selection.pin_digest,
        "core_closure_hash": selection.core_hash,
        "arms": {
            arm: {
                "model": model.name,
                "model_version_hash": model.version,
                "source_sha256": model.source_digest,
            }
            for arm, model in selection.arms.items()
        },
        "protocol_source_digests": _file_digests(
            [
                Path(__file__),
                Path(__file__).with_name("run_s1_replay.py"),
                Path(__file__).with_name("s2_historical_replay_inputs.py"),
                Path(__file__).with_name("historical_replay_inputs.py"),
                Path(__file__).with_name("compare_historical_replays.py"),
                Path(__file__).with_name("audit_historical_prefix.py"),
                *protocol_source_files(),
            ]
        ),
        "initial_manifest_digests": _file_digests(
            [AMENDMENTS, CONFIG_ROOT / "dev_mirror_2024_25_manifest.json"]
        ),
        "required_deadlines": DAYS,
    }


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    )


def _protocol_hash(attempt_digest: str, seed: Path) -> str:
    paths = protocol_data_files(SEASON, seed)
    return sha256(
        bytes.fromhex(attempt_digest)
        + b"".join(sha256(path.read_bytes()).digest() for path in paths)
    ).hexdigest()


def _reserve_json(path: Path, payload: dict[str, Any]) -> None:
    """Install a fully written reservation atomically without replacing a prior look."""
    encoded = _canonical_bytes(payload)
    with NamedTemporaryFile(dir=path.parent) as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
        try:
            os.link(handle.name, path)
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != encoded:
                raise ValueError(
                    f"Incompatible S-2 look already reserved at {path}"
                ) from None


def verified_s2_directories(
    selection: FrozenSelection,
    *,
    require_both_input_inventories: bool = False,
) -> tuple[dict[str, Path], str]:
    directory = selection.attempt_dir
    attempt = directory / "attempt.json"
    if attempt.is_symlink() or attempt.read_bytes() != _canonical_bytes(
        attempt_identity(selection)
    ):
        raise ValueError("S-2 reservation differs from the pinned attempt")
    protocol_path = directory / "protocol.json"
    if protocol_path.is_symlink():
        raise ValueError("S-2 shared protocol must reside under its reservation")
    protocol = json.loads(protocol_path.read_bytes())
    if protocol["attempt_sha256"] != sha256(
        attempt.read_bytes()
    ).hexdigest() or not is_sha256(protocol["protocol_hash"]):
        raise ValueError("S-2 protocol differs from the reserved attempt")
    result = {
        arm: replay_directory(
            directory / arm, model.name, 38, model.version, protocol["protocol_hash"]
        )
        for arm, model in selection.arms.items()
    }
    if any(path.resolve() != path for path in result.values()):
        raise ValueError("S-2 replay paths must remain under their reserved arms")
    if require_both_input_inventories:
        for arm in result:
            seed = directory / arm / "seed/seed_2023-24"
            if (
                _protocol_hash(protocol["attempt_sha256"], seed)
                != protocol["protocol_hash"]
            ):
                raise ValueError(
                    f"S-2 {arm} archive or staged seed changed after reservation"
                )
    return result, protocol["protocol_hash"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument(
        "--work",
        type=Path,
        help="Optional compatibility check for the canonical lane folder",
    )
    parser.add_argument("--arm", choices=("champion", "candidate"), required=True)
    args = parser.parse_args()
    selection = _verified_selection(args.pin)
    directory = selection.attempt_dir
    if args.work is not None and args.work.resolve() != directory:
        parser.error(f"S-2 work folder must be {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    attempt = attempt_identity(selection)
    _reserve_json(directory / "attempt.json", attempt)

    work = directory / args.arm
    if work.resolve() != work or (work / "replays").resolve() != work / "replays":
        raise ValueError("S-2 replay path must remain under its reserved arm")
    work.mkdir(exist_ok=True)
    with (work / ".arm.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest, seed = stage_s2_inputs(work)
        attempt_digest = sha256(_canonical_bytes(attempt)).hexdigest()
        _reserve_json(
            directory / "protocol.json",
            {
                "attempt_sha256": attempt_digest,
                "protocol_hash": _protocol_hash(attempt_digest, seed),
            },
        )
        directories, protocol = verified_s2_directories(selection)
        model = selection.arms[args.arm]
        if directories[args.arm].parent.parent != work:
            raise ValueError("Replay arm does not match its reservation")
        execute_replay(
            model.name,
            model.factory,
            model.source_digest,
            work,
            SEASON,
            manifest,
            seed,
            38,
            model.version,
            protocol,
        )


if __name__ == "__main__":
    main()
