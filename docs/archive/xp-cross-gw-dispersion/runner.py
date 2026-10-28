"""Redo Cross-Gameweek Dispersion companions (walk-forward ~25 min + live horizon ~1 min)."""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from models import get_model
from features.builder import build_features, history_before_target, resolve_operational_processed_dir
from features.contracts import assert_projection_contract
from backtesting.process_points import aggregate_process_points
from solver.planning import resolve_default_target_gw, SEASON_END_GW

TOPIC = Path(__file__).resolve().parent
PROJECT_ROOT = TOPIC.parents[2]
CHAMPION = "calibrated_matchup_hybrid"


def _stats(frame: pd.DataFrame, col: str) -> tuple[float, float, float]:
    grouped = frame.groupby("player_id")[col]
    ordered = frame.sort_values(["player_id", "gameweek_id"])
    w2w = ordered.groupby("player_id")[col].apply(lambda s: s.diff().abs().mean()).mean()
    return float(grouped.std(ddof=1).mean()), float(grouped.std(ddof=1).median()), float(w2w)


def main() -> None:
    data_dir = PROJECT_ROOT / "data" / "archive" / "2025-26" / "processed"
    seed_dir = PROJECT_ROOT / "data" / "archive" / "2024-25" / "processed"
    model = get_model(CHAMPION)
    df_perf = pd.read_parquet(data_dir / "player_performances.parquet")
    posmap = pd.read_parquet(data_dir / "players.parquet")[["id", "position_id"]].rename(
        columns={"id": "player_id"}
    ).drop_duplicates("player_id")
    rows: list[pd.DataFrame] = []
    for gw in range(1, 39):
        df_feat = build_features(
            data_dir, target_gw=gw, horizon=1,
            seed_processed_dir=seed_dir, use_archive_seed=False, as_of_gw=gw,
        )
        if hasattr(model, "fit"):
            model.fit(history_before_target(df_perf, gw, None, False))
        df_proj = assert_projection_contract(model.predict(df_feat, horizon=1))
        gw_proj = (
            df_proj[df_proj.gameweek_id == gw]
            .groupby(["player_id", "gameweek_id"], as_index=False)[
                ["projected_points", "projected_minutes"]].sum()
        )
        rows.append(gw_proj)
        print(f"GW{gw} done n={len(gw_proj)}", flush=True)
    proj = pd.concat(rows, ignore_index=True)
    real = df_perf.groupby(["player_id", "gameweek_id"], as_index=False).agg(
        actual=("total_points", "sum"), minutes=("minutes", "sum"))
    proc = aggregate_process_points(df_perf.merge(posmap, on="player_id", how="left"))
    ev = real.merge(proc, on=["player_id", "gameweek_id"], how="left").merge(
        posmap, on="player_id", how="left")
    ev["process_points"] = ev["process_points"].fillna(0)
    ev["blended_points"] = 0.5 * (ev["actual"] + ev["process_points"])
    proj2 = proj.merge(posmap, on="player_id", how="left").merge(
        real[["player_id", "gameweek_id", "minutes"]], on=["player_id", "gameweek_id"], how="left")
    out: list[dict] = []
    for pool, f_ev, f_pr in [
        ("all", ev, proj2), ("min>0", ev[ev.minutes > 0], proj2[proj2.minutes > 0]),
        ("60+", ev[ev.minutes >= 60], proj2[proj2.minutes >= 60]),
    ]:
        for series, frame, col in [
            ("realized", f_ev, "actual"), ("process", f_ev, "process_points"),
            ("blend", f_ev, "blended_points"), ("xp", f_pr, "projected_points"),
        ]:
            mean_sd, med_sd, w2w = _stats(frame, col)
            out.append(dict(window="GW1-38 2025-26 walk-forward", pool=pool, series=series,
                            nplayers=int(frame["player_id"].nunique()),
                            mean_obs=round(float(frame.groupby("player_id").size().mean()), 1),
                            mean_SD=round(mean_sd, 3), median_SD=round(med_sd, 3),
                            mean_abs_w2w=round(w2w, 3)))
    posname = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
    ev60, pr60 = ev[ev.minutes >= 60], proj2[proj2.minutes >= 60]
    for pid, pname in posname.items():
        for series, frame, col in [
            ("realized", ev60[ev60.position_id == pid], "actual"),
            ("process", ev60[ev60.position_id == pid], "process_points"),
            ("blend", ev60[ev60.position_id == pid], "blended_points"),
            ("xp", pr60[pr60.position_id == pid], "projected_points"),
        ]:
            mean_sd, med_sd, w2w = _stats(frame, col)
            out.append(dict(window="GW1-38 2025-26 walk-forward", pool=f"60+_{pname}",
                            series=series, nplayers=int(frame["player_id"].nunique()),
                            mean_obs=round(float(frame.groupby("player_id").size().mean()), 1),
                            mean_SD=round(mean_sd, 3), median_SD=round(med_sd, 3),
                            mean_abs_w2w=round(w2w, 3)))
    live_dir = resolve_operational_processed_dir(PROJECT_ROOT)
    live_tg = resolve_default_target_gw(live_dir)
    live_season = live_dir.parent.name if live_dir.parent.name != "data" else "live"
    live_window = f"GW{live_tg}-{live_tg + 5} {live_season} live horizon"
    live_feat = build_features(live_dir, live_tg, horizon=6, history_before_gw=SEASON_END_GW + 1)
    live_perf = pd.read_parquet(live_dir / "player_performances.parquet")
    model.fit(live_perf[live_perf["gameweek_id"] < live_tg])
    live_proj = assert_projection_contract(model.predict(live_feat, 6))
    live_proj["xp_attack"] = live_proj.get("xp_goals", 0) + live_proj.get("xp_assists", 0)
    live_proj["xp_clean"] = live_proj.get("xp_clean_sheet", 0) + live_proj.get("xp_conceded", 0)
    live_g = live_proj.groupby(["player_id", "gameweek_id"], as_index=False)[
        ["projected_points", "xp_attack", "xp_clean"]].sum()
    mean_sd, med_sd, w2w = _stats(live_g, "projected_points")
    out.append(dict(window=live_window, pool="all", series="xp",
                    nplayers=int(live_g["player_id"].nunique()), mean_obs=6.0,
                    mean_SD=round(mean_sd, 3), median_SD=round(med_sd, 3),
                    mean_abs_w2w=round(w2w, 3)))
    pd.DataFrame(out).to_csv(TOPIC / "dispersion_summary.csv", index=False)
    comp_rows = []
    for pool_label, frame in [("all", live_g)]:
        for comp in ["projected_points", "xp_attack", "xp_clean"]:
            mean_sd, med_sd, _ = _stats(frame, comp)
            comp_rows.append(dict(window=live_window,
                                  pool=pool_label, component=comp,
                                  mean_SD=round(mean_sd, 4), median_SD=round(med_sd, 4)))
    live_pos = pd.read_parquet(live_dir / "players.parquet")[["id", "position_id"]].rename(
        columns={"id": "player_id"}).drop_duplicates("player_id")
    live_g2 = live_g.merge(live_pos, on="player_id", how="left")
    for pid, pname in [(2, "DEF"), (3, "MID"), (4, "FWD")]:
        sub = live_g2[live_g2.position_id == pid]
        for comp in ["projected_points", "xp_attack", "xp_clean"]:
            mean_sd, _, _ = _stats(sub, comp)
            comp_rows.append(dict(window=live_window,
                                  pool=pname, component=comp,
                                  mean_SD=round(mean_sd, 4), median_SD=""))
    pd.DataFrame(comp_rows).to_csv(TOPIC / "fixture_component_swing.csv", index=False)
    print("Wrote dispersion_summary.csv + fixture_component_swing.csv")


if __name__ == "__main__":
    main()
