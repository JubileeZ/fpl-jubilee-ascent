"""Build a conservative replay admission inventory from existing audit summaries."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = {
    "coverage": "ownership_local_coverage.csv",
    "samples": "ownership_snapshot_samples.csv",
    "provenance": "ownership_snapshot_provenance.csv",
}
FIELDS = (
    "opening_ownership", "opening_price", "player_universe", "eligibility", "deadline_price_and_membership",
    "deadline", "six_gw_fixture_schedule", "availability", "seed_history",
    "outcomes", "components", "native_rules",
)
RULE_SOURCES = {
    "2023-24": "https://www.premierleague.com/en/news/3568527",
    "2024-25": "https://www.premierleague.com/en/news/4058895",
    "2025-26": "https://www.premierleague.com/en/news/4362211",
}
REQUIRED_COLUMNS = {
    "coverage": {"season", "population", "gw1_unique_players", "timing_status"},
    "samples": {"season", "raw_player_rows", "required_missing_rows", "timing_status", "gw1_deadline"},
    "provenance": {"season", "payload_gw1_deadline", "recorded_commit_before_deadline"},
}


def load(name: str) -> dict[str, dict[str, str]]:
    with (ROOT / SOURCES[name]).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = REQUIRED_COLUMNS[name] - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Missing columns in {name}: {sorted(missing)}")
        return {row["season"]: row for row in reader}


def build_rows(tables: dict[str, dict[str, dict[str, str]]]) -> list[dict[str, str | int]]:
    for name, required in REQUIRED_COLUMNS.items():
        if name not in tables:
            raise ValueError(f"Missing table: {name}")
        for season, row in tables[name].items():
            missing = required - row.keys()
            if missing:
                raise ValueError(f"Missing columns in {name} for {season}: {sorted(missing)}")
    coverage, samples, provenance = (tables[name] for name in SOURCES)
    rows: list[dict[str, str | int]] = []
    for season in RULE_SOURCES:
        if season not in coverage or season not in samples or season not in provenance:
            raise ValueError(f"Missing audited source row: {season}")
        for origin in range(1, 39):
            for field in FIELDS:
                requirement = "required"
                status = "unverified"
                source = ""
                columns = ""
                note = "No per-origin admission evidence established by input audits."
                if field in {"opening_ownership", "opening_price"}:
                    source = SOURCES["samples"] + ";" + SOURCES["provenance"]
                    columns = "raw_player_rows;required_missing_rows;timing_status;recorded_commit_before_deadline"
                    sample = samples[season]
                    before = provenance[season]["recorded_commit_before_deadline"]
                    note = (f"GW1 anchor reference; sample rows={sample['raw_player_rows']}, "
                            f"required missing rows={sample['required_missing_rows']}, "
                            f"recorded commit before deadline={before}; freshness and eligibility unverified.")
                elif field == "player_universe":
                    source = SOURCES["coverage"] + ";" + SOURCES["samples"]
                    columns = "population;gw1_unique_players;raw_player_rows;timing_status"
                    note = "Opening sample and terminal-metadata coverage only; complete deadline universe unverified."
                elif field == "deadline" and origin == 1:
                    source = SOURCES["samples"] + ";" + SOURCES["provenance"]
                    columns = "gw1_deadline;payload_gw1_deadline;recorded_commit_before_deadline"
                    note = (f"Sample deadline={samples[season]['gw1_deadline']}, "
                            f"provenance deadline={provenance[season]['payload_gw1_deadline']}, "
                            f"recorded commit before deadline={provenance[season]['recorded_commit_before_deadline']}; admission unverified.")
                elif field == "native_rules":
                    source = RULE_SOURCES[season]
                    columns = "official season rules article"
                    note = "Documentary rule evidence only; implementation and full season applicability unverified."
                rows.append({"season": season, "origin_gw": origin, "horizon_end_gw": min(origin + 5, 38),
                             "field": field, "requirement": requirement, "evidence_status": status,
                             "source_artifact": source, "source_columns": columns, "evidence_note": note})
    return rows


def main() -> None:
    rows = build_rows({name: load(name) for name in SOURCES})
    with (ROOT / "replay_admission_inventory.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
