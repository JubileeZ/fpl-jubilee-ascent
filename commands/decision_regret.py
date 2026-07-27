"""Evaluate one-Gameweek lineup decisions against legal hindsight."""

import argparse
import asyncio
import logging
from pathlib import Path

import httpx
import pandas as pd

from backtesting.decision_regret import (
    LineupDecision,
    PlayerOutcome,
    evaluate_decision_regret,
    optimize_model_lineup,
)
from clients.env_loader import configure_utf8_stdio, load_env
from clients.fpl_api import fetch_gameweek_picks
from features.builder import build_features
from models import get_model

load_env()
configure_utf8_stdio()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)


def _actual_decision(picks: list[dict[str, object]]) -> LineupDecision:
    ordered = sorted(picks, key=lambda pick: int(pick.get("position", 99)))
    starters = tuple(int(pick["element"]) for pick in ordered if int(pick.get("position", 99)) <= 11)
    bench = tuple(int(pick["element"]) for pick in ordered if int(pick.get("position", 99)) > 11)
    if len(starters) != 11 or len(bench) != 4:
        raise ValueError("FPL picks response must contain 11 starters and 4 bench players")
    captain = next(
        (
            int(pick["element"])
            for pick in ordered
            if pick.get("is_captain") or pick.get("multiplier") == 2
        ),
        None,
    )
    vice_captain = next(
        (
            int(pick["element"])
            for pick in ordered
            if pick.get("is_vice_captain")
            or (
                int(pick["element"]) != captain
                and pick.get("multiplier") == 0
            )
        ),
        None,
    )
    if (
        captain is None
        or vice_captain is None
        or captain not in starters
        or vice_captain not in starters
        or captain == vice_captain
    ):
        raise ValueError("FPL picks response must identify captain and vice-captain")
    return LineupDecision(starters, bench, captain, vice_captain)


def _actual_outcomes(
    performances: pd.DataFrame,
    positions: pd.Series,
    gameweek: int,
) -> dict[int, PlayerOutcome]:
    rows = performances[performances["gameweek_id"] == gameweek].copy()
    if rows.empty:
        return {}
    grouped = rows.groupby("player_id", as_index=False)[["total_points", "minutes"]].sum()
    return {
        int(row["player_id"]): PlayerOutcome(
            int(row["player_id"]),
            int(positions.get(row["player_id"], 0)),
            float(row["total_points"]),
            float(row["minutes"]),
        )
        for _, row in grouped.iterrows()
    }


def _projected_outcomes(
    projections: pd.DataFrame,
    positions: pd.Series,
    gameweek: int,
) -> dict[int, PlayerOutcome]:
    rows = projections[projections["gameweek_id"] == gameweek]
    grouped = rows.groupby("player_id", as_index=False)[["projected_points", "projected_minutes"]].sum()
    return {
        int(row["player_id"]): PlayerOutcome(
            int(row["player_id"]),
            int(positions.get(row["player_id"], 0)),
            float(row["projected_points"]),
            float(row["projected_minutes"]),
        )
        for _, row in grouped.iterrows()
    }


async def evaluate(
    entry_id: int,
    model_name: str,
    data_dir: Path,
    start_gw: int,
    end_gw: int,
    snapshot_root: Path | None = None,
    season: str | None = None,
) -> pd.DataFrame:
    performances = pd.read_parquet(data_dir / "player_performances.parquet")
    model = get_model(model_name)
    reports: list[dict[str, object]] = []
    gameweek_deadlines: dict[int, object] = {}
    gameweeks_path = data_dir / "gameweeks.parquet"
    if snapshot_root is not None and gameweeks_path.exists():
        gameweeks = pd.read_parquet(gameweeks_path)
        if {"id", "deadline_time"}.issubset(gameweeks.columns):
            gameweek_deadlines = gameweeks.set_index("id")["deadline_time"].to_dict()
    async with httpx.AsyncClient(timeout=30.0) as client:
        for gameweek in range(start_gw, end_gw + 1):
            picks_response = await fetch_gameweek_picks(
                client,
                entry_id,
                gameweek,
                write_cache=False,
            )
            picks = picks_response.get("picks", [])
            actual_decision = _actual_decision(picks)
            squad = actual_decision.starters + actual_decision.bench
            features = build_features(
                data_dir,
                target_gw=gameweek,
                horizon=1,
                use_archive_seed=False,
                as_of_gw=gameweek,
                availability_snapshot_root=snapshot_root,
                season=season,
                target_deadline=gameweek_deadlines.get(gameweek),
            )
            if hasattr(model, "fit"):
                model.fit(performances[performances["gameweek_id"] < gameweek])
            projections = model.predict(features, horizon=1)
            positions = features.drop_duplicates("player_id").set_index("player_id")["position_id"]
            actual_outcomes = _actual_outcomes(performances, positions, gameweek)
            projected_outcomes = _projected_outcomes(projections, positions, gameweek)
            squad_outcomes = {
                player_id: actual_outcomes.get(
                    player_id,
                    PlayerOutcome(
                        player_id,
                        int(positions.get(player_id, 0)),
                        0.0,
                        0.0,
                    ),
                )
                for player_id in squad
            }
            squad_projections = {
                player_id: projected_outcomes.get(
                    player_id,
                    PlayerOutcome(
                        player_id,
                        squad_outcomes[player_id].position_id,
                        0.0,
                        0.0,
                    ),
                )
                for player_id in squad
            }
            model_decision = optimize_model_lineup(squad, squad_projections)
            report = evaluate_decision_regret(
                actual_decision,
                model_decision,
                squad,
                squad_outcomes,
            )
            reports.append({
                "gameweek": gameweek,
                **{
                    key: value
                    for key, value in report.items()
                    if isinstance(value, (int, float))
                },
            })
    return pd.DataFrame(reports)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry_id", type=int, required=True)
    parser.add_argument("--model", default="participation_state_hybrid")
    parser.add_argument("--gw_range", default="1-38")
    parser.add_argument("--data_dir", default="data/processed")
    parser.add_argument("--snapshot_root", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--output", default="data/reports/decision_regret.csv")
    args = parser.parse_args()
    start_gw, end_gw = (int(value) for value in args.gw_range.split("-"))
    result = asyncio.run(
        evaluate(
            entry_id=args.entry_id,
            model_name=args.model,
            data_dir=(PROJECT_ROOT / args.data_dir).resolve(),
            start_gw=start_gw,
            end_gw=end_gw,
            snapshot_root=Path(args.snapshot_root).resolve() if args.snapshot_root else None,
            season=args.season,
        )
    )
    output = (PROJECT_ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    print(result.to_string(index=False))
    if not result.empty:
        print(
            f"\nMean lift over actual: {result['model_lift'].mean():+.2f} | "
            f"Mean regret versus oracle: {result['model_regret'].mean():.2f}"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    main()
