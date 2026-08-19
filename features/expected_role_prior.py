"""Expected Role Prior ingest for the Feature Contract (ADR 0016)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ROLE_PRIORS: dict[str, tuple[float, float, float, float, float]] = {
    "Nailed Starter": (0.90, 0.05, 0.05, 85.0, 20.0),
    "Regular Starter": (0.75, 0.10, 0.15, 80.0, 20.0),
    "Rotation": (0.40, 0.25, 0.35, 70.0, 20.0),
    "Cameo": (0.10, 0.35, 0.55, 60.0, 15.0),
    "Out of Contention": (0.00, 0.05, 0.95, 45.0, 10.0),
}
OUT_OF_CONTENTION = ROLE_PRIORS["Out of Contention"]
WATCH_P_START_FACTOR = 0.70
WATCH_HORIZON_MAX_GW = 5
EXCLUDE_GW1_5_MAX_GW = 5
BLEND_START_APPEARANCES = 1
BLEND_FULL_APPEARANCES = 5
LIVE_SEASON = "2026-27"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPECTED_ROLE_TABLE = PROJECT_ROOT / (
    "data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv"
)
DEFAULT_LINEUP_SIGNALS = PROJECT_ROOT / (
    "data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/lineup-signals.json"
)


def appearance_blend_weight(
    appearances: int,
    blend_start_appearances: int = BLEND_START_APPEARANCES,
    blend_full_appearances: int = BLEND_FULL_APPEARANCES,
) -> float:
    """Current-season weight: 0 through 1 appearance, 1.0 at 5 appearances."""
    if appearances < blend_start_appearances:
        return 0.0
    denom = max(1, blend_full_appearances - blend_start_appearances)
    return min(1.0, float(appearances - blend_start_appearances) / float(denom))


def apply_availability_priors(
    p_start: float,
    p_sub: float,
    p_dnp: float,
    draft_availability: str,
    availability_override: str,
    gameweek_id: int,
) -> tuple[float, float, float]:
    """Return (p_start, p_sub, p_dnp) after Draft Availability overlay for one GW."""
    draft_avail = str(draft_availability or "eligible")
    avail_override = str(availability_override or "")
    exclude_gw1_5 = draft_avail == "exclude_gw1-5" or "out_gw1-5" in avail_override
    exclude_gw1 = draft_avail == "exclude_gw1" or "unavailable_gw1" in avail_override
    is_watch = draft_avail == "watch"

    if exclude_gw1_5 and gameweek_id <= EXCLUDE_GW1_5_MAX_GW:
        return 0.0, 0.0, 1.0
    if exclude_gw1 and gameweek_id == 1:
        return 0.0, 0.0, 1.0
    if is_watch and gameweek_id <= WATCH_HORIZON_MAX_GW:
        new_start = p_start * WATCH_P_START_FACTOR
        return new_start, p_sub, p_dnp + (p_start - new_start)
    return p_start, p_sub, p_dnp


def minutes_if_appearance(p_start: float, p_sub: float, mins_start: float, mins_sub: float) -> float:
    featured = p_start + p_sub
    if featured <= 0:
        return 0.0
    return (p_start * mins_start + p_sub * mins_sub) / featured


def load_expected_role_table(path: Path, season: str) -> pd.DataFrame:
    """Load the Expected Role Table and refuse missing or other-season files."""
    if path is None or not Path(path).exists():
        raise ValueError(
            f"Expected Role Table missing at {path}. "
            "Run Expected Role Rebuild (--rebuild-roles) for this season."
        )
    table = pd.read_csv(path)
    if "season" not in table.columns or table.empty:
        raise ValueError(
            f"Expected Role Table at {path} has no season identity. "
            "Rebuild for the current season."
        )
    seasons = {str(value) for value in table["season"].dropna().unique()}
    if seasons != {season}:
        found = ", ".join(sorted(seasons)) or "none"
        raise ValueError(
            f"Expected Role Table season {found} is not {season}. "
            "Do not reuse last season's table."
        )
    return table


def table_season_status(path: Path, season: str) -> str:
    if path is None or not Path(path).exists():
        return "missing"
    try:
        load_expected_role_table(path, season)
    except ValueError:
        return "other_season"
    return "ok"


def ensure_expected_role_rebuild_choice(
    season: str,
    rebuild_roles: bool,
    keep_roles: bool,
    table_path: Path = DEFAULT_EXPECTED_ROLE_TABLE,
) -> None:
    if rebuild_roles and keep_roles:
        raise ValueError("Use only one of --rebuild-roles or --keep-roles")
    status = table_season_status(table_path, season)
    if status == "ok":
        return
    if rebuild_roles or keep_roles:
        return
    raise ValueError(
        "Expected Role Table missing or other season. "
        "Pass --rebuild-roles to run Expected Role Rebuild, or --keep-roles to defer "
        "(API refresh only; projections refuse until a this-season table exists)."
    )


def fit_role_prior(table: pd.DataFrame, player_id: int) -> dict[str, Any]:
    """Return fit-role Participation State and conditional minutes for one Player."""
    if "player_id" in table.columns:
        hit = table[pd.to_numeric(table["player_id"], errors="coerce") == player_id]
        if not hit.empty:
            row = hit.iloc[0]
            p_start, p_sub, p_dnp, mins_s, mins_u = OUT_OF_CONTENTION
            return {
                "p_start": float(row.get("p_start", p_start)),
                "p_sub_in": float(row.get("p_sub_in", p_sub)),
                "p_dnp": float(row.get("p_dnp", p_dnp)),
                "xmins_if_start": float(row.get("mins_if_start", mins_s)),
                "xmins_if_sub_in": float(row.get("mins_if_sub", mins_u)),
                "draft_availability": str(row.get("draft_availability") or "eligible"),
                "availability_override": str(row.get("availability_override") or ""),
            }
    p_start, p_sub, p_dnp, mins_s, mins_u = OUT_OF_CONTENTION
    return {
        "p_start": p_start,
        "p_sub_in": p_sub,
        "p_dnp": p_dnp,
        "xmins_if_start": mins_s,
        "xmins_if_sub_in": mins_u,
        "draft_availability": "eligible",
        "availability_override": "",
    }


def write_lineup_signals(
    path: Path,
    season: str,
    predicted_xi: dict[str, list[str]],
    nailed: dict[str, list[str]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "season": season,
        "predicted_xi": predicted_xi,
        "nailed": nailed,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
