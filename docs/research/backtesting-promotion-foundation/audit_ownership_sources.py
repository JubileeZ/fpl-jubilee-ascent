"""Audit unsealed ownership inputs and public snapshot samples; no optimization."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import lzma
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import pandas as pd

TOPIC = Path(__file__).resolve().parent
REPO = TOPIC.parents[2]
SOURCES: tuple[tuple[str, str], ...] = (
    ("2023-24", "cache/2023/8/11/1231.json.xz"),
    ("2024-25", "cache/2024/8/16/1238.json.xz"),
    ("2025-26", "cache/2025/8/15/1252.json.xz"),
)
FIELDS: tuple[str, ...] = ("id", "element_type", "team", "now_cost", "selected_by_percent")
PINNED_COMMITS: dict[str, str] = {
    "2023-24": "1e066f7405a23e0f00917706b297ec35c4218062",
    "2024-25": "2ae22a16ee2280311de07b8b5ee3b8393377a178",
    "2025-26": "4aaec38e6b5f5ade8b63162a3678ce67148adb67",
}


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with (TOPIC / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def local_coverage(season: str) -> dict[str, Any]:
    root = REPO / "data" / "archive" / season / "processed"
    players_path = root / "players.parquet"
    performances_path = root / "player_performances.parquet"
    players = pd.read_parquet(players_path, columns=["id", "position_id"])
    eligible = set(players.loc[players["position_id"].isin([1, 2, 3, 4]), "id"])
    rows = pd.read_parquet(
        performances_path,
        columns=["player_id", "gameweek_id", "fixture_id", "selected", "price"],
    )
    print(json.dumps({"season": season, "raw_rows": len(rows), "sample": rows.head(3).to_dict("records")}))
    rows = rows.loc[rows["player_id"].isin(eligible)]
    values = rows[["price", "selected"]].apply(pd.to_numeric, errors="coerce")
    groups = rows.groupby(["player_id", "gameweek_id"])
    sizes = groups.size()
    disagreement = groups[["price", "selected"]].nunique(dropna=False).gt(1).any(axis=1)
    gameweeks = pd.read_parquet(root / "gameweeks.parquet")
    return {
        "season": season,
        "population": "performance IDs with terminal metadata position 1-4; coverage only, not historical eligibility proof",
        "grain": "player_id,fixture_id,gameweek_id",
        "performance_sha256": hashlib.sha256(performances_path.read_bytes()).hexdigest(),
        "players_sha256": hashlib.sha256(players_path.read_bytes()).hexdigest(),
        "eligible_fixture_rows": len(rows),
        "represented_gws": rows["gameweek_id"].nunique(),
        "gw1_unique_players": rows.loc[rows["gameweek_id"].eq(1), "player_id"].nunique(),
        "duplicate_keys": rows.duplicated(["player_id", "fixture_id", "gameweek_id"]).sum(),
        "invalid_numeric_cells": values.isna().sum().sum(),
        "negative_price_or_ownership_cells": values.lt(0).sum().sum(),
        "multi_fixture_player_gws": sizes.gt(1).sum(),
        "player_gws_with_disagreeing_price_or_ownership": disagreement.sum(),
        "has_deadline_column": "deadline_time" in gameweeks.columns,
        "has_player_snapshots": (root / "player_snapshots.parquet").exists(),
        "has_price_history": (root / "price_history.parquet").exists(),
        "timing_status": "coverage verified; deadline ownership/price semantics not certified",
    }


def snapshot_probe(source: tuple[str, str]) -> dict[str, Any]:
    season, path = source
    commit = PINNED_COMMITS[season]
    url = f"https://raw.githubusercontent.com/Randdalf/fplcache/{commit}/{path}"
    try:
        request = Request(url, headers={"User-Agent": "FPL-data-provenance-probe"})
        with urlopen(request, timeout=25) as response:
            compressed = response.read()
        payload = json.loads(lzma.decompress(compressed))
        players = payload["elements"]
        print(json.dumps({"season": season, "source_sample": [{key: row.get(key) for key in FIELDS} for row in players[:3]]}))
        ids = [row.get("id") for row in players]
        return {
            "season": season,
            "source_url": url,
            "source_commit": commit,
            "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
            "raw_player_rows": len(players),
            "required_missing_rows": sum(any(row.get(key) is None for key in FIELDS) for row in players),
            "duplicate_ids": len(ids) - len(set(ids)),
            "invalid_ownership_rows": sum(not 0 <= float(row["selected_by_percent"]) <= 100 for row in players),
            "nonpositive_price_rows": sum(float(row["now_cost"]) <= 0 for row in players),
            "position_codes": json.dumps(sorted({row["element_type"] for row in players})),
            "gw1_deadline": next((row.get("deadline_time") for row in payload.get("events", []) if row.get("id") == 1), None),
            "timing_status": "content verified; recorded predeadline commit corroborated separately; freshness/eligibility admission pending",
        }
    except Exception as error:
        return {"season": season, "source_url": url, "error": str(error)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-samples", action="store_true", help="Fetch three public unsealed bootstrap samples in memory")
    args = parser.parse_args()
    write_csv("ownership_local_coverage.csv", [local_coverage(season) for season, _ in SOURCES])
    if args.fetch_samples:
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(snapshot_probe, SOURCES))
        write_csv("ownership_snapshot_samples.csv", results)
    print("Wrote ownership metadata audit companions; no forecasts, outcomes, or solver evaluation.")


if __name__ == "__main__":
    main()
