"""Retained training closure for synthetic or empirical causal forecast staging."""

import hashlib
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from backtesting.data_admission import AdmittedInput, verify_input
from backtesting.season_rules import load_season_lifecycle


def _read_canonical_json(catalog: dict[str, bytes], digest: str) -> dict[str, Any]:
    raw = catalog.get(digest)
    if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Missing or corrupt retained material")
    value = json.loads(raw)
    if not isinstance(value, dict) or json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() != raw:
        raise ValueError("Material must be canonical JSON")
    return value


def _parse_iso_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("Timezone required")
    return parsed


def validate_storage_path(path: Path) -> Path:
    return load_season_lifecycle().assert_unsealed_storage_path(path, error_message="Invalid storage path")


def _verify_empirical_training_bundle(
    capability: AdmittedInput,
    request: dict[str, Any],
    catalog: dict[str, bytes],
    authority: dict[str, Any],
    *,
    allow_disk_path_fallback: bool = True,
) -> dict[str, Any]:
    from backtesting.empirical_admission import resolve_and_verify_source_bytes, validate_seed_mapping
    from backtesting.empirical_mirrors import parse_fixtures_csv_window, validate_mirror_url
    from backtesting.fplcache_ingest import _sanitize_bootstrap, _utc

    required = {"version", "mode", "track", "input_digest", "season", "gw", "seed_identity", "source_digest"}
    if set(authority) != required or authority["version"] != 2 or authority["mode"] != "empirical":
        raise ValueError("Unsupported empirical training authority")
    track = authority["track"]
    if track != capability.track:
        raise ValueError("Training authority track mismatch")
    origin = next((o for o in request["origins"] if o["season"] == capability.season and o["gw"] == capability.gw), None)
    if origin is None:
        raise ValueError("Empirical origin missing from request")
    if (authority["input_digest"], authority["season"], authority["gw"]) != (
        capability.input_digest,
        capability.season,
        capability.gw,
    ):
        raise ValueError("Training authority scope mismatch")

    source = _read_canonical_json(catalog, authority["source_digest"])
    req_source = {
        "mode",
        "track",
        "url",
        "revision",
        "parser_version",
        "captured_at",
        "defensive_contribution_status",
        "disclosed_limitations",
        "seed_mapping",
        "tables",
    }
    if not req_source <= set(source) or source.get("mode") != "empirical" or source["track"] != track:
        raise ValueError("Invalid empirical training source")
    sources = origin["sources"]
    url = str(source["url"])
    if track in ("development_mirror", "validation_fplcache"):
        allowed_urls = {
            sources[role].get("url")
            for role in ("bootstrap", "fixtures", "history", "seed")
            if isinstance(sources.get(role), dict)
        }
        if url not in allowed_urls:
            raise ValueError("Empirical training source url must match an admitted origin source")
        if track == "development_mirror":
            validate_mirror_url(url, allow_prior_seed=(url == sources["seed"].get("url")))
    elif not url.startswith("receipt://"):
        raise ValueError("Prospective receipt track requires receipt:// URL")

    dl = _parse_iso_time(origin["deadline"])
    cap_ts = _parse_iso_time(source["captured_at"])
    bs_cap_up = _utc(sources["bootstrap"]["capture_upper"])
    if cap_ts >= dl or cap_ts != bs_cap_up or (dl - cap_ts).total_seconds() > 48 * 3600:
        raise ValueError("Empirical training source captured_at must bind bootstrap <=48h pre-deadline")

    tables = source.get("tables")
    needed_tables = {
        "clubs",
        "player_metadata",
        "target_fixtures",
        "history",
        "history_fixtures",
        "seed_players",
        "seed_history",
        "seed_fixtures",
    }
    if not isinstance(tables, dict) or not needed_tables <= set(tables):
        raise ValueError("Empirical training tables incomplete")

    # Enforce strict pre-deadline isolation on history and history_fixtures
    for row in tables["history"]:
        if type(row.get("gameweek_id")) is not int or not 1 <= row["gameweek_id"] < capability.gw:
            raise ValueError("Empirical history outside causal gameweek bounds")
        if _parse_iso_time(row["kickoff_time"]) >= dl:
            raise ValueError("Empirical history kickoff exceeds deadline")
    for row in tables["history_fixtures"]:
        if row.get("finished") is not True:
            raise ValueError("Empirical history_fixtures must declare finished=True")
        if type(row.get("gameweek_id")) is not int or not 1 <= row["gameweek_id"] < capability.gw:
            raise ValueError("Empirical history_fixtures outside causal gameweek bounds")
        if _parse_iso_time(row["kickoff_time"]) >= dl:
            raise ValueError("Empirical history_fixtures kickoff exceeds deadline")

    # Cryptographically bind tables back to admitted origin sources
    bs_dec = resolve_and_verify_source_bytes(
        sources["bootstrap"],
        catalog,
        role_label="bootstrap",
        allow_disk_path_fallback=allow_disk_path_fallback,
    )
    fx_dec = resolve_and_verify_source_bytes(
        sources["fixtures"],
        catalog,
        role_label="fixtures",
        allow_disk_path_fallback=allow_disk_path_fallback,
    )
    hist_dec = resolve_and_verify_source_bytes(
        sources["history"],
        catalog,
        role_label="history",
        allow_disk_path_fallback=allow_disk_path_fallback,
    )
    seed_dec = resolve_and_verify_source_bytes(
        sources["seed"],
        catalog,
        role_label="seed",
        allow_disk_path_fallback=allow_disk_path_fallback,
    )

    admitted_bs_elements, _, _ = _sanitize_bootstrap(
        json.loads(bs_dec.decode("utf-8")),
        capture_upper=_utc(sources["bootstrap"]["capture_upper"]),
    )
    admitted_pids = {int(r["id"]) for r in admitted_bs_elements}
    bundle_pids = {int(r["id"]) for r in tables["player_metadata"] if int(r.get("position_id", 0)) != 5}
    if bundle_pids != admitted_pids:
        raise ValueError("Empirical training player_metadata differs from admitted bootstrap")

    admitted_fx_ids = {int(r["id"]) for r in parse_fixtures_csv_window(fx_dec, capability.gw)}
    if {int(r["id"]) for r in tables["target_fixtures"]} != admitted_fx_ids:
        raise ValueError("Empirical target_fixtures differ from admitted fixtures source")

    admitted_hist = json.loads(hist_dec.decode("utf-8"))
    if len(tables["history"]) != len(admitted_hist) or tables["history"] != admitted_hist:
        raise ValueError("Empirical training history differs from admitted history source")

    admitted_seed = json.loads(seed_dec.decode("utf-8"))
    if (
        source["seed_mapping"] != admitted_seed.get("seed_mapping")
        or len(tables["seed_players"]) != len(admitted_seed.get("players", []))
        or len(tables["seed_history"]) != len(admitted_seed.get("history", []))
    ):
        raise ValueError("Empirical seed bundle differs from admitted seed source")

    non_mgr_meta = [row for row in tables["player_metadata"] if int(row.get("position_id", 0)) != 5]
    seed_issues = validate_seed_mapping(
        {
            "players": tables["seed_players"],
            "history": tables["seed_history"],
            "seed_mapping": source["seed_mapping"],
            "defensive_contribution_status": source.get("defensive_contribution_status"),
        },
        non_mgr_meta,
    )
    if seed_issues:
        raise ValueError(f"Invalid empirical seed mapping: {seed_issues[0]}")
    return source


def verify_training_bundle(
    capability: AdmittedInput,
    request: dict[str, Any],
    catalog: dict[str, bytes],
    authority_digest: str,
    *,
    allow_disk_path_fallback: bool = True,
) -> dict[str, Any]:
    """Resolve source-authorized rows for synthetic diagnostics or verified empirical bundles."""
    from backtesting.verification_cache import get_verification_cache, request_catalog_fingerprint

    cache = get_verification_cache()
    cache_key: Any = None
    if cache is not None:
        cache_key = (capability, request_catalog_fingerprint(request, catalog), authority_digest, bool(allow_disk_path_fallback))
        cached = cache["training"].get(cache_key)
        if cached is not None:
            return cached

    result = _verify_training_bundle_uncached(
        capability,
        request,
        catalog,
        authority_digest,
        allow_disk_path_fallback=allow_disk_path_fallback,
    )
    if cache is not None and cache_key is not None:
        cache["training"][cache_key] = result
    return result


def _verify_training_bundle_uncached(
    capability: AdmittedInput,
    request: dict[str, Any],
    catalog: dict[str, bytes],
    authority_digest: str,
    *,
    allow_disk_path_fallback: bool = True,
) -> dict[str, Any]:
    verify_input(capability, request, catalog, allow_disk_path_fallback=allow_disk_path_fallback)
    if capability.season in load_season_lifecycle().sealed_seasons():
        raise ValueError("Protected season")
    authority = _read_canonical_json(catalog, authority_digest)
    if isinstance(authority, dict) and authority.get("mode") == "empirical":
        return _verify_empirical_training_bundle(
            capability,
            request,
            catalog,
            authority,
            allow_disk_path_fallback=allow_disk_path_fallback,
        )
    required = {"version", "mode", "input_digest", "season", "gw", "seed_identity", "source_digest"}
    if set(authority) != required or authority["version"] != 2 or authority["mode"] != "synthetic":
        raise ValueError("Unsupported training authority")
    origin = next(o for o in request["origins"] if o["season"] == capability.season and o["gw"] == capability.gw)
    if (authority["input_digest"], authority["season"], authority["gw"], authority["seed_identity"]) != (capability.input_digest, capability.season, capability.gw, origin["seed_identity"]):
        raise ValueError("Training authority scope mismatch")
    source = _read_canonical_json(catalog, authority["source_digest"])
    keys = {"version", "url", "revision", "parser_version", "seed_season", "seed_registry_complete", "published_at", "captured_at", "timestamp_uncertainty_seconds", "tables", "seed_mapping"}
    if set(source) != keys or source["version"] != 2:
        raise ValueError("Invalid training source")
    if not isinstance(source["url"], str) or not source["url"].startswith("synthetic://") or not isinstance(source["revision"], str) or not re.fullmatch(r"[0-9a-f]{40}", source["revision"]) or source["revision"] not in source["url"] or not isinstance(source["parser_version"], str) or not source["parser_version"]:
        raise ValueError("Invalid synthetic source provenance")
    season = capability.season
    if season == "test":
        expected_seed = "synthetic-prior"
    elif re.fullmatch(r"20\d\d-\d\d", season) and int(season[:4]) + 1 == 2000 + int(season[5:]):
        year = int(season[:4]) - 1
        expected_seed = f"{year}-{str(year + 1)[-2:]}"
    else:
        raise ValueError("Unknown season")
    if source["seed_season"] != expected_seed:
        raise ValueError("Seed season mismatch")
    if source["seed_registry_complete"] is not True:
        raise ValueError("Seed registry completeness not declared")
    uncertainty = source["timestamp_uncertainty_seconds"]
    if type(uncertainty) is not int or uncertainty < 0:
        raise ValueError("Invalid timestamp uncertainty")
    cutoff = _parse_iso_time(origin["deadline"])
    if max(_parse_iso_time(source["published_at"]), _parse_iso_time(source["captured_at"])) + timedelta(seconds=uncertainty) >= cutoff:
        raise ValueError("Training source at or after issue cutoff")
    tables = source["tables"]
    names = {"clubs", "player_metadata", "target_fixtures", "history", "history_fixtures", "seed_players", "seed_history", "seed_fixtures"}
    if not isinstance(tables, dict) or set(tables) != names or any(not isinstance(tables[name], list) for name in names):
        raise ValueError("Incomplete training tables")
    if any(not isinstance(row, dict) or type(row.get("gameweek_id")) is not int or not 1 <= row["gameweek_id"] < capability.gw for row in tables["history"]):
        raise ValueError("History must precede issue")
    base_authority = _read_canonical_json(catalog, request["authority_digest"])
    if authority["source_digest"] not in base_authority.get("training_source_digests", []):
        raise ValueError("Training source outside admission authority")
    if source["seed_mapping"] != base_authority.get("seed_mapping"):
        raise ValueError("Seed mapping mismatch")
    mapping = source["seed_mapping"]
    if not isinstance(mapping, dict) or set(mapping) != {str(pid) for pid in origin["universe"]} or any(not isinstance(value, str) or not value for value in mapping.values()) or len(set(mapping.values())) != len(mapping):
        raise ValueError("Invalid seed identity mapping")
    seed_players = tables["seed_players"]
    if any(not isinstance(row, dict) or not isinstance(row.get("seed_key"), str) or not row["seed_key"] or type(row.get("id")) is not int or type(row.get("club_id")) is not int or row.get("position_id") not in (1, 2, 3, 4) or type(row.get("now_cost")) is not int or row["now_cost"] <= 0 for row in seed_players) or len({row["seed_key"] for row in seed_players}) != len(seed_players) or len({row["id"] for row in seed_players}) != len(seed_players):
        raise ValueError("Seed players do not match mapping")
    seed_keys = {row["seed_key"] for row in seed_players}
    for value in mapping.values():
        if value.startswith("absent:"):
            if not value[7:] or value[7:] in seed_keys:
                raise ValueError("Unmapped identity not proven absent")
        elif value not in seed_keys:
            raise ValueError("Matched seed identity missing")
    club_ids = {row.get("id") for row in tables["clubs"] if isinstance(row, dict)}
    expected_clubs = {player["club"] for player in origin["players"]} | {fixture[key] for fixture in origin["fixtures"] for key in ("home_club", "away_club")}
    if len(club_ids) != len(tables["clubs"]) or not expected_clubs <= club_ids:
        raise ValueError("Club source coverage incomplete")
    if any(type(row.get("strength")) not in (int, float) or not math.isfinite(row["strength"]) or row["strength"] <= 0 for row in tables["clubs"]):
        raise ValueError("Club strength missing")
    if any(not isinstance(row.get("short_name"), str) or not row["short_name"] for row in tables["clubs"]) or len({row["short_name"] for row in tables["clubs"]}) != len(tables["clubs"]):
        raise ValueError("Club display identity missing")
    metadata = tables["player_metadata"]
    if any(not isinstance(row, dict) or set(row) != {"id", "web_name"} or type(row["id"]) is not int or not isinstance(row["web_name"], str) or not row["web_name"] for row in metadata) or {row["id"] for row in metadata} != set(origin["universe"]) or len(metadata) != len(origin["universe"]):
        raise ValueError("Player display identity mismatch")
    expected_fixtures = {(fixture["id"], fixture["gw"], fixture["home_club"], fixture["away_club"]) for fixture in origin["fixtures"]}
    targets: set[tuple[int, int, int, int]] = set()
    for fixture in tables["target_fixtures"]:
        fixture_fields = {"id", "gameweek_id", "home_club_id", "away_club_id", "team_h_difficulty", "team_a_difficulty"}
        if not isinstance(fixture, dict) or set(fixture) != fixture_fields or any(type(fixture.get(key)) is not int for key in fixture_fields) or not 1 <= fixture["team_h_difficulty"] <= 5 or not 1 <= fixture["team_a_difficulty"] <= 5:
            raise ValueError("Invalid issue fixture metadata")
        key = (fixture["id"], fixture["gameweek_id"], fixture["home_club_id"], fixture["away_club_id"])
        if key in targets:
            raise ValueError("Duplicate issue fixture")
        targets.add(key)
    if targets != expected_fixtures:
        raise ValueError("Issue fixture metadata mismatch")
    for name in ("history_fixtures", "seed_fixtures"):
        fixtures = tables[name]
        ids: set[int] = set()
        fixture_gws: dict[int, int] = {}
        for fixture in fixtures:
            if not isinstance(fixture, dict) or type(fixture.get("id")) is not int or fixture["id"] in ids or type(fixture.get("gameweek_id")) is not int or not 1 <= fixture["gameweek_id"] <= 38 or fixture.get("finished") is not True or _parse_iso_time(fixture.get("finalized_at")) >= cutoff:
                raise ValueError("Fixture completion provenance missing")
            if name == "history_fixtures" and fixture["gameweek_id"] >= capability.gw:
                raise ValueError("History fixture outside issue scope")
            ids.add(fixture["id"])
            fixture_gws[fixture["id"]] = fixture["gameweek_id"]
        performance_name = "history" if name == "history_fixtures" else "seed_history"
        player_ids = set(origin["universe"]) if name == "history_fixtures" else {player["id"] for player in seed_players}
        seen: set[tuple[int, int]] = set()
        for row in tables[performance_name]:
            if not isinstance(row, dict) or type(row.get("player_id")) is not int or row["player_id"] not in player_ids or type(row.get("fixture_id")) is not int or row["fixture_id"] not in ids or row.get("gameweek_id") != fixture_gws[row["fixture_id"]] or _parse_iso_time(row.get("kickoff_time")) >= cutoff:
                raise ValueError("Performance fixture provenance missing")
            key = (row["player_id"], row["fixture_id"])
            if key in seen or type(row.get("minutes")) not in (int, float) or not 0 <= row["minutes"] <= 90 or type(row.get("total_points")) not in (int, float) or not math.isfinite(row["total_points"]):
                raise ValueError("Invalid performance row")
            seen.add(key)
    return source
