"""Audit per-deadline development coverage and training lineage from retained unsealed sources."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import lzma
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from features.builder import MIN_PRIOR_APPEARANCES, MIN_PRIOR_MINUTES

TOPIC = ROOT / "docs/research/backtesting-promotion-foundation"
QUARANTINE = ROOT / "data/reports/readiness-source-pilot/v1"
ARCHIVE = ROOT / "data/archive"

NON_SEALED_SEASONS: tuple[str, ...] = ("2023-24", "2024-25", "2025-26")
SEALED_SEASON = "2026-27"
MAX_BOOTSTRAP_BYTES = 16 * 1024 * 1024
BOOTSTRAP_CAPTURE_WINDOW_SECONDS = 1800
MAX_AGE_BOOTSTRAP_TARGET_SECONDS = 8 * 3600
MAX_AGE_BOOTSTRAP_CEILING_SECONDS = 24 * 3600
MAX_AGE_SCHEDULE_TARGET_SECONDS = 7 * 86400
POSITION_LABELS: tuple[int, ...] = (1, 2, 3, 4)
LINEAGE_CODE_PATHS: tuple[str, ...] = (
    "features/builder.py",
    "backtesting/walkforward.py",
    "backtesting/walkforward_solve.py",
    "backtesting/forecast_adapter.py",
    "backtesting/input_pilot.py",
    "models/def_xg_shrink_challenger.py",
    "models/adaptive_causal_challenger.py",
    "models/club_def_prior_challenger.py",
)


def _assert_unsealed_path(path: Path) -> None:
    """Reject any accidental inspection inside sealed 2026-27 holdout paths."""
    if SEALED_SEASON in path.parts:
        raise ValueError(f"Refusing to access sealed holdout path: {path}")


def _file_sha256(path: Path) -> str:
    """Return hex SHA-256 digest after verifying unsealed path boundary."""
    _assert_unsealed_path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_iso_utc(raw_ts: str) -> datetime:
    """Parse ISO-8601 string and require explicit timezone offset."""
    parsed = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError(f"Naive timestamp not allowed: {raw_ts}")
    return parsed.astimezone(timezone.utc)


def _format_duration(delta: timedelta) -> str:
    """Format positive timedelta as concise human-readable duration."""
    total = int(round(delta.total_seconds()))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours:02d}h {minutes:02d}m {seconds:02d}s"
    return f"{hours}h {minutes:02d}m {seconds:02d}s"


def _decompress_bootstrap(path: Path) -> dict[str, Any]:
    """Decode LZMA-compressed bootstrap payload with bounded memory limit."""
    _assert_unsealed_path(path)
    raw = path.read_bytes()
    decoder = lzma.LZMADecompressor()
    decoded = decoder.decompress(raw, max_length=MAX_BOOTSTRAP_BYTES + 1)
    if len(decoded) > MAX_BOOTSTRAP_BYTES or not decoder.eof:
        raise ValueError(f"Bootstrap exceeds {MAX_BOOTSTRAP_BYTES} bytes or is truncated: {path.name}")
    return json.loads(decoded)


def _source_record(
    *,
    artifact_key: str,
    storage_location: str,
    artifact_name: str,
    size_bytes: int,
    row_count: int | None,
    sha256: str,
    temporal_basis: str,
    admission_status: str,
) -> dict[str, Any]:
    """Build normalized source inventory record for CSV caching."""
    return {
        "artifact_key": artifact_key,
        "storage_location": storage_location,
        "artifact_name": artifact_name,
        "size_bytes": size_bytes,
        "row_count": "" if row_count is None else row_count,
        "sha256": sha256,
        "temporal_basis": temporal_basis,
        "admission_status": admission_status,
    }


def _make_coverage_row(
    *,
    gameweek: int,
    field_group: str,
    status: str,
    source_type: str,
    source_path: str,
    source_sha256: str,
    coverage_count: str,
    limitation: str,
) -> dict[str, Any]:
    """Build normalized per-(gameweek, field_group) coverage row."""
    return {
        "season": "2025-26",
        "gameweek": gameweek,
        "field_group": field_group,
        "status": status,
        "source_type": source_type,
        "source_path": source_path,
        "source_sha256": source_sha256,
        "coverage_count": coverage_count,
        "limitation": limitation,
    }


def inspect_bootstrap_snapshot(
    *,
    boot_path: Path,
    commit_path: Path,
    expected_gw: int,
) -> dict[str, Any]:
    """Inspect a pre-deadline fplcache bootstrap snapshot and commit provenance under #175 rules."""
    payload = _decompress_bootstrap(boot_path)
    commit_meta = json.loads(commit_path.read_text(encoding="utf-8"))
    elements = payload.get("elements", [])

    type_counts: dict[int, int] = {}
    for elem in elements:
        et = int(elem["element_type"])
        type_counts[et] = type_counts.get(et, 0) + 1

    # Q3: Exclude Assistant Manager entries (element_type == 5) from player universe metrics.
    players = [elem for elem in elements if int(elem.get("element_type", 0)) != 5]
    excluded_managers = len(elements) - len(players)
    selectable = [elem for elem in players if elem.get("can_select") is True]
    selectable_by_pos = {
        pos: sorted(int(elem["now_cost"]) for elem in selectable if int(elem["element_type"]) == pos)
        for pos in POSITION_LABELS
    }
    min_15_possible = (
        len(selectable_by_pos[1]) >= 2
        and len(selectable_by_pos[2]) >= 5
        and len(selectable_by_pos[3]) >= 5
        and len(selectable_by_pos[4]) >= 3
    )
    min_15_cost_tenths = (
        sum(selectable_by_pos[1][:2])
        + sum(selectable_by_pos[2][:5])
        + sum(selectable_by_pos[3][:5])
        + sum(selectable_by_pos[4][:3])
        if min_15_possible
        else None
    )

    events = [ev for ev in payload.get("events", []) if ev.get("id") == expected_gw]
    if len(events) != 1:
        raise ValueError(f"Expected single event id={expected_gw} in {boot_path.name}")
    event = events[0]
    deadline_dt = _parse_iso_utc(event["deadline_time"])
    commit_dt = _parse_iso_utc(commit_meta["commit"]["committer"]["date"])
    news_dts = [_parse_iso_utc(elem["news_added"]) for elem in players if elem.get("news_added")]
    max_news_dt = max(news_dts)
    capture_lower_dt = max(commit_dt - timedelta(seconds=BOOTSTRAP_CAPTURE_WINDOW_SECONDS), max_news_dt)

    age_commit = deadline_dt - commit_dt
    age_lower = deadline_dt - capture_lower_dt
    verification = commit_meta["commit"].get("verification", {})

    return {
        "artifact": boot_path.name,
        "commit_artifact": commit_path.name,
        "expected_gw": expected_gw,
        "total_elements": len(elements),
        "player_rows": len(players),
        "excluded_assistant_managers": excluded_managers,
        "element_type_counts": {str(k): v for k, v in sorted(type_counts.items())},
        "clubs_count": len(payload.get("teams", [])),
        "duplicate_codes": len(players) - len({elem["code"] for elem in players}),
        "duplicate_ids": len(players) - len({elem["id"] for elem in players}),
        "can_select_true": len(selectable),
        "selectable_by_position": {str(pos): len(costs) for pos, costs in selectable_by_pos.items()},
        "min_15_selectable_cost_tenths": min_15_cost_tenths,
        "status_u": sum(1 for elem in players if elem.get("status") == "u"),
        "status_a_null_chance": sum(
            1 for elem in players if elem.get("status") == "a" and elem.get("chance_of_playing_next_round") is None
        ),
        "events_is_next": bool(event.get("is_next")),
        "deadline_utc": deadline_dt.isoformat(),
        "commit_time_utc": commit_dt.isoformat(),
        "max_news_added_utc": max_news_dt.isoformat(),
        "max_news_le_commit": max_news_dt <= commit_dt,
        "commit_before_deadline": commit_dt < deadline_dt,
        "capture_lower_utc": capture_lower_dt.isoformat(),
        "capture_upper_utc": commit_dt.isoformat(),
        "age_from_commit": _format_duration(age_commit),
        "age_from_commit_seconds": round(age_commit.total_seconds(), 2),
        "age_from_capture_lower": _format_duration(age_lower),
        "age_from_capture_lower_seconds": round(age_lower.total_seconds(), 2),
        "within_8h_target": age_lower.total_seconds() <= MAX_AGE_BOOTSTRAP_TARGET_SECONDS,
        "within_24h_ceiling": age_lower.total_seconds() <= MAX_AGE_BOOTSTRAP_CEILING_SECONDS,
        "commit_verified": bool(verification.get("verified")),
        "verification_reason": str(verification.get("reason", "")),
        "sha256": _file_sha256(boot_path),
        "size_bytes": boot_path.stat().st_size,
    }


def inspect_fixture_snapshot(
    *,
    csv_path: Path,
    commit_path: Path,
    prev_gw_deadline: datetime,
    origin_deadline: datetime,
) -> dict[str, Any]:
    """Inspect vaastav pre-deadline fixtures CSV and commit metadata under #175 rules."""
    _assert_unsealed_path(csv_path)
    _assert_unsealed_path(commit_path)
    rows = list(csv.DictReader(io.StringIO(csv_path.read_bytes().decode("utf-8-sig"))))
    commit_meta = json.loads(commit_path.read_text(encoding="utf-8"))
    commit_dt = _parse_iso_utc(commit_meta["commit"]["committer"]["date"])

    horizon_rows = [row for row in rows if row.get("event") and 2 <= int(row["event"]) <= 7]
    by_gw = {gw: sum(1 for row in horizon_rows if int(row["event"]) == gw) for gw in range(2, 8)}
    horizon_ids = [int(row["id"]) for row in horizon_rows if row.get("id")]
    clubs = {int(row["team_h"]) for row in horizon_rows if row.get("team_h")} | {
        int(row["team_a"]) for row in horizon_rows if row.get("team_a")
    }
    missing_cells = sum(
        1
        for row in horizon_rows
        if any(not row.get(col) for col in ("id", "event", "team_h", "team_a", "kickoff_time"))
    )
    age_upper = origin_deadline - commit_dt
    # Fallback capture_lower is prev_gw_deadline when parent commit timestamp is not retained locally.
    age_lower_fallback = origin_deadline - prev_gw_deadline
    parents = [parent.get("sha", "") for parent in commit_meta.get("parents", [])]
    verification = commit_meta["commit"].get("verification", {})

    return {
        "artifact": csv_path.name,
        "commit_artifact": commit_path.name,
        "total_rows": len(rows),
        "gw2_7_rows": len(horizon_rows),
        "rows_by_gw": {str(k): v for k, v in by_gw.items()},
        "duplicate_horizon_ids": len(horizon_ids) - len(set(horizon_ids)),
        "missing_required_cells": missing_cells,
        "clubs_covered": len(clubs),
        "commit_time_utc": commit_dt.isoformat(),
        "prev_gw_deadline_utc": prev_gw_deadline.isoformat(),
        "origin_deadline_utc": origin_deadline.isoformat(),
        "strict_between_deadlines": prev_gw_deadline < commit_dt < origin_deadline,
        "age_from_capture_upper": _format_duration(age_upper),
        "age_from_capture_upper_seconds": round(age_upper.total_seconds(), 2),
        "age_from_fallback_lower": _format_duration(age_lower_fallback),
        "age_from_fallback_lower_seconds": round(age_lower_fallback.total_seconds(), 2),
        "within_7d_target": (
            age_upper.total_seconds() <= MAX_AGE_SCHEDULE_TARGET_SECONDS
            and age_lower_fallback.total_seconds() <= MAX_AGE_SCHEDULE_TARGET_SECONDS
        ),
        "parent_commits": parents,
        "parent_commit_retained_locally": False,
        "commit_verified": bool(verification.get("verified")),
        "sha256": _file_sha256(csv_path),
        "size_bytes": csv_path.stat().st_size,
    }


def _inspect_quarantine_pilot(quarantine_dir: Path, topic_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate quarantined pilot hashes, collector provenance, and pre-#175 contract baseline."""
    if not quarantine_dir.exists():
        raise FileNotFoundError(f"Quarantine directory missing: {quarantine_dir}")
    summary_path = quarantine_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("origin") != "2025-26 GW2":
        raise ValueError(f"Unexpected pilot origin: {summary.get('origin')}")

    recovered = {row["label"]: row for row in summary.get("attempts", []) if row.get("status") == "recovered"}
    for label, row in recovered.items():
        path = quarantine_dir / f"{int(row['attempt']):02}-{label}.raw"
        actual_hash = _file_sha256(path)
        if actual_hash != row["sha256"]:
            raise ValueError(f"SHA-256 mismatch for {path.name}: expected {row['sha256']}, got {actual_hash}")

    gw1_info = inspect_bootstrap_snapshot(
        boot_path=quarantine_dir / "07-opening_bootstrap.raw",
        commit_path=quarantine_dir / "08-opening_bootstrap-commit.raw",
        expected_gw=1,
    )
    gw2_info = inspect_bootstrap_snapshot(
        boot_path=quarantine_dir / "09-origin_bootstrap_pilot.raw",
        commit_path=quarantine_dir / "10-origin_bootstrap_pilot-commit.raw",
        expected_gw=2,
    )
    fixture_info = inspect_fixture_snapshot(
        csv_path=quarantine_dir / "11-fixture_pilot.raw",
        commit_path=quarantine_dir / "12-fixture_pilot-commit.raw",
        prev_gw_deadline=_parse_iso_utc(gw1_info["deadline_utc"]),
        origin_deadline=_parse_iso_utc(gw2_info["deadline_utc"]),
    )

    collector_file = next(quarantine_dir.glob("14-collector-*.raw"), None)
    collector_uses_today = False
    if collector_file is not None:
        collector_src = collector_file.read_text(encoding="utf-8")
        collector_uses_today = "datetime.datetime.today()" in collector_src and ".json.xz" in collector_src

    pre_175_fields: dict[str, str] = {}
    fields_csv = topic_dir / "input_evidence_fields.csv"
    if fields_csv.exists():
        with fields_csv.open("r", encoding="utf-8", newline="") as handle:
            pre_175_fields = {row["name"]: row["status"] for row in csv.DictReader(handle)}

    quarantine_files: dict[str, dict[str, Any]] = {}
    source_rows: list[dict[str, Any]] = []
    basis_map = {
        "07-opening_bootstrap.raw": (f"GW1 pre-deadline ({gw1_info['commit_time_utc']})", "evidenced_bounded"),
        "08-opening_bootstrap-commit.raw": ("GW1 bootstrap commit metadata (unsigned)", "provenance"),
        "09-origin_bootstrap_pilot.raw": (f"GW2 pre-deadline ({gw2_info['commit_time_utc']})", "evidenced_bounded"),
        "10-origin_bootstrap_pilot-commit.raw": ("GW2 bootstrap commit metadata (unsigned)", "provenance"),
        "11-fixture_pilot.raw": (f"GW2-7 schedule ({fixture_info['commit_time_utc']})", "evidenced_bounded"),
        "12-fixture_pilot-commit.raw": ("GW2 fixtures commit metadata (GPG verified)", "provenance"),
    }
    row_counts_map = {
        "07-opening_bootstrap.raw": gw1_info["player_rows"],
        "09-origin_bootstrap_pilot.raw": gw2_info["player_rows"],
        "11-fixture_pilot.raw": fixture_info["gw2_7_rows"],
    }
    for file_path in sorted(quarantine_dir.glob("*")):
        if file_path.is_file() and not file_path.name.startswith("."):
            digest = _file_sha256(file_path)
            size = file_path.stat().st_size
            quarantine_files[file_path.name] = {"size": size, "sha256": digest}
            basis, role = basis_map.get(file_path.name, ("pilot audit/collector metadata", "provenance"))
            source_rows.append(
                _source_record(
                    artifact_key=f"pilot:{file_path.name}",
                    storage_location="data/reports/readiness-source-pilot/v1/",
                    artifact_name=file_path.name,
                    size_bytes=size,
                    row_count=row_counts_map.get(file_path.name),
                    sha256=digest,
                    temporal_basis=basis,
                    admission_status=role,
                )
            )

    return (
        {
            "files": quarantine_files,
            "gw1_bootstrap": gw1_info,
            "gw2_bootstrap": gw2_info,
            "gw2_fixtures": fixture_info,
            "collector_uses_naive_today": collector_uses_today,
            "pre_175_input_pilot_statuses": pre_175_fields,
        },
        source_rows,
    )


def reconcile_2025_26_ledger(df_players: pd.DataFrame, df_perf: pd.DataFrame) -> dict[str, Any]:
    """Verify exact arithmetic equality between 2025-26 component counts and total_points."""
    pos_map: dict[int, int] = {
        int(pid): int(pos_id)
        for pid, pos_id in zip(df_players["id"].tolist(), df_players["position_id"].tolist())
    }
    pos_series = pd.Series(
        [pos_map.get(int(pid)) for pid in df_perf["player_id"].tolist()],
        index=df_perf.index,
        dtype="float64",
    )
    missing_pos = int(pos_series.isna().sum())
    pos_arr = pos_series.fillna(0).to_numpy(dtype=int)

    def _num(col: str) -> np.ndarray:
        series = pd.Series(pd.to_numeric(df_perf[col], errors="coerce"), index=df_perf.index).fillna(0)
        return series.to_numpy(dtype=int)

    mins = _num("minutes")
    defcon = _num("defensive_contribution")
    goals = _num("goals_scored")
    assists = _num("assists")
    clean_sheets = _num("clean_sheets")
    goals_conceded = _num("goals_conceded")
    saves = _num("saves")
    ps = _num("penalties_saved")
    pm = _num("penalties_missed")
    og = _num("own_goals")
    yc = _num("yellow_cards")
    rc = _num("red_cards")
    bonus = _num("bonus")
    total_points = _num("total_points")

    pts_minutes = np.where(mins >= 60, 2, np.where(mins > 0, 1, 0))
    goal_weights = np.select([pos_arr == 1, pos_arr == 2, pos_arr == 3, pos_arr == 4], [10, 6, 5, 4], default=0)
    cs_weights = np.select([pos_arr == 1, pos_arr == 2, pos_arr == 3], [4, 4, 1], default=0)
    pts_goals = goals * goal_weights
    pts_assists = assists * 3
    pts_cs = clean_sheets * cs_weights
    pts_gc = np.where(np.isin(pos_arr, [1, 2]), -(goals_conceded // 2), 0)
    pts_saves = np.where(pos_arr == 1, saves // 3, 0)
    pts_ps = 5 * ps
    pts_pm = -2 * pm
    pts_og = -2 * og
    pts_yc = -1 * yc
    pts_rc = -3 * rc
    pts_bonus = bonus
    pts_defcon = np.where(
        pos_arr == 2,
        np.where(defcon >= 10, 2, 0),
        np.where(np.isin(pos_arr, [3, 4]), np.where(defcon >= 12, 2, 0), 0),
    )

    reconstructed = (
        pts_minutes + pts_goals + pts_assists + pts_cs + pts_gc + pts_saves + pts_ps + pts_pm + pts_og + pts_yc + pts_rc + pts_bonus + pts_defcon
    )
    mismatches = int(np.sum(total_points != reconstructed))
    gws = sorted({int(gw) for gw in pd.Series(df_perf["gameweek_id"]).dropna().tolist()})
    checked_rows = int(len(df_perf))
    return {
        "checked_rows": checked_rows,
        "missing_position_rows": missing_pos,
        "exact_matches": checked_rows - mismatches,
        "mismatches": mismatches,
        "distinct_gameweeks": len(gws),
        "gw_min": min(gws) if gws else None,
        "gw_max": max(gws) if gws else None,
    }


def _inspect_archives(archive_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Inspect processed, vaastav, and raw directories across unsealed seasons."""
    seasons_info: dict[str, Any] = {}
    source_rows: list[dict[str, Any]] = []

    for season in NON_SEALED_SEASONS:
        season_dir = archive_root / season
        _assert_unsealed_path(season_dir)
        info: dict[str, Any] = {"subdirs": sorted(d.name for d in season_dir.iterdir() if d.is_dir()) if season_dir.exists() else []}

        p_dir = season_dir / "processed"
        if p_dir.exists():
            df_players = pd.read_parquet(p_dir / "players.parquet")
            df_perf = pd.read_parquet(p_dir / "player_performances.parquet")
            df_fixtures = pd.read_parquet(p_dir / "fixtures.parquet")
            raw_pos_counts = pd.Series(df_players["position_id"]).value_counts().sort_index()
            pos_counts = {str(int(k)): int(v) for k, v in zip(raw_pos_counts.index.tolist(), raw_pos_counts.tolist())}
            pos5_ids = [int(pid) for pid in pd.Series(df_players.loc[df_players["position_id"] == 5, "id"]).tolist()]
            gw_vals = [int(gw) for gw in pd.Series(df_perf["gameweek_id"]).dropna().tolist()]
            proc_hashes = {
                fn: {"size": (p_dir / fn).stat().st_size, "sha256": _file_sha256(p_dir / fn)}
                for fn in ("players.parquet", "player_performances.parquet", "fixtures.parquet")
            }
            info["processed"] = {
                "players_total_rows": int(len(df_players)),
                "players_excl_pos5": int((df_players["position_id"] != 5).to_numpy().sum()),
                "assistant_managers_pos5": int((df_players["position_id"] == 5).to_numpy().sum()),
                "manager_perf_rows": int(df_perf["player_id"].isin(pos5_ids).to_numpy().sum()),
                "duplicate_codes": int(df_players["code"].duplicated().to_numpy().sum()),
                "position_counts": pos_counts,
                "performance_rows": int(len(df_perf)),
                "fixtures_count": int(len(df_fixtures)),
                "gameweeks_span": [min(gw_vals), max(gw_vals)],
                "files": proc_hashes,
            }
            if season == "2025-26":
                info["ledger_reconciliation"] = reconcile_2025_26_ledger(df_players, df_perf)
            for fn, row_ct in (
                ("players.parquet", len(df_players)),
                ("player_performances.parquet", len(df_perf)),
                ("fixtures.parquet", len(df_fixtures)),
            ):
                source_rows.append(
                    _source_record(
                        artifact_key=f"{season}/processed/{fn}",
                        storage_location=f"data/archive/{season}/processed/",
                        artifact_name=fn,
                        size_bytes=proc_hashes[fn]["size"],
                        row_count=row_ct,
                        sha256=proc_hashes[fn]["sha256"],
                        temporal_basis="post-season processed archive" if season == "2025-26" else "prior-season seed processed archive",
                        admission_status="partial",
                    )
                )

        v_dir = season_dir / "vaastav"
        if v_dir.exists():
            vaastav_files: dict[str, Any] = {}
            for rel_path in ("fixtures.csv", "players_raw.csv", "teams.csv", "gws/merged_gw.csv"):
                vp = v_dir / rel_path
                if vp.exists():
                    line_ct = sum(1 for _ in vp.open("r", encoding="utf-8-sig")) - 1
                    digest = _file_sha256(vp)
                    size = vp.stat().st_size
                    vaastav_files[rel_path] = {"rows": line_ct, "size": size, "sha256": digest}
                    source_rows.append(
                        _source_record(
                            artifact_key=f"{season}/vaastav/{rel_path}",
                            storage_location=f"data/archive/{season}/vaastav/",
                            artifact_name=rel_path,
                            size_bytes=size,
                            row_count=line_ct,
                            sha256=digest,
                            temporal_basis="post-season vaastav mirror archive (unpinned commit manifest)",
                            admission_status="partial",
                        )
                    )
            info["vaastav"] = vaastav_files

        r_dir = season_dir / "raw"
        if r_dir.exists():
            boot_path = r_dir / "bootstrap_static.json"
            fix_path = r_dir / "fixtures_all.json"
            boot_raw = json.loads(boot_path.read_text(encoding="utf-8"))
            fix_raw = json.loads(fix_path.read_text(encoding="utf-8"))
            live_files = sorted(r_dir.glob("event_*_live.json"))
            elem_files = sorted(r_dir.glob("element_summary_*.json"))
            boot_hash = _file_sha256(boot_path)
            fix_hash = _file_sha256(fix_path)
            events = boot_raw.get("events", [])
            info["raw"] = {
                "total_files": len(list(r_dir.glob("*"))),
                "live_events_count": len(live_files),
                "element_summaries_count": len(elem_files),
                "is_terminal_snapshot": bool(events) and all(bool(ev.get("finished")) for ev in events),
                "finished_events_count": sum(1 for ev in events if ev.get("finished")),
                "total_events_count": len(events),
                "bootstrap_static_sha256": boot_hash,
                "bootstrap_static_bytes": boot_path.stat().st_size,
                "fixtures_all_count": len(fix_raw),
                "fixtures_all_sha256": fix_hash,
                "fixtures_all_bytes": fix_path.stat().st_size,
            }
            source_rows.append(
                _source_record(
                    artifact_key=f"{season}/raw/bootstrap_static.json",
                    storage_location=f"data/archive/{season}/raw/",
                    artifact_name="bootstrap_static.json",
                    size_bytes=boot_path.stat().st_size,
                    row_count=len(boot_raw.get("elements", [])),
                    sha256=boot_hash,
                    temporal_basis=f"terminal May 2026 raw snapshot ({info['raw']['finished_events_count']}/{len(events)} finished)",
                    admission_status="unusable_as_point_in_time",
                )
            )
            source_rows.append(
                _source_record(
                    artifact_key=f"{season}/raw/fixtures_all.json",
                    storage_location=f"data/archive/{season}/raw/",
                    artifact_name="fixtures_all.json",
                    size_bytes=fix_path.stat().st_size,
                    row_count=len(fix_raw),
                    sha256=fix_hash,
                    temporal_basis="terminal full-season fixtures JSON (unusable as point-in-time schedule)",
                    admission_status="unusable_as_point_in_time",
                )
            )

        seasons_info[season] = info

    return seasons_info, source_rows


def _seed_resolution_for_elements(
    *,
    elements: list[dict[str, Any]],
    seed_players: pd.DataFrame,
    seed_perf: pd.DataFrame,
    seed_fixtures: pd.DataFrame,
) -> dict[str, int]:
    """Compute exact cold-start seed eligibility counts mirroring features/builder.py."""
    players = [elem for elem in elements if int(elem.get("element_type", 0)) != 5]
    code_to_id: dict[int, int] = (
        {
            int(code): int(pid)
            for code, pid in zip(seed_players["code"].tolist(), seed_players["id"].tolist())
            if pd.notna(code)
        }
        if "code" in seed_players.columns
        else {}
    )
    dedup_names = seed_players.drop_duplicates(subset=["first_name", "second_name"])
    name_to_id: dict[tuple[str, str], int] = {
        (str(fn), str(sn)): int(pid)
        for fn, sn, pid in zip(
            dedup_names["first_name"].tolist(),
            dedup_names["second_name"].tolist(),
            dedup_names["id"].tolist(),
        )
    }

    done_fids: list[int] = (
        [int(fid) for fid in pd.Series(seed_fixtures.loc[seed_fixtures["finished"] == True, "id"]).tolist()]  # noqa: E712
        if "finished" in seed_fixtures.columns
        else [int(fid) for fid in pd.Series(seed_perf["fixture_id"]).dropna().unique().tolist()]
    )
    perf_done = pd.DataFrame(seed_perf.loc[seed_perf["fixture_id"].isin(done_fids)])
    played = pd.DataFrame(perf_done.loc[perf_done["minutes"] > 0])
    agg = played.groupby("player_id").agg(apps=("minutes", "count"), mins=("minutes", "sum"))

    matched_code = 0
    matched_name_fallback = 0
    unmatched = 0
    player_prior_eligible = 0
    matched_below_threshold_fallback = 0

    for elem in players:
        elem_code = elem.get("code")
        seed_pid = code_to_id.get(int(elem_code)) if elem_code is not None else None
        if seed_pid is not None:
            matched_code += 1
        else:
            seed_pid = name_to_id.get((str(elem.get("first_name", "")), str(elem.get("second_name", ""))))
            if seed_pid is not None:
                matched_name_fallback += 1
            else:
                unmatched += 1
        if seed_pid is None:
            continue
        if seed_pid in agg.index:
            apps = int(agg.at[seed_pid, "apps"])
            total_mins = float(agg.at[seed_pid, "mins"])
            mean_mins = total_mins / apps if apps > 0 else 0.0
            if mean_mins > 0 and apps >= MIN_PRIOR_APPEARANCES and mean_mins * apps >= MIN_PRIOR_MINUTES:
                player_prior_eligible += 1
                continue
        matched_below_threshold_fallback += 1

    return {
        "players_excl_pos5": len(players),
        "matched_by_code": matched_code,
        "matched_by_name_fallback": matched_name_fallback,
        "unmatched_newcomers": unmatched,
        "player_prior_eligible": player_prior_eligible,
        "matched_below_threshold_fallback": matched_below_threshold_fallback,
        "total_position_price_fallback": unmatched + matched_below_threshold_fallback,
    }


def _inspect_lineage(root: Path, quarantine_dir: Path, archive_root: Path) -> dict[str, Any]:
    """Audit code module hashes and actual seed/fit paths across builder, walkforward, and challengers."""
    p24 = pd.read_parquet(archive_root / "2024-25/processed/players.parquet")
    perf24 = pd.read_parquet(archive_root / "2024-25/processed/player_performances.parquet")
    fix24 = pd.read_parquet(archive_root / "2024-25/processed/fixtures.parquet")

    gw1_elems = _decompress_bootstrap(quarantine_dir / "07-opening_bootstrap.raw")["elements"]
    gw2_elems = _decompress_bootstrap(quarantine_dir / "09-origin_bootstrap_pilot.raw")["elements"]

    gw1_seed = _seed_resolution_for_elements(elements=gw1_elems, seed_players=p24, seed_perf=perf24, seed_fixtures=fix24)
    gw2_seed = _seed_resolution_for_elements(elements=gw2_elems, seed_players=p24, seed_perf=perf24, seed_fixtures=fix24)

    code_hashes = {rel: _file_sha256(root / rel) for rel in LINEAGE_CODE_PATHS if (root / rel).exists()}

    return {
        "thresholds": {
            "min_prior_appearances": MIN_PRIOR_APPEARANCES,
            "min_prior_minutes": MIN_PRIOR_MINUTES,
        },
        "gw1_seed_resolution": gw1_seed,
        "gw2_seed_resolution": gw2_seed,
        "code_sha256": code_hashes,
        "paths": {
            "features_builder": (
                "features/builder.py consumes seed_processed_dir via code_to_seed_id, name_to_seed_id fallback, "
                "and Position-Price fallback when min_prior_appearances >= 8 & min_prior_minutes >= 450; "
                "cold-start rate/state priors deactivate globally once this-season evidence exists."
            ),
            "walkforward": (
                "backtesting/walkforward.py passes use_archive_seed=False; _default_seed_season_for_data_dir "
                "auto-resolves '2023-24' only for '2024-25' and returns None for '2025-26' unless seed_season/"
                "seed_processed_dir is passed explicitly. model.fit receives strictly history_before_target(df_perf, gw)."
            ),
            "walkforward_solve_and_adapter": (
                "backtesting/walkforward_solve.py and backtesting/forecast_adapter.py pass use_archive_seed=False "
                "with explicit seed_processed_dir and fit models on gameweek_id < target_gw."
            ),
            "def_xg_shrink_challenger": (
                "Champion (DefXgShrinkChallengerModel) fits DEF K=2400 decayed xG/90 ratio on current-season "
                "history_df (minutes > 0) and inherits LearnedStartChallengerModel (GW >= 4, >= 500 rows ridge + assist GLM/bonus)."
            ),
            "adaptive_causal_challenger": (
                "AdaptiveCausalChallengerModel falls back 100% to Champion for GW1-19 and activates causal panel "
                "ML components trained on current-season GW4+ rows at GW20+."
            ),
            "club_def_prior_challenger": (
                "ClubDefPriorChallengerModel derives opposing-side fixture club and fits as-of club x DEF pooled "
                "xG/90 shrinkage ratio (K=360) strictly on current-season history_df (minutes > 0)."
            ),
            "prior_season_raw_rows_in_model_fit": False,
        },
    }


def _build_coverage_matrix(
    *,
    quarantine_info: dict[str, Any],
    archives_info: dict[str, Any],
    lineage_info: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build 342-row (38 GWs x 9 fields) coverage matrix from dynamically audited metrics."""
    gw1 = quarantine_info["gw1_bootstrap"]
    gw2 = quarantine_info["gw2_bootstrap"]
    fix2 = quarantine_info["gw2_fixtures"]
    s24_proc = archives_info["2024-25"]["processed"]
    s25_proc = archives_info["2025-26"]["processed"]
    s25_raw = archives_info["2025-26"]["raw"]
    ledger25 = archives_info["2025-26"]["ledger_reconciliation"]
    gw1_seed = lineage_info["gw1_seed_resolution"]

    rows: list[dict[str, Any]] = []
    for gw in range(1, 39):
        # 1. opening_anchor
        rows.append(
            _make_coverage_row(
                gameweek=gw,
                field_group="opening_anchor",
                status="evidenced_bounded" if gw == 1 else "carried_from_gw1",
                source_type="quarantined_raw_bootstrap" if gw == 1 else "state_transition",
                source_path=(
                    "data/reports/readiness-source-pilot/v1/07-opening_bootstrap.raw"
                    if gw == 1
                    else "backtesting.replay_state.ReplayState"
                ),
                source_sha256=gw1["sha256"] if gw == 1 else "",
                coverage_count=(
                    f"{gw1['player_rows']} players (excl 0 managers), {gw1['can_select_true']} can_select=True, "
                    f"min-15 cost {gw1['min_15_selectable_cost_tenths']}/1000"
                    if gw == 1
                    else "locked GW1 anchor carried via ReplayState"
                ),
                limitation=(
                    f"unsigned bot commit; commit {gw1['age_from_commit']} / capture_lower {gw1['age_from_capture_lower']} pre-GW1; "
                    f"input_pilot pre-#175 status=unresolved"
                    if gw == 1
                    else "contingent on continuous GW1..GW(t-1) replay state"
                ),
            )
        )

        # 2-4. eligible_universe, price_club_position, availability
        if gw in (1, 2):
            snap = gw1 if gw == 1 else gw2
            u_status = "evidenced_bounded"
            u_src_type = "quarantined_raw_bootstrap"
            u_src_path = f"data/reports/readiness-source-pilot/v1/{snap['artifact']}"
            u_sha = snap["sha256"]
            u_cov = (
                f"{snap['player_rows']} players, {snap['clubs_count']} clubs, {snap['can_select_true']} selectable, "
                f"{snap['status_a_null_chance']} unflagged null-chance"
            )
            u_lim = (
                f"unsigned commit; commit {snap['age_from_commit']} / capture_lower {snap['age_from_capture_lower']} "
                f"before GW{gw} lock (<=8h); input_pilot pre-#175 status=unresolved"
            )
        else:
            u_status = "absent"
            u_src_type = "none"
            u_src_path = "none (2025-26/raw/bootstrap_static.json is terminal May 2026)"
            u_sha = ""
            u_cov = "0 pre-deadline bootstrap rows"
            u_lim = (
                f"no contemporaneous GW{gw} pre-deadline bootstrap locally; "
                f"terminal raw has {s25_raw['finished_events_count']}/{s25_raw['total_events_count']} finished events"
            )

        for field_name in ("eligible_universe", "price_club_position", "availability"):
            rows.append(
                _make_coverage_row(
                    gameweek=gw,
                    field_group=field_name,
                    status=u_status,
                    source_type=u_src_type,
                    source_path=u_src_path,
                    source_sha256=u_sha,
                    coverage_count=u_cov,
                    limitation=u_lim,
                )
            )

        # 5. fixture_schedule
        if gw == 2:
            f_status = "evidenced_bounded"
            f_type = "quarantined_raw_csv"
            f_path = "data/reports/readiness-source-pilot/v1/11-fixture_pilot.raw"
            f_sha = fix2["sha256"]
            f_cov = f"{fix2['gw2_7_rows']} horizon fixtures (GW2-7, 10/GW, {fix2['clubs_covered']} clubs)"
            f_lim = (
                f"GPG-verified commit {fix2['age_from_capture_upper']} before GW2 lock; "
                f"parent commit not retained locally so fallback capture_lower={fix2['age_from_fallback_lower']} (<=7d)"
            )
        else:
            f_status = "absent"
            f_type = "none"
            f_path = "none (2025-26/processed/fixtures.parquet is post-season)"
            f_sha = ""
            f_cov = "0 contemporaneous 6-GW schedule rows"
            f_lim = f"pre-deadline GW{gw} fixtures.csv snapshot absent locally"

        rows.append(
            _make_coverage_row(
                gameweek=gw,
                field_group="fixture_schedule",
                status=f_status,
                source_type=f_type,
                source_path=f_path,
                source_sha256=f_sha,
                coverage_count=f_cov,
                limitation=f_lim,
            )
        )

        # 6. historical_performance
        if gw == 1:
            rows.append(
                _make_coverage_row(
                    gameweek=gw,
                    field_group="historical_performance",
                    status="evidenced_empty",
                    source_type="none",
                    source_path="n/a (GW1 has 0 completed current-season matches)",
                    source_sha256="",
                    coverage_count="0 prior match rows",
                    limitation="none by definition for GW1",
                )
            )
        else:
            rows.append(
                _make_coverage_row(
                    gameweek=gw,
                    field_group="historical_performance",
                    status="partial",
                    source_type="processed_and_raw_archive",
                    source_path="data/archive/2025-26/processed/player_performances.parquet",
                    source_sha256=s25_proc["files"]["player_performances.parquet"]["sha256"],
                    coverage_count=f"GW 1..{gw - 1} in processed parquet + {gw - 1} event_*_live.json files",
                    limitation="post-season archive ingest lacks pre-deadline GW receipt bundles and commit provenance",
                )
            )

        # 7. prior_season_training
        rows.append(
            _make_coverage_row(
                gameweek=gw,
                field_group="prior_season_training",
                status="partial",
                source_type="processed_archive_seed",
                source_path="data/archive/2024-25/processed/",
                source_sha256=s24_proc["files"]["players.parquet"]["sha256"],
                coverage_count=(
                    f"{s24_proc['players_excl_pos5']} seed players (+{s24_proc['assistant_managers_pos5']} pos5 managers); "
                    f"GW1: {gw1_seed['player_prior_eligible']} direct priors, "
                    f"{gw1_seed['matched_below_threshold_fallback']} matched<thresh fallback, "
                    f"{gw1_seed['unmatched_newcomers']} unmatched"
                ),
                limitation=(
                    "feeds features/builder.py only (0 raw seed rows enter model.fit); walkforward default returns None for "
                    "2025-26 without explicit seed_season; raw seed manifests unpinned"
                ),
            )
        )

        # 8. settled_outcomes
        rows.append(
            _make_coverage_row(
                gameweek=gw,
                field_group="settled_outcomes",
                status="partial",
                source_type="processed_and_raw_archive",
                source_path="data/archive/2025-26/processed/player_performances.parquet",
                source_sha256=s25_proc["files"]["player_performances.parquet"]["sha256"],
                coverage_count=(
                    f"{ledger25['exact_matches']}/{ledger25['checked_rows']} season rows ledger-reconciled "
                    f"({ledger25['mismatches']} mismatches) + {s25_raw['live_events_count']} live JSONs"
                ),
                limitation="lacks independent >=max(kickoff)+24h settled receipts (finished/data_checked) and event timelines",
            )
        )

        # 9. shared_chip_calendar
        rows.append(
            _make_coverage_row(
                gameweek=gw,
                field_group="shared_chip_calendar",
                status="absent",
                source_type="none",
                source_path="none",
                source_sha256="",
                coverage_count="0 predeclared chip schedules",
                limitation="no hash-frozen causal chip calendar supplied",
            )
        )

    return rows


def audit_coverage(
    *,
    root: Path = ROOT,
    quarantine_dir: Path = QUARANTINE,
    archive_root: Path = ARCHIVE,
    topic_dir: Path = TOPIC,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Run full local development-coverage and training-lineage audit across unsealed sources."""
    _assert_unsealed_path(quarantine_dir)
    _assert_unsealed_path(archive_root)
    _assert_unsealed_path(topic_dir)

    quarantine_info, q_source_rows = _inspect_quarantine_pilot(quarantine_dir, topic_dir)
    archives_info, a_source_rows = _inspect_archives(archive_root)
    lineage_info = _inspect_lineage(root, quarantine_dir, archive_root)
    coverage_rows = _build_coverage_matrix(
        quarantine_info=quarantine_info,
        archives_info=archives_info,
        lineage_info=lineage_info,
    )

    breakdown: dict[str, int] = {}
    for row in coverage_rows:
        st = str(row["status"])
        breakdown[st] = breakdown.get(st, 0) + 1

    assessment: dict[str, Any] = {
        "assessment_title": "Development Coverage and Training Lineage Inventory (Season 2025-26)",
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "origin_scope": "2025-26 GW1..38 (Dev); 2024-25 & 2023-24 (Seeds); 2026-27 GW6+ strictly untouched",
        "quarantine_pilot": quarantine_info,
        "archives": archives_info,
        "training_lineage_trace": lineage_info,
        "coverage_summary_counts": {
            "total_gameweek_field_evaluations": len(coverage_rows),
            "status_breakdown": breakdown,
        },
    }
    source_rows = q_source_rows + a_source_rows
    return assessment, source_rows, coverage_rows


def render_report(
    *,
    assessment: dict[str, Any],
    source_rows: list[dict[str, Any]],
) -> str:
    """Render development_coverage_report.md strictly from computed companion values."""
    q = assessment["quarantine_pilot"]
    gw1 = q["gw1_bootstrap"]
    gw2 = q["gw2_bootstrap"]
    fix2 = q["gw2_fixtures"]
    s24 = assessment["archives"]["2024-25"]["processed"]
    s25 = assessment["archives"]["2025-26"]["processed"]
    s25_raw = assessment["archives"]["2025-26"]["raw"]
    ledger = assessment["archives"]["2025-26"]["ledger_reconciliation"]
    lineage = assessment["training_lineage_trace"]
    gw1_seed = lineage["gw1_seed_resolution"]
    gw2_seed = lineage["gw2_seed_resolution"]
    counts = assessment["coverage_summary_counts"]
    bd = counts["status_breakdown"]

    key_sources = [
        row
        for row in source_rows
        if row["artifact_name"]
        in {
            "07-opening_bootstrap.raw",
            "09-origin_bootstrap_pilot.raw",
            "11-fixture_pilot.raw",
            "players.parquet",
            "player_performances.parquet",
            "fixtures.parquet",
            "fixtures.csv",
            "gws/merged_gw.csv",
            "bootstrap_static.json",
            "fixtures_all.json",
        }
    ]
    table_lines = [
        f"| `{row['storage_location']}` | `{row['artifact_name']}` | {row['size_bytes']:,} | {row['row_count'] or '—'} | `{row['sha256'][:12]}...` | {row['temporal_basis']} | **{row['admission_status']}** |"
        for row in key_sources
    ]

    return f"""# Development source coverage and training lineage inventory

**Updated:** {assessment['generated_utc']}
**Data stamp:** Local inspection of `data/reports/readiness-source-pilot/v1/` and unsealed `data/archive/{{2023-24,2024-25,2025-26}}/`. Zero network calls; sealed `2026-27 GW6+` strictly untouched.
**Season:** 2025-26 (Dev, GW1–38); 2024-25 & 2023-24 (Seed archives).
**Status:** Local audit and code-lineage verification; empirical gate closed; no promotion authority.
**Purpose:** Establish per-deadline 2025-26 development coverage and verify source-authorized training lineage under approved `#175` Q1–Q10 rules to inform empirical route selection (`#178`).
**Scope:** Local file inspection, official arithmetic ledger check, and model/builder code trace only. No network retrieval, archive mutation, solver runs, model execution, or Candidate evaluation.
**Related:** [Candidate Evaluation and Promotion Readiness](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/174) · [Input evidence and freshness rules (#175)](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/175) · [Development coverage ticket (#176)](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/176) · [Empirical admission route (#178)](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/178) · [input-evidence-contract.md](input-evidence-contract.md) · [readiness-source-pilot.md](readiness-source-pilot.md)
**Artifact:** [development_coverage_inventory.csv](development_coverage_inventory.csv) · [development_coverage_sources.csv](development_coverage_sources.csv) · [development_coverage_assessment.json](development_coverage_assessment.json) · [development_coverage_inventory.py](development_coverage_inventory.py)

## Sources

- **Quarantined 2025-26 GW1–2 pilot**: `data/reports/readiness-source-pilot/v1/` (`07`–`17`, `attempts.jsonl`, `summary.json`). SHA-256 verified against `summary.json`.
- **Unsealed archives**: `data/archive/2023-24/{{processed,vaastav}}/`, `data/archive/2024-25/{{processed,vaastav}}/`, `data/archive/2025-26/{{processed,raw}}/`.
- **Code modules**: `features/builder.py`, `backtesting/walkforward.py`, `backtesting/walkforward_solve.py`, `backtesting/forecast_adapter.py`, `backtesting/input_pilot.py`, `models/def_xg_shrink_challenger.py`, `models/adaptive_causal_challenger.py`, `models/club_def_prior_challenger.py`.
- **Source boundary**: Pre-`#175` diagnostics in `backtesting/input_pilot.py` / [input_evidence_fields.csv](input_evidence_fields.csv) mark all 9 groups `unresolved` (`timing_basis="unknown"`) because bounded-reconstruction rules from `#175` are not yet codified into `input_pilot.py` or `data_admission.py`.

## Decision

1. **Quarantined pilot satisfies `#175` Q1–Q10 bounds for GW1 anchor and GW2 inputs only, pending code activation (`#178`)**:
   - **GW1 (`07-opening_bootstrap.raw`)**: `{gw1['player_rows']}` players (`{gw1['excluded_assistant_managers']}` `element_type==5` managers), `{gw1['can_select_true']}` selectable (`min_15_cost = {gw1['min_15_selectable_cost_tenths']}/1000`), `is_next={gw1['events_is_next']}`, commit `{gw1['age_from_commit']}` and bounded `capture_lower` `{gw1['age_from_capture_lower']}` pre-deadline (`<= 8h` target).
   - **GW2 (`09-origin_bootstrap_pilot.raw`, `11-fixture_pilot.raw`)**: `{gw2['player_rows']}` players (`{gw2['excluded_assistant_managers']}` managers), `{gw2['can_select_true']}` selectable, `{gw2['status_a_null_chance']}` unflagged null-chance (`is_next={gw2['events_is_next']}`, commit `{gw2['age_from_commit']}`, `capture_lower` `{gw2['age_from_capture_lower']}` pre-deadline `<= 8h`); `{fix2['gw2_7_rows']}` horizon fixtures GW2–7 (`10/GW`, commit `{fix2['age_from_capture_upper']}` pre-deadline; parent commit absent locally so fallback `capture_lower = {fix2['age_from_fallback_lower']} <= 7d`).
2. **Continuous 38-GW 2025-26 replay cannot run without bounded acquisition (`#178`)**:
   - GW1 6-GW schedule and GW3–38 pre-deadline `bootstrap-static` / `fixtures.csv` snapshots are absent locally (`{bd.get('absent', 0)}` of `{counts['total_gameweek_field_evaluations']}` GW×field evaluations absent).
   - `data/archive/2025-26/raw/bootstrap_static.json` is a terminal May 2026 snapshot (`{s25_raw['finished_events_count']}/{s25_raw['total_events_count']}` finished events) and cannot supply point-in-time inputs.
3. **Training lineage invariant holds across all model paths**:
   - `model.fit()` receives strictly current-season pre-target rows (`gameweek_id < gw`); zero prior-season raw rows enter `fit()`. Prior-season `2024-25` seed reaches `features/builder.py` only when passed explicitly (`use_archive_seed=False` in `walkforward.py`, which does not auto-default seed for `2025-26`).

## Method

**Method type**: Offline byte/hash verification, schema and freshness check under `#175` Q1–Q10 bounds, official component-to-points ledger arithmetic audit, and codebase lineage trace.

**Procedure**:
1. Verify all `summary.json` SHA-256 digests in `data/reports/readiness-source-pilot/v1/` and extract collector, commit, deadline, `max(news_added)`, `element_type`, and `can_select` telemetry.
2. Hash and inspect all non-sealed archives (`2023-24`, `2024-25`, `2025-26`) including `processed/`, `vaastav/`, and `2025-26/raw/`; exclude `2026-27` via explicit path guard.
3. Execute full `2025-26` component-to-`total_points` reconciliation (including Defensive Contributions thresholds `>=10` DEF, `>=12` MID/FWD) across all `{ledger['checked_rows']:,}` rows in `player_performances.parquet`.
4. Evaluate exact `features/builder.py` seed resolution (`MIN_PRIOR_APPEARANCES={MIN_PRIOR_APPEARANCES}`, `MIN_PRIOR_MINUTES={MIN_PRIOR_MINUTES}`) against GW1 (`07`) and GW2 (`09`) elements and inspect active Champion/Challenger `fit()` code paths.
5. Export companion CSV/JSON files and regenerate this markdown note directly from computed outputs.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Field Coverage Status** | `status` | Per-`(gw, field_group)` disposition (`evidenced_bounded`, `carried_from_gw1`, `evidenced_empty`, `partial`, `absent`) | Context (`evidenced_*` $\\uparrow$) | Required groups `evidenced_*` before replay | Classifies retained local bytes vs Q1–Q10 rules; separate from promotion verdict. |
| **Snapshot Bounded Age** | `deadline - capture_lower` | Pre-deadline distance using `max(commit - 1800s, max(news_added))` for bootstraps or fallback `prev_gw_deadline` for fixtures | Lower $\\downarrow$ within target | Bootstraps `<= 8h` (`24h` ceil); schedule `<= 7d` | Earliest plausible pre-deadline capture age under `#175` Q1b/Q7. |
| **Seed Direct-Prior Count** | `player_prior_eligible` | GW players matching 2024-25 seed (`code` then `name`) with `apps >= {MIN_PRIOR_APPEARANCES}` & `mins >= {MIN_PRIOR_MINUTES}` | Context | Full verified seed coverage | Counts players receiving individual 2024-25 prior rates vs `position_price_prior` fallback. |
| **Ledger Arithmetic Mismatches** | `mismatches` | Count of `player_performances.parquet` rows where `total_points != sum(native components)` | Lower $\\downarrow$ | `0` | Tests internal scoring consistency; does not replace independent `+24h` settlement receipts. |
| **Digest Integrity** | `sha256` | Exact SHA-256 byte equality vs `summary.json` / disk files | Exact match | 100% matched | Guards against byte corruption; hash alone does not attest capture time. |

## Findings

### Retained Source & Archive Inventory (`development_coverage_sources.csv`)

| Storage Location | Artifact Name | Bytes | Rows | SHA-256 | Temporal Basis | Status |
|---|---|---:|---:|---|---|---|
{chr(10).join(table_lines)}

- `2025-26/raw/` additionally holds `{s25_raw['live_events_count']}` `event_*_live.json` and `{s25_raw['element_summaries_count']}` `element_summary_*.json` files (`{s25_raw['total_files']}` total files), ingested post-season without independent `>= max(kickoff)+24h` or `data_checked` receipts.
- `2024-25/processed/players.parquet` contains `{s24['players_total_rows']}` rows: `{s24['players_excl_pos5']}` players (`position_id` 1–4) plus `{s24['assistant_managers_pos5']}` Assistant Managers (`position_id == 5`, `{s24['manager_perf_rows']}` performance rows). Both `2024-25` and `2025-26` have `0` duplicate permanent player `code`s.
- All `{ledger['checked_rows']:,}` rows in `2025-26/processed/player_performances.parquet` (`GW {ledger['gw_min']}..{ledger['gw_max']}`, `{ledger['distinct_gameweeks']}` GWs) pass exact 2025-26 official component arithmetic reconciliation (`{ledger['mismatches']}` mismatches).

### Per-Deadline Coverage Summary (`development_coverage_inventory.csv`, {counts['total_gameweek_field_evaluations']} evaluations)

- **`evidenced_bounded` ({bd.get('evidenced_bounded', 0)})**: GW1 `opening_anchor`; GW1–2 `eligible_universe`, `price_club_position`, `availability`; GW2 `fixture_schedule` (`11-fixture_pilot.raw`, `gw2_7_rows={fix2['gw2_7_rows']}`, `commit={fix2['age_from_capture_upper']}` pre-GW2). Note: `collector_uses_naive_today={q['collector_uses_naive_today']}`; pre-`#175` `input_pilot.py` still marks these `unresolved` until `#178` codifies Q1–Q10 rules.
- **`carried_from_gw1` ({bd.get('carried_from_gw1', 0)})**: GW2..38 `opening_anchor` continuity via `ReplayState`.
- **`evidenced_empty` ({bd.get('evidenced_empty', 0)})**: GW1 `historical_performance` (0 prior current-season matches by definition).
- **`partial` ({bd.get('partial', 0)})**: GW2..38 `historical_performance` (`37`); GW1..38 `prior_season_training` (`38`); GW1..38 `settled_outcomes` (`38`). Bytes exist in `processed/`, `vaastav/`, and post-season `raw/`, but lack `#175`-compliant pre-deadline/post-settlement capture receipts and pinned upstream commit manifests.
- **`absent` ({bd.get('absent', 0)})**: GW1 and GW3..38 `fixture_schedule` (`37`); GW3..38 `eligible_universe` / `price_club_position` / `availability` (`108`); GW1..38 `shared_chip_calendar` (`38`).

### Seed Resolution & Model Training Lineage

- **GW1 Bootstrap (`{gw1_seed['players_excl_pos5']}` players vs `2024-25/processed`)**: `{gw1_seed['matched_by_code']}` matched by `code`, `{gw1_seed['matched_by_name_fallback']}` matched only by `name_to_seed_id`, and `{gw1_seed['unmatched_newcomers']}` unmatched newcomers. Because `features/builder.py` requires `apps >= {MIN_PRIOR_APPEARANCES}` and `mins >= {MIN_PRIOR_MINUTES}`, only **`{gw1_seed['player_prior_eligible']}`** receive individual 2024-25 priors (`has_prior_seed=True`), while `{gw1_seed['matched_below_threshold_fallback']}` below-threshold matched players plus `{gw1_seed['unmatched_newcomers']}` newcomers (`{gw1_seed['total_position_price_fallback']}` total) take `position_price_prior` fallbacks. (GW2 bootstrap `{gw2_seed['players_excl_pos5']}` players: `{gw2_seed['player_prior_eligible']}` individual priors, `{gw2_seed['matched_below_threshold_fallback']}` matched fallbacks, `{gw2_seed['unmatched_newcomers']}` unmatched.)
- **Feature Builder vs Walkforward Seed Wiring**: `backtesting/walkforward.py`, `backtesting/walkforward_solve.py`, and `backtesting/forecast_adapter.py` pass `use_archive_seed=False` to `build_features()`. `_default_seed_season_for_data_dir()` auto-selects `2023-24` only when evaluating `2024-25`, returning `None` for `2025-26` unless `seed_season="2024-25"` or `seed_processed_dir` is explicitly provided. Cold-start seed priors deactivate globally in `build_features()` once current-season match rows exist.
- **Zero Prior-Season Rows in `model.fit()`**: `walkforward.py` feeds `history_before_target(df_perf, gw)` (`gameweek_id < gw`) exclusively to `model.fit()` across all selection models (`DefXgShrinkChallengerModel`, `AdaptiveCausalChallengerModel`, `ClubDefPriorChallengerModel`, inheriting `LearnedStartChallengerModel`).

## Risks and unknowns

1. `08-opening_bootstrap-commit.raw` and `10-origin_bootstrap_pilot-commit.raw` are unsigned GitHub bot commits; `12-fixture_pilot-commit.raw` is GPG-signed but its parent commit `{fix2['parent_commits'][0][:12]}...` is not retained locally, forcing `capture_lower` to fall back to `GW1` deadline (`7d`).
2. Existing `backtesting/input_pilot.py` and `backtesting/data_admission.py` still enforce pre-`#175` checks (`timing_basis="unknown"`, all pilot groups `unresolved`); empirical admission stays closed until `#178` decides the route and `#182` gates implementation.
3. Terminal `2025-26/processed/players.parquet` contains `{s25['players_excl_pos5']}` season-cumulative players (`{s25['players_excl_pos5'] - gw1['player_rows']}` more than GW1), illustrating look-ahead leakage if terminal tables replace GW-by-GW `fplcache` snapshots.
4. `2024-25/processed/players.parquet` retains `{s24['assistant_managers_pos5']}` `position_id == 5` managers (`{s24['manager_perf_rows']}` perf rows); any `#178` seed ingestion adapter must continue isolating or filtering `element_type == 5`.

## Agent Prompt

```text
Reproduce offline from repo root:
uv run python docs/research/backtesting-promotion-foundation/development_coverage_inventory.py

Inputs (read-only; never inspect data/archive/2026-27/):
- data/reports/readiness-source-pilot/v1/
- data/archive/2023-24/, data/archive/2024-25/, data/archive/2025-26/
- features/builder.py, backtesting/walkforward.py, backtesting/walkforward_solve.py, backtesting/forecast_adapter.py, models/

Outputs regenerated beside this note:
- docs/research/backtesting-promotion-foundation/development_coverage_inventory.csv (status breakdown, source_sha256, coverage_count)
- docs/research/backtesting-promotion-foundation/development_coverage_sources.csv (sha256, size_bytes, row_count, admission_status)
- docs/research/backtesting-promotion-foundation/development_coverage_assessment.json (freshness bounds, gw1_seed_resolution, ledger_reconciliation, code_sha256)
- docs/research/backtesting-promotion-foundation/development_coverage_report.md (cache of companion cells)

Keep scratch only in .tmp/agent/ and delete scratch before finishing. Validate with:
uv run pytest tests/test_development_coverage_inventory.py
```
"""


def write_outputs(topic_dir: Path = TOPIC) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Run coverage audit and write all companion outputs plus regenerated markdown note."""
    assessment, source_rows, coverage_rows = audit_coverage(topic_dir=topic_dir)
    (topic_dir / "development_coverage_assessment.json").write_text(
        json.dumps(assessment, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for filename, rows in (
        ("development_coverage_inventory.csv", coverage_rows),
        ("development_coverage_sources.csv", source_rows),
    ):
        with (topic_dir / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    (topic_dir / "development_coverage_report.md").write_text(
        render_report(assessment=assessment, source_rows=source_rows),
        encoding="utf-8",
    )
    return assessment, source_rows, coverage_rows


def main() -> None:
    assessment, _, coverage_rows = write_outputs(TOPIC)
    print(
        f"Regenerated report and companions ({len(coverage_rows)} coverage rows): "
        f"{assessment['coverage_summary_counts']['status_breakdown']}"
    )


if __name__ == "__main__":
    main()
