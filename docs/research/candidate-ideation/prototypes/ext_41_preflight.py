"""Build and inventory deadline-bound source Champion inputs for EXT-41."""

from __future__ import annotations

import argparse
from concurrent.futures import Future, ProcessPoolExecutor
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

import pandas as pd

from backtesting.empirical_mirrors import extract_gw_df_from_merged_csv
from backtesting.forecast_export import REQUIRED_COMPONENTS, validate_components
from commands.run_stage_a_and_b import (
    _bootstrap_players_and_clubs,
    _prepare_filtered_seed,
)
from features.availability_snapshots import write_availability_snapshot
from historical_replay_inputs import (
    CONFIG_ROOT,
    REPO,
    _PERFORMANCE_NAMES,
    _checked_bytes,
)
from prototypes.ext_40.run import source_panel
from run_s1_replay import champion_factory, forecast
from s2_historical_replay_inputs import AMENDMENTS, _fixture_table
import s2_historical_replay_inputs


def _check_issue(
    source: Path,
    seed: Path,
    gw: int,
    deadline: str,
    source_season: str,
    examples: dict[str, pd.DataFrame],
) -> dict[str, object]:
    _, factory, _ = champion_factory()
    forecast(source, source, factory, seed, gw, deadline, season=source_season)
    parquet = source / "projections" / f"gw{gw:02d}.parquet"
    result = pd.read_parquet(parquet)
    validate_components(result, source_season)
    columns = ["player_id", "fixture_id"]
    issued = result.loc[
        result["gameweek_id"].eq(gw) & result["fixture_id"].ge(0),
        [*columns, *REQUIRED_COMPONENTS],
    ]
    coverage: dict[str, object] = {"forecast_sha256": sha256(parquet.read_bytes()).hexdigest()}
    for component, expected in examples.items():
        matched = expected.merge(issued, on=columns, validate="one_to_one")
        if len(matched) != len(expected):
            raise ValueError(f"Lost {component} source examples at GW{gw}")
        coverage[f"{component}_matched"] = len(matched)
    return coverage


def preflight(work: Path, pool: ProcessPoolExecutor) -> None:
    """Require a complete fixture-key join on the original EXT-40 source cohort."""
    source_season = "2024-25"
    source_path = CONFIG_ROOT / "dev_mirror_2024_25_manifest.json"
    manifest = json.loads(source_path.read_bytes())
    dev = json.loads((CONFIG_ROOT / "dev_mirror_2025_26_manifest.json").read_bytes())
    panel = source_panel(work, dev)
    source = work / "ext41_source"
    seed = _prepare_filtered_seed("2023-24", source / "seed")
    s2_historical_replay_inputs.MIRROR_ROOT = work / "mirror"
    amendments = pd.read_csv(AMENDMENTS)
    schema = pd.read_parquet(
        REPO / "data/archive" / source_season / "processed/player_performances.parquet"
    ).iloc[:0]
    # Archive supplies column types. Earlier source receipts supply every history value.
    publication: dict[int, datetime] = {}
    history_by_gw: dict[int, pd.DataFrame] = {}
    champion, _, model_digest = champion_factory()
    columns = ["player_id", "fixture_id"]
    inventory: list[dict[str, object]] = []
    pending: list[tuple[dict[str, object], Future[dict[str, object]]]] = []
    for origin in manifest["origins"]:
        gw = origin["gw"]
        deadline = datetime.fromisoformat(origin["deadline_utc"])
        examples = {
            component: frame.loc[frame["gameweek_id"].eq(gw), columns]
            for component, frame in panel.training.items()
        }
        eligible_weeks = [week for week, ready in publication.items() if ready < deadline]
        row: dict[str, object] = {
            "gameweek": gw,
            "deadline_utc": deadline.isoformat(),
            "published_prior_gameweeks": len(eligible_weeks),
            "fixture_status": origin["fixtures"]["status"],
            "champion": champion,
            "model_sha256": model_digest,
            "forecast_sha256": "",
        }
        for component, expected in examples.items():
            row[f"{component}_examples"] = len(expected)
            row[f"{component}_matched"] = 0
        if any(not expected.empty for expected in examples.values()):
            receipt = origin["bootstrap"]
            capture = datetime.fromisoformat(receipt["capture_upper_utc"])
            if receipt["status"] != "supported" or capture >= deadline:
                raise ValueError(f"Unusable source bootstrap at GW{gw}")
            path = work / "mirror" / receipt["local_relpath"]
            _checked_bytes(path, receipt["blob_sha256"])
            players, clubs = _bootstrap_players_and_clubs(path, capture_upper=capture)
            players = players[players["position_id"].between(1, 4)]
            fixtures = _fixture_table(origin, amendments)
            history = pd.concat([history_by_gw[week] for week in eligible_weeks])
            kickoff = pd.to_datetime(history["kickoff_time"], utc=True, errors="raise")
            history = history.loc[kickoff.lt(deadline)].copy()
            fixtures["finished"] |= fixtures["id"].isin(history["fixture_id"])
            staged = source / "verified_inputs" / f"gw{gw:02d}"
            staged.mkdir(parents=True, exist_ok=True)
            history.to_parquet(staged / "player_performances.parquet", index=False)
            players.to_parquet(staged / "market.parquet", index=False)
            availability = players[
                [
                    "id",
                    "club_id",
                    "position_id",
                    "now_cost",
                    "code",
                    "status",
                    "chance_of_playing_next_round",
                ]
            ]
            fixture_receipt = origin["fixtures"]
            caps = [capture, datetime.fromisoformat(fixture_receipt["commit_time_utc"])]
            notices = amendments.loc[amendments["origin_gw"].eq(gw), "announced_date"]
            caps.extend(datetime.fromisoformat(f"{day}T23:59:59+00:00") for day in notices)
            endpoint_sources = {
                "bootstrap_sha256": receipt["blob_sha256"],
                "fixtures_sha256": fixture_receipt["blob_sha256"],
                "amendments_sha256": sha256(AMENDMENTS.read_bytes()).hexdigest(),
                "history_sha256": sha256(
                    (staged / "player_performances.parquet").read_bytes()
                ).hexdigest(),
            }
            write_availability_snapshot(
                staged / "snapshots",
                source_season,
                gw,
                deadline,
                max(caps),
                availability,
                clubs,
                fixtures,
                endpoint_sources,
            )
            pending.append(
                (
                    row,
                    pool.submit(
                        _check_issue, source, seed, gw, deadline.isoformat(), source_season, examples
                    ),
                )
            )
        inventory.append(row)
        settled = origin["settled_outcomes"]
        if not settled["zero_diff_verified"] or settled["ledger_mismatch_rows"]:
            raise ValueError(f"Unverified source settlement at GW{gw}")
        raw = _checked_bytes(work / "mirror" / settled["local_relpath"], settled["blob_sha256"])
        history = extract_gw_df_from_merged_csv(raw, gw).rename(columns=_PERFORMANCE_NAMES)
        history = history.loc[history["minutes"].astype(str).ne(""), schema.columns].copy()
        history["was_home"] = history["was_home"].astype(str).str.lower().map(
            {"true": True, "false": False}
        )
        if history["was_home"].isna().any():
            raise ValueError(f"Invalid source home/away flag at GW{gw}")
        history_by_gw[gw] = history.drop_duplicates().astype(schema.dtypes.to_dict())
        publication[gw] = datetime.fromisoformat(settled["finalized_at_utc"])
    for row, check in pending:
        row.update(check.result())
    pd.DataFrame(inventory).to_csv(source / "coverage.csv", index=False, lineterminator="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        preflight(args.work.resolve(), pool)


if __name__ == "__main__":
    main()
