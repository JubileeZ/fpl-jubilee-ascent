from datetime import date
from pathlib import Path
import pandas as pd

from features.injury_triage import (
    parse_fpl_return_date,
    build_broad_pool_shield,
    select_scouting_targets,
    synthesize_xmins_override,
)
from features.builder import resolve_operational_processed_dir


def test_parse_fpl_return_date():
    ref = date(2026, 10, 20)
    # Expected back DD Mon
    d1 = parse_fpl_return_date("Hamstring injury - Expected back 31 Oct", ref)
    assert d1 == date(2026, 10, 31)

    # Suspended until DD Mon
    d2 = parse_fpl_return_date("Suspended until 7 Nov", ref)
    assert d2 == date(2026, 11, 7)

    # Next year rollover (e.g. Jan return from Oct)
    d3 = parse_fpl_return_date("Hamstring injury - Expected back 2 Jan", ref)
    assert d3 == date(2027, 1, 2)

    # Unknown return date
    d4 = parse_fpl_return_date("Knee injury - Unknown return date", ref)
    assert d4 is None

    # Chance string without date
    d5 = parse_fpl_return_date("Thigh injury - 50% chance of playing", ref)
    assert d5 is None


def test_build_broad_pool_shield(tmp_path: Path):
    # Pass deterministic reference date before GW8 (e.g. 20 Oct 2026)
    ref = date(2026, 10, 20)

    # Hermetic synthetic fixture & player records
    df_players = pd.DataFrame([
        {
            "id": 63,
            "web_name": "Milosavljević",
            "club_id": 1,
            "position_id": 3,
            "now_cost": 60,
            "status": "i",
            "chance_of_playing_next_round": 0.0,
            "news": "Thigh injury - Expected back 31 Oct",
        },
        {
            "id": 516,
            "web_name": "Bentancur",
            "club_id": 2,
            "position_id": 3,
            "now_cost": 60,
            "status": "s",
            "chance_of_playing_next_round": 0.0,
            "news": "Suspended until 7 Nov",
        },
        {
            "id": 12,
            "web_name": "Saka",
            "club_id": 1,
            "position_id": 3,
            "now_cost": 100,
            "status": "i",
            "chance_of_playing_next_round": 0.0,
            "news": "Thigh injury - Unknown return date",
        },
    ])
    df_players.to_parquet(tmp_path / "players.parquet")

    df_fixtures = pd.DataFrame([
        {"id": 1, "gameweek_id": 8, "home_club_id": 1, "away_club_id": 3, "kickoff_time": "2026-10-24T14:00:00Z"},
        {"id": 2, "gameweek_id": 8, "home_club_id": 2, "away_club_id": 4, "kickoff_time": "2026-10-24T16:30:00Z"},
        {"id": 3, "gameweek_id": 9, "home_club_id": 1, "away_club_id": 4, "kickoff_time": "2026-10-31T14:00:00Z"},
        {"id": 4, "gameweek_id": 9, "home_club_id": 2, "away_club_id": 3, "kickoff_time": "2026-10-31T16:30:00Z"},
        {"id": 5, "gameweek_id": 10, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2026-11-07T14:00:00Z"},
        {"id": 6, "gameweek_id": 11, "home_club_id": 3, "away_club_id": 1, "kickoff_time": "2026-11-14T14:00:00Z"},
        {"id": 7, "gameweek_id": 11, "home_club_id": 4, "away_club_id": 2, "kickoff_time": "2026-11-14T16:30:00Z"},
    ])
    df_fixtures.to_parquet(tmp_path / "fixtures.parquet")

    shield = build_broad_pool_shield(tmp_path, target_gw=8, horizon=4, reference_date=ref)

    # Milosavljević (ID 63) is injured until 31 Oct (GW9 fixture is 31 Oct)
    # GW8: 0.0 (injured)
    # GW9: 20.0 (cameo on return GW)
    # GW10: 65.0 (managed start)
    # GW11: healthy baseline >= 60.0
    assert shield.get((63, 8)) == 0.0
    assert shield.get((63, 9)) == 20.0
    assert shield.get((63, 10)) == 65.0
    assert shield.get((63, 11)) is not None and shield[(63, 11)] >= 60.0

    # Bentancur (ID 516) is suspended until 7 Nov (GW10 match is 7 Nov)
    # Suspensions restore match-fit directly on return_gw without injury cameo ramp:
    # GW8: 0.0
    # GW9: 0.0
    # GW10: healthy baseline >= 60.0
    # GW11: healthy baseline >= 60.0
    assert shield.get((516, 8)) == 0.0
    assert shield.get((516, 9)) == 0.0
    assert shield.get((516, 10)) is not None and shield[(516, 10)] >= 60.0
    assert shield.get((516, 11)) is not None and shield[(516, 11)] >= 60.0

    # Unknown return date + status 'i' (Saka ID 12)
    # Zeroed out across the entire planning horizon
    assert shield.get((12, 8)) == 0.0
    assert shield.get((12, 9)) == 0.0
    assert shield.get((12, 10)) == 0.0
    assert shield.get((12, 11)) == 0.0


def test_select_scouting_targets():
    proc = resolve_operational_processed_dir(Path("."))
    squad_ids = {12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15}
    targets = select_scouting_targets(proc, user_squad_ids=squad_ids, top_per_tier=2)

    squad_flagged = targets["squad_flagged"]
    assert any(p["id"] == 12 for p in squad_flagged)

    market_tiers = targets["market_flagged_by_tier"]
    assert "DEF_budget" in market_tiers
    assert len(market_tiers["DEF_budget"]) > 0
    for p in market_tiers["DEF_budget"]:
        assert p["price"] <= 4.5


def test_synthesize_xmins_override_cascade_precedence(tmp_path: Path):
    proc = resolve_operational_processed_dir(Path("."))
    out_csv = tmp_path / "xmins_override.csv"
    ref = date(2026, 10, 20)

    # 1. Base External CSV (Tier 2) gives Haaland 80m, Saka 85m, and Milosavljević 75m (stale external data)
    base_csv = tmp_path / "base_fpl_review.csv"
    base_csv.write_text(
        "ID,Name,8_xMins,9_xMins\n"
        "411,Haaland,80.0,80.0\n"
        "12,Saka,85.0,85.0\n"
        "63,Milosavljevic,75.0,75.0\n",
        encoding="utf-8",
    )

    # 2. Targeted Override (Layer 3 Top) overrides Saka to 0m (GW8) and 45m (GW9)
    targeted = {
        (12, 8): 0.0,
        (12, 9): 45.0,
    }

    path = synthesize_xmins_override(
        processed_dir=proc,
        target_gw=8,
        horizon=2,
        targeted_overrides=targeted,
        base_csv_path=base_csv,
        output_path=out_csv,
        reference_date=ref,
    )
    assert path.exists()
    df = pd.read_csv(path)

    # Layer 3 Targeted wins over Layer 2: Saka receives targeted curve (0.0, 45.0)
    saka = df[df["ID"] == 12].iloc[0]
    assert saka["8_xMins"] == 0.0
    assert saka["9_xMins"] == 45.0

    # Layer 2 holds when healthy and unshielded: Haaland receives 80.0, 80.0
    haaland = df[df["ID"] == 411].iloc[0]
    assert haaland["8_xMins"] == 80.0
    assert haaland["9_xMins"] == 80.0

    # Layer 3 Broad Pool Shield overrides stale Layer 2 external minutes for injured assets (Milosavljević ID 63 = 0.0 in GW8)
    milosavljevic = df[df["ID"] == 63].iloc[0]
    assert milosavljevic["8_xMins"] == 0.0


def test_resolve_default_target_gw_advances_when_deadline_passed(tmp_path: Path):
    from solver.planning import resolve_default_target_gw
    import pandas as pd

    # Create dummy gameweeks.parquet where GW8 deadline is in past, GW9 in future
    df = pd.DataFrame({
        "id": [8, 9, 10],
        "is_next": [True, False, False],
        "finished": [False, False, False],
        "deadline_time": [
            "2026-10-20T17:30:00Z",  # in the past
            "2099-10-31T11:00:00Z",  # far future
            "2099-11-06T18:30:00Z",
        ],
    })
    df.to_parquet(tmp_path / "gameweeks.parquet")
    resolved = resolve_default_target_gw(tmp_path)
    assert resolved == 9


def test_audit_solution_players(tmp_path: Path):
    import json
    from features.injury_triage import audit_solution_players
    proc = resolve_operational_processed_dir(Path("."))
    sol_json = tmp_path / "solution.json"
    sol_json.write_text(
        json.dumps({
            "weeks": [
                {
                    "gw": 9,
                    "buy": [{"id": 427, "name": "Mbeumo"}],
                    "sell": [{"id": 398, "name": "Foden"}],
                    "squad_ids": [427, 8, 165],
                }
            ]
        }),
        encoding="utf-8",
    )
    res = audit_solution_players(proc, sol_json)
    assert len(res["transfers_in"]) == 1
    assert res["transfers_in"][0]["web_name"] == "Mbeumo"
    assert len(res["transfers_out"]) == 1
    assert res["transfers_out"][0]["web_name"] == "Foden"
    # Calafiori (8) and Joao Pedro (165) are flagged in operational players.parquet
    assert len(res["held_flagged"]) >= 1
    assert "free_hit_picks" in res
    assert "held_rotation_risk" in res


def test_synthesize_post_return_layer2_precedence_and_suspension_target_gw(tmp_path: Path):
    ref = date(2026, 10, 20)
    df_players = pd.DataFrame([
        {
            "id": 10,
            "web_name": "InjuredStar",
            "club_id": 1,
            "position_id": 3,
            "now_cost": 90,
            "status": "i",
            "chance_of_playing_next_round": 0.0,
            "news": "Thigh injury - Expected back 24 Oct",
        },
        {
            "id": 20,
            "web_name": "ZeroedExtStar",
            "club_id": 1,
            "position_id": 3,
            "now_cost": 90,
            "status": "i",
            "chance_of_playing_next_round": 0.0,
            "news": "Thigh injury - Expected back 24 Oct",
        },
        {
            "id": 30,
            "web_name": "ReturningBan",
            "club_id": 2,
            "position_id": 4,
            "now_cost": 80,
            "status": "s",
            "chance_of_playing_next_round": 0.0,
            "news": "Suspended until 24 Oct",
        },
    ])
    df_players.to_parquet(tmp_path / "players.parquet")

    df_fixtures = pd.DataFrame([
        {"id": 1, "gameweek_id": 8, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2026-10-24T14:00:00Z"},
        {"id": 2, "gameweek_id": 9, "home_club_id": 2, "away_club_id": 1, "kickoff_time": "2026-10-31T14:00:00Z"},
        {"id": 3, "gameweek_id": 10, "home_club_id": 1, "away_club_id": 3, "kickoff_time": "2026-11-07T14:00:00Z"},
    ])
    df_fixtures.to_parquet(tmp_path / "fixtures.parquet")

    base_csv = tmp_path / "ext.csv"
    base_csv.write_text(
        "ID,Name,8_xMins,9_xMins,10_xMins\n"
        "10,InjuredStar,85.0,85.0,79.1\n"
        "20,ZeroedExtStar,0.0,0.0,0.0\n"
        "30,ReturningBan,87.3,87.3,87.3\n",
        encoding="utf-8",
    )

    out_csv = tmp_path / "out.csv"
    synthesize_xmins_override(
        processed_dir=tmp_path,
        target_gw=8,
        horizon=3,
        base_csv_path=base_csv,
        output_path=out_csv,
        reference_date=ref,
    )
    df = pd.read_csv(out_csv).set_index("ID")

    # Injury on target_gw with chance=0 still hard-DNP in GW8, ramp 65.0 in GW9, then Layer 2 (79.1) wins in GW10
    assert df.loc[10, "8_xMins"] == 0.0
    assert df.loc[10, "9_xMins"] == 65.0
    assert df.loc[10, "10_xMins"] == 79.1

    # When Layer 2 is 0.0 post-return (GW10), Shield healthy baseline rescues it
    assert df.loc[20, "10_xMins"] >= 60.0

    # Suspension expiring on target_gw (24 Oct) is NOT zeroed in GW8 and uses Layer 2 (87.3) directly
    assert df.loc[30, "8_xMins"] == 87.3
    assert df.loc[30, "9_xMins"] == 87.3


def test_audit_squad_minutes_and_solution_audit_fh_and_rotation(tmp_path: Path):
    import json
    from features.injury_triage import audit_solution_players, audit_squad_minutes

    df_players = pd.DataFrame([
        {"id": 1, "web_name": "Nailed", "club_id": 1, "position_id": 2, "now_cost": 50, "status": "a", "chance_of_playing_next_round": 100.0, "news": ""},
        {"id": 2, "web_name": "Dropped", "club_id": 2, "position_id": 2, "now_cost": 41, "status": "a", "chance_of_playing_next_round": 100.0, "news": ""},
        {"id": 3, "web_name": "Cliff", "club_id": 1, "position_id": 2, "now_cost": 49, "status": "a", "chance_of_playing_next_round": None, "news": ""},
        {"id": 4, "web_name": "FHStar", "club_id": 3, "position_id": 3, "now_cost": 80, "status": "a", "chance_of_playing_next_round": 100.0, "news": ""},
        {"id": 5, "web_name": "FHBench", "club_id": 4, "position_id": 2, "now_cost": 45, "status": "a", "chance_of_playing_next_round": 100.0, "news": ""},
    ])
    df_players.to_parquet(tmp_path / "players.parquet")

    df_perfs = pd.DataFrame([
        {"player_id": 1, "gameweek_id": 10, "minutes": 90, "starts": 1},
        {"player_id": 1, "gameweek_id": 11, "minutes": 90, "starts": 1},
        {"player_id": 2, "gameweek_id": 10, "minutes": 90, "starts": 1},
        {"player_id": 2, "gameweek_id": 11, "minutes": 0, "starts": 0},
        {"player_id": 3, "gameweek_id": 10, "minutes": 90, "starts": 1},
        {"player_id": 3, "gameweek_id": 11, "minutes": 90, "starts": 1},
    ])
    df_perfs.to_parquet(tmp_path / "player_performances.parquet")

    df_picks = pd.DataFrame([{"player_id": 1}, {"player_id": 2}, {"player_id": 3}])
    df_picks.to_parquet(tmp_path / "user_picks.parquet")

    base_csv = tmp_path / "base.csv"
    base_csv.write_text(
        "ID,Name,12_xMins,13_xMins\n"
        "1,Nailed,85.0,85.0\n"
        "2,Dropped,86.9,86.9\n"
        "3,Cliff,73.8,25.5\n",
        encoding="utf-8",
    )

    risks = audit_squad_minutes(tmp_path, {1, 2, 3}, target_gw=12, horizon=2, base_csv_path=base_csv)
    by_id = {r["id"]: r for r in risks}
    assert 1 not in by_id
    assert "recent_non_start_or_sub60" in by_id[2]["triggers"]
    assert "recent_vs_external_gap" in by_id[2]["triggers"]
    assert "external_xmins_cliff" in by_id[3]["triggers"]

    sol_json = tmp_path / "solution.json"
    sol_json.write_text(
        json.dumps({
            "meta": {"next_gw": 12, "horizon": 2},
            "weeks": [
                {"gw": 12, "chip": None, "buy": [], "sell": [], "squad_ids": [1, 2, 3], "lineup_ids": [1, 3], "bench_ids": [2]},
                {"gw": 13, "chip": "FH", "buy": [], "sell": [], "squad_ids": [1, 4, 5], "lineup_ids": [1, 4], "bench_ids": [5]},
            ],
        }),
        encoding="utf-8",
    )
    audit_res = audit_solution_players(tmp_path, sol_json, override_csv_path=base_csv)
    fh_by_id = {p["id"]: p for p in audit_res["free_hit_picks"]}
    assert fh_by_id[4]["fh_role"] == "starter"
    assert fh_by_id[5]["fh_role"] == "bench"
    assert 1 not in fh_by_id
    rot_ids = {p["id"] for p in audit_res["held_rotation_risk"]}
    assert {2, 3}.issubset(rot_ids)
