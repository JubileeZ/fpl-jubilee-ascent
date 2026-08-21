"""Prior-Season Dual-Vector Seed from 2025/26 FPL expected_goals / expected_goals_conceded."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "data/archive/2025-26/processed"
LIVE_CLUBS = ROOT / "data/processed/clubs.parquet"
OUT_CSV = ROOT / "docs/archive/gw1-19-first-half-chip-path/prior_season_dual_vector_seed.csv"
PROMOTED = frozenset({"COV", "HUL", "IPS"})
STRENGTH_COLS = (
    "strength_attack_home",
    "strength_attack_away",
    "strength_defence_home",
    "strength_defence_away",
)


def _club_fixture_rates(perf: pd.DataFrame, fixtures: pd.DataFrame, clubs: pd.DataFrame) -> pd.DataFrame:
    """One row per club-fixture: attack = sum player xG; defence = one team xGC (not summed)."""
    xg = pd.to_numeric(perf["expected_goals"], errors="coerce").fillna(0.0)
    xgc = pd.to_numeric(perf["expected_goals_conceded"], errors="coerce").fillna(0.0)
    minutes = pd.to_numeric(perf["minutes"], errors="coerce").fillna(0.0)
    work = perf.assign(xg=xg, xgc=xgc, minutes=minutes)
    fx = fixtures.rename(columns={"id": "fixture_id"})[["fixture_id", "home_club_id", "away_club_id"]]
    work = work.merge(fx, on="fixture_id", how="inner")
    work["club_id"] = work["home_club_id"].where(work["was_home"], work["away_club_id"])

    attack = work.groupby(["fixture_id", "club_id", "was_home"], as_index=False)["xg"].sum()
    played = work[work["minutes"] > 0]
    if played.empty:
        played = work
    defence = played.groupby(["fixture_id", "club_id", "was_home"], as_index=False)["xgc"].max()
    rates = attack.merge(defence, on=["fixture_id", "club_id", "was_home"], how="left")
    rates["xgc"] = rates["xgc"].fillna(0.0)
    names = clubs.set_index("id")["short_name"]
    rates["club_short"] = rates["club_id"].map(names)
    return rates.dropna(subset=["club_short"])


def build_dual_vector_seed(
    archive_dir: Path = ARCHIVE,
    live_clubs_path: Path = LIVE_CLUBS,
    out_csv: Path = OUT_CSV,
) -> pd.DataFrame:
    perf = pd.read_parquet(archive_dir / "player_performances.parquet")
    fixtures = pd.read_parquet(archive_dir / "fixtures.parquet")
    archive_clubs = pd.read_parquet(archive_dir / "clubs.parquet")
    live = pd.read_parquet(live_clubs_path)

    rates = _club_fixture_rates(perf, fixtures, archive_clubs)
    home = rates[rates["was_home"]]
    away = rates[~rates["was_home"]]
    home_xg = float(home["xg"].mean()) if len(home) else 1.0
    away_xg = float(away["xg"].mean()) if len(away) else 1.0
    home_xgc = float(home["xgc"].mean()) if len(home) else 1.0
    away_xgc = float(away["xgc"].mean()) if len(away) else 1.0
    home_xg = home_xg if home_xg > 0 else 1.0
    away_xg = away_xg if away_xg > 0 else 1.0
    home_xgc = home_xgc if home_xgc > 0 else 1.0
    away_xgc = away_xgc if away_xgc > 0 else 1.0

    def _club_vec(short: str) -> dict[str, float]:
        if short in PROMOTED:
            return {
                "strength_attack_home": 1.0,
                "strength_attack_away": 1.0,
                "strength_defence_home": 1.0,
                "strength_defence_away": 1.0,
                "home_xg": home_xg,
                "away_xg": away_xg,
                "home_xgc": home_xgc,
                "away_xgc": away_xgc,
            }
        h = home[home["club_short"] == short]
        a = away[away["club_short"] == short]
        hxg = float(h["xg"].mean()) if len(h) else home_xg
        axg = float(a["xg"].mean()) if len(a) else away_xg
        hxgc = float(h["xgc"].mean()) if len(h) else home_xgc
        axgc = float(a["xgc"].mean()) if len(a) else away_xgc
        hxgc = hxgc if hxgc > 0 else home_xgc
        axgc = axgc if axgc > 0 else away_xgc
        return {
            "strength_attack_home": hxg / home_xg,
            "strength_attack_away": axg / away_xg,
            "strength_defence_home": home_xgc / hxgc,
            "strength_defence_away": away_xgc / axgc,
            "home_xg": hxg,
            "away_xg": axg,
            "home_xgc": hxgc,
            "away_xgc": axgc,
        }

    rows = []
    for _, club in live.iterrows():
        short = str(club["short_name"])
        vec = _club_vec(short)
        rows.append({
            "club_id": int(club["id"]),
            "club_short": short,
            "promoted": short in PROMOTED,
            "league_home_xg": home_xg,
            "league_away_xg": away_xg,
            "league_home_xgc": home_xgc,
            "league_away_xgc": away_xgc,
            **vec,
        })
    out = pd.DataFrame(rows)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False)
    return out


def apply_seed_to_clubs(df_clubs: pd.DataFrame, seed: pd.DataFrame) -> pd.DataFrame:
    """In-memory clubs copy with Prior-Season Dual-Vector Seed in API strength columns."""
    patched = df_clubs.copy()
    by_short = seed.set_index("club_short")
    for col in STRENGTH_COLS:
        patched[col] = patched["short_name"].map(by_short[col]).fillna(1.0)
    return patched


def load_seeded_clubs(live_clubs_path: Path = LIVE_CLUBS, seed_csv: Path = OUT_CSV) -> pd.DataFrame:
    """Live clubs parquet with Seed strength columns. Builds seed CSV if missing."""
    if not seed_csv.exists():
        build_dual_vector_seed(live_clubs_path=live_clubs_path, out_csv=seed_csv)
    seed = pd.read_csv(seed_csv)
    clubs = pd.read_parquet(live_clubs_path)
    return apply_seed_to_clubs(clubs, seed)


if __name__ == "__main__":
    df = build_dual_vector_seed()
    print(df.to_string(index=False))
