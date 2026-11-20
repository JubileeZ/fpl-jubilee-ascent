"""Unified empirical admission for historical mirrors, receipts, and active-season fplcache."""

from __future__ import annotations

import json
import lzma
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from backtesting.empirical_mirrors import (
    _BOOTSTRAP_CHIP_NAMES,
    EMPIRICAL_TRACKS,
    FIXTURE_DISCLOSURE_AGE_SECONDS,
    FIXTURE_MAX_CAP_SECONDS,
    FIXTURE_MIN_CAP_SECONDS,
    FIXTURE_TARGET_SECONDS,
    FPLCACHE_MAX_HARD_SECONDS,
    FPLCACHE_MAX_TARGET_SECONDS,
    SETTLEMENT_MIN_WAIT_SECONDS,
    canonical_bootstrap_table,
    canonical_json_bytes,
    canonical_json_sha256,
    empirical_checkpoint_scope,
    parse_fixtures_csv_window,
    sha256_bytes,
    validate_mirror_url,
    verify_validation_fplcache_snapshot,
)
from backtesting.fplcache_ingest import (
    LOCAL_RECEIPT_HARD_MAX_AGE_SECONDS,
    _sanitize_bootstrap,
    _unpack_bootstrap_xz,
    _utc,
    extract_max_news_added,
)
from backtesting.replay_state import Outcome, _validate_outcome
from backtesting.season_rules import AccessPurpose, Chip, chip_window, get_rules, load_season_lifecycle, validate_chip_calendar
from models.scoring_matrix import Position, event_points

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


def resolve_source_bytes(
    spec: Mapping[str, Any],
    catalog: Mapping[str, bytes] | None,
    *,
    allow_disk_path_fallback: bool = True,
) -> bytes | None:
    """Resolve raw source bytes from in-memory catalog or verified local disk path."""
    sid = spec.get("source_id")
    if isinstance(sid, str) and catalog is not None and sid in catalog:
        return catalog[sid]
    if allow_disk_path_fallback:
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


def verify_table_sha256(spec: Mapping[str, Any], table_obj: Any) -> str | None:
    """Verify table_sha256 against parsed canonical table structure when declared."""
    expected = spec.get("table_sha256")
    if expected is None:
        return None
    if not isinstance(expected, str) or expected != canonical_json_sha256(table_obj):
        return "table_sha256_mismatch"
    return None


def resolve_and_verify_source_bytes(
    spec: Mapping[str, Any],
    catalog: Mapping[str, bytes] | None,
    *,
    role_label: str = "source",
    allow_disk_path_fallback: bool = True,
) -> bytes:
    """Resolve raw bytes and verify blob/decompressed SHA-256 digests cleanly."""
    raw_bytes = resolve_source_bytes(spec, catalog, allow_disk_path_fallback=allow_disk_path_fallback)
    if raw_bytes is None:
        raise ValueError(f"Missing {role_label} source bytes")
    dec_bytes, err = verify_digests(spec, raw_bytes)
    if err is not None:
        raise ValueError(f"{role_label} digest mismatch: {err}")
    return dec_bytes


def normalize_identity_text(value: Any) -> str:
    """Normalize player name / date identity token for deterministic cross-season fallback matching."""
    if value is None:
        return ""
    raw = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return " ".join(raw.lower().strip().split())


def build_empirical_seed_mapping(
    current_elements: Sequence[Mapping[str, Any]],
    seed_players: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    """Map non-manager current players to prior seed via Opta code primary, normalized identity secondary, else absent:<id>."""
    non_mgr_seed = [
        p for p in seed_players if int(p.get("position_id", p.get("element_type", 0)) or 0) != 5
    ]
    by_code: dict[int, str] = {}
    by_identity_full: dict[tuple[str, str, str, str], list[str]] = {}
    by_identity_name: dict[tuple[str, str, str], list[str]] = {}
    for row in non_mgr_seed:
        sid_raw = row.get("id", row.get("player_id"))
        if sid_raw is None:
            continue
        sid = str(int(sid_raw))
        code_raw = row.get("code")
        if type(code_raw) is int and code_raw > 0:
            by_code[code_raw] = sid
        fn = normalize_identity_text(row.get("first_name"))
        sn = normalize_identity_text(row.get("second_name"))
        wn = normalize_identity_text(row.get("web_name"))
        bd = normalize_identity_text(row.get("birth_date"))
        if fn or sn or wn:
            by_identity_name.setdefault((fn, sn, wn), []).append(sid)
            if bd:
                by_identity_full.setdefault((fn, sn, wn, bd), []).append(sid)

    mapping: dict[str, str] = {}
    used_seed_ids: set[str] = set()
    for el in sorted(current_elements, key=lambda item: int(item["id"])):
        if int(el.get("position_id", el.get("element_type", 0)) or 0) == 5:
            continue
        pid = int(el["id"])
        matched: str | None = None
        code_raw = el.get("code")
        if type(code_raw) is int and code_raw in by_code and by_code[code_raw] not in used_seed_ids:
            matched = by_code[code_raw]
        else:
            fn = normalize_identity_text(el.get("first_name"))
            sn = normalize_identity_text(el.get("second_name"))
            wn = normalize_identity_text(el.get("web_name"))
            bd = normalize_identity_text(el.get("birth_date"))
            if bd and len(by_identity_full.get((fn, sn, wn, bd), [])) == 1:
                cand = by_identity_full[(fn, sn, wn, bd)][0]
                if cand not in used_seed_ids:
                    matched = cand
            elif (fn or sn or wn) and len(by_identity_name.get((fn, sn, wn), [])) == 1:
                cand = by_identity_name[(fn, sn, wn)][0]
                if cand not in used_seed_ids:
                    matched = cand
        if matched is not None:
            used_seed_ids.add(matched)
            mapping[str(pid)] = matched
        else:
            mapping[str(pid)] = f"absent:{pid}"
    return mapping


_SEED_IDENTITY_KEYS = ("code", "first_name", "second_name", "web_name")


def validate_seed_mapping(
    seed_obj: Mapping[str, Any],
    elements: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Validate 1-to-1 prior-season seed mapping, position_id==5 exclusion, and DefCon applicability."""
    issues: list[str] = []
    seed_players = seed_obj.get("players", [])
    if not isinstance(seed_players, list):
        return ["malformed_seed_players"]
    non_manager_seed = [
        row for row in seed_players if int(row.get("position_id", row.get("element_type", 0)) or 0) != 5
    ]
    seed_ids = {str(row.get("id") or row.get("player_id")) for row in non_manager_seed}
    seed_mapping = seed_obj.get("seed_mapping")
    if not isinstance(seed_mapping, Mapping):
        return ["missing_seed_mapping"]

    if seed_obj.get("defensive_contribution_status") == "inapplicable_native":
        hist = seed_obj.get("history", [])
        if isinstance(hist, list) and any(isinstance(r, Mapping) and "defensive_contribution" in r for r in hist):
            issues.append("seed:inapplicable_defensive_contribution_imputed")

    seen_mapped: set[str] = set()
    for el in elements:
        if int(el.get("position_id", el.get("element_type", 0)) or 0) == 5:
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

    if (
        not issues
        and any(any(k in el for k in _SEED_IDENTITY_KEYS) for el in elements)
        and any(any(k in sp for k in _SEED_IDENTITY_KEYS) for sp in non_manager_seed)
    ):
        expected = build_empirical_seed_mapping(elements, seed_players)
        if dict(seed_mapping) != expected:
            issues.append("seed:mapping_hierarchy_mismatch")
    return issues


_FULL_COMPONENT_KEYS = frozenset(
    {
        "position_id",
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
    }
)
_POS_BY_ID: dict[int, Position] = {1: "GK", 2: "D", 3: "M", 4: "F"}


def _compute_outcome_component_sum(row: Mapping[str, Any], rules_version: str) -> int:
    """Compute exact 13-component FPL integer score from settled outcome component fields."""
    pos = _POS_BY_ID[int(row["position_id"])]
    defcon_raw = int(row.get("defensive_contribution", 0) or 0)
    defcon_cnt = 1.0 if ((pos == "D" and defcon_raw >= 10) or (pos in ("M", "F") and defcon_raw >= 12)) else 0.0
    total = (
        event_points("minutes", pos, float(row["minutes"]), rules_version=rules_version)
        + event_points("goals", pos, float(row["goals_scored"]), rules_version=rules_version)
        + event_points("assists", pos, float(row["assists"]), rules_version=rules_version)
        + event_points("clean_sheets", pos, float(row["clean_sheets"]), rules_version=rules_version)
        + event_points("goals_conceded", pos, float(row["goals_conceded"]), rules_version=rules_version)
        + event_points("saves", pos, float(row["saves"]), rules_version=rules_version)
        + event_points("defensive_contributions", pos, defcon_cnt, rules_version=rules_version)
        + event_points("bonus", pos, float(row["bonus"]), rules_version=rules_version)
        + event_points("yellow_cards", pos, float(row["yellow_cards"]), rules_version=rules_version)
        + event_points("red_cards", pos, float(row["red_cards"]), rules_version=rules_version)
        + event_points("penalties_saved", pos, float(row["penalties_saved"]), rules_version=rules_version)
        + event_points("penalties_missed", pos, float(row["penalties_missed"]), rules_version=rules_version)
        + event_points("own_goals", pos, float(row["own_goals"]), rules_version=rules_version)
    )
    return int(round(total))


def _valid_outcomes_payload(
    rows: Any,
    *,
    rules_version: str,
    expected_player_fixtures: set[tuple[int, int]] | None = None,
    expected_player_ids: set[int] | None = None,
    position_by_id: Mapping[int, int] | None = None,
) -> list[str]:
    issues: list[str] = []
    if not isinstance(rows, list):
        return ["outcomes_empty"]
    if not rows:
        return [] if expected_player_fixtures == set() else ["outcomes_empty"]
    get_rules(rules_version)
    comp_keys_no_pos = _FULL_COMPONENT_KEYS - {"position_id"}
    seen_pairs: set[tuple[int, int]] = set()
    seen_ids: set[int] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            issues.append("malformed_outcome_row")
            break
        pid = row.get("player_id")
        if type(pid) is not int or pid <= 0:
            issues.append("invalid_or_duplicate_outcome_player")
            break
        if expected_player_fixtures is not None or "fixture_id" in row:
            fid = row.get("fixture_id")
            if type(fid) is not int or fid <= 0 or (pid, fid) in seen_pairs:
                issues.append("invalid_or_duplicate_outcome_player_fixture")
                break
            seen_pairs.add((pid, fid))
            seen_ids.add(pid)
        else:
            if pid in seen_ids:
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
        if comp_keys_no_pos <= set(row):
            pos_id = row["position_id"] if "position_id" in row else (position_by_id.get(pid) if position_by_id else None)
            defcon_raw = row.get("defensive_contribution")
            if (
                type(pos_id) is not int
                or pos_id not in _POS_BY_ID
                or any(type(row[k]) is not int for k in comp_keys_no_pos)
                or (defcon_raw is not None and type(defcon_raw) is not int)
            ):
                issues.append("invalid_outcome_field_types")
                break
            computed_sum = _compute_outcome_component_sum({**row, "position_id": pos_id}, rules_version)
            if computed_sum != pts or (comp_sum is not None and comp_sum != computed_sum):
                issues.append("unreconciled_outcome_components")
                break
            if comp_sum is None:
                comp_sum = computed_sum
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
    if not issues:
        if expected_player_fixtures is not None:
            if expected_player_fixtures - seen_pairs:
                issues.append("outcomes_missing_admitted_player_fixtures")
            if seen_pairs - expected_player_fixtures:
                issues.append("outcomes_unexpected_player_fixture")
        elif expected_player_ids and not expected_player_ids <= seen_ids:
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


def _assess_bootstrap_role(
    *,
    spec: Mapping[str, Any],
    dec_bytes: bytes,
    track: str,
    season: str,
    gw_int: int,
    dl: datetime,
    cal_error: str | None,
    chip_calendar: tuple[tuple[int, Chip], ...],
    disclosed: list[str],
    eligible_since: dict[int, int],
    anchor_squad_ids: list[int],
    inv_bucket: list[str],
    unr_bucket: list[str],
) -> tuple[list[dict[str, Any]], list[Mapping[str, Any]], set[int]]:
    """Validate empirical bootstrap source bytes, windows, table digest, chip bounds, and anchor."""
    try:
        bs_payload = json.loads(dec_bytes.decode("utf-8"))
        cap_lo = _utc(spec.get("capture_lower"))
        cap_up = _utc(spec.get("capture_upper"))
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        inv_bucket.append("bootstrap:malformed_metadata_or_json")
        return [], [], set()

    if cap_lo > cap_up:
        inv_bucket.append("bootstrap:capture_bounds_reversed")
    if cap_up >= dl:
        inv_bucket.append("bootstrap:capture_after_deadline")
    if track == "prospective_receipt" and spec.get("timing_basis") != "receipt":
        inv_bucket.append("bootstrap:prospective_requires_receipt")
    if track == "validation_fplcache":
        bs_timing = spec.get("timing_basis")
        if bs_timing == "bounded_reconstruction":
            try:
                verify_validation_fplcache_snapshot(
                    str(spec.get("url", "")),
                    commit_sha=spec.get("commit_sha"), capture_lower=cap_lo, capture_upper=cap_up,
                )
            except ValueError:
                inv_bucket.append("bootstrap:invalid_fplcache_provenance")
        elif bs_timing == "receipt":
            if not str(spec.get("url", "")).startswith("receipt://"):
                inv_bucket.append("bootstrap:validation_requires_receipt_url")
        else:
            inv_bucket.append("bootstrap:validation_requires_bounded_reconstruction")
        try:
            event_deadlines = [
                _utc(event.get("deadline_time")) for event in bs_payload.get("events", ())
                if isinstance(event, Mapping) and event.get("id") == gw_int
            ]
        except (TypeError, ValueError):
            event_deadlines = []
        if event_deadlines != [dl]:
            inv_bucket.append("bootstrap:deadline_mismatch")
    max_news = extract_max_news_added(bs_payload)
    if max_news is not None and max_news > cap_up:
        inv_bucket.append("bootstrap:news_added_after_capture")
    age = (dl - cap_lo).total_seconds()
    if track == "development_mirror" or (track == "validation_fplcache" and spec.get("timing_basis") == "bounded_reconstruction"):
        url_path = urlparse(str(spec.get("url", ""))).path
        if (url_path.startswith("/Randdalf/fplcache/") or url_path.startswith("/repos/Randdalf/fplcache/")) and "fplcache_mirror_provenance" not in disclosed:
            disclosed.append("fplcache_mirror_provenance")
        if age > FPLCACHE_MAX_HARD_SECONDS:
            unr_bucket.append("bootstrap:source_stale_gt_24h")
        elif age > FPLCACHE_MAX_TARGET_SECONDS and "bootstrap_stale_band_8h_to_24h" not in disclosed:
            disclosed.append("bootstrap_stale_band_8h_to_24h")
    elif age > PROSPECTIVE_MAX_SECONDS:
        unr_bucket.append("bootstrap:prospective_stale_gt_6h")

    sanitized_elements, bs_club_ids, bs_issues = _sanitize_bootstrap(bs_payload, capture_upper=cap_up)
    bs_table = canonical_bootstrap_table(bs_payload, sanitized_elements, bs_club_ids, gw_int)
    if t_err := verify_table_sha256(spec, bs_table):
        inv_bucket.append(f"bootstrap:{t_err}")
    if bs_issues:
        inv_bucket.extend(f"bootstrap:{i}" for i in bs_issues)
    if not cal_error and isinstance(bs_payload.get("chips"), list) and bs_payload["chips"]:
        rules_s = get_rules(season)
        declared_bounds: dict[tuple[Chip, int], list[tuple[int, int]]] = {}
        for item in bs_payload["chips"]:
            if not isinstance(item, Mapping):
                continue
            mapped_c = _BOOTSTRAP_CHIP_NAMES.get(str(item.get("name", "")).strip().lower())
            s_ev, e_ev = item.get("start_event"), item.get("stop_event")
            if mapped_c is not None and type(s_ev) is int and type(e_ev) is int and 1 <= s_ev <= e_ev <= 38:
                try:
                    win = chip_window(rules_s, mapped_c, s_ev)
                except ValueError:
                    inv_bucket.append("bootstrap:invalid_chip_window")
                else:
                    declared_bounds.setdefault((mapped_c, win), []).append((s_ev, e_ev))
        for cal_gw, cal_chip in chip_calendar:
            if cal_gw >= gw_int:
                try:
                    cal_win = chip_window(rules_s, cal_chip, cal_gw)
                except ValueError:
                    inv_bucket.append("chip_calendar:outside_bootstrap_chip_window")
                    continue
                bounds = declared_bounds.get((cal_chip, cal_win))
                if bounds and not any(s_ev <= cal_gw <= e_ev for s_ev, e_ev in bounds):
                    inv_bucket.append("chip_calendar:outside_bootstrap_chip_window")
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
    admitted_ids = {int(r["id"]) for r in sanitized_elements if type(r.get("id")) is int}
    raw_bs_elements: list[Mapping[str, Any]] = [
        el
        for el in bs_payload.get("elements", [])
        if isinstance(el, Mapping) and type(el.get("id")) is int and int(el["id"]) in admitted_ids
    ]
    return sanitized_elements, raw_bs_elements, bs_club_ids


def _assess_fixtures_role(
    *,
    spec: Mapping[str, Any],
    dec_bytes: bytes,
    track: str,
    gw_int: int,
    dl: datetime,
    prev_dl: datetime | None,
    bs_club_ids: set[int],
    disclosed: list[str],
    inv_bucket: list[str],
    unr_bucket: list[str],
) -> list[dict[str, Any]]:
    """Validate empirical fixtures CSV table digest, capture bounds, horizon coverage, and clubs."""
    try:
        cap_lo = _utc(spec.get("capture_lower"))
        cap_up = _utc(spec.get("capture_upper"))
        fx_rows = parse_fixtures_csv_window(dec_bytes, gw_int)
    except (TypeError, ValueError, UnicodeDecodeError):
        inv_bucket.append("fixtures:malformed_csv_or_bounds")
        return []

    if t_err := verify_table_sha256(spec, fx_rows):
        inv_bucket.append(f"fixtures:{t_err}")
    if track == "development_mirror":
        url_path = urlparse(str(spec.get("url", ""))).path
        if (url_path.startswith("/vaastav/Fantasy-Premier-League/") or url_path.startswith("/repos/vaastav/Fantasy-Premier-League/")) and "vaastav_mirror_provenance" not in disclosed:
            disclosed.append("vaastav_mirror_provenance")
    if cap_lo > cap_up:
        inv_bucket.append("fixtures:capture_bounds_reversed")
    if cap_up >= dl:
        inv_bucket.append("fixtures:capture_after_deadline")
    if track == "prospective_receipt":
        if spec.get("timing_basis") != "receipt":
            inv_bucket.append("fixtures:prospective_requires_receipt")
        if (dl - cap_lo).total_seconds() > PROSPECTIVE_MAX_SECONDS:
            unr_bucket.append("fixtures:prospective_stale_gt_6h")
    elif track == "validation_fplcache":
        if spec.get("timing_basis") != "receipt":
            inv_bucket.append("fixtures:validation_requires_receipt")
        in_window = (cap_up < dl) if gw_int == 1 else (prev_dl is not None and prev_dl < cap_up < dl)
        if not in_window:
            unr_bucket.append("fixtures:out_of_window")
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
    return fx_rows


def _assess_history_role(
    *,
    spec: Mapping[str, Any],
    dec_bytes: bytes,
    gw_int: int,
    dl: datetime,
    inv_bucket: list[str],
    unr_bucket: list[str],
) -> None:
    """Validate pre-deadline empirical history rows, cutoff timestamp, and GW completeness."""
    try:
        cap_up = _utc(spec.get("capture_upper"))
        hist_rows = json.loads(dec_bytes.decode("utf-8"))
    except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        inv_bucket.append("history:malformed")
        return
    if not isinstance(hist_rows, list) or any(not isinstance(r, Mapping) or type(r.get("gameweek_id")) is not int for r in hist_rows):
        inv_bucket.append("history:malformed")
        return
    if t_err := verify_table_sha256(spec, hist_rows):
        inv_bucket.append(f"history:{t_err}")
    if cap_up >= dl:
        inv_bucket.append("history:capture_after_deadline")
    if gw_int >= 1 and any(int(r["gameweek_id"]) >= gw_int for r in hist_rows):
        inv_bucket.append("history:future_gw_leakage")
    if gw_int > 1:
        present_gws = {int(r["gameweek_id"]) for r in hist_rows}
        missing_gws = [pg for pg in range(1, gw_int) if pg not in present_gws]
        if missing_gws:
            unr_bucket.append(f"history:missing_prior_gws:{missing_gws}")


def _assess_outcomes_role(
    *,
    spec: Mapping[str, Any],
    dec_bytes: bytes,
    origin: Mapping[str, Any],
    track: str,
    season: str,
    gw_int: int,
    fx_rows: list[dict[str, Any]],
    sanitized_elements: list[dict[str, Any]],
    inv_bucket: list[str],
    unr_bucket: list[str],
) -> None:
    """Validate settled empirical outcomes +24h lag, fixture finish, and ledger reconciliation."""
    try:
        fin_at = _utc(spec.get("finalized_at"))
        max_ko = _utc(origin.get("max_kickoff_utc"))
        out_rows = json.loads(dec_bytes.decode("utf-8"))
    except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        inv_bucket.append("outcomes:malformed")
        return
    if t_err := verify_table_sha256(spec, out_rows):
        inv_bucket.append(f"outcomes:{t_err}")
    gw_kickoffs = [_utc(r["kickoff_time"]) for r in fx_rows if int(r["event"]) == gw_int]
    if gw_kickoffs and max_ko < max(gw_kickoffs):
        inv_bucket.append("outcomes:max_kickoff_precedes_fixture")
    if (fin_at - max_ko).total_seconds() < SETTLEMENT_MIN_WAIT_SECONDS:
        unr_bucket.append("outcomes:premature_settlement_lt_24h")
    if spec.get("finished") is not True:
        unr_bucket.append("outcomes:fixture_unfinished")
    if track in ("prospective_receipt", "validation_fplcache") and spec.get("data_checked") is not True:
        unr_bucket.append("outcomes:prospective_data_unchecked")
    if not sanitized_elements:
        unr_bucket.append("outcomes:awaiting_bootstrap")
        return
    expected_pids = {int(r["id"]) for r in sanitized_elements if type(r.get("id")) is int}
    try:
        get_rules(season)
    except ValueError:
        inv_bucket.append("outcomes:invalid_rules_version")
    else:
        pos_map = {
            int(r["id"]): int(r["element_type"])
            for r in sanitized_elements
            if type(r.get("id")) is int and type(r.get("element_type")) is int
        }
        gw_fx_rows = [r for r in fx_rows if int(r["event"]) == gw_int]
        expected_player_fixtures: set[tuple[int, int]] | None = None
        if gw_fx_rows and sanitized_elements:
            club_fixtures: dict[int, list[int]] = {}
            for fx in gw_fx_rows:
                fid = int(fx["id"])
                club_fixtures.setdefault(int(fx["team_h"]), []).append(fid)
                club_fixtures.setdefault(int(fx["team_a"]), []).append(fid)
            expected_player_fixtures = {
                (int(el["id"]), fid)
                for el in sanitized_elements
                if type(el.get("id")) is int and type(el.get("team")) is int
                for fid in club_fixtures.get(int(el["team"]), ())
            }
        out_issues = _valid_outcomes_payload(
            out_rows,
            rules_version=season,
            expected_player_fixtures=expected_player_fixtures,
            expected_player_ids=expected_pids if expected_pids else None,
            position_by_id=pos_map if pos_map else None,
        )
        if out_issues:
            inv_bucket.extend(out_issues)


def assess_empirical_origins(
    request: Mapping[str, Any],
    catalog: Mapping[str, bytes] | None = None,
    *,
    allow_disk_path_fallback: bool = True,
    allowed_checkpoints: Sequence[int] = (15, 30, 38),
) -> list[dict[str, Any]]:
    """Evaluate unified version=2 mode='empirical' origins under #175/#178 rules."""
    track = request.get("track")
    if track not in EMPIRICAL_TRACKS:
        raise ValueError(f"Empirical request requires track in {EMPIRICAL_TRACKS}")
    checkpoint_gw = empirical_checkpoint_scope(
        track,
        request.get("purpose"),
        request.get("checkpoint_gw"),
        allowed_checkpoints=allowed_checkpoints,
    )
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
            role_s = lifecycle.role_of(season)
            purpose_s: AccessPurpose = (
                ("historical_filter" if role_s == "historical_filter" else "dev")
                if track == "development_mirror"
                else ("active_validation" if track == "validation_fplcache" else "validation")
            )
            if gw_int >= 1:
                lifecycle.assert_access(season, gw_int, purpose=purpose_s)
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
        elif track in ("development_mirror", "validation_fplcache") and any(code not in MIRROR_DISCLOSURE_CODES for code in disclosed):
            invalid_pre.append("invalid_disclosed_limitations")

        sources = origin.get("sources")
        if not isinstance(sources, Mapping):
            unresolved_pre.append("sources_missing")
            sources = {}

        pre_role_digests: dict[str, dict[str, str]] = {}
        all_role_digests: dict[str, dict[str, str]] = {}
        sanitized_elements: list[dict[str, Any]] = []
        raw_bs_elements: list[Mapping[str, Any]] = []
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
            if track == "development_mirror":
                try:
                    validate_mirror_url(str(spec.get("url", "")), allow_prior_seed=(role == "seed"))
                except ValueError:
                    inv_bucket.append(f"{role}:unapproved_mirror_url")
            if track == "validation_fplcache" and role != "bootstrap" and (
                spec.get("timing_basis") != "receipt" or not str(spec.get("url", "")).startswith("receipt://")
            ):
                inv_bucket.append(f"{role}:validation_requires_receipt")
            raw_bytes = resolve_source_bytes(
                spec,
                catalog,
                allow_disk_path_fallback=(allow_disk_path_fallback and track != "validation_fplcache"),
            )
            if raw_bytes is None:
                unr_bucket.append(f"{role}_bytes_missing")
                continue
            if track == "validation_fplcache" and role == "bootstrap" and (
                not raw_bytes.startswith(b"\xfd7zXZ\x00") or not isinstance(spec.get("decompressed_sha256"), str)
            ):
                inv_bucket.append("bootstrap:fplcache_requires_retained_xz_and_decompressed_digest")
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
                sanitized_elements, raw_bs_elements, bs_club_ids = _assess_bootstrap_role(
                    spec=spec,
                    dec_bytes=dec_bytes,
                    track=track,
                    season=season,
                    gw_int=gw_int,
                    dl=dl,
                    cal_error=cal_error,
                    chip_calendar=chip_calendar,
                    disclosed=disclosed,
                    eligible_since=eligible_since,
                    anchor_squad_ids=anchor_squad_ids,
                    inv_bucket=inv_bucket,
                    unr_bucket=unr_bucket,
                )
            elif role == "fixtures":
                fx_rows = _assess_fixtures_role(
                    spec=spec,
                    dec_bytes=dec_bytes,
                    track=track,
                    gw_int=gw_int,
                    dl=dl,
                    prev_dl=prev_dl,
                    bs_club_ids=bs_club_ids,
                    disclosed=disclosed,
                    inv_bucket=inv_bucket,
                    unr_bucket=unr_bucket,
                )
            elif role == "history":
                _assess_history_role(
                    spec=spec,
                    dec_bytes=dec_bytes,
                    gw_int=gw_int,
                    dl=dl,
                    inv_bucket=inv_bucket,
                    unr_bucket=unr_bucket,
                )
            elif role == "seed":
                try:
                    seed_parsed = json.loads(dec_bytes.decode("utf-8"))
                except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
                    inv_bucket.append("seed:malformed")
                    continue
                if not isinstance(seed_parsed, Mapping):
                    inv_bucket.append("seed:malformed")
                    continue
                if track == "validation_fplcache" and season in lifecycle.seasons:
                    if seed_parsed.get("season") != lifecycle.seasons[season].prior_seed:
                        inv_bucket.append("seed:wrong_prior_seed_season")
                    try:
                        seed_cap_lo = _utc(spec.get("capture_lower"))
                        seed_cap_up = _utc(spec.get("capture_upper"))
                        if not seed_cap_lo <= seed_cap_up < dl:
                            inv_bucket.append("seed:invalid_capture_bounds")
                    except (TypeError, ValueError):
                        inv_bucket.append("seed:invalid_capture_bounds")
                if t_err := verify_table_sha256(spec, seed_parsed):
                    inv_bucket.append(f"seed:{t_err}")
                parsed_seed_obj = seed_parsed
            elif role == "outcomes":
                _assess_outcomes_role(
                    spec=spec,
                    dec_bytes=dec_bytes,
                    origin=origin,
                    track=track,
                    season=season,
                    gw_int=gw_int,
                    fx_rows=fx_rows,
                    sanitized_elements=sanitized_elements,
                    inv_bucket=inv_bucket,
                    unr_bucket=unr_bucket,
                )

        if parsed_seed_obj is not None and sanitized_elements:
            invalid_pre.extend(validate_seed_mapping(parsed_seed_obj, raw_bs_elements or sanitized_elements))
        if track == "development_mirror" and not any(
            d in ("fplcache_mirror_provenance", "vaastav_mirror_provenance") for d in disclosed
        ):
            invalid_pre.append("missing_mirror_provenance_disclosure")

        invalid_all = invalid_pre + invalid_post
        unresolved_all = unresolved_pre + unresolved_post
        status = "invalid" if invalid_all else ("unresolved" if unresolved_all else "admitted_empirical")

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
    checkpoint_complete = (
        checkpoint_gw is not None
        and not declared_partial
        and [rep["gw"] for rep in raw_reports] == list(range(1, checkpoint_gw + 1))
        and all(rep["status"] == "admitted_empirical" for rep in raw_reports)
    )
    for rep in raw_reports:
        rep["partial_prefix"] = prefix_is_partial
        rep["promotable"] = (rep["status"] == "admitted_empirical") and (not prefix_is_partial) and all_38_admitted
        if track == "validation_fplcache":
            rep["checkpoint_gw"] = checkpoint_gw
            rep["checkpoint_complete"] = checkpoint_complete
    return raw_reports
