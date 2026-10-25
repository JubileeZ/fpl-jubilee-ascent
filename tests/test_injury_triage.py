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


def test_build_broad_pool_shield():
    proc = resolve_operational_processed_dir(Path("."))
    # Pass deterministic reference date before GW8 (e.g. 20 Oct 2026)
    ref = date(2026, 10, 20)
    shield = build_broad_pool_shield(proc, target_gw=8, horizon=4, reference_date=ref)

    # Janelt (ID 98) is suspended until 31 Oct (GW9 fixture is 31 Oct)
    # GW8: 0.0 (suspended)
    # GW9: 20.0 (cameo on return GW)
    # GW10: 65.0 (managed start)
    # GW11: healthy baseline >= 60.0
    assert shield.get((98, 8)) == 0.0
    assert shield.get((98, 9)) == 20.0
    assert shield.get((98, 10)) == 65.0
    assert shield.get((98, 11)) is not None and shield[(98, 11)] >= 60.0

    # Bentancur (ID 516) is suspended until 7 Nov (Spurs GW10 match is 7 Nov)
    # GW8: 0.0
    # GW9: 0.0
    # GW10: 20.0 (cameo on return GW)
    # GW11: 65.0 (managed start)
    assert shield.get((516, 8)) == 0.0
    assert shield.get((516, 9)) == 0.0
    assert shield.get((516, 10)) == 20.0
    assert shield.get((516, 11)) == 65.0

    # Unknown return date + status 'i' (Szoboszlai ID 368)
    # Zeroed out across the entire planning horizon
    assert shield.get((368, 8)) == 0.0
    assert shield.get((368, 9)) == 0.0
    assert shield.get((368, 10)) == 0.0
    assert shield.get((368, 11)) == 0.0


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

    # 1. Base External CSV (Tier 2) gives Haaland 80m and Saka 85m
    base_csv = tmp_path / "base_fpl_review.csv"
    base_csv.write_text(
        "ID,Name,8_xMins,9_xMins\n"
        "411,Haaland,80.0,80.0\n"
        "12,Saka,85.0,85.0\n",
        encoding="utf-8",
    )

    # 2. Targeted Override (Tier 3) overrides Saka to 0m (GW8) and 45m (GW9)
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

    # Tier 3 wins over Tier 2: Saka receives targeted curve (0.0, 45.0)
    saka = df[df["ID"] == 12].iloc[0]
    assert saka["8_xMins"] == 0.0
    assert saka["9_xMins"] == 45.0

    # Tier 2 holds when Tier 3 omitted: Haaland receives 80.0, 80.0
    haaland = df[df["ID"] == 411].iloc[0]
    assert haaland["8_xMins"] == 80.0
    assert haaland["9_xMins"] == 80.0

    # Tier A Broad Pool Shield applies to unlisted injured assets (Janelt ID 98 = 0.0 in GW8)
    janelt = df[df["ID"] == 98].iloc[0]
    assert janelt["8_xMins"] == 0.0
