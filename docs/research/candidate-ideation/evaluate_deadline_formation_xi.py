from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from backtesting.decision_regret import LineupDecision, PlayerOutcome, resolve_autosubs
from backtesting.metrics import select_squad_and_formation_xi
from run_deadline_research import ARCHIVE, ISSUES, VARIANTS, load_staged

CHAMPION = "def_xg_shrink_challenger"
KEYS = ["player_id", "gameweek_id", "fixture_id"]


def lineup(
    market: pd.DataFrame, projections: pd.DataFrame, settled: pd.DataFrame, gw: int
) -> dict[str, int | tuple[int, ...]]:
    active = projections[projections["gameweek_id"].eq(gw)]
    counts = (
        active.groupby("player_id")["projected_points"].sum().rename("projected_points")
    )
    available = market.loc[
        market["purchase_eligible"], ["player_id", "position_id", "club_id", "now_cost"]
    ]
    candidates = available.join(counts, on="player_id", validate="one_to_one")
    if candidates["projected_points"].isna().any():
        raise ValueError("Projection missing for issued market")
    start, bench = select_squad_and_formation_xi(candidates)
    squad = pd.concat([start, bench])
    if (
        len(start) != 11
        or len(bench) != 4
        or not squad["player_id"].is_unique
        or squad["now_cost"].sum() > 1000
        or squad["club_id"].value_counts().max() > 3
        or squad["position_id"].value_counts().to_dict() != {1: 2, 2: 5, 3: 5, 4: 3}
    ):
        raise ValueError(f"Illegal squad at GW{gw}")
    scoring = squad.merge(
        settled, on="player_id", how="left", validate="one_to_one"
    ).fillna({"total_points": 0, "minutes": 0})
    starters, reserves = (
        tuple(int(pid) for pid in table["player_id"]) for table in (start, bench)
    )
    outcomes = {
        int(row.player_id): PlayerOutcome(
            int(row.player_id),
            int(row.position_id),
            float(row.total_points),
            float(row.minutes),
        )
        for row in scoring.itertuples(index=False)
    }
    choice = LineupDecision(starters, reserves, starters[0], starters[1])
    final = resolve_autosubs(choice, outcomes)
    return {
        "credited_xi_points": int(sum(outcomes[pid].points for pid in final)),
        "defender_starts": int(start["position_id"].eq(2).sum()),
        "starting_ids": starters,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    load_staged(work)
    screen = work / "ext38-diagnostic"
    identity = (screen / "diagnostic_identity.txt").read_text().strip()
    source = {CHAMPION: work / "diagnostic_forecasts" / CHAMPION / "projections"}
    source.update({name: screen / identity / name / "projections" for name in VARIANTS})
    labels = pd.read_parquet(
        ARCHIVE / "player_performances.parquet",
        columns=KEYS + ["total_points", "minutes"],
    )
    if labels.duplicated(KEYS).any():
        raise ValueError("Duplicate finalized fixture rows")
    rows = []
    for gw in ISSUES:
        tables = {
            name: pd.read_parquet(path / f"gw{gw:02d}.parquet")
            for name, path in source.items()
        }
        market = pd.read_parquet(
            work / "verified_inputs" / f"gw{gw:02d}" / "market.parquet"
        )
        settled = (
            labels[labels["gameweek_id"].eq(gw)]
            .groupby("player_id", as_index=False)[["total_points", "minutes"]]
            .sum()
        )
        baseline = tables[CHAMPION]
        common = baseline.loc[
            baseline["fixture_id"].ge(0) & baseline["projected_minutes"].gt(0), KEYS
        ].merge(labels, on=KEYS, validate="one_to_one")
        champion_lineup = lineup(market, baseline, settled, gw)
        for name, projections in tables.items():
            evaluations = common.merge(projections, on=KEYS, validate="one_to_one")
            if len(evaluations) != len(common):
                raise ValueError("Forecast arms differ in matched fixture coverage")
            errors = evaluations["projected_points"] - evaluations["total_points"]
            result = (
                champion_lineup
                if name == CHAMPION
                else lineup(market, projections, settled, gw)
            )
            rows.append(
                {
                    "gameweek": gw,
                    "model": name,
                    "rows": len(errors),
                    "sse": float(np.square(errors).sum()),
                    "error_sum": float(errors.sum()),
                    "credited_xi_points": result["credited_xi_points"],
                    "defender_starts": result["defender_starts"],
                    "xi_differs_from_champion": int(
                        set(result["starting_ids"])
                        != set(champion_lineup["starting_ids"])
                    ),
                }
            )
        print(f"Forecast and legal XI comparison GW{gw}", flush=True)
    comparison = pd.DataFrame(rows)
    comparison.to_csv(work / "ext38_forecast_xi_by_issue.csv", index=False)
    summary = comparison.drop(columns="gameweek").groupby("model").sum()
    summary["fixture_points_mse"] = summary["sse"] / summary["rows"]
    summary["fixture_points_bias"] = summary["error_sum"] / summary["rows"]
    summary.reset_index().to_csv(work / "ext38_forecast_xi_summary.csv", index=False)
    print(summary.to_string())


if __name__ == "__main__":
    main()
