"""Compare a one-fixture outfield return override against archive forecasts."""

import json
from pathlib import Path
from statistics import median
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from commands.transfer_scouting import rank_market, recent_roles, review_queue  # noqa: E402
from features.builder import build_features, history_before_target  # noqa: E402
from models import get_model  # noqa: E402

ARCHIVE = ROOT / "data/archive/2025-26/processed"
SEED = ROOT / "data/archive/2024-25/processed"
MODELS = ("def_xg_shrink_challenger", "participation_state_hybrid")
# Deadline, FPL player, role-window endpoint, known unavailable GWs, evidence type, source date.
CASES = (
    (13, "Palmer", 5, (2, 3), "available", "2025-11-28"),
    (15, "Palmer", 5, (2, 3), "managed_start_ready", "2025-12-05"),
    (15, "M.Salah", 13, (), "selection_change", "2025-12-05"),
    (19, "Gabriel", 12, (), "appearance_after_injury", "2025-12-29"),
    (34, "Bruno G.", 26, (23, 24), "appearance_after_injury", "2026-04-23"),
)


def role_window(
    history: pd.DataFrame, seed: pd.DataFrame, pid: int, seed_pid: int, stop_gw: int,
    unavailable: tuple[int, ...],
) -> tuple[int, int, float]:
    current = history.loc[
        history.player_id.eq(pid) & history.gameweek_id.lt(stop_gw) & ~history.gameweek_id.isin(unavailable)
    ].sort_values("kickoff_time")
    earlier = seed.loc[seed.player_id.eq(seed_pid)].sort_values("kickoff_time")
    window = pd.concat([earlier.tail(max(0, 6 - len(current))), current]).tail(6)
    started = window.loc[window.starts.eq(1), "minutes"]
    return len(window), len(started), float(median(started)) if len(started) else 0.0


def main() -> None:
    players = pd.read_parquet(ARCHIVE / "players.parquet").set_index("id")
    seed_ids = pd.read_parquet(SEED / "players.parquet").set_index("code").id
    seed = pd.read_parquet(SEED / "player_performances.parquet")
    fixtures = pd.read_parquet(ARCHIVE / "fixtures.parquet")
    kickoffs = pd.to_datetime(fixtures.kickoff_time, utc=True)
    deadlines = pd.read_parquet(ARCHIVE / "gameweeks.parquet").set_index("id").deadline_time
    performance = pd.read_parquet(ARCHIVE / "player_performances.parquet")
    for frame in (performance, seed):
        assert not frame.duplicated(["player_id", "fixture_id"]).any()
        assert frame.minutes.between(0, 90).all()
        assert frame.starts.isin([0, 1]).all()
        assert pd.to_datetime(frame.kickoff_time, utc=True, errors="coerce").notna().all()
    outcomes = performance.set_index(["player_id", "fixture_id"])
    rows = []
    for gw in dict.fromkeys(case[0] for case in CASES):
        cases = [case for case in CASES if case[0] == gw]
        deadline = pd.Timestamp(deadlines.loc[gw])
        history = history_before_target(performance, gw, deadline, True)
        features = build_features(
            ARCHIVE, gw, horizon=4, seed_season="2024-25", as_of_gw=gw, target_deadline=deadline,
        )
        metadata = history.sort_values("kickoff_time").drop_duplicates("player_id", keep="last")
        metadata = metadata.merge(fixtures[["id", "home_club_id", "away_club_id"]], left_on="fixture_id", right_on="id")
        metadata = metadata.set_index("player_id")
        metadata["club_id"] = metadata.home_club_id.where(metadata.was_home, metadata.away_club_id)
        market_players = players.loc[metadata.index, ["web_name", "position_id"]].join(metadata[["club_id", "price"]])
        market_players = (
            market_players.rename(columns={"price": "now_cost"}).assign(status="a").rename_axis("id").reset_index()
        )
        pids = {name: int(players.index[players.web_name.eq(name)].item()) for _, name, *_ in cases}
        projections = {}
        for name in MODELS:
            model = get_model(name)
            if hasattr(model, "fit"):
                model.fit(history)
            projections[name] = model.predict(features, 4)

        champion = projections[MODELS[0]]
        empty_roles = recent_roles(history.iloc[:0], pd.Series(dtype=float), gw)
        market, role = rank_market(market_players, champion, champion, empty_roles, set(), gw)
        receipts = {pid: [{"detail": "Frozen historical availability evidence"}] for pid in pids.values()}
        queue = review_queue(market, role, receipts, position_quotas=True)
        shortlisted = {row["player_id"] for row in queue}
        assert len(shortlisted) == 30 and set(pids.values()) <= shortlisted

        for _, name, stop_gw, unavailable, evidence, source_date in cases:
            assert pd.Timestamp(source_date, tz="UTC") < deadline.normalize()
            pid = pids[name]
            club = int(metadata.loc[pid, "club_id"])
            previous_id = int(seed_ids.loc[players.loc[pid, "code"]])
            eligible, starts, fit_minutes = role_window(history, seed, pid, previous_id, stop_gw, unavailable)
            assert eligible == 6
            match_ids = fixtures.loc[
                (fixtures.home_club_id.eq(club) | fixtures.away_club_id.eq(club)) & kickoffs.gt(deadline)
            ].sort_values("kickoff_time").id.head(3).tolist()
            actual = outcomes.loc[(pid, match_ids), ["minutes", "starts"]].droplevel("player_id").loc[match_ids]
            assert len(actual) == 3 and fixtures.set_index("id").loc[match_ids[0], "gameweek_id"] == gw
            if evidence in {"managed_start_ready", "appearance_after_injury"}:
                assert history.loc[history.player_id.eq(pid)].sort_values("kickoff_time").iloc[-1].minutes > 0
            recovery_target = {"managed_start_ready": 60.0, "appearance_after_injury": 65.0}.get(evidence)
            override = min(fit_minutes, recovery_target) if starts >= 5 and recovery_target is not None else None
            for model_name, projection in projections.items():
                baseline = projection.loc[projection.player_id.eq(pid)].set_index("fixture_id").loc[
                    match_ids, "projected_minutes"
                ].tolist()
                proposed = baseline if override is None else [override, *baseline[1:]]
                rows.append({
                    "gameweek": gw, "player": name, "evidence": evidence, "model": model_name,
                    "fit_starts": starts, "eligible_fixtures": eligible, "healthy_reference": fit_minutes,
                    "override": override, "actual_minutes": actual.minutes.tolist(),
                    "actual_starts": actual.starts.tolist(), "baseline": baseline, "proposed": proposed,
                    "false_restoration": bool(override is not None and override > baseline[0] and actual.starts.iloc[0] == 0),
                })

    for row in rows:
        print(json.dumps(row, default=int))
    for name in MODELS:
        group = pd.DataFrame([row for row in rows if row["model"] == name])
        metrics = {}
        for arm in ("baseline", "proposed"):
            errors = (group[arm].apply(pd.Series) - group.actual_minutes.apply(pd.Series)).abs()
            metrics[arm] = {"next_fixture_mae": errors[0].mean(), "three_fixture_mae": errors.to_numpy().mean()}
        print(json.dumps({"model": name, "mae": metrics, "false_restorations": int(group.false_restoration.sum())}))


if __name__ == "__main__":
    main()
