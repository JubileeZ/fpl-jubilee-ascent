"""Quarantined Randdalf/fplcache pre-deadline ingestion and settled outcome reconciliation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
import json
import lzma
from pathlib import Path
import re
from typing import Any, Literal, Protocol
from urllib.parse import urlparse
from urllib.request import urlopen

import pandas as pd

from backtesting.admission_fixtures import assess_fixture_coverage, assess_issue_fixture_coverage
from backtesting.input_evidence import (
    FieldAssessment,
    FieldEvidence,
    FreshnessRule,
    SourceEvidence,
    assess_field,
    load_receipt,
    validate_player_inputs,
    validate_schedule_inputs,
)
from backtesting.season_rules import load_season_lifecycle

FPLCACHE_REPO = "Randdalf/fplcache"
FPLCACHE_URL = "https://github.com/Randdalf/fplcache"
FPLCACHE_LICENSE = "The Unlicense"
FPLCACHE_TREE_URL = "https://api.github.com/repos/Randdalf/fplcache/git/trees/main?recursive=1"
FPLCACHE_RAW_BASE = "https://raw.githubusercontent.com/Randdalf/fplcache/main"
FPLCACHE_NORMAL_MAX_AGE_SECONDS = 8 * 3600
FPLCACHE_HARD_MAX_AGE_SECONDS = 24 * 3600
LOCAL_RECEIPT_HARD_MAX_AGE_SECONDS = 6 * 3600
MAX_DECOMPRESSED_BYTES = 16 * 1024 * 1024
PLAYER_ELEMENT_TYPES = (1, 2, 3, 4)

ALLOWLISTED_ELEMENT_FIELDS = (
    "id",
    "code",
    "team",
    "element_type",
    "now_cost",
    "status",
    "chance_of_playing_next_round",
    "chance_of_playing_this_round",
    "news",
    "news_added",
    "can_select",
    "removed",
    "selected_by_percent",
)
_CACHE_PATH_RE = re.compile(r"^cache/(20\d{2})/(\d{1,2})/(\d{1,2})/(\d{4})\.json\.xz$")
_BASE_LIMITATIONS: tuple[dict[str, Any], ...] = (
    {
        "code": "late_press_conference_lag",
        "window": "<=24h",
        "applies_to": "fplcache",
        "reference": "issue #175 Q13",
        "detail": (
            "Randdalf/fplcache polls every ~6h (<=24h ceiling); late pre-deadline press conferences "
            "and unsigned bot commits leave a bounded pre-deadline news lag disclosed per #175."
        ),
    },
)
_SEASON_SPECIFIC_LIMITATIONS: Mapping[str, tuple[dict[str, Any], ...]] = {
    "2026-27": (
        {
            "code": "gw1_5_exploratory_baseline_checks",
            "gameweeks": [1, 2, 3, 4, 5],
            "reference": "ADR 0069 / issue #185",
            "detail": (
                "2026-27 GW1-5 included prior exploratory baseline checks prior to ADR 0069 quarantine "
                "designation and is permanently disclosed when evaluating 2026-27."
            ),
        },
    ),
}


@dataclass(frozen=True)
class _ReconciliationResult:
    sched_errors: list[str]
    dgw_club_count: int
    bgw_club_count: int
    settlement_status: str
    settlement_errors: list[str]
    transfer_reconciled_count: int = 0


@dataclass(frozen=True)
class _CandidateSnapshot:
    status: str
    source_type: str
    source_path: str
    snapshot_ts: datetime
    capture_lower: datetime
    capture_upper: datetime
    lag_hours: float
    lower_lag_hours: float
    payload_bytes: bytes = b""
    payload: dict[str, Any] = field(default_factory=dict)
    disclosures: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()


class FplCachePort(Protocol):
    """Port for listing and fetching Randdalf/fplcache LZMA bootstrap snapshots."""

    def list_snapshots(self) -> Sequence[tuple[str, datetime]]: ...

    def fetch_snapshot_xz(self, path: str) -> bytes: ...


def validate_fplcache_url(url: str) -> str:
    parsed = urlparse(url)
    allowed_raw = parsed.netloc == "raw.githubusercontent.com" and parsed.path.startswith("/Randdalf/fplcache/")
    allowed_api = parsed.netloc == "api.github.com" and parsed.path.startswith("/repos/Randdalf/fplcache/")
    if parsed.scheme != "https" or not (allowed_raw or allowed_api):
        raise ValueError(f"URL outside approved Randdalf/fplcache origin: {url}")
    return url


def parse_fplcache_snapshot_path(path: str) -> datetime | None:
    match = _CACHE_PATH_RE.fullmatch(path)
    if not match:
        return None
    year, month, day, hhmm = int(match.group(1)), int(match.group(2)), int(match.group(3)), match.group(4)
    return datetime(year, month, day, int(hhmm[:2]), int(hhmm[2:]), tzinfo=UTC)


class GitHubFplCacheAdapter:
    """HTTPS adapter reading public Randdalf/fplcache snapshots with strict URL allowlist."""

    def __init__(self, tree_url: str = FPLCACHE_TREE_URL, raw_base: str = FPLCACHE_RAW_BASE) -> None:
        self._tree_url = validate_fplcache_url(tree_url)
        self._raw_base = validate_fplcache_url(raw_base + "/").rstrip("/")

    def list_snapshots(self) -> Sequence[tuple[str, datetime]]:
        with urlopen(validate_fplcache_url(self._tree_url), timeout=30) as resp:  # noqa: S310
            payload = json.loads(resp.read())
        snapshots: list[tuple[str, datetime]] = []
        for entry in payload.get("tree", []):
            path = str(entry.get("path", ""))
            ts = parse_fplcache_snapshot_path(path)
            if ts is not None:
                snapshots.append((path, ts))
        return sorted(snapshots, key=lambda item: item[1])

    def fetch_snapshot_xz(self, path: str) -> bytes:
        if parse_fplcache_snapshot_path(path) is None:
            raise ValueError(f"Unexpected fplcache snapshot path: {path}")
        url = validate_fplcache_url(f"{self._raw_base}/{path}")
        with urlopen(url, timeout=30) as resp:  # noqa: S310
            data: bytes = resp.read()
        return data


def _utc(value: Any) -> datetime:
    if isinstance(value, pd.Timestamp):
        dt = value.to_pydatetime()
    elif isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    else:
        raise ValueError(f"Invalid timestamp: {value!r}")
    if dt.tzinfo is None or dt.utcoffset() is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _unpack_bootstrap_xz(raw: bytes) -> tuple[bytes, dict[str, Any]]:
    decoder = lzma.LZMADecompressor()
    decoded = decoder.decompress(raw, max_length=MAX_DECOMPRESSED_BYTES + 1)
    if len(decoded) > MAX_DECOMPRESSED_BYTES or not decoder.eof:
        raise ValueError("Bootstrap size cap or incomplete LZMA stream")
    payload = json.loads(decoded)
    if not isinstance(payload, dict):
        raise ValueError("Malformed bootstrap JSON object")
    return decoded, payload


def extract_max_news_added(payload: Mapping[str, Any]) -> datetime | None:
    """Return latest element ``news_added`` UTC timestamp inside a bootstrap payload."""
    max_news_added: datetime | None = None
    for el in payload.get("elements", []):
        if not isinstance(el, Mapping):
            continue
        news_raw = el.get("news_added")
        if isinstance(news_raw, str) and news_raw.strip():
            news_dt = _utc(news_raw)
            if max_news_added is None or news_dt > max_news_added:
                max_news_added = news_dt
    return max_news_added


def is_purchase_eligible(element: Mapping[str, Any]) -> bool:
    """Resolve purchase eligibility from FPL element payload without mutating hold/sell rights."""
    can_select = element.get("can_select")
    selectable = bool(can_select) if can_select is not None else (element.get("status") != "u")
    return selectable and not bool(element.get("removed", False))


def _sanitize_bootstrap(
    payload: dict[str, Any],
    *,
    capture_upper: datetime,
) -> tuple[list[dict[str, Any]], set[int], list[str]]:
    issues: list[str] = []
    club_ids = {int(t["id"]) for t in payload.get("teams", []) if isinstance(t, Mapping) and "id" in t}
    sanitized: list[dict[str, Any]] = []
    max_news_added = extract_max_news_added(payload)

    for el in payload.get("elements", []):
        if not isinstance(el, Mapping):
            continue
        if el.get("element_type") not in PLAYER_ELEMENT_TYPES:
            continue
        row = {field: el.get(field) for field in ALLOWLISTED_ELEMENT_FIELDS}
        row["purchase_eligible"] = is_purchase_eligible(el)
        sanitized.append(row)

    if max_news_added is not None and max_news_added > capture_upper:
        issues.append("news_added_after_capture")
    player_issues = validate_player_inputs(sanitized, club_ids, require_ownership=True)
    issues.extend(player_issues)
    return sanitized, club_ids, sorted(set(issues))


def _build_schedule_rows(
    players: Sequence[Mapping[str, int]],
    target_gws: Sequence[int],
    club_gw_counts: Mapping[tuple[int, int], Sequence[int]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for player in players:
        pid, club = player["id"], player["club"]
        for tgt_gw in target_gws:
            matches = club_gw_counts.get((club, tgt_gw), ())
            if matches:
                for fid in matches:
                    rows.append({"player": pid, "gw": tgt_gw, "status": "fixture", "fixture": fid})
            else:
                rows.append({"player": pid, "gw": tgt_gw, "status": "blank", "fixture": None})
    return rows


def _reconcile_post_snapshot_transfers(
    players: Sequence[dict[str, int]],
    club_ids: set[int],
    gw_fx: pd.DataFrame,
    gw_perf: pd.DataFrame,
) -> tuple[list[dict[str, int]], int]:
    fx_clubs = {int(fx["id"]): (int(fx["home_club_id"]), int(fx["away_club_id"])) for _, fx in gw_fx.iterrows()}
    has_was_home = "was_home" in gw_perf.columns
    player_club_candidates: dict[int, set[int]] = {}
    for _, row in gw_perf.iterrows():
        fid = int(row["fixture_id"])
        clubs = fx_clubs.get(fid)
        if clubs is None:
            continue
        pid = int(row["player_id"])
        home, away = clubs
        row_clubs = {home if bool(row["was_home"]) else away} if (has_was_home and pd.notna(row.get("was_home"))) else {home, away}
        player_club_candidates[pid] = row_clubs if pid not in player_club_candidates else (player_club_candidates[pid] & row_clubs)

    reconciled: list[dict[str, int]] = []
    reconciled_count = 0
    for player in players:
        pid, pre_club = player["id"], player["club"]
        cands = player_club_candidates.get(pid)
        if cands and pre_club not in cands and len(cands) == 1:
            settled_club = next(iter(cands))
            if settled_club in club_ids:
                reconciled.append({"id": pid, "club": settled_club})
                reconciled_count += 1
                continue
        reconciled.append({"id": pid, "club": pre_club})
    return reconciled, reconciled_count


ADMITTED_STATUSES = frozenset({"admitted", "admitted_disclosed_8h_24h", "admitted_local_receipt"})


def _reconcile_schedule_and_outcomes(
    *,
    gw: int,
    deadline: datetime,
    gw_row: Mapping[str, Any],
    sanitized_players: list[dict[str, Any]],
    club_ids: set[int],
    fixtures_df: pd.DataFrame,
    performances_df: pd.DataFrame | None,
    outcome_captured_at: datetime | None,
    horizon_gws: int,
) -> _ReconciliationResult:
    target_gws = list(range(gw, min(gw + horizon_gws, 39)))
    target_set = set(target_gws)
    window_fx = fixtures_df[fixtures_df["gameweek_id"].isin(target_set)] if not fixtures_df.empty else fixtures_df

    schedule_fix_rows: list[dict[str, Any]] = []
    issue_fixtures: list[dict[str, Any]] = []
    for _, fx in window_fx.iterrows():
        fid = int(fx["id"])
        fgw = int(fx["gameweek_id"])
        home = int(fx["home_club_id"])
        away = int(fx["away_club_id"])
        ko_iso = _utc(fx["kickoff_time"]).isoformat().replace("+00:00", "Z") if pd.notna(fx.get("kickoff_time")) else None
        schedule_fix_rows.append({"id": fid, "event": fgw, "team_h": home, "team_a": away, "kickoff_time": ko_iso})
        issue_fixtures.append({"id": fid, "gw": fgw, "home_club": home, "away_club": away})

    represented_gws = {r["event"] for r in schedule_fix_rows}
    declared_blanks = frozenset(target_set - represented_gws)
    sched_issues = set(validate_schedule_inputs(schedule_fix_rows, tuple(target_gws), club_ids, declared_blanks))

    players = [{"id": int(p["id"]), "club": int(p["team"])} for p in sanitized_players]
    club_gw_counts: dict[tuple[int, int], list[int]] = {}
    for row in issue_fixtures:
        club_gw_counts.setdefault((row["home_club"], row["gw"]), []).append(row["id"])
        club_gw_counts.setdefault((row["away_club"], row["gw"]), []).append(row["id"])

    dgw_club_count = sum(1 for c in club_ids if len(club_gw_counts.get((c, gw), [])) > 1)
    bgw_club_count = sum(1 for c in club_ids if len(club_gw_counts.get((c, gw), [])) == 0)

    schedule_rows = _build_schedule_rows(players, target_gws, club_gw_counts)
    cutoff_iso = deadline.isoformat().replace("+00:00", "Z")
    input_package: dict[str, Any] = {"players": players, "fixtures": issue_fixtures, "schedule": schedule_rows}
    if players and issue_fixtures:
        sched_issues.update(
            assess_issue_fixture_coverage(
                input_package, issue_gw=gw, target_gws=target_gws, issue_cutoff=cutoff_iso
            )
        )

    gw_fx = fixtures_df[fixtures_df["gameweek_id"] == gw]
    gw_finished = bool(gw_row.get("finished", False))
    gw_data_checked = bool(gw_row.get("data_checked", False))
    all_fx_finished = (not gw_fx.empty) and bool(gw_fx["finished"].fillna(False).astype(bool).all())

    if not (gw_finished and gw_data_checked and all_fx_finished) or outcome_captured_at is None:
        return _ReconciliationResult(sorted(sched_issues), dgw_club_count, bgw_club_count, "unsettled", [])

    max_ko = max(_utc(ko) for ko in gw_fx["kickoff_time"])
    if outcome_captured_at < max_ko + timedelta(hours=24):
        return _ReconciliationResult(sorted(sched_issues), dgw_club_count, bgw_club_count, "unsettled", [])

    if performances_df is None or not players:
        return _ReconciliationResult(sorted(sched_issues), dgw_club_count, bgw_club_count, "settled_no_performances", [])

    finalized_iso = (max_ko + timedelta(hours=24)).isoformat().replace("+00:00", "Z")
    captured_iso = outcome_captured_at.isoformat().replace("+00:00", "Z")
    fixture_events = [
        {
            "fixture": int(fx["id"]),
            "gw": gw,
            "status": "final",
            "home_club": int(fx["home_club_id"]),
            "away_club": int(fx["away_club_id"]),
            "changed_at": finalized_iso,
            "finalized_at": finalized_iso,
        }
        for _, fx in gw_fx.iterrows()
    ]
    pre_player_ids = {p["id"] for p in players}
    gw_perf = performances_df[performances_df["gameweek_id"] == gw]
    outcomes_rows: list[dict[str, Any]] = []
    for _, row in gw_perf.iterrows():
        pid = int(row["player_id"])
        if pid not in pre_player_ids:
            continue
        mins = float(row.get("minutes", 0) or 0)
        pts = float(row.get("total_points", 0) or 0)
        is_dnp = mins == 0 and pts == 0
        outcomes_rows.append(
            {
                "player": pid,
                "gw": gw,
                "fixture": int(row["fixture_id"]),
                "status": "dnp" if is_dnp else "played",
                "points": 0 if is_dnp else int(pts),
            }
        )
    settled_players, transfer_reconciled = _reconcile_post_snapshot_transfers(players, club_ids, gw_fx, gw_perf)
    settled_input = (
        input_package
        if transfer_reconciled == 0
        else {
            "players": settled_players,
            "fixtures": issue_fixtures,
            "schedule": _build_schedule_rows(settled_players, target_gws, club_gw_counts),
        }
    )
    settlement_errors = list(
        assess_fixture_coverage(
            settled_input,
            {"fixture_events": fixture_events, "outcomes": outcomes_rows},
            issue_gw=gw,
            target_gws=target_gws,
            issue_cutoff=cutoff_iso,
            outcome_cutoff=captured_iso,
        )
    )
    status = "settled_verified" if not settlement_errors else "settlement_coverage_mismatch"
    return _ReconciliationResult(
        sorted(sched_issues),
        dgw_club_count,
        bgw_club_count,
        status,
        settlement_errors,
        transfer_reconciled,
    )


def _assess_bootstrap_evidence(
    *,
    source_id: str,
    raw_bytes: bytes,
    timing_basis: Literal["receipt", "bounded_reconstruction"],
    capture_lower: datetime,
    capture_upper: datetime,
    references: tuple[str, ...],
    coverage_reference: str,
    max_age_seconds: int,
    rule_reference: str,
    deadline: datetime,
) -> FieldAssessment:
    field = FieldEvidence(
        name="origin_bootstrap",
        source=SourceEvidence(
            source_id=source_id,
            raw=raw_bytes,
            sha256=hashlib.sha256(raw_bytes).hexdigest(),
            timing_basis=timing_basis,
            capture_lower=capture_lower,
            capture_upper=capture_upper,
            publication_upper=capture_upper,
            references=references,
        ),
        content_issues=(),
        coverage_reference=coverage_reference,
        freshness=FreshnessRule(max_age_seconds, rule_reference, True),
    )
    return assess_field(field, deadline)


def _select_receipt_override(
    receipt_storage: Path | None,
    receipt_id: str | None,
    *,
    season: str,
    gw: int,
    deadline: datetime,
) -> tuple[dict[str, Any], bytes, datetime] | None:
    if receipt_storage is None or receipt_id is None:
        return None
    record, raw_bytes = load_receipt(receipt_storage, receipt_id)
    if (
        record.get("season") != season
        or record.get("gw") != gw
        or record.get("endpoint") != "bootstrap-static"
    ):
        raise ValueError(f"Receipt {receipt_id} scope/endpoint mismatch for {season} GW{gw}")
    received = _utc(record["received_at"])
    assessment = _assess_bootstrap_evidence(
        source_id=f"receipt:{receipt_id}",
        raw_bytes=raw_bytes,
        timing_basis="receipt",
        capture_lower=received,
        capture_upper=received,
        references=("local_receipt",),
        coverage_reference="local_receipt",
        max_age_seconds=LOCAL_RECEIPT_HARD_MAX_AGE_SECONDS,
        rule_reference="issue #175 receipt <= 6h",
        deadline=deadline,
    )
    if assessment.status != "supported" or record["late"]:
        return None
    return record, raw_bytes, received


def _resolve_fplcache_candidate(
    *,
    season: str,
    gw: int,
    deadline: datetime,
    reference_utc: datetime,
    snapshots: Sequence[tuple[str, datetime]],
    source_port: FplCachePort,
    receipt_override: tuple[dict[str, Any], bytes, datetime] | None,
) -> _CandidateSnapshot:
    season_disclosures = ("gw1_5_exploratory_baseline_checks",) if (season == "2026-27" and gw <= 5) else ()
    pre = [(path, ts) for path, ts in snapshots if ts < deadline]
    cand_path, cand_ts = pre[-1] if pre else (None, None)
    cand_lag_sec = (deadline - cand_ts).total_seconds() if cand_ts is not None else float("inf")
    if receipt_override is not None and (cand_ts is None or receipt_override[2] >= cand_ts or cand_lag_sec > FPLCACHE_HARD_MAX_AGE_SECONDS):
        record, raw_bytes, received = receipt_override
        payload = json.loads(raw_bytes)
        lag_h = round((deadline - received).total_seconds() / 3600.0, 2)
        return _CandidateSnapshot(
            status="admitted_local_receipt",
            source_type="local_receipt",
            source_path=record["receipt_id"],
            snapshot_ts=received,
            capture_lower=received,
            capture_upper=received,
            lag_hours=lag_h,
            lower_lag_hours=lag_h,
            payload_bytes=raw_bytes,
            payload=payload,
            disclosures=season_disclosures,
        )

    is_future = deadline > reference_utc
    if cand_path is None or cand_ts is None:
        return _CandidateSnapshot(
            status="pending_future_gw" if is_future else "source_missing",
            source_type="none",
            source_path="",
            snapshot_ts=deadline,
            capture_lower=deadline,
            capture_upper=deadline,
            lag_hours=0.0,
            lower_lag_hours=0.0,
            issues=() if is_future else ("source_missing",),
        )
    lag_h = round(cand_lag_sec / 3600.0, 2)
    cap_lower = cand_ts - timedelta(seconds=1800)
    lower_lag_h = round((deadline - cap_lower).total_seconds() / 3600.0, 2)
    if is_future and cand_lag_sec > FPLCACHE_HARD_MAX_AGE_SECONDS:
        return _CandidateSnapshot("pending_future_gw", "fplcache", cand_path, cand_ts, cap_lower, cand_ts, lag_h, lower_lag_h)
    if cand_lag_sec > FPLCACHE_HARD_MAX_AGE_SECONDS:
        return _CandidateSnapshot(
            "source_stale", "fplcache", cand_path, cand_ts, cap_lower, cand_ts, lag_h, lower_lag_h, issues=("source_stale",)
        )

    raw_xz = source_port.fetch_snapshot_xz(cand_path)
    _, payload = _unpack_bootstrap_xz(raw_xz)
    assessment = _assess_bootstrap_evidence(
        source_id=f"{FPLCACHE_REPO}:{cand_path}",
        raw_bytes=raw_xz,
        timing_basis="bounded_reconstruction",
        capture_lower=cap_lower,
        capture_upper=cand_ts,
        references=(FPLCACHE_URL, cand_path),
        coverage_reference=cand_path,
        max_age_seconds=FPLCACHE_HARD_MAX_AGE_SECONDS,
        rule_reference="issue #175 fplcache <= 24h",
        deadline=deadline,
    )
    if assessment.status != "supported":
        return _CandidateSnapshot(
            "source_stale" if "source_stale" in assessment.reasons else assessment.status,
            "fplcache",
            cand_path,
            cand_ts,
            cap_lower,
            cand_ts,
            lag_h,
            lower_lag_h,
            issues=assessment.reasons,
        )
    disclosures = ("late_press_conference_lag", *season_disclosures)
    if cand_lag_sec > FPLCACHE_NORMAL_MAX_AGE_SECONDS:
        return _CandidateSnapshot(
            "admitted_disclosed_8h_24h",
            "fplcache",
            cand_path,
            cand_ts,
            cap_lower,
            cand_ts,
            lag_h,
            lower_lag_h,
            payload_bytes=raw_xz,
            payload=payload,
            disclosures=(*disclosures, "stale_window_8h_24h"),
        )
    return _CandidateSnapshot(
        "admitted",
        "fplcache",
        cand_path,
        cand_ts,
        cap_lower,
        cand_ts,
        lag_h,
        lower_lag_h,
        payload_bytes=raw_xz,
        payload=payload,
        disclosures=disclosures,
    )


def ingest_season_fplcache(
    *,
    season: str,
    gameweeks_df: pd.DataFrame,
    fixtures_df: pd.DataFrame,
    performances_df: pd.DataFrame | None = None,
    source_port: FplCachePort,
    quarantine_dir: Path,
    manifest_path: Path,
    reference_utc: datetime,
    outcome_captured_at: datetime | None = None,
    receipt_storage: Path | None = None,
    receipt_ids_by_gw: Mapping[int, str] | None = None,
    horizon_gws: int = 6,
) -> dict[str, Any]:
    """Ingest GW1-38 pre-deadline fplcache snapshots, sanitize inputs, and reconcile settled outcomes."""
    lifecycle = load_season_lifecycle()
    lifecycle.assert_access(season, purpose="active_validation")
    quarantine = lifecycle.assert_unsealed_storage_path(quarantine_dir)
    manifest_file = lifecycle.assert_unsealed_storage_path(manifest_path)
    quarantine.mkdir(parents=True, exist_ok=True)
    snapshots = sorted(source_port.list_snapshots(), key=lambda item: item[1])
    receipt_map = receipt_ids_by_gw or {}
    records: list[dict[str, Any]] = []

    for _, gw_row in gameweeks_df.sort_values("id").iterrows():
        gw = int(gw_row["id"])
        deadline = _utc(gw_row["deadline_time"])
        override = _select_receipt_override(
            receipt_storage, receipt_map.get(gw), season=season, gw=gw, deadline=deadline
        )
        cand = _resolve_fplcache_candidate(
            season=season,
            gw=gw,
            deadline=deadline,
            reference_utc=reference_utc,
            snapshots=snapshots,
            source_port=source_port,
            receipt_override=override,
        )

        status = cand.status
        issues = list(cand.issues)
        raw_sha = hashlib.sha256(cand.payload_bytes).hexdigest() if cand.payload_bytes else None
        player_count = 0
        recon = _ReconciliationResult([], 0, 0, "not_applicable", [])

        if status in ADMITTED_STATUSES:
            sanitized, club_ids, sanitize_issues = _sanitize_bootstrap(cand.payload, capture_upper=cand.capture_upper)
            player_count = len(sanitized)
            if sanitize_issues:
                status = "invalid"
                issues = sorted(set(issues + sanitize_issues))
            else:
                recon = _reconcile_schedule_and_outcomes(
                    gw=gw,
                    deadline=deadline,
                    gw_row=gw_row,
                    sanitized_players=sanitized,
                    club_ids=club_ids,
                    fixtures_df=fixtures_df,
                    performances_df=performances_df,
                    outcome_captured_at=outcome_captured_at,
                    horizon_gws=horizon_gws,
                )
                quarantine_payload = {
                    "season": season,
                    "gw": gw,
                    "deadline_utc": deadline.isoformat(),
                    "snapshot_utc": cand.snapshot_ts.isoformat(),
                    "source_type": cand.source_type,
                    "source_path": cand.source_path,
                    "players": sanitized,
                }
                (quarantine / f"gw{gw:02d}_pre_deadline_inputs.json").write_text(
                    json.dumps(quarantine_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )

        has_snap = status != "source_missing"
        records.append(
            {
                "gw": gw,
                "deadline_utc": deadline.isoformat(),
                "input_status": status,
                "source_type": cand.source_type,
                "source_path": cand.source_path,
                "snapshot_utc": cand.snapshot_ts.isoformat() if has_snap else None,
                "capture_lower_utc": cand.capture_lower.isoformat() if has_snap else None,
                "capture_upper_utc": cand.capture_upper.isoformat() if has_snap else None,
                "lag_hours": cand.lag_hours if has_snap else None,
                "capture_lower_lag_hours": cand.lower_lag_hours if has_snap else None,
                "payload_sha256": raw_sha,
                "player_count": player_count,
                "schedule_coverage_errors": recon.sched_errors,
                "dgw_club_count": recon.dgw_club_count,
                "bgw_club_count": recon.bgw_club_count,
                "outcome_settlement_status": recon.settlement_status,
                "settlement_coverage_errors": recon.settlement_errors,
                "transfer_reconciled_count": recon.transfer_reconciled_count,
                "disclosed_limitations": list(cand.disclosures),
                "issues": issues,
            }
        )

    admitted = [r for r in records if r["input_status"] in ADMITTED_STATUSES]
    lags = [float(r["lag_hours"]) for r in admitted if r["lag_hours"] is not None]
    limitations = [*_BASE_LIMITATIONS, *_SEASON_SPECIFIC_LIMITATIONS.get(season, ())]
    manifest = {
        "schema_version": 1,
        "adr": "0069",
        "freshness_policy_issue": 175,
        "season": season,
        "rules_id": lifecycle.seasons[season].rules_id,
        "reference_utc": reference_utc.isoformat(),
        "outcome_captured_at": outcome_captured_at.isoformat() if outcome_captured_at else None,
        "attribution": {
            "repo": FPLCACHE_REPO,
            "url": FPLCACHE_URL,
            "license": FPLCACHE_LICENSE,
            "credit": f"Pre-deadline bootstrap snapshots sourced from {FPLCACHE_REPO} ({FPLCACHE_LICENSE}).",
        },
        "disclosed_limitations": limitations,
        "summary": {
            "admitted_gws": [r["gw"] for r in admitted],
            "disclosed_8h_24h_gws": [r["gw"] for r in records if r["input_status"] == "admitted_disclosed_8h_24h"],
            "pending_future_gws": [r["gw"] for r in records if r["input_status"] == "pending_future_gw"],
            "settled_verified_gws": [r["gw"] for r in records if r["outcome_settlement_status"] == "settled_verified"],
            "min_lag_hours": min(lags) if lags else None,
            "max_lag_hours": max(lags) if lags else None,
        },
        "gameweeks": records,
    }
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
