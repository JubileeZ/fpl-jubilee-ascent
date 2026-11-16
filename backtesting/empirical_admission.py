"""Unified mode='empirical' admission engine for development mirrors and prospective receipts (#178)."""

from __future__ import annotations

import json
import lzma
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtesting.empirical_mirrors import (
    FIXTURE_DISCLOSURE_AGE_SECONDS,
    FIXTURE_MAX_CAP_SECONDS,
    FIXTURE_MIN_CAP_SECONDS,
    FIXTURE_TARGET_SECONDS,
    FPLCACHE_MAX_HARD_SECONDS,
    FPLCACHE_MAX_TARGET_SECONDS,
    SETTLEMENT_MIN_WAIT_SECONDS,
    canonical_json_bytes,
    parse_fixtures_csv_window,
    sha256_bytes,
)
from backtesting.fplcache_ingest import (
    LOCAL_RECEIPT_HARD_MAX_AGE_SECONDS,
    _sanitize_bootstrap,
    _unpack_bootstrap_xz,
    _utc,
    extract_max_news_added,
)
from backtesting.replay_state import Outcome, _validate_outcome
from backtesting.season_rules import Chip, get_rules, load_season_lifecycle, validate_chip_calendar

UTC = timezone.utc

PROSPECTIVE_MAX_SECONDS = LOCAL_RECEIPT_HARD_MAX_AGE_SECONDS
MIRROR_DISCLOSURE_CODES = frozenset(
    {
        "fplcache_mirror_provenance",
        "vaastav_mirror_provenance",
        "bootstrap_stale_band_8h_to_24h",
        "fixture_schedule_gt_48h",
        "fixture_stale_band_7d_to_21d",
    }
)
ALLOWED_STATUSES = frozenset({"a", "d", "i", "s", "u", "n"})


def resolve_source_bytes(spec: Mapping[str, Any], catalog: Mapping[str, bytes] | None) -> bytes | None:
    """Resolve raw source bytes from in-memory catalog or verified local disk path."""
    sid = spec.get("source_id")
    if isinstance(sid, str) and catalog is not None and sid in catalog:
        return catalog[sid]
    path_raw = spec.get("path")
    if isinstance(path_raw, str) and path_raw:
        p = Path(path_raw)
        if p.exists() and p.is_file():
            return p.read_bytes()
    return None


def verify_digests(spec: Mapping[str, Any], raw_bytes: bytes) -> tuple[bytes, str | None]:
    """Verify content-addressed blob_sha256 and decompressed_sha256."""
    expected_blob = spec.get("blob_sha256")
    if not isinstance(expected_blob, str) or expected_blob != sha256_bytes(raw_bytes):
        return raw_bytes, "blob_sha256_mismatch"

    if raw_bytes.startswith(b"\xfd7zXZ\x00"):
        try:
            decompressed, _ = _unpack_bootstrap_xz(raw_bytes)
        except (ValueError, lzma.LZMAError):
            return raw_bytes, "malformed_xz_payload"
    else:
        decompressed = raw_bytes

    expected_dec = spec.get("decompressed_sha256")
    if isinstance(expected_dec, str) and expected_dec != sha256_bytes(decompressed):
        return decompressed, "decompressed_sha256_mismatch"
    return decompressed, None


def validate_seed_mapping(
    seed_obj: Mapping[str, Any],
    elements: list[Mapping[str, Any]],
    *,
    check_defcon: bool = True,
) -> list[str]:
    """Validate 1-to-1 prior-season seed mapping, position_id==5 exclusion, and DefCon applicability."""
    issues: list[str] = []
    seed_players = seed_obj.get("players", [])
    if not isinstance(seed_players, list):
        return ["malformed_seed_players"]
    non_manager_seed = [row for row in seed_players if int(row.get("position_id", 0)) != 5]
    seed_ids = {str(row.get("id") or row.get("player_id")) for row in non_manager_seed}
    seed_mapping = seed_obj.get("seed_mapping")
    if not isinstance(seed_mapping, Mapping):
        return ["missing_seed_mapping"]

    if check_defcon and seed_obj.get("defensive_contribution_status") == "inapplicable_native":
        hist = seed_obj.get("history", [])
        if isinstance(hist, list) and any(isinstance(r, Mapping) and "defensive_contribution" in r for r in hist):
            issues.append("seed:inapplicable_defensive_contribution_imputed")

    seen_mapped: set[str] = set()
    for el in elements:
        if int(el.get("position_id", 0)) == 5:
            continue
        pid = str(el["id"])
        mapped = seed_mapping.get(pid)
        if not isinstance(mapped, str) or not mapped:
            issues.append(f"unmapped_player:{pid}")
            continue
        if mapped.startswith("absent:"):
            if mapped != f"absent:{pid}":
                issues.append(f"invalid_absent_token:{pid}")
        elif mapped not in seed_ids:
            issues.append(f"unknown_seed_target:{pid}->{mapped}")
        else:
            if mapped in seen_mapped:
                issues.append(f"duplicate_seed_target:{mapped}")
            seen_mapped.add(mapped)
    return issues


def _valid_outcomes_payload(
    rows: Any,
    *,
    rules_version: str,
    expected_player_ids: set[int] | None = None,
) -> list[str]:
    issues: list[str] = []
    if not isinstance(rows, list) or not rows:
        return ["outcomes_empty"]
    get_rules(rules_version)
    seen_ids: set[int] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            issues.append("malformed_outcome_row")
            break
        pid = row.get("player_id")
        if type(pid) is not int or pid <= 0 or pid in seen_ids:
            issues.append("invalid_or_duplicate_outcome_player")
            break
        seen_ids.add(pid)
        pts = row.get("total_points")
        mins = row.get("minutes")
        appeared = row.get("appeared")
        if appeared is None and type(mins) is int:
            appeared = mins > 0
        yc = row.get("yellow_cards", 0)
        rc = row.get("red_cards", 0)
        comp_sum = row.get("component_points_sum")
        if type(pts) is not int or type(mins) is not int or type(appeared) is not bool:
            issues.append("incomplete_outcome_row")
            break
        if type(yc) is not int or type(rc) is not int or (comp_sum is not None and type(comp_sum) is not int):
            issues.append("invalid_outcome_field_types")
            break
        try:
            _validate_outcome(
                Outcome(
                    points=pts,
                    minutes=mins,
                    appeared=appeared,
                    yellow_cards=yc,
                    red_cards=rc,
                    component_points_sum=comp_sum,
                )
            )
        except ValueError:
            issues.append("unreconciled_zero_min_or_invalid_outcome")
            break
    if not issues and expected_player_ids and not expected_player_ids <= seen_ids:
        issues.append("outcomes_missing_admitted_players")
    return issues


def _validate_chip_calendar_spec(season: str, raw_cal: Any) -> tuple[tuple[int, Chip], ...]:
    if not isinstance(raw_cal, list) or not raw_cal:
        raise ValueError("Empirical request requires predeclared shared_chip_calendar")
    entries: list[tuple[int, Chip]] = []
    for item in raw_cal:
        if not isinstance(item, Mapping):
            raise ValueError("Invalid shared_chip_calendar item")
        gw = item.get("gameweek")
        chip = item.get("chip")
        if type(gw) is not int or not isinstance(chip, str):
            raise ValueError("Invalid shared_chip_calendar entry")
        entries.append((gw, chip))  # type: ignore[arg-type]
    cal = tuple(sorted(entries, key=lambda x: x[0]))
    validate_chip_calendar(get_rules(season), cal)
    return cal


def assess_empirical_origins(
    request: Mapping[str, Any],
    catalog: Mapping[str, bytes] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate unified version=2 mode='empirical' origins under #175/#178 rules."""
    track = request.get("track")
    if track not in ("development_mirror", "prospective_receipt"):
        raise ValueError("Empirical request requires track in ('development_mirror', 'prospective_receipt')")
    if request.get("eligibility_policy") != "empirical-v2":
        raise ValueError("Unsupported empirical eligibility_policy")

    lifecycle = load_season_lifecycle()
    season_req = str(request.get("season", "")).strip()
    if not season_req:
        raise ValueError("Empirical request requires season")
    cal_error: str | None = None
    chip_calendar: tuple[tuple[int, Chip], ...] = ()
    try:
        chip_calendar = _validate_chip_calendar_spec(season_req, request.get("shared_chip_calendar"))
    except ValueError as exc:
        cal_error = str(exc)

    origins = request.get("origins", [])
    if not isinstance(origins, list) or not origins:
        raise ValueError("Origins required")

    eligible_since: dict[int, int] = {}
    anchor_spec = request.get("anchor")
    anchor_squad_ids = list(anchor_spec.get("squad_ids", [])) if isinstance(anchor_spec, Mapping) else []
    expected_next_gw = 1
    prior_admitted = True
    declared_partial = bool(request.get("partial_prefix", False))

    raw_reports: list[dict[str, Any]] = []
    for origin in origins:
        season = str(origin.get("season", "")).strip()
        gw = origin.get("gw")
        raw_disclosed = origin.get("disclosed_limitations", [])
        invalid_pre: list[str] = []
        unresolved_pre: list[str] = []
        invalid_post: list[str] = []
        unresolved_post: list[str] = []

        if not isinstance(raw_disclosed, list) or any(not isinstance(item, str) for item in raw_disclosed):
            invalid_pre.append("invalid_disclosed_limitations")
            disclosed: list[str] = []
        else:
            disclosed = list(raw_disclosed)

        if cal_error:
            invalid_pre.append(f"chip_calendar:{cal_error}")
        if season != season_req:
            invalid_pre.append("origin_season_mismatch")
        if type(gw) is not int or not 1 <= gw <= 38:
            invalid_pre.append("invalid_gw")
            gw_int = -1
        else:
            gw_int = gw

        try:
            get_rules(season)
            if gw_int >= 1:
                lifecycle.assert_access(season, gw_int, purpose="validation")
        except ValueError as exc:
            msg = str(exc)
            invalid_pre.append("sealed_holdout_leakage" if "Sealed scope" in msg else f"lifecycle:{msg}")

        if not prior_admitted or (gw_int != expected_next_gw):
            unresolved_pre.append("window_gap_or_prior_origin_unadmitted")
        expected_next_gw = (gw_int + 1) if gw_int >= 1 else expected_next_gw

        try:
            dl = _utc(origin.get("deadline"))
        except (TypeError, ValueError):
            invalid_pre.append("invalid_deadline")
            dl = datetime(1970, 1, 1, tzinfo=UTC)

        prev_dl_raw = origin.get("prev_deadline")
        prev_dl: datetime | None = None
        if prev_dl_raw is not None and prev_dl_raw != "":
            try:
                prev_dl = _utc(prev_dl_raw)
            except (TypeError, ValueError):
                invalid_pre.append("invalid_prev_deadline")

        if track == "prospective_receipt" and disclosed:
            invalid_pre.append("mirror_disclosure_on_prospective_receipt")

        sources = origin.get("sources")
        if not isinstance(sources, Mapping):
            unresolved_pre.append("sources_missing")
            sources = {}

        pre_role_digests: dict[str, dict[str, str]] = {}
        all_role_digests: dict[str, dict[str, str]] = {}
        sanitized_elements: list[dict[str, Any]] = []
        bs_club_ids: set[int] = set()
        fx_rows: list[dict[str, Any]] = []
        parsed_seed_obj: Mapping[str, Any] | None = None

        for role in ("bootstrap", "fixtures", "history", "seed", "outcomes"):
            inv_bucket = invalid_post if role == "outcomes" else invalid_pre
            unr_bucket = unresolved_post if role == "outcomes" else unresolved_pre

            spec = sources.get(role)
            if not isinstance(spec, Mapping):
                unr_bucket.append(f"{role}_missing")
                continue
            raw_bytes = resolve_source_bytes(spec, catalog)
            if raw_bytes is None:
                unr_bucket.append(f"{role}_bytes_missing")
                continue
            dec_bytes, err = verify_digests(spec, raw_bytes)
            if err:
                inv_bucket.append(f"{role}:{err}")
                continue
            digest_entry = {
                "blob_sha256": str(spec["blob_sha256"]),
                "decompressed_sha256": sha256_bytes(dec_bytes),
            }
            all_role_digests[role] = digest_entry
            if role != "outcomes":
                pre_role_digests[role] = digest_entry

            if role == "bootstrap":
                try:
                    bs_payload = json.loads(dec_bytes.decode("utf-8"))
                    cap_lo = _utc(spec.get("capture_lower"))
                    cap_up = _utc(spec.get("capture_upper"))
                except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
                    inv_bucket.append("bootstrap:malformed_metadata_or_json")
                    continue
                if cap_lo > cap_up:
                    inv_bucket.append("bootstrap:capture_bounds_reversed")
                basis = spec.get("timing_basis")
                if cap_up >= dl:
                    inv_bucket.append("bootstrap:capture_after_deadline")
                if track == "prospective_receipt" and basis != "receipt":
                    inv_bucket.append("bootstrap:prospective_requires_receipt")
                max_news = extract_max_news_added(bs_payload)
                if max_news is not None and max_news > cap_up:
                    inv_bucket.append("bootstrap:news_added_after_capture")
                age = (dl - cap_lo).total_seconds()
                if track == "development_mirror":
                    if age > FPLCACHE_MAX_HARD_SECONDS:
                        unr_bucket.append("bootstrap:source_stale_gt_24h")
                    elif age > FPLCACHE_MAX_TARGET_SECONDS and "bootstrap_stale_band_8h_to_24h" not in disclosed:
                        disclosed.append("bootstrap_stale_band_8h_to_24h")
                elif age > PROSPECTIVE_MAX_SECONDS:
                    unr_bucket.append("bootstrap:prospective_stale_gt_6h")

                sanitized_elements, bs_club_ids, bs_issues = _sanitize_bootstrap(bs_payload, capture_upper=cap_up)
                if bs_issues:
                    inv_bucket.extend(f"bootstrap:{i}" for i in bs_issues)
                for row in sanitized_elements:
                    pid_raw = row.get("id")
                    if type(pid_raw) is not int or pid_raw <= 0:
                        inv_bucket.append("bootstrap:invalid_player_id")
                        continue
                    if pid_raw not in eligible_since:
                        eligible_since[pid_raw] = gw_int
                    if row.get("status") not in ALLOWED_STATUSES:
                        inv_bucket.append(f"bootstrap:invalid_status:{pid_raw}")
                if not any(isinstance(ev, Mapping) and ev.get("id") == gw_int and ev.get("is_next") is True for ev in bs_payload.get("events", [])):
                    inv_bucket.append("bootstrap:events_is_next_mismatch")
                if gw_int == 1 and anchor_squad_ids:
                    if len(anchor_squad_ids) != 15 or len(set(anchor_squad_ids)) != 15:
                        inv_bucket.append("anchor:invalid_squad_size")
                    else:
                        el_by_id = {int(r["id"]): r for r in sanitized_elements if type(r.get("id")) is int}
                        if any(pid not in el_by_id or not el_by_id[pid]["purchase_eligible"] for pid in anchor_squad_ids):
                            inv_bucket.append("anchor:ineligible_player")

            elif role == "fixtures":
                try:
                    cap_lo = _utc(spec.get("capture_lower"))
                    cap_up = _utc(spec.get("capture_upper"))
                    fx_rows = parse_fixtures_csv_window(dec_bytes, gw_int)
                except (TypeError, ValueError, UnicodeDecodeError):
                    inv_bucket.append("fixtures:malformed_csv_or_bounds")
                    continue
                if cap_lo > cap_up:
                    inv_bucket.append("fixtures:capture_bounds_reversed")
                if cap_up >= dl:
                    inv_bucket.append("fixtures:capture_after_deadline")
                if track == "prospective_receipt":
                    if spec.get("timing_basis") != "receipt":
                        inv_bucket.append("fixtures:prospective_requires_receipt")
                    if (dl - cap_lo).total_seconds() > PROSPECTIVE_MAX_SECONDS:
                        unr_bucket.append("fixtures:prospective_stale_gt_6h")
                else:
                    in_window = (cap_up < dl) if gw_int == 1 else (prev_dl is not None and prev_dl < cap_up < dl)
                    if not in_window:
                        unr_bucket.append("fixtures:out_of_window")
                    else:
                        gap = (dl - prev_dl).total_seconds() if prev_dl is not None else float(FIXTURE_MAX_CAP_SECONDS)
                        hard_cap = float(FIXTURE_MAX_CAP_SECONDS if gw_int == 1 else min(FIXTURE_MAX_CAP_SECONDS, max(FIXTURE_MIN_CAP_SECONDS, gap)))
                        lower_cap = float(min(FIXTURE_MAX_CAP_SECONDS, max(FIXTURE_TARGET_SECONDS, gap)) if prev_dl is not None else FIXTURE_MAX_CAP_SECONDS)
                        age_up = (dl - cap_up).total_seconds()
                        age_lo = (dl - cap_lo).total_seconds()
                        if age_up > hard_cap or age_lo > lower_cap:
                            unr_bucket.append("fixtures:source_stale")
                        else:
                            if age_up > FIXTURE_DISCLOSURE_AGE_SECONDS and "fixture_schedule_gt_48h" not in disclosed:
                                disclosed.append("fixture_schedule_gt_48h")
                            if age_up > FIXTURE_TARGET_SECONDS and "fixture_stale_band_7d_to_21d" not in disclosed:
                                disclosed.append("fixture_stale_band_7d_to_21d")
                if not fx_rows:
                    unr_bucket.append("fixtures:empty_window")
                elif gw_int >= 1:
                    covered = {int(r["event"]) for r in fx_rows}
                    expected_gws = set(range(gw_int, min(gw_int + 6, 39)))
                    if not expected_gws <= covered:
                        unr_bucket.append("fixtures:incomplete_horizon_window")
                if bs_club_ids and any(int(r["team_h"]) not in bs_club_ids or int(r["team_a"]) not in bs_club_ids for r in fx_rows):
                    inv_bucket.append("fixtures:unknown_club_id")

            elif role == "history":
                try:
                    cap_up = _utc(spec.get("capture_upper"))
                    hist_rows = json.loads(dec_bytes.decode("utf-8"))
                except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
                    inv_bucket.append("history:malformed")
                    continue
                if not isinstance(hist_rows, list):
                    inv_bucket.append("history:malformed")
                    continue
                if cap_up >= dl:
                    inv_bucket.append("history:capture_after_deadline")
                if any(int(r.get("gameweek_id", gw_int)) >= gw_int for r in hist_rows):
                    inv_bucket.append("history:future_gw_leakage")
                if gw_int > 1:
                    present_gws = {int(r.get("gameweek_id", 0)) for r in hist_rows}
                    missing_gws = [pg for pg in range(1, gw_int) if pg not in present_gws]
                    if missing_gws:
                        unr_bucket.append(f"history:missing_prior_gws:{missing_gws}")

            elif role == "seed":
                try:
                    seed_parsed = json.loads(dec_bytes.decode("utf-8"))
                except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
                    inv_bucket.append("seed:malformed")
                    continue
                if not isinstance(seed_parsed, Mapping):
                    inv_bucket.append("seed:malformed")
                    continue
                parsed_seed_obj = seed_parsed

            elif role == "outcomes":
                try:
                    fin_at = _utc(spec.get("finalized_at"))
                    max_ko = _utc(origin.get("max_kickoff_utc"))
                    out_rows = json.loads(dec_bytes.decode("utf-8"))
                except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
                    inv_bucket.append("outcomes:malformed")
                    continue
                gw_kickoffs = [_utc(r["kickoff_time"]) for r in fx_rows if int(r["event"]) == gw_int]
                if gw_kickoffs and max_ko < max(gw_kickoffs):
                    inv_bucket.append("outcomes:max_kickoff_precedes_fixture")
                if (fin_at - max_ko).total_seconds() < SETTLEMENT_MIN_WAIT_SECONDS:
                    unr_bucket.append("outcomes:premature_settlement_lt_24h")
                if spec.get("finished") is not True:
                    unr_bucket.append("outcomes:fixture_unfinished")
                if track == "prospective_receipt" and spec.get("data_checked") is not True:
                    unr_bucket.append("outcomes:prospective_data_unchecked")
                expected_pids = {int(r["id"]) for r in sanitized_elements if type(r.get("id")) is int}
                try:
                    get_rules(season)
                except ValueError:
                    inv_bucket.append("outcomes:invalid_rules_version")
                else:
                    out_issues = _valid_outcomes_payload(
                        out_rows,
                        rules_version=season,
                        expected_player_ids=expected_pids if expected_pids else None,
                    )
                    if out_issues:
                        inv_bucket.extend(out_issues)

        if parsed_seed_obj is not None and sanitized_elements:
            invalid_pre.extend(validate_seed_mapping(parsed_seed_obj, sanitized_elements))

        invalid_all = invalid_pre + invalid_post
        unresolved_all = unresolved_pre + unresolved_post
        if invalid_all:
            status = "invalid"
        elif unresolved_all:
            status = "unresolved"
        else:
            status = "admitted_empirical"

        prior_admitted = status == "admitted_empirical"
        input_ready = (not invalid_pre) and (not unresolved_pre)
        input_digest = sha256_bytes(
            canonical_json_bytes(
                {
                    "version": 2,
                    "mode": "empirical",
                    "track": track,
                    "season": season,
                    "gw": gw_int,
                    "role_digests": pre_role_digests,
                    "chip_calendar": chip_calendar,
                }
            )
        )
        raw_reports.append(
            {
                "season": season,
                "gw": gw,
                "mode": "empirical",
                "track": track,
                "status": status,
                "input_ready": input_ready,
                "input_digest": input_digest,
                "reasons": invalid_all + unresolved_all,
                "limitations": disclosed,
                "disclosed_limitations": disclosed,
                "eligible_since_count": len(eligible_since),
                "role_digests": all_role_digests,
                "chip_calendar": [list(item) for item in chip_calendar],
            }
        )

    all_38_admitted = (
        len(raw_reports) == 38
        and [r["gw"] for r in raw_reports] == list(range(1, 39))
        and all(r["status"] == "admitted_empirical" for r in raw_reports)
    )
    prefix_is_partial = declared_partial or (not all_38_admitted)
    for rep in raw_reports:
        rep["partial_prefix"] = prefix_is_partial
        rep["promotable"] = (rep["status"] == "admitted_empirical") and (not prefix_is_partial) and all_38_admitted
    return raw_reports
