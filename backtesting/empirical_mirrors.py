"""Historical development-mirror acquisition, provenance bounds, zero-diff, and causal chip calendar."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import pandas as pd

from backtesting.fplcache_ingest import (
    FPLCACHE_HARD_MAX_AGE_SECONDS,
    FPLCACHE_NORMAL_MAX_AGE_SECONDS,
    _sanitize_bootstrap,
    _unpack_bootstrap_xz,
    _utc,
    extract_max_news_added,
    parse_fplcache_snapshot_path,
)
from backtesting.replay_state import zero_min_card_points
from backtesting.season_rules import Chip, SeasonRules, get_rules, validate_chip_calendar
from backtesting.walkforward import LEDGER_COMPONENTS, _build_actual_components

UTC = timezone.utc

FPLCACHE_MAX_TARGET_SECONDS = FPLCACHE_NORMAL_MAX_AGE_SECONDS
FPLCACHE_MAX_HARD_SECONDS = FPLCACHE_HARD_MAX_AGE_SECONDS
FPLCACHE_FILENAME_TOLERANCE_SECONDS = 900
BOOTSTRAP_RECONSTRUCTION_WINDOW_SECONDS = 1800
FIXTURE_DISCLOSURE_AGE_SECONDS = 48 * 3600
FIXTURE_TARGET_SECONDS = 7 * 86400
FIXTURE_MIN_CAP_SECONDS = 14 * 86400
FIXTURE_MAX_CAP_SECONDS = 21 * 86400
SETTLEMENT_MIN_WAIT_SECONDS = 24 * 3600

_ALLOWED_HOSTS = frozenset({"raw.githubusercontent.com", "api.github.com"})
_FPLCACHE_PATH_RE = re.compile(
    r"^/(?:Randdalf/fplcache/[^/]+/|repos/Randdalf/fplcache/)(cache/(\d{4})/(\d{1,2})/\d{1,2}/\d{4}\.json\.xz)$"
)
_VAASTAV_PATH_RE = re.compile(
    r"^/(?:vaastav/Fantasy-Premier-League/[^/]+/|repos/vaastav/Fantasy-Premier-League/)(data/(2024-25|2025-26)/.+$)"
)
_ZERO_DIFF_COLS_COMMON = (
    "minutes",
    "total_points",
    "goals_scored",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "own_goals",
    "penalties_saved",
    "penalties_missed",
    "yellow_cards",
    "red_cards",
    "saves",
    "bonus",
    "bps",
)


def sha256_bytes(data: bytes) -> str:
    """Return lowercase hex SHA-256 digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize JSON object canonically with strict non-finite rejection."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_json_sha256(obj: Any) -> str:
    """Return SHA-256 digest of canonical JSON representation."""
    return sha256_bytes(canonical_json_bytes(obj))


def validate_mirror_url(url: str) -> str:
    """Validate URL stays within allowlisted historical mirror hosts/paths and excludes 2026-27."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_HOSTS:
        raise ValueError(f"Mirror URL outside approved GitHub HTTPS hosts: {url}")
    path = parsed.path
    if "2026-27" in path or "2027-" in path or "2027/" in path:
        raise ValueError(f"Sealed 2026-27+ mirror access forbidden: {url}")
    if m_fc := _FPLCACHE_PATH_RE.search(path):
        year, month = int(m_fc.group(2)), int(m_fc.group(3))
        if (year == 2024 and 8 <= month <= 12) or (year == 2025 and 1 <= month <= 12) or (year == 2026 and 1 <= month <= 5):
            return url
        raise ValueError(f"fplcache date outside 2024-25/2025-26 boundaries: {url}")
    if _VAASTAV_PATH_RE.search(path):
        return url
    raise ValueError(f"Mirror URL outside allowlisted historical repositories/seasons: {url}")


def build_bootstrap_mirror_record(
    *,
    season: Literal["2024-25", "2025-26"],
    gw: int,
    deadline: datetime,
    prev_deadline: datetime | None,
    url: str,
    repo_path: str,
    commit_sha: str,
    commit_time: datetime,
    raw_bytes: bytes,
    local_relpath: str | None = None,
) -> dict[str, Any]:
    """Verify and summarize one pinned Randdalf/fplcache bootstrap snapshot per #175/#178."""
    validate_mirror_url(url)
    dl_utc = _utc(deadline)
    commit_utc = _utc(commit_time)
    filename_utc = parse_fplcache_snapshot_path(repo_path)
    decoded_bytes, payload = _unpack_bootstrap_xz(raw_bytes)
    sanitized, club_ids, issues = _sanitize_bootstrap(payload, capture_upper=commit_utc)
    max_news_added = extract_max_news_added(payload)

    excluded_managers = sum(
        1 for el in payload.get("elements", []) if isinstance(el, Mapping) and el.get("element_type") == 5
    )
    is_next_matches = any(
        isinstance(ev, Mapping) and ev.get("id") == gw and ev.get("is_next") is True
        for ev in payload.get("events", [])
    )

    filename_within_900s = (
        filename_utc is not None
        and abs((commit_utc - filename_utc).total_seconds()) <= FPLCACHE_FILENAME_TOLERANCE_SECONDS
    )
    if filename_within_900s and "news_added_after_capture" not in issues:
        lower_candidate = commit_utc - timedelta(seconds=BOOTSTRAP_RECONSTRUCTION_WINDOW_SECONDS)
        capture_lower: datetime | None = max(lower_candidate, max_news_added) if max_news_added is not None else lower_candidate
        timing_basis = "bounded_reconstruction"
    elif prev_deadline is not None:
        capture_lower = _utc(prev_deadline)
        timing_basis = "fallback_prior_deadline"
    else:
        capture_lower = None
        timing_basis = "unresolved_lower_bound"

    capture_upper = commit_utc
    age_lower = (dl_utc - capture_lower).total_seconds() if capture_lower is not None else None
    disclosed: list[str] = ["fplcache_mirror_provenance"]
    status = "supported"
    reason = "ok"

    if capture_upper >= dl_utc or "news_added_after_capture" in issues or issues or not is_next_matches:
        status = "invalid"
        if "news_added_after_capture" in issues:
            reason = "news_added_after_capture"
        elif capture_upper >= dl_utc:
            reason = "capture_after_deadline"
        elif not is_next_matches:
            reason = "is_next_mismatch"
        else:
            reason = ",".join(issues)
    elif age_lower is None:
        status = "unresolved"
        reason = "missing_filename_timestamp_lower_bound"
    elif age_lower > FPLCACHE_MAX_HARD_SECONDS:
        status = "source_stale"
        reason = "bootstrap_exceeds_24h"
    elif age_lower > FPLCACHE_MAX_TARGET_SECONDS:
        disclosed.append("bootstrap_stale_band_8h_to_24h")

    canonical_table = {
        "elements": sorted(sanitized, key=lambda r: int(r["id"])),
        "club_ids": sorted(club_ids),
        "events": [
            {k: ev.get(k) for k in ("id", "deadline_time", "is_next")}
            for ev in payload.get("events", [])
            if isinstance(ev, Mapping) and ev.get("id") == gw
        ],
        "chips": payload.get("chips", []),
    }
    return {
        "season": season,
        "gw": gw,
        "deadline_utc": dl_utc.isoformat(),
        "url": url,
        "repo": "Randdalf/fplcache",
        "path": repo_path,
        "commit_sha": commit_sha,
        "commit_time_utc": commit_utc.isoformat(),
        "filename_utc": filename_utc.isoformat() if filename_utc is not None else None,
        "filename_within_900s": filename_within_900s,
        "capture_lower_utc": capture_lower.isoformat() if capture_lower is not None else None,
        "capture_upper_utc": capture_upper.isoformat(),
        "timing_basis": timing_basis,
        "age_seconds": round(age_lower, 3) if age_lower is not None else None,
        "status": status,
        "reason": reason,
        "disclosed_limitations": disclosed,
        "blob_sha256": sha256_bytes(raw_bytes),
        "decompressed_sha256": sha256_bytes(decoded_bytes),
        "table_sha256": canonical_json_sha256(canonical_table),
        "element_count": len(sanitized),
        "purchase_eligible_count": sum(1 for row in sanitized if row["purchase_eligible"]),
        "excluded_manager_count": excluded_managers,
        "null_chance_count": sum(1 for row in sanitized if row.get("chance_of_playing_next_round") is None),
        "max_news_added_utc": max_news_added.isoformat() if max_news_added is not None else None,
        "is_next_ok": is_next_matches,
        "local_relpath": local_relpath,
    }


def parse_fixtures_csv_window(raw_bytes: bytes, gw: int, *, horizon: int = 6) -> list[dict[str, Any]]:
    """Parse vaastav fixtures.csv rows inside ``[gw, min(gw+horizon-1, 38)]`` cleanly."""
    reader = csv.DictReader(io.StringIO(raw_bytes.decode("utf-8-sig")))
    target_end = min(gw + horizon - 1, 38)
    window_rows: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for row in reader:
        ev_raw = (row.get("event") or "").strip()
        if not ev_raw:
            continue
        event_gw = int(float(ev_raw))
        if not gw <= event_gw <= target_end:
            continue
        fid = int(row["id"])
        if fid in seen_ids:
            raise ValueError(f"Duplicate fixture id {fid} in fixtures.csv")
        seen_ids.add(fid)
        ko = (row.get("kickoff_time") or "").strip()
        if not ko:
            raise ValueError(f"Missing kickoff_time for fixture {fid}")
        window_rows.append(
            {
                "id": fid,
                "event": event_gw,
                "team_h": int(row["team_h"]),
                "team_a": int(row["team_a"]),
                "kickoff_time": ko,
                "provisional_start_time": str(row.get("provisional_start_time", "False")),
            }
        )
    window_rows.sort(key=lambda r: (r["event"], r["id"]))
    return window_rows


def build_fixture_mirror_record(
    *,
    season: Literal["2024-25", "2025-26"],
    gw: int,
    deadline: datetime,
    prev_deadline: datetime | None,
    url: str,
    commit_sha: str,
    commit_time: datetime,
    prev_commit_time: datetime | None,
    raw_bytes: bytes,
    local_relpath: str | None = None,
) -> dict[str, Any]:
    """Verify and summarize one pinned vaastav fixtures.csv snapshot against #175 Q7 bounds."""
    validate_mirror_url(url)
    dl_utc = _utc(deadline)
    commit_utc = _utc(commit_time)
    prev_dl_utc = _utc(prev_deadline) if prev_deadline is not None else None
    prev_commit_utc = _utc(prev_commit_time) if prev_commit_time is not None else None

    window_rows = parse_fixtures_csv_window(raw_bytes, gw)
    capture_upper = commit_utc
    if prev_dl_utc is not None and prev_commit_utc is not None:
        capture_lower = max(prev_dl_utc, prev_commit_utc)
    elif prev_dl_utc is not None:
        capture_lower = prev_dl_utc
    elif prev_commit_utc is not None:
        capture_lower = prev_commit_utc
    else:
        capture_lower = commit_utc

    age_upper = (dl_utc - capture_upper).total_seconds()
    age_lower = (dl_utc - capture_lower).total_seconds()
    if gw == 1:
        in_window = capture_upper < dl_utc
        hard_cap = float(FIXTURE_MAX_CAP_SECONDS)
    else:
        in_window = prev_dl_utc is not None and prev_dl_utc < capture_upper < dl_utc
        inter_gw_gap = (dl_utc - prev_dl_utc).total_seconds() if prev_dl_utc is not None else float(FIXTURE_MIN_CAP_SECONDS)
        hard_cap = float(min(FIXTURE_MAX_CAP_SECONDS, max(FIXTURE_MIN_CAP_SECONDS, inter_gw_gap)))

    lower_cap = float(min(FIXTURE_MAX_CAP_SECONDS, max(FIXTURE_TARGET_SECONDS, (dl_utc - prev_dl_utc).total_seconds() if prev_dl_utc else FIXTURE_MAX_CAP_SECONDS)))

    status = "supported"
    reason = "ok"
    if capture_upper >= dl_utc:
        status = "invalid"
        reason = "fixture_capture_after_deadline"
    elif not in_window:
        status = "out_of_window"
        reason = "no_commit_between_prev_and_origin_deadline"
    elif age_upper > hard_cap or age_lower > lower_cap:
        status = "source_stale"
        reason = "fixture_exceeds_age_ceiling"

    disclosed: list[str] = ["vaastav_mirror_provenance"]
    if age_upper > FIXTURE_DISCLOSURE_AGE_SECONDS:
        disclosed.append("fixture_schedule_gt_48h")
    if status == "supported" and age_upper > FIXTURE_TARGET_SECONDS:
        disclosed.append("fixture_stale_band_7d_to_21d")

    covered_gws = sorted({row["event"] for row in window_rows})
    return {
        "season": season,
        "gw": gw,
        "deadline_utc": dl_utc.isoformat(),
        "url": url,
        "repo": "vaastav/Fantasy-Premier-League",
        "commit_sha": commit_sha,
        "commit_time_utc": commit_utc.isoformat(),
        "capture_lower_utc": capture_lower.isoformat(),
        "capture_upper_utc": capture_upper.isoformat(),
        "age_upper_seconds": round(age_upper, 3),
        "age_lower_seconds": round(age_lower, 3),
        "hard_cap_seconds": round(hard_cap, 3),
        "in_window": in_window,
        "status": status,
        "reason": reason,
        "disclosed_limitations": disclosed,
        "blob_sha256": sha256_bytes(raw_bytes),
        "table_sha256": canonical_json_sha256(window_rows),
        "window_gws": covered_gws,
        "row_count": len(window_rows),
        "local_relpath": local_relpath,
    }


def verify_settled_outcomes_zero_diff(
    vaastav_merged_df: pd.DataFrame,
    processed_perf_df: pd.DataFrame,
    processed_players_df: pd.DataFrame,
    *,
    season: Literal["2024-25", "2025-26"],
) -> dict[str, Any]:
    """Verify settled vaastav outcomes zero-diff vs local processed parquet and 13-component ledger."""
    rules = get_rules(season)
    players = processed_players_df.copy()
    if "player_id" not in players.columns and "id" in players.columns:
        players = players.rename(columns={"id": "player_id"})
    players["native_rules_version"] = season

    non_manager_ids = set(players[players["position_id"] != 5]["player_id"].astype(int))
    manager_ids = set(players[players["position_id"] == 5]["player_id"].astype(int))

    # Deduplicate vaastav (element, fixture, GW) only when exact stat values agree across duplicates
    work_va = vaastav_merged_df.copy()
    work_va["player_id"] = pd.to_numeric(work_va["element"], errors="raise").astype(int)
    work_va["fixture_id"] = pd.to_numeric(work_va["fixture"], errors="raise").astype(int)
    work_va["gameweek_id"] = pd.to_numeric(work_va["GW"], errors="raise").astype(int)
    work_va = work_va[work_va["player_id"].isin(non_manager_ids)].copy()

    compare_cols = list(_ZERO_DIFF_COLS_COMMON)
    if rules.defensive_contributions:
        compare_cols.append("defensive_contribution")

    key_cols = ["player_id", "fixture_id", "gameweek_id"]
    dup_mask = work_va.duplicated(key_cols, keep=False)
    dup_count = int(work_va.duplicated(key_cols, keep="last").sum())
    if dup_count > 0:
        dups = work_va[dup_mask]
        for _, grp in dups.groupby(key_cols):
            for col in compare_cols:
                vals = pd.to_numeric(grp[col], errors="raise")
                if vals.isna().any() or vals.astype(int).nunique() > 1:
                    raise ValueError(f"Conflicting or missing duplicate values in vaastav outcomes for col={col}")
        work_va = work_va.drop_duplicates(key_cols, keep="last").copy()

    proc_filtered = processed_perf_df[processed_perf_df["player_id"].isin(non_manager_ids)].copy()
    excluded_manager_perf_rows = int(processed_perf_df["player_id"].isin(manager_ids).sum())

    if len(work_va) != len(proc_filtered):
        raise ValueError(f"Row count mismatch against processed archive: {len(work_va)} vs {len(proc_filtered)}")

    merged = proc_filtered.merge(
        work_va,
        on=key_cols,
        how="inner",
        suffixes=("_proc", "_va"),
        validate="one_to_one",
    )
    if len(merged) != len(proc_filtered):
        raise ValueError(f"Key join mismatch against processed archive: {len(merged)} vs {len(proc_filtered)}")

    for col in compare_cols:
        left = pd.to_numeric(merged[f"{col}_proc"], errors="raise").astype(int)
        right = pd.to_numeric(merged[f"{col}_va"], errors="raise").astype(int)
        diffs = int((left != right).sum())
        if diffs > 0:
            raise ValueError(f"Outcome zero-diff failure on column {col}: {diffs} mismatched rows")

    # Component ledger reconciliation (13 components)
    actual = _build_actual_components(proc_filtered.copy(), players)
    residual = actual["total_points"] - actual[[f"actual_{c}" for c in LEDGER_COMPONENTS]].sum(axis=1)
    mismatches = int((residual.abs() > 1e-9).sum())
    if mismatches > 0:
        raise ValueError(f"Component ledger residual mismatch on {mismatches} rows")

    zero_min_nonzero = actual[(actual["minutes"] == 0) & (actual["total_points"] != 0)]
    card_exceptions: list[dict[str, int]] = []
    for _, r in zero_min_nonzero.iterrows():
        yc = int(r.get("yellow_cards", 0))
        rc = int(r.get("red_cards", 0))
        tp = int(r["total_points"])
        expected_card_pts = zero_min_card_points(yc, rc)
        if (yc == 0 and rc == 0) or tp != expected_card_pts:
            raise ValueError(f"Zero-minute non-card scoring residual on player={int(r['player_id'])} gw={int(r['gameweek_id'])}")
        card_exceptions.append(
            {
                "player_id": int(r["player_id"]),
                "gameweek_id": int(r["gameweek_id"]),
                "minutes": 0,
                "yellow_cards": yc,
                "red_cards": rc,
                "total_points": tp,
            }
        )

    return {
        "season": season,
        "zero_diff": True,
        "verified_rows": int(len(proc_filtered)),
        "duplicate_rows_collapsed": dup_count,
        "excluded_manager_rows": excluded_manager_perf_rows,
        "ledger_mismatch_rows": mismatches,
        "zero_minute_card_rows": len(card_exceptions),
        "zero_minute_card_exceptions": card_exceptions,
    }


def _best_dgw_in_range(
    fixtures_by_gw: Mapping[int, pd.DataFrame],
    start_gw: int,
    end_gw: int,
    *,
    exclude: set[int],
    rules: SeasonRules,
    fallback_gw: int,
    opening_schedule: pd.DataFrame | None = None,
) -> int:
    best_gw = fallback_gw
    best_score = -1
    for gw in range(start_gw, end_gw + 1):
        if gw in exclude:
            continue
        frame = opening_schedule if opening_schedule is not None else fixtures_by_gw.get(gw)
        score = 0
        if frame is not None and not frame.empty:
            sub = frame[frame["event"] == gw]
            counts: dict[int, int] = {}
            for _, row in sub.iterrows():
                counts[int(row["team_h"])] = counts.get(int(row["team_h"]), 0) + 1
                counts[int(row["team_a"])] = counts.get(int(row["team_a"]), 0) + 1
            dgw_clubs = sum(1 for c in counts.values() if c >= 2)
            score = dgw_clubs * 100 + len(sub)
        if score > best_score:
            best_score = score
            best_gw = gw
    return best_gw


def build_causal_chip_calendar(
    season: Literal["2024-25", "2025-26"],
    *,
    fixtures_by_gw: Mapping[int, pd.DataFrame] | None = None,
    opening_schedule: pd.DataFrame | None = None,
) -> tuple[tuple[int, Chip], ...]:
    """Deterministically derive one model-independent chip_calendar from causal pre-GW1/pre-deadline fixtures."""
    rules = get_rules(season)
    fx_map = fixtures_by_gw or {}
    used_gws: set[int] = set()
    entries: list[tuple[int, Chip]] = []

    if rules.two_chip_sets:
        # Set 1 (GW2-19) and Set 2 (GW20-38)
        candidates_s1: list[tuple[Chip, int, int, int]] = [
            ("wildcard", 4, 19, 8),
            ("free_hit", 12, 19, 14),
            ("bench_boost", 6, 19, 10),
            ("triple_captain", 2, 19, 3),
        ]
        candidates_s2: list[tuple[Chip, int, int, int]] = [
            ("wildcard", 24, 38, 30),
            ("free_hit", 28, 38, 32),
            ("bench_boost", 30, 38, 34),
            ("triple_captain", 22, 38, 25),
        ]
        for chip, start, end, default_gw in (*candidates_s1, *candidates_s2):
            blocked = set(used_gws)
            if chip == "free_hit":
                blocked |= {g - 1 for g, c in entries if c == "free_hit"} | {g + 1 for g, c in entries if c == "free_hit"}
            gw = _best_dgw_in_range(
                fx_map, start, end, exclude=blocked, rules=rules, fallback_gw=default_gw, opening_schedule=opening_schedule
            )
            used_gws.add(gw)
            entries.append((gw, chip))
    else:
        plan: list[tuple[Chip, int, int, int]] = [
            ("wildcard", 4, 19, 6),
            ("wildcard", 24, 38, 30),
            ("triple_captain", 20, 38, 24),
            ("bench_boost", 30, 38, 33),
            ("free_hit", 25, 38, 29),
        ]
        for chip, start, end, default_gw in plan:
            gw = _best_dgw_in_range(
                fx_map, start, end, exclude=used_gws, rules=rules, fallback_gw=default_gw, opening_schedule=opening_schedule
            )
            used_gws.add(gw)
            entries.append((gw, chip))

    calendar = tuple(sorted(entries, key=lambda item: item[0]))
    validate_chip_calendar(rules, calendar)
    return calendar


def build_causal_origin_chip_metadata(
    season: Literal["2024-25", "2025-26"],
    *,
    gw: int,
    bootstrap_chips: list[dict[str, Any]],
    horizon_fixtures: list[dict[str, Any]],
    club_ids: set[int],
) -> dict[str, Any]:
    """Build causal per-origin chip/schedule metadata strictly from pre-deadline bootstrap & fixtures."""
    rules = get_rules(season)
    counts: dict[str, dict[str, int]] = {}
    end_gw = min(gw + 5, 38)
    for w in range(gw, end_gw + 1):
        gw_counts = {str(cid): 0 for cid in sorted(club_ids)}
        for row in horizon_fixtures:
            if int(row["event"]) == w:
                th, ta = str(int(row["team_h"])), str(int(row["team_a"]))
                if th in gw_counts:
                    gw_counts[th] += 1
                if ta in gw_counts:
                    gw_counts[ta] += 1
        counts[str(w)] = gw_counts
    return {
        "gw": gw,
        "rules_version": rules.version,
        "two_chip_sets": rules.two_chip_sets,
        "afcon_gw15_topup": rules.afcon_gw15_topup and gw == 16,
        "active_chip_windows": [
            {
                "name": str(c.get("name", "")),
                "start_event": c.get("start_event"),
                "stop_event": c.get("stop_event"),
            }
            for c in bootstrap_chips
            if isinstance(c, Mapping)
        ],
        "blank_clubs_by_gw": {w: [int(cid) for cid, n in gw_map.items() if n == 0] for w, gw_map in counts.items()},
        "double_clubs_by_gw": {w: [int(cid) for cid, n in gw_map.items() if n >= 2] for w, gw_map in counts.items()},
    }


def build_seed_manifest(
    *,
    season: Literal["2024-25"],
    processed_dir: Path,
    vaastav_commits: list[dict[str, Any]],
    upstream_digests: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build pinned 2024-25 prior-season seed manifest with manager exclusions and DefCon status."""
    players = pd.read_parquet(processed_dir / "players.parquet")
    perf = pd.read_parquet(processed_dir / "player_performances.parquet")
    manager_ids = set(players[players["position_id"] == 5]["id"].astype(int))
    excluded_perf_rows = int(perf["player_id"].isin(manager_ids).sum())

    processed_digests: dict[str, dict[str, Any]] = {}
    for pq in sorted(processed_dir.glob("*.parquet")):
        raw = pq.read_bytes()
        processed_digests[pq.name] = {"sha256": sha256_bytes(raw), "bytes": len(raw)}

    return {
        "schema_version": 2,
        "season": season,
        "role": "prior_season_seed",
        "vaastav_commits": vaastav_commits,
        "upstream_digests": upstream_digests,
        "processed_digests": processed_digests,
        "players_total": int(len(players)),
        "excluded_position_5_count": int(len(manager_ids)),
        "excluded_position_5_perf_rows": excluded_perf_rows,
        "retained_player_count": int(len(players) - len(manager_ids)),
        "retained_perf_rows": int(len(perf) - excluded_perf_rows),
        "defensive_contribution_status": "inapplicable_native",
        "code_mapping_rule": "opta_code_primary_normalized_identity_secondary_absent_newcomer",
    }
