"""Build FPL bootstrap-static and fixtures payloads from a processed season archive."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ELEMENT_TYPES: list[dict[str, object]] = [
    {"id": 1, "singular_name_short": "GKP", "squad_min_play": 1, "squad_max_play": 1, "squad_select": 2},
    {"id": 2, "singular_name_short": "DEF", "squad_min_play": 3, "squad_max_play": 5, "squad_select": 5},
    {"id": 3, "singular_name_short": "MID", "squad_min_play": 2, "squad_max_play": 5, "squad_select": 5},
    {"id": 4, "singular_name_short": "FWD", "squad_min_play": 1, "squad_max_play": 3, "squad_select": 3},
]


def bootstrap_from_processed(processed_dir: Path) -> dict[str, object]:
    players = pd.read_parquet(processed_dir / "players.parquet")
    clubs = pd.read_parquet(processed_dir / "clubs.parquet")
    gameweeks = pd.read_parquet(processed_dir / "gameweeks.parquet") if (processed_dir / "gameweeks.parquet").exists() else pd.DataFrame()
    elements: list[dict[str, object]] = []
    for _, row in players.iterrows():
        elements.append({
            "id": int(row["id"]),
            "code": int(row["code"]) if "code" in players.columns and pd.notna(row.get("code")) else int(row["id"]),
            "first_name": str(row.get("first_name") or ""),
            "second_name": str(row.get("second_name") or ""),
            "web_name": str(row.get("web_name") or ""),
            "team": int(row["club_id"]),
            "element_type": int(row["position_id"]),
            "now_cost": int(row["now_cost"]),
        })
    teams: list[dict[str, object]] = []
    for _, row in clubs.iterrows():
        teams.append({
            "id": int(row["id"]),
            "name": str(row["name"]),
            "short_name": str(row.get("short_name") or row["name"]),
        })
    events: list[dict[str, object]] = []
    if gameweeks.empty:
        events = [{"id": gw, "is_next": gw == 1, "finished": False} for gw in range(1, 39)]
    else:
        for _, row in gameweeks.iterrows():
            events.append({
                "id": int(row["id"]),
                "is_next": bool(row.get("is_next", False)),
                "finished": bool(row.get("finished", False)),
            })
    return {"elements": elements, "teams": teams, "events": events, "element_types": ELEMENT_TYPES}


def fixtures_from_processed(processed_dir: Path) -> list[dict[str, object]]:
    fixtures = pd.read_parquet(processed_dir / "fixtures.parquet")
    rows: list[dict[str, object]] = []
    for _, row in fixtures.iterrows():
        if pd.isna(row.get("gameweek_id")):
            continue
        rows.append({
            "event": int(row["gameweek_id"]),
            "team_h": int(row["home_club_id"]),
            "team_a": int(row["away_club_id"]),
        })
    return rows
