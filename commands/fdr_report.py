from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd
from tabulate import tabulate

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)
REQUIRED_FIXTURE_COLUMNS = {
    "gameweek_id",
    "home_club_id",
    "away_club_id",
}


def _number(value: object, default: float = 3.0) -> float:
    number = pd.to_numeric(value, errors="coerce")
    return default if pd.isna(number) else float(number)


def _club_names(clubs: pd.DataFrame | None) -> dict[int, str]:
    if clubs is None or clubs.empty:
        return {}

    id_column = "id" if "id" in clubs.columns else "club_id"
    if id_column not in clubs.columns:
        return {}

    names: dict[int, str] = {}
    for _, row in clubs.iterrows():
        club_id = pd.to_numeric(row[id_column], errors="coerce")
        if pd.isna(club_id):
            continue
        name = row.get("name")
        if pd.isna(name) or not str(name).strip():
            name = row.get("short_name")
        if pd.isna(name) or not str(name).strip():
            name = f"Club {int(club_id)}"
        names[int(club_id)] = str(name)
    return names


def _fixture_label(
    venue: str,
    difficulty: float,
    opponent_id: int,
    names: dict[int, str],
) -> str:
    difficulty_text = f"{difficulty:g}"
    opponent = names.get(opponent_id, f"Club {opponent_id}")
    direction = "vs" if venue == "H" else "@"
    return f"{venue}:{difficulty_text} {direction} {opponent}"


def _empty_report(gameweeks: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "club_id",
            "club",
            *(f"GW{gameweek}" for gameweek in gameweeks),
            "Average FDR",
            "Fixtures",
        ]
    )


def build_fdr_report(
    fixtures: pd.DataFrame,
    clubs: pd.DataFrame | None,
    start_gw: int,
    horizon: int,
    sort_by: str = "average",
) -> pd.DataFrame:
    """Build a club-by-gameweek FPL fixture difficulty report.

    Each gameweek cell contains one entry per fixture, preserving double
    gameweeks and marking home/away explicitly. Lower FDR is easier.
    """
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    if start_gw < 1:
        raise ValueError("start_gw must be at least 1")
    if sort_by not in {"average", "club"}:
        raise ValueError("sort_by must be 'average' or 'club'")

    missing = sorted(REQUIRED_FIXTURE_COLUMNS - set(fixtures.columns))
    if missing:
        raise ValueError(f"fixtures.parquet is missing columns: {', '.join(missing)}")

    gameweeks = list(range(start_gw, start_gw + horizon))
    report_columns = [f"GW{gameweek}" for gameweek in gameweeks]
    selected = fixtures.copy()
    selected["_fixture_order"] = range(len(selected))
    selected["_gameweek"] = pd.to_numeric(selected["gameweek_id"], errors="coerce")
    selected = selected.dropna(subset=["_gameweek", "home_club_id", "away_club_id"])
    selected["_gameweek"] = selected["_gameweek"].astype(int)
    selected = selected[selected["_gameweek"].isin(gameweeks)]
    if selected.empty:
        return _empty_report(gameweeks)

    names = _club_names(clubs)
    fixture_cells: dict[tuple[int, int], list[str]] = {}
    fixture_difficulties: dict[int, list[float]] = {}

    for _, fixture in selected.sort_values(["_gameweek", "_fixture_order"]).iterrows():
        gameweek = int(fixture["_gameweek"])
        home_id = int(fixture["home_club_id"])
        away_id = int(fixture["away_club_id"])
        home_difficulty = _number(fixture.get("team_h_difficulty"))
        away_difficulty = _number(fixture.get("team_a_difficulty"))

        for club_id, opponent_id, venue, difficulty in (
            (home_id, away_id, "H", home_difficulty),
            (away_id, home_id, "A", away_difficulty),
        ):
            fixture_cells.setdefault((club_id, gameweek), []).append(
                _fixture_label(venue, difficulty, opponent_id, names)
            )
            fixture_difficulties.setdefault(club_id, []).append(difficulty)

    rows: list[dict[str, object]] = []
    for club_id in sorted(fixture_difficulties):
        row: dict[str, object] = {
            "club_id": club_id,
            "club": names.get(club_id, f"Club {club_id}"),
        }
        for gameweek, column in zip(gameweeks, report_columns):
            row[column] = " | ".join(fixture_cells.get((club_id, gameweek), [])) or "—"
        difficulties = fixture_difficulties[club_id]
        row["Average FDR"] = sum(difficulties) / len(difficulties)
        row["Fixtures"] = len(difficulties)
        rows.append(row)

    report = pd.DataFrame(rows, columns=["club_id", "club", *report_columns, "Average FDR", "Fixtures"])
    if sort_by == "club":
        return report.sort_values(["club", "club_id"], kind="stable").reset_index(drop=True)
    return report.sort_values(["Average FDR", "club"], kind="stable").reset_index(drop=True)


def _default_start_gw(data_dir: Path, fixtures: pd.DataFrame) -> int:
    gameweeks_path = data_dir / "gameweeks.parquet"
    if gameweeks_path.exists():
        gameweeks = pd.read_parquet(gameweeks_path)
        if "id" in gameweeks.columns:
            if "is_next" in gameweeks.columns:
                next_gameweeks = gameweeks[gameweeks["is_next"].fillna(False)]
                if not next_gameweeks.empty:
                    return int(next_gameweeks.iloc[0]["id"])
            if "finished" in gameweeks.columns:
                unfinished = gameweeks[~gameweeks["finished"].fillna(False)]
                if not unfinished.empty:
                    return int(unfinished.iloc[0]["id"])

    values = pd.to_numeric(fixtures["gameweek_id"], errors="coerce").dropna()
    if values.empty:
        raise ValueError("could not determine start gameweek from gameweeks.parquet or fixtures.parquet")
    return int(values.min())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print fixture difficulty by club and gameweek.")
    parser.add_argument(
        "--data_dir",
        "--data-dir",
        dest="data_dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed",
        help="Processed data directory containing fixtures.parquet.",
    )
    parser.add_argument("--start_gw", "--start-gw", dest="start_gw", type=int)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--sort_by", "--sort-by", dest="sort_by", choices=["average", "club"], default="average")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path; defaults to data/reports/fdr_report.csv.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    data_dir = args.data_dir.resolve()
    fixtures_path = data_dir / "fixtures.parquet"
    if not fixtures_path.exists():
        raise SystemExit(f"Fixture data not found: {fixtures_path}")

    fixtures = pd.read_parquet(fixtures_path)
    clubs_path = data_dir / "clubs.parquet"
    clubs = pd.read_parquet(clubs_path) if clubs_path.exists() else None
    start_gw = args.start_gw if args.start_gw is not None else _default_start_gw(data_dir, fixtures)

    try:
        report = build_fdr_report(
            fixtures,
            clubs,
            start_gw=start_gw,
            horizon=args.horizon,
            sort_by=args.sort_by,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if report.empty:
        raise SystemExit(f"No fixtures found for GW{start_gw}-GW{start_gw + args.horizon - 1}.")

    print(f"FDR REPORT: GW{start_gw}-GW{start_gw + args.horizon - 1} (lower is easier)")
    print(tabulate(report.drop(columns=["club_id"]), headers="keys", tablefmt="grid", showindex=False))

    output = args.output or PROJECT_ROOT / "data" / "reports" / "fdr_report.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output, index=False)
    LOGGER.info("FDR report saved to %s", output)


if __name__ == "__main__":
    main()
