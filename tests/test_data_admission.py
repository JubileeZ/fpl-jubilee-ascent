import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from backtesting.data_admission import assess_origins, strict_load, require_admitted


RETAINED: dict[str, bytes] = {}


def request() -> dict[str, Any]:
    raw = b"synthetic input"
    source = {
        "id": "s",
        "role": "input",
        "url": "synthetic://" + "a" * 40,
        "manifest_version": 1,
        "decompressed_sha256": hashlib.sha256(raw).hexdigest(),
        "revision": "a" * 40,
        "blob_sha256": hashlib.sha256(raw).hexdigest(),
        "captured_at": "2025-01-01T11:00:00Z",
        "published_at": "2025-01-01T10:00:00Z",
        "retrieved_at": "2025-01-02T00:00:00Z",
        "timestamp_semantics": "synthetic capture",
        "timestamp_uncertainty_seconds": 0,
        "parser_version": "1",
        "parent_manifest": "c" * 64,
        "table_sha256": "b" * 64,
        "bytes": raw,
    }
    value = {
        "version": 1,
        "mode": "synthetic",
        "freshness_seconds": 7200,
        "eligibility_policy": "synthetic-v1",
        "authority_digest": "",
        "origins": [
            {
                "season": "test",
                "gw": 1,
                "deadline": "2025-01-01T12:00:00Z",
                "sources": [
                    source,
                    {
                        **source,
                        "id": "outcome",
                        "role": "outcome",
                        "captured_at": "2025-01-03T11:00:00Z",
                        "published_at": "2025-01-03T10:00:00Z",
                        "retrieved_at": "2025-01-04T00:00:00Z",
                    },
                ],
                "universe": [1, 2],
                "players": [
                    {
                        "id": 1,
                        "club": 1,
                        "position": 1,
                        "price": 50,
                        "eligible": True,
                        "ownership": 20.0,
                        "availability": "available",
                    },
                    {
                        "id": 2,
                        "club": 2,
                        "position": 2,
                        "price": 45,
                        "eligible": True,
                        "ownership": 10.0,
                        "availability": "available",
                    },
                ],
                "schedule": [
                    {"player": 1, "gw": 1, "status": "fixture", "fixture": 11},
                    {"player": 2, "gw": 1, "status": "blank", "fixture": None},
                ],
                "outcomes": [
                    {
                        "player": 1,
                        "gw": 1,
                        "fixture": 11,
                        "status": "final",
                        "points": 2,
                    },
                    {
                        "player": 2,
                        "gw": 1,
                        "fixture": None,
                        "status": "blank",
                        "points": 0,
                    },
                ],
                "native_rules": "synthetic-rules-v1",
                "chip_policy": "no_assistant_manager",
                "seed_identity": "synthetic-seed",
                "components_complete": True,
            }
        ],
    }
    origin = value["origins"][0]
    origin["target_gws"] = list(range(1, 7))
    origin["fixtures"] = [
        {"id": 10 + gw, "gw": gw, "home_club": 1, "away_club": 3} for gw in range(1, 7)
    ]
    origin["fixture_events"] = [
        {
            "fixture": 11,
            "gw": 1,
            "status": "final",
            "home_club": 1,
            "away_club": 3,
            "changed_at": None,
            "finalized_at": "2025-01-02T12:00:00Z",
        }
    ]
    origin["outcomes"] = [
        {"player": 1, "gw": 1, "fixture": 11, "status": "played", "points": 2}
    ]
    origin["schedule"] = [
        {
            "player": pid,
            "gw": gw,
            "status": "fixture" if pid == 1 else "blank",
            "fixture": 10 + gw if pid == 1 else None,
            "price": 50 if pid == 1 else 45,
            "ownership": 20.0 if pid == 1 else 10.0,
        }
        for gw in range(1, 7)
        for pid in (1, 2)
    ]
    authority = {
        "version": 1,
        "season": "test",
        "first_gw": 1,
        "last_gw": 38,
        "universe": [1, 2],
        "seed_identity": "synthetic-seed",
        "seed_mapping": {"1": "s1", "2": "s2"},
        "components": {"1": ["points"], "2": ["points"]},
        "eligible_since": {"1": 1, "2": 1},
    }
    rehash(value)
    manifests = []
    for source in origin["sources"]:
        manifest = {
            k: v for k, v in source.items() if k not in ("bytes", "parent_manifest")
        }
        raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        RETAINED[digest] = raw
        manifests.append(digest)
    authority["source_manifests"] = manifests
    raw = json.dumps(authority, sort_keys=True, separators=(",", ":")).encode()
    value["authority_digest"] = hashlib.sha256(raw).hexdigest()
    RETAINED[value["authority_digest"]] = raw
    for source in origin["sources"]:
        source["parent_manifest"] = value["authority_digest"]
    return value


def catalog(value: dict[str, Any]) -> dict[str, bytes]:
    entries = dict(RETAINED)
    for origin in value["origins"]:
        if isinstance(origin, dict):
            for source in origin.get("sources", []):
                if isinstance(source, dict) and isinstance(source.get("bytes"), bytes):
                    entries[hashlib.sha256(source["bytes"]).hexdigest()] = source[
                        "bytes"
                    ]
    return entries


def rehash(value: dict[str, Any]) -> None:
    origin = value["origins"][0]
    for source in origin["sources"]:
        keys = (
            ("universe", "players", "fixtures", "schedule")
            if source["role"] == "input"
            else ("fixture_events", "outcomes")
        )
        tables = {key: origin[key] for key in keys}
        source["bytes"] = json.dumps(
            tables, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        source["blob_sha256"] = hashlib.sha256(source["bytes"]).hexdigest()
        source["decompressed_sha256"] = source["blob_sha256"]
        source["table_sha256"] = source["blob_sha256"]


def authorize(value: dict[str, Any]) -> None:
    authority = json.loads(RETAINED[value["authority_digest"]])
    authority["source_manifests"] = []
    for source in value["origins"][0]["sources"]:
        manifest = {
            k: v for k, v in source.items() if k not in ("bytes", "parent_manifest")
        }
        raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        RETAINED[digest] = raw
        authority["source_manifests"].append(digest)
    raw = json.dumps(authority, sort_keys=True, separators=(",", ":")).encode()
    value["authority_digest"] = hashlib.sha256(raw).hexdigest()
    RETAINED[value["authority_digest"]] = raw
    for source in value["origins"][0]["sources"]:
        source["parent_manifest"] = value["authority_digest"]


def test_synthetic_origin_admitted_and_report_deterministic() -> None:
    value = request()
    reports = assess_origins(value, catalog(value))
    assert reports == assess_origins(copy.deepcopy(value), catalog(value))
    assert reports[0]["status"] == "admitted_synthetic"
    assert require_admitted(value, catalog(value), "test", 1).season == "test"


def test_late_corrupt_and_missing_player_fail_closed() -> None:
    value = request()
    source = value["origins"][0]["sources"][0]
    source["captured_at"] = value["origins"][0]["deadline"]
    source["blob_sha256"] = "0" * 64
    value["origins"][0]["players"].pop()
    report = assess_origins(value, catalog(value))[0]
    assert report["status"] == "unavailable"
    assert {"source_input", "universe"} <= set(report["reasons"])
    assert {"source_hash", "source_cutoff"} <= set(
        report["excluded_sources"][0]["reasons"]
    )
    with pytest.raises(ValueError):
        require_admitted(value, catalog(value), "test", 1)


def test_sealed_path_rejected_before_reader(tmp_path: Path) -> None:
    calls: list[Path] = []
    descriptor = {
        "version": 1,
        "season": "2026-27",
        "gw": 6,
        "path": str(tmp_path / "data"),
        "sha256": "a" * 64,
        "parent_manifest": "b" * 64,
    }
    with pytest.raises(ValueError):
        strict_load(descriptor, {}, lambda path: calls.append(path) or b"")
    assert calls == []


def test_empirical_approval_pending() -> None:
    value = request()
    value.update(mode="empirical", freshness_seconds=None, eligibility_policy=None)
    assert assess_origins(value, catalog(value))[0]["status"] in (
        "pending_approval",
        "unavailable",
    )
    with pytest.raises(ValueError):
        require_admitted(value, catalog(value), "test", 1)


def test_missing_future_schedule_and_table_tampering() -> None:
    value = request()
    value["origins"][0]["schedule"].pop()
    report = assess_origins(value, catalog(value))[0]
    assert {"schedule", "input_table_hash"} <= set(report["reasons"])


def test_ambiguous_sources_and_unfinished_outcome() -> None:
    value = request()
    origin = value["origins"][0]
    other = copy.deepcopy(origin["sources"][0])
    other["id"] = "other"
    origin["sources"].append(other)
    origin["fixture_events"][0]["status"] = "postponed"
    rehash(value)
    authorize(value)
    report = assess_origins(value, catalog(value))[0]
    assert {"ambiguous_input_source", "outcome_candidate_input_unavailable"} <= set(
        report["reasons"]
    )


def test_all_requested_origins_reported() -> None:
    value = request()
    second = copy.deepcopy(value["origins"][0])
    second["season"] = "second"
    value["origins"].append(second)
    assert [r["season"] for r in assess_origins(value, catalog(value))] == [
        "test",
        "second",
    ]


def test_mandatory_sealed_season_before_reader() -> None:
    called: list[Path] = []
    descriptor = {
        "version": 1,
        "season": "2026-27",
        "gw": 6,
        "path": "other/location",
        "sha256": "a" * 64,
        "parent_manifest": "b" * 64,
    }
    with pytest.raises(ValueError):
        strict_load(descriptor, {}, lambda path: called.append(path) or b"")
    assert called == []


def test_malformed_origin_does_not_hide_other_origins() -> None:
    value = request()
    value["origins"].append({"season": "broken", "gw": 1})
    reports = assess_origins(value, catalog(value))
    assert reports[0]["status"] == "admitted_synthetic"
    assert reports[1]["status"] == "unavailable"


def test_policy_and_authority_are_bound() -> None:
    from backtesting.data_admission import verify_admitted

    value = request()
    capability = require_admitted(value, catalog(value), "test", 1)
    value["freshness_seconds"] = 7100
    with pytest.raises(ValueError):
        verify_admitted(capability, value, catalog(value))
    value["eligibility_policy"] = "anything"
    with pytest.raises(ValueError):
        assess_origins(value, catalog(value))


def test_excludes_bad_source_but_uses_latest_valid() -> None:
    value = request()
    late = copy.deepcopy(value["origins"][0]["sources"][0])
    late.update(id="late", captured_at="2025-01-01T12:01:00Z")
    value["origins"][0]["sources"].append(late)
    value["origins"][0]["sources"].append(None)
    report = assess_origins(value, catalog(value))[0]
    assert report["status"] == "admitted_synthetic"
    assert report["selected_source"]["input"] == "s"
    assert len(report["excluded_sources"]) == 2


def test_truncated_normalized_universe_cannot_rehash_pinned_authority() -> None:
    value = request()
    origin = value["origins"][0]
    origin["universe"] = [1]
    origin["players"] = origin["players"][:1]
    origin["schedule"] = [r for r in origin["schedule"] if r["player"] == 1]
    origin["outcomes"] = [r for r in origin["outcomes"] if r["player"] == 1]
    rehash(value)
    assert "authority_universe" in assess_origins(value, catalog(value))[0]["reasons"]


def test_strict_loader_checks_chain_before_read() -> None:
    parent = {
        "version": 1,
        "season": "test",
        "first_gw": 1,
        "last_gw": 5,
        "parent": None,
        "sources": [
            {"path": "synthetic.json", "sha256": hashlib.sha256(b"data").hexdigest()}
        ],
    }
    raw = json.dumps(parent, sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()
    descriptor = {
        "version": 1,
        "season": "test",
        "gw": 1,
        "path": "synthetic.json",
        "sha256": hashlib.sha256(b"data").hexdigest(),
        "parent_manifest": digest,
    }
    calls: list[Path] = []

    def reader(path: Path) -> bytes:
        calls.append(path)
        return b"data"

    with pytest.raises(ValueError):
        strict_load(descriptor, {}, reader)
    assert not calls
    assert strict_load(descriptor, {digest: raw}, reader) == b"data"
    assert len(calls) == 1


def test_input_identity_excludes_future_outcome() -> None:
    value = request()
    first = assess_origins(value, catalog(value))[0]
    value["origins"][0]["sources"] = [
        s for s in value["origins"][0]["sources"] if s["role"] == "input"
    ]
    value["origins"][0].pop("fixture_events")
    value["origins"][0].pop("outcomes")
    second = assess_origins(value, catalog(value))[0]
    assert second["status"] == "unavailable"
    assert second["input_ready"] is True
    assert second["input_digest"] == first["input_digest"]


def test_input_capability_rechecks_issue_inputs_without_outcomes() -> None:
    from backtesting.data_admission import require_input, verify_input

    value = request()
    capability = require_input(value, catalog(value), "test", 1)
    value["origins"][0]["sources"] = [
        s for s in value["origins"][0]["sources"] if s["role"] == "input"
    ]
    value["origins"][0].pop("fixture_events")
    value["origins"][0].pop("outcomes")
    verify_input(capability, value, catalog(value))
    value["freshness_seconds"] = 7100
    with pytest.raises(ValueError):
        verify_input(capability, value, catalog(value))


def test_missing_source_closure_and_bad_scope_block_capability() -> None:
    value = request()
    retained = catalog(value)
    input_source = value["origins"][0]["sources"][0]
    del retained[input_source["blob_sha256"]]
    assert "input_source_closure" in assess_origins(value, retained)[0]["reasons"]
    with pytest.raises(ValueError):
        require_admitted(value, retained, "test", 1)
    value["origins"][0]["season"] = "another"
    assert "authority_scope" in assess_origins(value, catalog(value))[0]["reasons"]


def test_manifest_timestamp_tampering_fails() -> None:
    value = request()
    retained = catalog(value)
    value["origins"][0]["sources"][0]["captured_at"] = "2025-01-01T10:30:00Z"
    report = assess_origins(value, retained)[0]
    assert "input_manifest_closure" in report["reasons"]
    assert report["input_ready"] is False


def test_newer_broken_source_does_not_hide_valid_source() -> None:
    value = request()
    other = copy.deepcopy(value["origins"][0]["sources"][0])
    other.update(id="newer", captured_at="2025-01-01T11:30:00Z")
    value["origins"][0]["sources"].append(other)
    authorize(value)
    retained = catalog(value)
    manifest = {k: v for k, v in other.items() if k not in ("bytes", "parent_manifest")}
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    del retained[hashlib.sha256(raw).hexdigest()]
    report = assess_origins(value, retained)[0]
    assert report["selected_source"]["input"] == "s"
    assert "input_manifest_closure" in report["excluded_sources"][0]["reasons"]
    assert report["status"] == "admitted_synthetic"


def test_future_outcome_authorization_preserves_issue_capability() -> None:
    from backtesting.data_admission import require_input, verify_input

    value = request()
    origin = value["origins"][0]
    outcome = origin["sources"].pop()
    authorize(value)
    capability = require_input(value, catalog(value), "test", 1)
    origin["sources"].append(outcome)
    authorize(value)
    verify_input(capability, value, catalog(value))
    assert require_admitted(value, catalog(value), "test", 1).season == "test"


def test_newest_snapshot_cannot_be_hidden_by_stale_origin() -> None:
    value = request()
    origin = value["origins"][0]
    newer = copy.deepcopy(origin["sources"][0])
    package = json.loads(newer["bytes"])
    package["players"][0]["price"] = 51
    for row in package["schedule"]:
        if row["player"] == 1:
            row["price"] = 51
    raw = json.dumps(package, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    newer.update(
        id="newer",
        captured_at="2025-01-01T11:30:00Z",
        bytes=raw,
        blob_sha256=digest,
        decompressed_sha256=digest,
        table_sha256=digest,
    )
    origin["sources"].append(newer)
    authorize(value)
    report = assess_origins(value, catalog(value))[0]
    assert report["selected_source"]["input"] == "newer"
    assert report["status"] == "unavailable"
    assert not report["input_ready"]


@pytest.mark.parametrize("defect", ["status", "club"])
def test_scoring_defect_preserves_issue_capability(defect: str) -> None:
    from backtesting.data_admission import require_input, verify_input

    value = request()
    capability = require_input(value, catalog(value), "test", 1)
    origin = value["origins"][0]
    if defect == "status":
        origin["fixture_events"][0]["status"] = "invalid"
    else:
        origin["fixture_events"][0]["away_club"] = 99
    rehash(value)
    authorize(value)
    report = assess_origins(value, catalog(value))[0]
    assert report["status"] == "unavailable"
    assert report["input_ready"] is True
    assert report["input_digest"] == capability.input_digest
    verify_input(capability, value, catalog(value))


@pytest.mark.parametrize("role", ["input", "outcome"])
def test_invalid_newer_candidate_falls_back(role: str) -> None:
    value = request()
    origin = value["origins"][0]
    older = next(source for source in origin["sources"] if source["role"] == role)
    newer = copy.deepcopy(older)
    package = json.loads(newer["bytes"])
    if role == "input":
        package["players"][0]["price"] = 51
        captured = "2025-01-01T11:30:00Z"
    else:
        package["fixture_events"][0]["status"] = "invalid"
        captured = "2025-01-03T12:00:00Z"
    raw = json.dumps(package, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    newer.update(
        id="invalid-newer",
        captured_at=captured,
        bytes=raw,
        blob_sha256=digest,
        decompressed_sha256=digest,
        table_sha256=digest,
    )
    origin["sources"].append(newer)
    authorize(value)
    report = assess_origins(value, catalog(value))[0]
    assert report["status"] == "admitted_synthetic"
    assert report["selected_source"][role] == older["id"]
    assert any(item["id"] == "invalid-newer" for item in report["excluded_sources"])


@pytest.mark.parametrize("defect", ["empty", "malformed"])
def test_unavailable_scoring_reports_unavailable_outcomes(defect: str) -> None:
    from backtesting.data_admission import require_input

    value = request()
    capability = require_input(value, catalog(value), "test", 1)
    origin = value["origins"][0]
    if defect == "empty":
        origin["outcomes"] = []
    else:
        origin["fixture_events"][0]["status"] = "invalid"
    rehash(value)
    authorize(value)
    report = assess_origins(value, catalog(value))[0]
    assert report["status"] == "unavailable"
    assert report["coverage"]["outcomes"]["availability"] == "unavailable"
    assert report["input_ready"] is True
    assert report["input_digest"] == capability.input_digest
