"""Causal admission checks for future replay; legacy runners remain unchanged."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from backtesting.admission_fixtures import (
    assess_fixture_coverage,
    assess_issue_fixture_coverage,
)
from backtesting.season_rules import get_rules


@dataclass(frozen=True)
class AdmittedOrigin:
    season: str
    gw: int
    mode: str
    evidence_digest: str


def _utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("Timezone required")
    return parsed


def strict_load(
    descriptor: dict[str, Any],
    catalog: dict[str, bytes],
    reader: Callable[[Path], bytes],
) -> bytes:
    """Resolve declared parent scopes and hashes before invoking the sole source reader."""
    required = {"version", "season", "gw", "path", "sha256", "parent_manifest"}
    if (
        not isinstance(descriptor, dict)
        or set(descriptor) != required
        or descriptor["version"] != 1
    ):
        raise ValueError("Invalid source descriptor")
    season, gw = descriptor["season"], descriptor["gw"]
    if (
        season not in ("test", "2023-24", "2024-25", "2025-26", "2026-27")
        or type(gw) is not int
        or not 1 <= gw <= 38
        or (season == "2026-27" and gw >= 6)
    ):
        raise ValueError("Unknown or sealed scope")
    if not isinstance(descriptor["path"], str) or not descriptor["path"]:
        raise ValueError("Invalid path")
    if not isinstance(descriptor["sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", descriptor["sha256"]
    ):
        raise ValueError("Invalid source hash")
    path = Path(descriptor["path"]).resolve()
    if "2026-27" in path.parts:
        raise ValueError("Sealed path")
    digest = descriptor["parent_manifest"]
    if not isinstance(digest, str):
        raise ValueError("Parent manifest required")
    seen: set[str] = set()
    while digest is not None:
        if not isinstance(digest, str) or digest in seen:
            raise ValueError("Invalid parent chain")
        seen.add(digest)
        raw = catalog.get(digest)
        if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Missing parent manifest")
        try:
            parent = json.loads(raw)
            if (
                set(parent)
                != {"version", "season", "first_gw", "last_gw", "parent", "sources"}
                or parent["version"] != 1
                or parent["season"] != season
                or type(parent["first_gw"]) is not int
                or type(parent["last_gw"]) is not int
                or not parent["first_gw"] <= gw <= parent["last_gw"]
                or (season == "2026-27" and parent["last_gw"] >= 6)
            ):
                raise ValueError("Invalid parent scope")
            if (
                not isinstance(parent["sources"], list)
                or {"path": descriptor["path"], "sha256": descriptor["sha256"]}
                not in parent["sources"]
            ):
                raise ValueError("Source outside parent scope")
            digest = parent["parent"]
        except (TypeError, KeyError, ValueError):
            raise ValueError("Invalid parent manifest") from None
    content = reader(path)
    if (
        not isinstance(content, bytes)
        or hashlib.sha256(content).hexdigest() != descriptor["sha256"]
    ):
        raise ValueError("Source hash mismatch")
    return content


def _source(
    source: dict[str, Any], deadline: datetime, freshness: int | None
) -> tuple[list[str], datetime | None]:
    reasons: list[str] = []
    required = {
        "id",
        "role",
        "url",
        "revision",
        "blob_sha256",
        "decompressed_sha256",
        "manifest_version",
        "captured_at",
        "published_at",
        "retrieved_at",
        "timestamp_semantics",
        "timestamp_uncertainty_seconds",
        "parser_version",
        "parent_manifest",
        "table_sha256",
        "bytes",
    }
    if set(source) != required or any(
        not isinstance(source.get(k), str) or not source[k]
        for k in (
            "id",
            "url",
            "revision",
            "timestamp_semantics",
            "parser_version",
            "parent_manifest",
        )
    ):
        return ["source_manifest"], None
    if (
        source["manifest_version"] != 1
        or not isinstance(source["url"], str)
        or source["revision"] not in source["url"]
    ):
        reasons.append("source_identity")
    raw = source["bytes"]
    if (
        not isinstance(raw, bytes)
        or not isinstance(source["blob_sha256"], str)
        or hashlib.sha256(raw).hexdigest() != source["blob_sha256"]
    ):
        reasons.append("source_hash")
    if (
        not isinstance(raw, bytes)
        or source["decompressed_sha256"] != hashlib.sha256(raw).hexdigest()
    ):
        reasons.append("decompressed_hash")
    if not re.fullmatch(r"[0-9a-f]{64}", source["parent_manifest"]):
        reasons.append("parent_manifest")
    if not re.fullmatch(r"[0-9a-f]{40}", source["revision"]):
        reasons.append("source_revision")
    if not isinstance(source["table_sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", source["table_sha256"]
    ):
        reasons.append("table_hash_missing")
    uncertainty = source["timestamp_uncertainty_seconds"]
    if type(uncertainty) is not int or uncertainty < 0:
        reasons.append("source_timestamp")
        return reasons, None
    try:
        captured, published, retrieved = (
            _utc(source[k]) for k in ("captured_at", "published_at", "retrieved_at")
        )
        if (
            published > retrieved
            or retrieved < captured
            or (
                source["role"] == "input"
                and max(captured, published) + timedelta(seconds=uncertainty)
                >= deadline
            )
            or (source["role"] == "outcome" and captured <= deadline)
        ):
            reasons.append("source_cutoff")
        if (
            source["role"] == "input"
            and freshness is not None
            and (deadline - captured).total_seconds() + uncertainty > freshness
        ):
            reasons.append("source_stale")
    except (ValueError, OverflowError):
        reasons.append("source_timestamp")
        return reasons, None
    return reasons, captured


def _issue_errors(
    origin: dict[str, Any], authority: dict[str, Any], gw: int
) -> set[str]:
    reasons: set[str] = set()
    if set(origin["universe"]) != set(authority["universe"]):
        reasons.add("authority_universe")
    if any(
        str(p["id"]) not in authority["seed_mapping"]
        or str(p["id"]) not in authority["components"]
        for p in origin["players"]
    ):
        reasons.add("authority_coverage")
    if any(
        not isinstance(authority["seed_mapping"].get(str(p["id"])), str)
        or not authority["seed_mapping"].get(str(p["id"]))
        or not isinstance(authority["components"].get(str(p["id"])), list)
        or not authority["components"].get(str(p["id"]))
        for p in origin["players"]
    ):
        reasons.add("authority_coverage")
    if any(
        str(p["id"]) not in authority["eligible_since"]
        or type(authority["eligible_since"][str(p["id"])]) is not int
        or authority["eligible_since"][str(p["id"])] > gw
        or p["eligible"] is not True
        for p in origin["players"]
    ):
        reasons.add("authority_eligibility")
    targets = origin["target_gws"]
    if targets != list(range(gw, min(gw + 5, 38) + 1)):
        reasons.add("target_coverage")
    universe = origin["universe"]
    players = origin["players"]
    if (
        not isinstance(universe, list)
        or not universe
        or any(type(i) is not int for i in universe)
        or len(set(universe)) != len(universe)
        or not isinstance(players, list)
        or {p["id"] for p in players} != set(universe)
        or len(players) != len(universe)
    ):
        reasons.add("universe")
    for player in players:
        if (
            type(player["club"]) is not int
            or type(player["position"]) is not int
            or player["position"] not in (1, 2, 3, 4)
            or type(player["price"]) is not int
            or player["price"] <= 0
            or type(player["eligible"]) is not bool
            or type(player["ownership"]) not in (int, float)
            or not 0 <= player["ownership"] <= 100
            or not isinstance(player["availability"], str)
            or not player["availability"]
        ):
            reasons.add("player_metadata")
    schedule = origin["schedule"]
    for pid in universe:
        player = next((p for p in players if p["id"] == pid), None)
        for target in targets:
            rows = [r for r in schedule if r["player"] == pid and r["gw"] == target]
            if (
                not rows
                or any(r["status"] not in ("fixture", "blank") for r in rows)
                or (len(rows) > 1 and any(r["status"] != "fixture" for r in rows))
                or any((r["status"] == "blank") != (r["fixture"] is None) for r in rows)
                or len({r["fixture"] for r in rows}) != len(rows)
            ):
                reasons.add("schedule")
            if player is not None and any(
                r.get("price") != player["price"]
                or r.get("ownership") != player["ownership"]
                for r in rows
            ):
                reasons.add("stock_disagreement")
    issue_package = {key: origin[key] for key in ("players", "fixtures", "schedule")}
    reasons.update(
        assess_issue_fixture_coverage(
            issue_package,
            issue_gw=gw,
            target_gws=targets,
            issue_cutoff=origin["deadline"],
        )
    )
    return reasons


def assess_origins(
    request: dict[str, Any], catalog: dict[str, bytes]
) -> list[dict[str, Any]]:
    if (
        not isinstance(request, dict)
        or set(request)
        != {
            "version",
            "mode",
            "freshness_seconds",
            "eligibility_policy",
            "authority_digest",
            "origins",
        }
        or type(request["version"]) is not int
        or request["version"] != 1
        or request["mode"] not in ("synthetic", "empirical")
        or not isinstance(request["origins"], list)
        or not request["origins"]
    ):
        raise ValueError("Invalid admission request")
    freshness = request["freshness_seconds"]
    if freshness is not None and (type(freshness) is not int or freshness <= 0):
        raise ValueError("Invalid freshness policy")
    if (
        request["mode"] == "synthetic"
        and request["eligibility_policy"] != "synthetic-v1"
    ):
        raise ValueError("Unsupported synthetic eligibility policy")
    authority_digest = request["authority_digest"]
    authority_raw = catalog.get(authority_digest)
    if (
        not isinstance(authority_raw, bytes)
        or hashlib.sha256(authority_raw).hexdigest() != authority_digest
    ):
        raise ValueError("Missing authority closure")
    try:
        authority = json.loads(authority_raw)
        if authority["version"] not in (1, 2):
            raise ValueError("Unknown authority version")
    except (ValueError, TypeError, KeyError):
        raise ValueError("Invalid authority closure") from None
    reports: list[dict[str, Any]] = []
    for request_index, origin in enumerate(request["origins"]):
        reasons: set[str] = set()
        try:
            season, gw = origin["season"], origin["gw"]
            if (
                not isinstance(season, str)
                or not season
                or type(gw) is not int
                or not 1 <= gw <= 38
            ):
                raise ValueError("Invalid origin")
            if season == "2026-27" and gw >= 6:
                reasons.add("sealed_window")
            if (
                authority.get("season") != season
                or type(authority.get("first_gw")) is not int
                or type(authority.get("last_gw")) is not int
                or not authority["first_gw"] <= gw <= authority["last_gw"]
            ):
                reasons.add("authority_scope")
            deadline = _utc(origin["deadline"])
            sources = origin["sources"]
            if not isinstance(sources, list) or not sources:
                reasons.add("source_manifest")
                sources = []
            candidates: dict[str, list[tuple[datetime, dict[str, Any]]]] = {
                "input": [],
                "outcome": [],
            }
            excluded: list[dict[str, Any]] = []
            selected_sources: dict[str, dict[str, Any]] = {}
            for source in sources:
                if not isinstance(source, dict) or source.get("role") not in candidates:
                    excluded.append({"id": None, "reasons": ["source_manifest"]})
            for role in ("input", "outcome"):
                for source in sources:
                    if not isinstance(source, dict) or source.get("role") != role:
                        continue
                    try:
                        errors, captured = _source(source, deadline, freshness)
                    except (TypeError, ValueError, KeyError, OverflowError):
                        errors, captured = ["source_manifest"], None
                    role = source["role"]
                    keys = (
                        ("universe", "players", "fixtures", "schedule")
                        if role == "input"
                        else ("fixture_events", "outcomes")
                    )
                    try:
                        manifest = {
                            k: v
                            for k, v in source.items()
                            if k not in ("bytes", "parent_manifest")
                        }
                        manifest_bytes = json.dumps(
                            manifest,
                            sort_keys=True,
                            separators=(",", ":"),
                            allow_nan=False,
                        ).encode()
                        manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
                        if (
                            manifest_hash not in authority.get("source_manifests", [])
                            or catalog.get(manifest_hash) != manifest_bytes
                        ):
                            errors.append(role + "_manifest_closure")
                        if catalog.get(source["blob_sha256"]) != source["bytes"]:
                            errors.append(role + "_source_closure")
                        if source["parent_manifest"] != authority_digest:
                            errors.append(role + "_parent_manifest")
                        tables = json.loads(source["bytes"])
                        if not isinstance(tables, dict) or set(tables) != set(keys):
                            errors.append(role + "_source_transform")
                        table_bytes = json.dumps(
                            tables,
                            sort_keys=True,
                            separators=(",", ":"),
                            allow_nan=False,
                        ).encode()
                        if (
                            source["table_sha256"]
                            != hashlib.sha256(table_bytes).hexdigest()
                        ):
                            errors.append(role + "_table_hash")
                        if role == "input":
                            candidate_origin = {**origin, **tables}
                            candidate_errors = _issue_errors(
                                candidate_origin, authority, gw
                            )
                            errors.extend(
                                "input_candidate_" + error
                                for error in sorted(candidate_errors)
                            )
                        elif "input" in selected_sources:
                            input_tables = json.loads(
                                selected_sources["input"]["bytes"]
                            )
                            outcome_errors = assess_fixture_coverage(
                                input_tables,
                                tables,
                                issue_gw=gw,
                                target_gws=origin["target_gws"],
                                issue_cutoff=origin["deadline"],
                                outcome_cutoff=source["captured_at"],
                            )
                            errors.extend(
                                "outcome_candidate_" + error for error in outcome_errors
                            )
                        else:
                            errors.append("outcome_candidate_input_unavailable")
                    except (
                        KeyError,
                        TypeError,
                        ValueError,
                        UnicodeDecodeError,
                        OverflowError,
                        AttributeError,
                    ):
                        errors.append(role + "_source_transform")
                    if errors or captured is None:
                        excluded.append(
                            {"id": source.get("id"), "reasons": sorted(set(errors))}
                        )
                    else:
                        candidates[role].append((captured, source))
                choices = candidates[role]
                if not choices:
                    reasons.add("source_" + role)
                    for item in excluded:
                        reasons.update(
                            error
                            for error in item["reasons"]
                            if error.startswith(role + "_")
                        )
                else:
                    latest = max(item[0] for item in choices)
                    winners = [item[1] for item in choices if item[0] == latest]
                    if len(winners) != 1:
                        reasons.add("ambiguous_" + role + "_source")
                    else:
                        selected_sources[role] = winners[0]
            for role, keys in (
                ("input", ("universe", "players", "fixtures", "schedule")),
                ("outcome", ("fixture_events", "outcomes")),
            ):
                source = selected_sources.get(role)
                if source is not None:
                    try:
                        if json.loads(source["bytes"]) != {
                            key: origin[key] for key in keys
                        }:
                            reasons.add(role + "_source_transform")
                            reasons.add(role + "_table_hash")
                    except (KeyError, TypeError, ValueError, UnicodeDecodeError):
                        reasons.add(role + "_source_transform")
            reasons.update(_issue_errors(origin, authority, gw))
            targets = origin["target_gws"]
            issue_package = {
                key: origin[key] for key in ("players", "fixtures", "schedule")
            }
            try:
                expected_rules = "synthetic-rules-v1" if authority["version"] == 1 else get_rules(season).rules_id
                rules_authorized = authority["version"] == 1 or authority.get("native_rules") == expected_rules
            except ValueError:
                expected_rules, rules_authorized = "", False
            if (
                origin["native_rules"] != expected_rules
                or not rules_authorized
                or request["mode"] != "synthetic"
                or origin["chip_policy"] != "no_assistant_manager"
            ):
                reasons.add("rules")
            if (
                not isinstance(origin["seed_identity"], str)
                or not origin["seed_identity"]
                or origin["seed_identity"] != authority.get("seed_identity")
                or origin["components_complete"] is not True
            ):
                reasons.add("seed_components")
            selected = {role: source["id"] for role, source in selected_sources.items()}
            input_blockers = {
                "source_input",
                "source_manifest",
                "ambiguous_input_source",
                "input_table_hash",
                "input_source_transform",
                "input_source_closure",
                "input_parent_manifest",
                "input_manifest_closure",
                "fixture_identity",
                "authority_scope",
                "authority_universe",
                "authority_coverage",
                "authority_eligibility",
                "universe",
                "player_metadata",
                "target_coverage",
                "schedule",
                "stock_disagreement",
                "rules",
                "seed_components",
                "schedule_coverage",
                "duplicate_identity",
                "sealed_window",
            }
            input_ready = request["mode"] == "synthetic" and not (
                reasons & input_blockers
            )
            input_payload = {
                "version": request["version"],
                "mode": request["mode"],
                "freshness_seconds": request["freshness_seconds"],
                "eligibility_policy": request["eligibility_policy"],
                "authority": {
                    k: v for k, v in authority.items() if k != "source_manifests"
                },
                "season": season,
                "gw": gw,
                "deadline": origin["deadline"],
                "target_gws": targets,
                "input_source": {
                    k: v
                    for k, v in selected_sources.get("input", {}).items()
                    if k != "parent_manifest"
                },
                "universe": origin["universe"],
                "players": origin["players"],
                "fixtures": origin["fixtures"],
                "schedule": origin["schedule"],
                "native_rules": origin["native_rules"],
                "chip_policy": origin["chip_policy"],
                "seed_identity": origin["seed_identity"],
            }
            input_digest = (
                hashlib.sha256(
                    json.dumps(
                        input_payload,
                        sort_keys=True,
                        separators=(",", ":"),
                        default=lambda v: v.hex() if isinstance(v, bytes) else v,
                        allow_nan=False,
                    ).encode()
                ).hexdigest()
                if input_ready
                else None
            )
            outcome_source = selected_sources.get("outcome")
            outcome_available = (
                outcome_source is not None
                and "input" in selected_sources
                and "outcome_source_transform" not in reasons
                and "outcome_table_hash" not in reasons
            )
            if outcome_source is not None:
                try:
                    outcome_errors = assess_fixture_coverage(
                        issue_package,
                        {
                            key: origin.get(key, [])
                            for key in ("fixture_events", "outcomes")
                        },
                        issue_gw=gw,
                        target_gws=targets,
                        issue_cutoff=origin["deadline"],
                        outcome_cutoff=outcome_source["captured_at"],
                    )
                    reasons.update(outcome_errors)
                    outcome_available = outcome_available and not outcome_errors
                except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
                    reasons.add("outcome_malformed")
                    outcome_available = False
            pending = request["mode"] == "empirical"
            status = (
                "unavailable"
                if reasons
                else ("pending_approval" if pending else "admitted_synthetic")
            )
            reports.append(
                {
                    "version": 1,
                    "request_index": request_index,
                    "season": season,
                    "gw": gw,
                    "status": status,
                    "reasons": sorted(reasons),
                    "selected_source": selected,
                    "input_ready": input_ready,
                    "input_digest": input_digest,
                    "excluded_sources": excluded,
                    "coverage": {
                        name: {
                            "requirement": "required",
                            "availability": "unavailable"
                            if (name == "outcomes" and not outcome_available)
                            or (name != "outcomes" and reasons.intersection(blockers))
                            else "available",
                        }
                        for name, blockers in {
                            "input_source": {
                                "source_input",
                                "ambiguous_input_source",
                                "input_table_hash",
                                "input_source_transform",
                                "input_source_closure",
                                "input_parent_manifest",
                            },
                            "outcome_source": {
                                "source_outcome",
                                "ambiguous_outcome_source",
                                "outcome_table_hash",
                                "outcome_source_transform",
                                "outcome_source_closure",
                                "outcome_parent_manifest",
                            },
                            "universe": {
                                "universe",
                                "authority_scope",
                                "authority_universe",
                                "authority_eligibility",
                            },
                            "metadata": {"player_metadata", "stock_disagreement"},
                            "forecast_schedule": {
                                "target_coverage",
                                "schedule",
                                "schedule_coverage",
                                "duplicate_identity",
                            },
                            "outcomes": {
                                "event_coverage",
                                "event_chronology",
                                "event_transition",
                                "event_finalization",
                                "outcome_coverage",
                                "duplicate_event",
                                "fixture_identity",
                                "outcome_malformed",
                            },
                            "rules": {"rules"},
                            "seed_components": {
                                "seed_components",
                                "authority_coverage",
                            },
                        }.items()
                    },
                    "limitations": ["synthetic verification only"]
                    if not pending
                    else ["empirical approval and coverage not established"],
                }
            )
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
            reports.append(
                {
                    "version": 1,
                    "request_index": request_index,
                    "season": origin.get("season")
                    if isinstance(origin, dict)
                    else None,
                    "gw": origin.get("gw") if isinstance(origin, dict) else None,
                    "status": "unavailable",
                    "reasons": ["malformed_origin"],
                    "selected_source": {},
                    "excluded_sources": [],
                    "coverage": {},
                    "limitations": ["origin could not be assessed"],
                }
            )
    return reports


def require_admitted(
    request: dict[str, Any], catalog: dict[str, bytes], season: str, gw: int
) -> AdmittedOrigin:
    reports = assess_origins(request, catalog)
    match = [r for r in reports if r["season"] == season and r["gw"] == gw]
    if len(match) != 1 or match[0]["status"] != "admitted_synthetic":
        raise ValueError("Origin not admitted")
    serialized = json.dumps(
        {"request": request, "catalog": catalog},
        sort_keys=True,
        separators=(",", ":"),
        default=lambda value: value.hex() if isinstance(value, bytes) else value,
        allow_nan=False,
    ).encode()
    return AdmittedOrigin(
        season, gw, request["mode"], hashlib.sha256(serialized).hexdigest()
    )


def verify_admitted(
    capability: AdmittedOrigin, request: dict[str, Any], catalog: dict[str, bytes]
) -> None:
    """Revalidate retained payload at each consumer boundary; never trust a record alone."""
    if capability != require_admitted(
        request, catalog, capability.season, capability.gw
    ):
        raise ValueError("Admission capability does not match inputs")


@dataclass(frozen=True)
class AdmittedInput:
    season: str
    gw: int
    input_digest: str


def require_input(
    request: dict[str, Any], catalog: dict[str, bytes], season: str, gw: int
) -> AdmittedInput:
    matches = [
        report
        for report in assess_origins(request, catalog)
        if report["season"] == season and report["gw"] == gw
    ]
    if len(matches) != 1 or matches[0].get("input_ready") is not True:
        raise ValueError("Input not admitted")
    return AdmittedInput(season, gw, matches[0]["input_digest"])


def verify_input(
    capability: AdmittedInput, request: dict[str, Any], catalog: dict[str, bytes]
) -> None:
    if capability != require_input(request, catalog, capability.season, capability.gw):
        raise ValueError("Input capability does not match inputs")
