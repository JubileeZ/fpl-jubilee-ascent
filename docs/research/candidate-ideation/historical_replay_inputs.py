"""Stage S-1 archive inputs with deadline-dated fixtures and admitted prefix history."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import pandas as pd

from backtesting.empirical_mirrors import (
    extract_prior_settled_df,
    load_empirical_manifest_bundle,
)
from commands.run_stage_a_and_b import (
    CONFIG_ROOT,
    MIRROR_ROOT,
    REPO,
    _bootstrap_players_and_clubs,
    _prepare_filtered_seed,
)
from features.availability_snapshots import (
    canonical_content_hash,
    resolve_latest_snapshot,
    write_availability_snapshot,
)
from features.builder import completed_performance_rows, history_before_target

SOURCE_PATH = Path(__file__).with_name("s1_historical_fixture_sources.csv")
SEASON = "2025-26"
PREFIX_END = 7
FIXTURE_COLUMNS = {
    "id": "id",
    "event": "gameweek_id",
    "team_h": "home_club_id",
    "team_a": "away_club_id",
    "kickoff_time": "kickoff_time",
    "finished": "finished",
    "started": "started",
    "team_h_difficulty": "team_h_difficulty",
    "team_a_difficulty": "team_a_difficulty",
}
_PERFORMANCE_NAMES = {
    "element": "player_id",
    "fixture": "fixture_id",
    "GW": "gameweek_id",
    "opponent_team": "opponent_club_id",
    "value": "price",
}


def _checked_bytes(path: Path, digest: str, source_url: str | None = None) -> bytes:
    if path.is_file():
        payload = path.read_bytes()
    elif source_url is not None:
        with urlopen(source_url, timeout=30) as response:
            payload = response.read()
    else:
        raise FileNotFoundError(path)
    if sha256(payload).hexdigest() != digest:
        raise ValueError(f"Pinned input SHA-256 mismatch at {path}")
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return payload


def _admitted_history(
    gw: int, manifest: dict[str, Any], schema: pd.DataFrame
) -> pd.DataFrame:
    if gw == 1:
        return schema.iloc[:0].copy()
    receipt = manifest["origins"][gw - 2]["settled_outcomes"]
    deadline = datetime.fromisoformat(manifest["origins"][gw - 1]["deadline_utc"])
    if (
        not receipt["historical_performance_ready_by_next_gw"]
        or datetime.fromisoformat(receipt["finalized_at_utc"]) >= deadline
    ):
        raise ValueError(f"Admitted history not available before GW{gw}")
    data = _checked_bytes(
        MIRROR_ROOT / receipt["local_relpath"], receipt["blob_sha256"]
    )
    parsed = extract_prior_settled_df(data, before_gw=gw).rename(
        columns=_PERFORMANCE_NAMES
    )
    parsed["was_home"] = (
        parsed["was_home"].astype(str).str.lower().map({"true": True, "false": False})
    )
    if parsed["was_home"].isna().any():
        raise ValueError(f"Invalid empirical home/away flag before GW{gw}")
    return parsed[schema.columns].astype(schema.dtypes.to_dict())


def stage_s1_inputs(work: Path) -> tuple[dict[str, Any], Path]:
    """Stage full development schedule and its original admitted GW1–7 inputs."""
    manifest_path = CONFIG_ROOT / "dev_mirror_2025_26_manifest.json"
    load_empirical_manifest_bundle(
        manifest_path,
        quarantine_root=MIRROR_ROOT,
        prefix_end_gw=PREFIX_END,
        require_admitted=True,
    )
    manifest = json.loads(manifest_path.read_text())
    sources = pd.read_csv(SOURCE_PATH).set_index("origin_gw")
    if (
        sources.index.to_list() != list(range(1, 39))
        or not sources["season"].eq(SEASON).all()
    ):
        raise ValueError(
            "S-1 replay requires exactly one pinned fixture source for every deadline"
        )
    archive = REPO / "data/archive" / SEASON / "processed"
    archive_history = pd.read_parquet(archive / "player_performances.parquet")
    seed = _prepare_filtered_seed("2024-25", work / "seed")
    for origin in manifest["origins"]:
        gw = int(origin["gw"])
        source = sources.loc[gw]
        deadline = datetime.fromisoformat(origin["deadline_utc"])
        if (
            source["deadline_utc"] != origin["deadline_utc"]
            or datetime.fromisoformat(source["capture_upper_utc"]) >= deadline
        ):
            raise ValueError(f"Unbound or post-deadline fixture snapshot for GW{gw}")
        if gw <= PREFIX_END:
            receipt = origin["fixtures"]
            if (
                source["sha256"] != receipt["blob_sha256"]
                or source["usage"] != "admitted_prefix"
            ):
                raise ValueError(
                    f"Fixture identity diverges from the admitted GW{gw} prefix"
                )
            fixture_path = MIRROR_ROOT / receipt["local_relpath"]
            _checked_bytes(fixture_path, source["sha256"])
            raw_fixtures = pd.read_csv(fixture_path)
            history = _admitted_history(gw, manifest, archive_history)
        else:
            fixture_path = work / "fixtures" / f"gw{gw:02d}.json"
            _checked_bytes(fixture_path, source["sha256"], source["source_url"])
            raw_fixtures = pd.read_json(fixture_path)
            history = archive_history
        if len(raw_fixtures) != 380 or raw_fixtures["id"].nunique() != 380:
            raise ValueError(f"Incomplete fixture universe for GW{gw}")
        fixtures = (
            raw_fixtures[list(FIXTURE_COLUMNS)]
            .rename(columns=FIXTURE_COLUMNS)
            .dropna(subset=["gameweek_id"])
            .copy()
        )
        fixtures["gameweek_id"] = fixtures["gameweek_id"].astype(int)
        for col in ("finished", "started"):
            fixtures[col] = fixtures[col].astype(str).str.lower().isin(["true", "1"])
        history = completed_performance_rows(
            history_before_target(history, gw, deadline, True), fixtures
        )

        receipt = origin["bootstrap"]
        capture = datetime.fromisoformat(receipt["capture_upper_utc"])
        if receipt["status"] != "supported" or capture >= deadline:
            raise ValueError(f"Missing supported pre-deadline bootstrap for GW{gw}")
        bootstrap_path = MIRROR_ROOT / receipt["local_relpath"]
        _checked_bytes(bootstrap_path, receipt["blob_sha256"])
        players, clubs = _bootstrap_players_and_clubs(
            bootstrap_path, capture_upper=capture
        )
        players = players[players["position_id"].between(1, 4)].copy()
        path = work / "verified_inputs" / f"gw{gw:02d}"
        path.mkdir(parents=True, exist_ok=True)
        history.to_parquet(path / "player_performances.parquet", index=False)
        players.to_parquet(path / "market.parquet", index=False)
        availability = players[
            [
                "id",
                "club_id",
                "position_id",
                "now_cost",
                "code",
                "status",
                "chance_of_playing_next_round",
            ]
        ]
        endpoint_sources = {
            "kind": "historical_replay",
            "fixtures_sha256": source["sha256"],
            "fixtures_capture_upper_utc": str(source["capture_upper_utc"]),
            "bootstrap_sha256": receipt["blob_sha256"],
            "bootstrap_capture_upper_utc": receipt["capture_upper_utc"],
        }
        package_capture = max(
            capture, datetime.fromisoformat(source["capture_upper_utc"])
        )
        write_availability_snapshot(
            path / "snapshots",
            SEASON,
            gw,
            deadline,
            package_capture,
            availability,
            clubs,
            fixtures,
            endpoint_sources,
        )
        snapshot = resolve_latest_snapshot(path / "snapshots", SEASON, gw, deadline)
        expected_hash = canonical_content_hash(availability, clubs, fixtures)
        if (
            snapshot is None
            or snapshot["metadata"]["content_hash"] != expected_hash
            or snapshot["metadata"]["source_endpoint_versions"] != endpoint_sources
            or datetime.fromisoformat(snapshot["metadata"]["captured_at"])
            != package_capture
        ):
            raise ValueError(f"Could not stage availability snapshot for GW{gw}")
    return manifest, seed
