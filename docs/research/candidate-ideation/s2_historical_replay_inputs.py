"""Assemble S-2 issue inputs from pinned fixtures and dated kickoff notices."""

from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, cast

import pandas as pd

from backtesting.empirical_mirrors import load_empirical_manifest_bundle
from backtesting.fplcache_ingest import _unpack_bootstrap_xz
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
from historical_replay_inputs import FIXTURE_COLUMNS, _checked_bytes

SEASON = "2024-25"
AMENDMENTS = Path(__file__).with_name("s2_historical_fixture_amendments.csv")


def _fixture_table(origin: dict[str, Any], amendments: pd.DataFrame) -> pd.DataFrame:
    gw = origin["gw"]
    receipt = origin["fixtures"]
    deadline = datetime.fromisoformat(origin["deadline_utc"])
    captured = datetime.fromisoformat(receipt["commit_time_utc"])
    if captured >= deadline:
        raise ValueError(f"Fixtures captured after the S-2 GW{gw} deadline")
    path = MIRROR_ROOT / receipt["local_relpath"]
    _checked_bytes(path, receipt["blob_sha256"])
    fixtures = pd.read_csv(path, usecols=list(FIXTURE_COLUMNS)).rename(
        columns=FIXTURE_COLUMNS
    )
    if len(fixtures) != 380 or not fixtures["id"].is_unique:
        raise ValueError(f"Incomplete S-2 fixture universe for GW{gw}")
    fixtures = fixtures.set_index("id")
    for row in amendments[amendments["origin_gw"].eq(gw)].itertuples(index=False):
        if (
            not captured.date()
            <= date.fromisoformat(row.announced_date)
            < deadline.date()
            or not gw <= row.target_gw <= min(gw + 5, 38)
            or fixtures.at[row.fixture_id, "gameweek_id"] != row.target_gw
        ):
            raise ValueError(
                f"Amendment would alter the point-in-time GW assignment at S-2 GW{gw}"
            )
        fixtures.at[row.fixture_id, "kickoff_time"] = row.kickoff_utc
    fixtures = fixtures.reset_index().dropna(subset=["gameweek_id"])
    fixtures["gameweek_id"] = fixtures["gameweek_id"].astype(int)
    for col in ("finished", "started"):
        fixtures[col] = fixtures[col].astype(str).str.lower().isin(["true", "1"])
    return fixtures


def stage_s2_inputs(work: Path) -> tuple[dict[str, Any], Path]:
    manifest_path = CONFIG_ROOT / "dev_mirror_2024_25_manifest.json"
    admitted = load_empirical_manifest_bundle(
        manifest_path,
        quarantine_root=MIRROR_ROOT,
        prefix_end_gw=1,
        require_admitted=True,
    )
    manifest = json.loads(manifest_path.read_text())
    if manifest["season"] != SEASON or [o["gw"] for o in manifest["origins"]] != list(
        range(1, 39)
    ):
        raise ValueError("Expected full S-2 origin schedule")
    if len(admitted["origins"]) != 1:
        raise ValueError("Expected an independently admitted GW1 prefix")
    amendments = pd.read_csv(AMENDMENTS)
    amendment_digest = sha256(AMENDMENTS.read_bytes()).hexdigest()
    if amendments.duplicated(["origin_gw", "fixture_id"]).any():
        raise ValueError("Duplicate S-2 kickoff amendment")
    archive = REPO / "data/archive" / SEASON / "processed"
    all_history = pd.read_parquet(archive / "player_performances.parquet")
    roster = pd.read_parquet(archive / "players.parquet", columns=["id", "position_id"])
    eligible = roster[roster["position_id"].between(1, 4)]["id"]
    all_history = all_history[all_history["player_id"].isin(eligible)]
    seed = _prepare_filtered_seed("2023-24", work / "seed")

    for origin in manifest["origins"]:
        gw = origin["gw"]
        deadline = datetime.fromisoformat(origin["deadline_utc"])
        receipt = origin["bootstrap"]
        capture = datetime.fromisoformat(receipt["capture_upper_utc"])
        if receipt["status"] != "supported" or capture >= deadline:
            raise ValueError(f"Missing supported S-2 bootstrap for GW{gw}")
        path = MIRROR_ROOT / receipt["local_relpath"]
        _, payload = _unpack_bootstrap_xz(_checked_bytes(path, receipt["blob_sha256"]))
        players, clubs = _bootstrap_players_and_clubs(path, capture_upper=capture)
        players = players[players["position_id"].between(1, 4)].copy()
        fixtures = _fixture_table(origin, amendments)
        checked = {
            event["id"]
            for event in payload["events"]
            if event["id"] < gw and event["finished"] is True
        }
        past = pd.to_datetime(fixtures["kickoff_time"], utc=True, errors="coerce").lt(
            deadline
        )
        fixtures["finished"] |= fixtures["gameweek_id"].isin(checked) & past
        history = completed_performance_rows(
            history_before_target(all_history, gw, deadline, True), fixtures
        )

        staged = work / "verified_inputs" / f"gw{gw:02d}"
        staged.mkdir(parents=True, exist_ok=True)
        history.to_parquet(staged / "player_performances.parquet", index=False)
        players.to_parquet(staged / "market.parquet", index=False)
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
        fixture_receipt = origin["fixtures"]
        caps = [capture, datetime.fromisoformat(fixture_receipt["commit_time_utc"])]
        dates = amendments.loc[amendments["origin_gw"].eq(gw), "announced_date"]
        # The notices carry release dates. End of that date bounds availability.
        caps.extend(datetime.fromisoformat(f"{day}T23:59:59+00:00") for day in dates)
        captured = max(caps)
        sources = {
            "kind": "historical_filter",
            "fixture_sha256": fixture_receipt["blob_sha256"],
            "fixture_capture_upper": fixture_receipt["commit_time_utc"],
            "kickoff_amendments_sha256": amendment_digest,
            "bootstrap_sha256": receipt["blob_sha256"],
            "bootstrap_capture_upper": capture.isoformat(),
        }
        write_availability_snapshot(
            staged / "snapshots",
            SEASON,
            gw,
            deadline,
            captured,
            availability,
            clubs,
            fixtures,
            sources,
        )
        snapshot = resolve_latest_snapshot(staged / "snapshots", SEASON, gw, deadline)
        metadata = cast(dict[str, Any], snapshot["metadata"]) if snapshot else {}
        if (
            metadata.get("content_hash")
            != canonical_content_hash(availability, clubs, fixtures)
            or metadata.get("source_endpoint_versions") != sources
            or datetime.fromisoformat(metadata["captured_at"]) != captured
        ):
            raise ValueError(f"Unverified S-2 package for GW{gw}")
    return manifest, seed
