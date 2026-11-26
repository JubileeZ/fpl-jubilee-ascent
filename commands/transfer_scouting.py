"""Generate a live market review queue from local planner inputs."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any
from urllib.parse import urlparse

import pandas as pd

from features.builder import build_features, load_fit_history
from features.contracts import assert_projection_contract
from features.injury_triage import select_scouting_targets, synthesize_xmins_override
from models import get_model, resolve_model_or_champion
from solver.planning import MAX_PLANNING_HORIZON, resolve_default_target_gw

ROOT = Path(__file__).resolve().parents[1]
QUOTAS = {1: 4, 2: 10, 3: 10, 4: 6}
POSITIONS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
KINDS = {"new_signing", "replacement", "return", "rotation"}
MINIMUM_GAP = 15


def load_events(path: Path | None, as_of: pd.Timestamp, gw: int, horizon: int) -> dict[int, list[dict[str, Any]]]:
    """Accept dated scouting receipts that were public by the run/deadline cutoff."""
    events: dict[int, list[dict[str, Any]]] = {}
    if path is None:
        return events
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Role evidence must be a JSON list")
    for record in records:
        pid, kind = record["player_id"], record["kind"]
        published = pd.Timestamp(record["published_at"])
        source = urlparse(record["source"])
        start, end = record["first_gw"], record["last_gw"]
        note = record["detail"]
        if (type(pid) is not int or pid <= 0 or kind not in KINDS or source.scheme != "https" or not source.hostname
                or pd.isna(published) or published.tzinfo is None or type(start) is not int or type(end) is not int
                or not 1 <= start <= end <= 38 or not isinstance(note, str) or not note.strip()):
            raise ValueError(f"Invalid role receipt for player {pid}")
        if published <= as_of and start < gw + horizon and end >= gw:
            events.setdefault(pid, []).append(record)
    return events


def recent_roles(history: pd.DataFrame, baseline: pd.Series, gw: int) -> pd.DataFrame:
    """Find recent changes in starts with a plausible minutes difference."""
    rows = []
    if not history.empty:
        ordered = history.sort_values(["gameweek_id", "kickoff_time", "fixture_id"])
        for pid, games in ordered.groupby("player_id"):
            recent, prior = games.tail(2), games.iloc[:-2].tail(4)
            last = recent.iloc[-1]
            if prior.empty or gw - int(last.gameweek_id) > 2 or pid not in baseline:
                continue
            starts = recent["starts"].gt(0)
            recent_mins, prior_mins = recent["minutes"].mean(), prior["minutes"].mean()
            base = float(baseline[pid])
            if last["starts"] > 0 and recent_mins >= prior_mins + MINIMUM_GAP:
                target = min(85.0, float(recent.loc[starts, "minutes"].median()))
                direction = "more_minutes"
            elif not starts.any() and prior["starts"].gt(0).sum() >= 2 and prior_mins >= recent_mins + 20:
                target = max(5.0, float(recent_mins))
                direction = "fewer_minutes"
            else:
                continue
            signed_gap = target - base if direction == "more_minutes" else base - target
            if signed_gap >= MINIMUM_GAP:
                rows.append((int(pid), direction, target, int(starts.sum()), float(recent_mins), float(prior_mins)))
    return pd.DataFrame(rows, columns=["id", "signal", "target", "recent_starts", "recent_minutes", "prior_minutes"]).set_index("id")


def rank_market(
    players: pd.DataFrame, base: pd.DataFrame, upside: pd.DataFrame, roles: pd.DataFrame,
    excluded: set[int], gw: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    def summarize(frame: pd.DataFrame) -> pd.DataFrame:
        return frame.assign(
            short=frame["projected_points"].where(frame["gameweek_id"].lt(gw + 3), 0),
            next_gw=frame["projected_points"].where(frame["gameweek_id"].eq(gw), 0),
            next_minutes=frame["projected_minutes"].where(frame["gameweek_id"].eq(gw), 0),
        ).groupby("player_id")[["projected_points", "short", "next_gw", "next_minutes"]].sum()

    meta = players[~players["id"].isin(excluded) & ~players["status"].isin(("u", "n"))].set_index("id")
    market = meta.join(summarize(base), how="inner")
    market["band"] = market["now_cost"] // 15
    market["rank"] = market.groupby(["position_id", "band"])[["next_gw", "short", "projected_points"]].rank(
        ascending=False, method="min",
    ).min(axis=1)
    market["value"] = market["projected_points"] / market["now_cost"]
    market = market.sort_values(["rank", "value", "next_gw"], ascending=[True, False, False], kind="stable")
    role = roles.join(market[["rank", "short", "now_cost"]], how="inner")
    role["scenario_points_delta"] = summarize(upside)["short"].reindex(role.index) - role["short"]
    role["impact"] = role["scenario_points_delta"].abs()
    role = role.sort_values(["impact", "rank", "now_cost"], ascending=[False, True, True], kind="stable")
    return market, role


def review_queue(
    market: pd.DataFrame, roles: pd.DataFrame, events: dict[int, list[dict[str, Any]]], *,
    position_quotas: bool,
) -> list[dict[str, Any]]:
    rows = []
    groups = QUOTAS.items() if position_quotas else [(None, 18)]
    for position, budget in groups:
        pool = market[market["position_id"].eq(position)] if position is not None else market
        points = list(pool.index[pool["projected_points"].gt(0)])
        # Sources may justify a review even if a player currently projects for zero points.
        evidence = [int(pid) for pid in pool.index if pid in events]
        timely = [int(pid) for pid in roles.index if pid in pool.index]
        role_ids = list(dict.fromkeys([*evidence, *timely]))[:budget // 2]
        for pid in list(dict.fromkeys([*role_ids, *points]))[:budget]:
            item = pool.loc[pid]
            role = roles.loc[pid] if pid in roles.index else None
            rows.append({
                "player_id": int(pid), "player": item.web_name, "position": POSITIONS[int(item.position_id)],
                "club_id": int(item.club_id), "price": int(item.now_cost) / 10, "status": item.status,
                "next_xmins": round(float(item.next_minutes), 2), "next_xpts": round(float(item.next_gw), 3),
                "three_gw_xpts": round(float(item.short), 3), "horizon_xpts": round(float(item.projected_points), 3),
                "reason": "role_evidence" if pid in evidence else "recent_role" if pid in role_ids else "points",
                "role_signal": None if role is None else str(role.signal),
                "scenario_minutes_per_fixture": None if role is None else float(role.target),
                "scenario_three_gw_xpts_delta": None if role is None else round(float(role.scenario_points_delta), 3),
                "evidence": events.get(pid, []),
            })
    return rows


def build_shortlists(
    processed: Path, gw: int, horizon: int, model_name: str, base_csv: Path | None,
    event_file: Path | None, shadow: bool,
) -> dict[str, Any]:
    players = pd.read_parquet(processed / "players.parquet").sort_values("id")
    picks = pd.read_parquet(processed / "user_picks.parquet")
    owned = set(picks["player_id"].astype(int))
    if len(owned) != 15:
        raise ValueError("Expected 15 distinct current squad players")
    deadlines = pd.read_parquet(processed / "gameweeks.parquet").set_index("id")["deadline_time"]
    deadline = pd.Timestamp(deadlines.loc[gw])
    now = pd.Timestamp(datetime.now(UTC))
    if deadline <= now:
        raise ValueError(f"GW{gw} deadline is locked")
    start = perf_counter()
    events = load_events(event_file, now, gw, horizon)
    triage = select_scouting_targets(processed, owned, target_gw=gw, horizon=horizon, base_csv_path=base_csv,
                                     reference_date=deadline.date())
    excluded = owned | {p["id"] for group in triage["market_flagged_by_tier"].values() for p in group}
    scratch_root = ROOT / ".tmp" / "agent"
    scratch_root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="scouting-", dir=scratch_root) as scratch:
        override = synthesize_xmins_override(processed, gw, horizon, base_csv_path=base_csv,
                                             output_path=Path(scratch) / "guard.csv", reference_date=deadline.date())
        features = build_features(processed, gw, horizon=horizon, history_before_gw=39, xmins_override=override)
        history = load_fit_history(processed, gw)
        if history is None:
            raise ValueError("Missing completed player performance data")
        history = history[history["gameweek_id"].lt(gw)]
        model = get_model(model_name)
        if hasattr(model, "fit"):
            model.fit(history)
        base = assert_projection_contract(model.predict(features, horizon))
        next_fixtures = base[base["gameweek_id"].eq(gw) & base["fixture_id"].ge(0)]
        baseline = next_fixtures.groupby("player_id")["projected_minutes"].mean()
        available = set(players.loc[
            players["status"].eq("a") & players["chance_of_playing_next_round"].fillna(100).ge(100), "id",
        ])
        roles = recent_roles(history[history["player_id"].isin(available - excluded)], baseline, gw)
        upside = base
        if not roles.empty:
            mask = features["player_id"].isin(roles.index) & features["fixture_id"].ge(0) & features["gameweek_id"].lt(gw + 2)
            adjusted = features.copy()
            current = base.set_index(["player_id", "gameweek_id", "fixture_id"])["projected_minutes"]
            scope = adjusted.loc[mask, ["player_id", "gameweek_id", "fixture_id"]]
            original = current.reindex(pd.MultiIndex.from_frame(scope)).to_numpy()
            target = scope["player_id"].map(roles["target"]).to_numpy()
            weight = scope["gameweek_id"].map({gw: 1.0, gw + 1: 0.5}).to_numpy()
            adjusted.loc[mask, "external_xmins"] = original + (target - original) * weight
            upside = assert_projection_contract(model.predict(adjusted, horizon))
    market, role = rank_market(players, base, upside, roles, excluded, gw)
    candidate = review_queue(market, role, events, position_quotas=True)
    report = {"target_gw": gw, "deadline_utc": deadline.isoformat(), "evaluated_at_utc": now.isoformat(),
              "model": model_name, "horizon": horizon, "quotas": {POSITIONS[p]: n for p, n in QUOTAS.items()},
              "excluded_from_extra_review": len(excluded), "external_minutes": base_csv is not None,
              "queue_seconds": round(perf_counter() - start, 3), "candidate": candidate}
    if shadow:
        comparator = review_queue(market, role, {}, position_quotas=False)
        candidate_ids = {p["player_id"] for p in candidate}
        comparator_ids = {p["player_id"] for p in comparator}
        report["shadow"] = {"baseline": comparator, "overlap": sorted(candidate_ids & comparator_ids),
                            "candidate_only": sorted(candidate_ids - comparator_ids),
                            "baseline_only": sorted(comparator_ids - candidate_ids)}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path)
    parser.add_argument("--target-gw", type=int)
    parser.add_argument("--horizon", type=int, default=10)
    parser.add_argument("--model")
    parser.add_argument("--base-csv", type=Path)
    parser.add_argument("--role-evidence", type=Path)
    parser.add_argument("--shadow", action="store_true")
    args = parser.parse_args()
    processed = args.processed_dir or ROOT / "data" / "processed"
    gw = args.target_gw if args.target_gw is not None else resolve_default_target_gw(processed)
    if not 1 <= gw <= 38 or not 1 <= args.horizon <= MAX_PLANNING_HORIZON:
        parser.error("Invalid target Gameweek or planning horizon")
    horizon = min(args.horizon, 39 - gw)
    result = build_shortlists(processed, gw, horizon, resolve_model_or_champion(args.model),
                              args.base_csv, args.role_evidence, args.shadow)
    print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))


if __name__ == "__main__":
    main()
