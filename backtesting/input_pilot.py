"""Offline field-level assessment of the fixed, retained 2025-26 GW2 pilot."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import lzma
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from backtesting.input_evidence import (
    FieldEvidence, SourceEvidence, assess_field, validate_player_inputs, validate_schedule_inputs,
)

ROOT = Path(__file__).resolve().parents[1]
TOPIC = ROOT / "docs/research/backtesting-promotion-foundation"
QUARANTINE = ROOT / "data/reports/readiness-source-pilot/v1"


def _bootstrap(raw: bytes) -> dict[str, Any]:
    decoder = lzma.LZMADecompressor()
    decoded = decoder.decompress(raw, max_length=16 * 1024 * 1024 + 1)
    if len(decoded) > 16 * 1024 * 1024 or not decoder.eof:
        raise ValueError("Bootstrap size cap or incomplete stream")
    return json.loads(decoded)


def assess_retained_pilot(quarantine: Path) -> dict[str, Any]:
    quarantine = quarantine.resolve()
    if any(part in {"archive", "2026-27", ".git", ".agents"} for part in quarantine.parts):
        raise ValueError("Protected pilot path")
    summary_raw = (quarantine / "summary.json").read_bytes()
    summary = json.loads(summary_raw)
    if summary.get("origin") != "2025-26 GW2":
        raise ValueError("Only fixed unsealed pilot scope supported")
    sources: dict[str, SourceEvidence] = {}
    required = ("opening_bootstrap", "origin_bootstrap_pilot", "fixture_pilot")
    for label in required:
        candidates = [row for row in summary["attempts"] if row["label"] == label and row["status"] == "recovered"]
        if not candidates:
            continue
        attempt = candidates[-1]
        if type(attempt["attempt"]) is not int or attempt["attempt"] <= 0:
            raise ValueError("Invalid retained attempt")
        raw = (quarantine / f"{attempt['attempt']:02}-{label}.raw").read_bytes()
        if len(raw) > 10 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != attempt["sha256"]:
            raise ValueError("Retained source hash/size mismatch")
        sources[label] = SourceEvidence(label, raw, attempt["sha256"], "unknown", None, None, None,
                                         (f"summary.json#attempt-{attempt['attempt']}",))

    player_fields = ("id", "team", "element_type", "now_cost", "status", "chance_of_playing_next_round",
                     "selected_by_percent", "news", "news_added")
    bootstraps = {label: _bootstrap(source.raw) for label, source in sources.items() if "bootstrap" in label}
    players = {label: [{key: row.get(key) for key in player_fields} for row in payload["elements"]]
               for label, payload in bootstraps.items()}
    clubs = {label: {row["id"] for row in payload["teams"]} for label, payload in bootstraps.items()}
    fixture_source = sources.get("fixture_pilot")
    fixture_fields = ("id", "event", "team_h", "team_a", "kickoff_time")
    fixtures = [] if fixture_source is None else [
        {key: row.get(key) for key in fixture_fields}
        for row in csv.DictReader(io.StringIO(fixture_source.raw.decode("utf-8-sig")))
        if row.get("event") and 2 <= int(row["event"]) <= 7
    ]
    current = "origin_bootstrap_pilot"
    opening = "opening_bootstrap"
    current_issues = validate_player_inputs(players.get(current, []), clubs.get(current, set()))
    opening_issues = validate_player_inputs(players.get(opening, []), clubs.get(opening, set()), require_ownership=True)
    schedule_issues = validate_schedule_inputs(fixtures, tuple(range(2, 8)), clubs.get(current, set()))
    cutoff = datetime.fromisoformat("2025-08-22T17:30:00+00:00")
    opening_cutoff = datetime.fromisoformat("2025-08-15T17:30:00+00:00")
    for label, gw, expected in ((current, 2, cutoff), (opening, 1, opening_cutoff)):
        if label in bootstraps:
            events = [row for row in bootstraps[label]["events"] if row.get("id") == gw]
            if len(events) != 1 or datetime.fromisoformat(events[0]["deadline_time"].replace("Z", "+00:00")) != expected:
                raise ValueError("Retained deadline does not match fixed pilot")
    specs = (
        ("eligible_universe", current, current_issues, "Eligibility and complete legal universe not independently verified."),
        ("price_club_position", current, current_issues, "Commit time not substituted for capture bounds; no age policy approved."),
        ("availability", current, current_issues, "Null next-round chance remains unknown; no terminal-status substitution."),
        ("fixture_schedule", "fixture_pilot", schedule_issues, "Observed horizon rows do not establish announcement-history completeness."),
        ("opening_anchor", opening, opening_issues, "Metadata only; no ownership optimization or eligibility certificate."),
        ("historical_performance", "", (), "Causal pre-origin history source/coverage not admitted."),
        ("prior_season_training", "", (), "Code trace distinguishes seeded features from current-history model.fit; empirical seed lineage unverified."),
        ("settled_outcomes", "", (), "Independent post-settlement completeness unverified; no missing outcomes converted to zero."),
        ("shared_chip_calendar", "", (), "No causal calendar supplied; no future-outcome calendar optimization."),
    )
    assessments = [asdict(assess_field(FieldEvidence(name, sources.get(label), issues, None,
                          limitations=(limitation,)), opening_cutoff if name == "opening_anchor" else cutoff))
                   for name, label, issues, limitation in specs]
    return {
        "version": 1, "origin": "2025-26 GW2", "promotion_authority": False,
        "assessment_scope": "offline supplied-evidence diagnostics; not empirical admission",
        "summary_sha256": hashlib.sha256(summary_raw).hexdigest(),
        "sources": {key: {"sha256": value.sha256, "timing_basis": value.timing_basis,
                          "capture_lower": None, "capture_upper": None, "publication_upper": None,
                          "references": list(value.references)} for key, value in sources.items()},
        "metrics": {"current_player_rows": len(players.get(current, [])), "opening_player_rows": len(players.get(opening, [])),
                    "horizon_fixture_rows": len(fixtures),
                    "null_next_round_chance": sum(row["chance_of_playing_next_round"] is None for row in players.get(current, []))},
        "fields": assessments,
        "code_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in (
            "backtesting/input_evidence.py", "backtesting/walkforward.py", "features/builder.py", "backtesting/forecast_adapter.py")},
    }


def main() -> None:
    report = assess_retained_pilot(QUARANTINE)
    (TOPIC / "input_evidence_assessment.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    with (TOPIC / "input_evidence_fields.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("name", "source_id", "status", "reasons", "limitations", "promotion_authority"))
        writer.writeheader()
        for field in report["fields"]:
            writer.writerow({**field, "reasons": ";".join(field["reasons"]), "limitations": ";".join(field["limitations"])})
    print(json.dumps({"origin": report["origin"], "statuses": {row["name"]: row["status"] for row in report["fields"]},
                      "promotion_authority": False}, sort_keys=True))


if __name__ == "__main__":
    main()
