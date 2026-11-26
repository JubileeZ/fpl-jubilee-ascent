"""Replay sourced 2025–26 goalkeeper role decisions from fixed deadlines."""

from pathlib import Path
import json
from statistics import mean
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from features.builder import build_features, history_before_target  # noqa: E402
from models import get_model  # noqa: E402

ARCHIVE = ROOT / "data/archive/2025-26/processed"
MODELS = ("def_xg_shrink_challenger", "participation_state_hybrid")
# GW, incoming keeper, rival, evidence state, latest source date. Note links each case.
CASES = (
    (6, "Donnarumma", "Trafford", "fit_rival", "2025-09-21"),
    (6, "Darlow", "Perri", "injured_rival", "2025-09-26"),
    (7, "Areola", "Hermansen", "fit_rival", "2025-09-29"),
    (8, "Johnstone", "José Sá", "fit_rival", "2025-10-05"),
    (12, "A.Becker", "Mamardashvili", "expected_start", "2025-11-21"),
    (15, "Ramsdale", "Pope", "injured_rival", "2025-11-29"),
    (19, "Ramsdale", "Pope", "uncertain", "2025-12-29"),
)


def main() -> None:
    players = pd.read_parquet(ARCHIVE / "players.parquet").set_index("web_name")
    fixtures = pd.read_parquet(ARCHIVE / "fixtures.parquet")
    deadlines = pd.read_parquet(ARCHIVE / "gameweeks.parquet").set_index("id").deadline_time
    performances = pd.read_parquet(ARCHIVE / "player_performances.parquet")
    assert not performances.duplicated(["player_id", "fixture_id"]).any()
    assert performances.minutes.between(0, 90).all()
    assert performances.starts.isin([0, 1]).all()
    assert pd.to_datetime(performances.kickoff_time, utc=True, errors="coerce").notna().all()
    rows = []
    for gw in dict.fromkeys(case[0] for case in CASES):
        deadline = pd.Timestamp(deadlines.loc[gw])
        history = history_before_target(performances, gw, deadline, True)
        features = build_features(
            ARCHIVE, gw, horizon=4, seed_season="2024-25", as_of_gw=gw, target_deadline=deadline,
        )
        predictions = {}
        for name in MODELS:
            model = get_model(name)
            if hasattr(model, "fit"):
                model.fit(history)
            predictions[name] = model.predict(features, 4).set_index(["player_id", "fixture_id"])

        for _, incoming, rival, evidence, evidence_date in (case for case in CASES if case[0] == gw):
            assert pd.Timestamp(evidence_date, tz="UTC") < deadline.normalize()
            pair = players.loc[[incoming, rival]]
            assert pair.position_id.eq(1).all()
            club = int(pair.club_id.iloc[0])
            assert pair.club_id.eq(club).all()
            pids = pair.id.tolist()
            kickoffs = pd.to_datetime(fixtures.kickoff_time, utc=True)
            club_fixtures = fixtures.loc[fixtures.home_club_id.eq(club) | fixtures.away_club_id.eq(club)]
            past = club_fixtures.loc[kickoffs.lt(deadline)].sort_values("kickoff_time").id.tail(2)
            upcoming = club_fixtures.loc[kickoffs.gt(deadline)].sort_values("kickoff_time").id.head(3).tolist()
            assert len(upcoming) == 3
            if evidence in {"fit_rival", "injured_rival"}:
                prior_pair = history.loc[history.fixture_id.isin(past) & history.player_id.isin(pids)]
                assert prior_pair.groupby("player_id").starts.sum().reindex(pids).tolist() == [2, 0]

            keys = pd.MultiIndex.from_product([pids, upcoming], names=["player_id", "fixture_id"])
            realized = performances.set_index(["player_id", "fixture_id"]).loc[keys]
            actual = [realized.loc[pid].minutes.tolist() for pid in pids]
            starts = [realized.loc[pid].starts.tolist() for pid in pids]
            start_confirmed = evidence == "expected_start"
            extra_override = evidence == "fit_rival"
            for name, forecast in predictions.items():
                native = [forecast.loc[(pid, upcoming), "projected_minutes"].tolist() for pid in pids]
                current = [[90 if i == 0 else 0, *values[1:]] if start_confirmed else values
                           for i, values in enumerate(native)]
                proposed = [[90 if i == 0 else 0, *values[1:]] if extra_override else values
                            for i, values in enumerate(current)]
                sensitivity = [[75 if i == 0 else 15, *values[1:]] if extra_override else values
                               for i, values in enumerate(current)]
                rows.append({
                    "gw": gw, "incoming": incoming, "rival": rival, "evidence": evidence,
                    "model": name, "actual": actual, "starts": starts, "current": current,
                    "proposed": proposed, "sensitivity": sensitivity,
                    "extra_override": extra_override,
                    "false_override": extra_override and (starts[0][0], starts[1][0]) != (1, 0),
                })
    for row in rows:
        print(json.dumps(row, ensure_ascii=False, default=int), flush=True)
    for name in MODELS:
        model_rows = [row for row in rows if row["model"] == name]
        metrics = {}
        for arm in ("current", "proposed", "sensitivity"):
            metrics[arm] = {
                str(horizon): mean(
                    abs(predicted - actual) for row in model_rows for forecast, realized in
                    zip(row[arm], row["actual"], strict=True)
                    for predicted, actual in zip(forecast[:horizon], realized[:horizon], strict=True)
                )
                for horizon in (1, 3)
            }
        print(json.dumps({
            "model": name, "mae": metrics,
            "extra_overrides": sum(row["extra_override"] for row in model_rows),
            "false_overrides": sum(row["false_override"] for row in model_rows),
        }, default=int), flush=True)


if __name__ == "__main__":
    main()
