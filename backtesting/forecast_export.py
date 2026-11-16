"""Strict solver-table preparation for an admitted synthetic or empirical issue."""

import math
from typing import Any, cast

import pandas as pd

from backtesting.data_admission import AdmittedInput, verify_input

REQUIRED_COMPONENTS = ("xp_minutes", "xp_goals", "xp_assists", "xp_clean_sheet", "xp_conceded", "xp_defcon", "xp_saves", "xp_yellow_cards", "xp_red_cards", "xp_penalties_saved", "xp_penalties_missed", "xp_own_goals", "xp_bonus")


def validate_components(predictions: pd.DataFrame, rules_version: str) -> None:
    """Require every declared component and reconcile each fixture total."""
    if not set(REQUIRED_COMPONENTS).issubset(predictions.columns):
        raise ValueError("Required forecast components missing")
    for row in predictions.to_dict(orient="records"):
        values: list[float] = []
        for component in REQUIRED_COMPONENTS:
            value = row[component]
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Nonfinite forecast component")
            values.append(float(value))
        if not math.isclose(sum(values), float(row["projected_points"]), rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("Forecast component reconciliation failed")
        if rules_version in ("2023-24", "2024-25") and row["xp_defcon"] != 0:
            raise ValueError("Defensive contribution unsupported by native rules")
        if row["fixture_id"] == -1 and any(value != 0 for value in values):
            raise ValueError("Blank components must be zero")


def _expected_empirical_coverage(
    origin: dict[str, Any],
    capability: AdmittedInput,
    targets: list[int],
    catalog: dict[str, bytes],
) -> tuple[set[tuple[int, int, int]], pd.DataFrame]:
    import json

    from backtesting.empirical_admission import resolve_and_verify_source_bytes
    from backtesting.empirical_mirrors import parse_fixtures_csv_window
    from backtesting.fplcache_ingest import _sanitize_bootstrap, _utc

    sources = origin["sources"]
    bs_dec = resolve_and_verify_source_bytes(sources["bootstrap"], catalog, role_label="bootstrap")
    fx_dec = resolve_and_verify_source_bytes(sources["fixtures"], catalog, role_label="fixtures")
    bs_payload = json.loads(bs_dec.decode("utf-8"))
    elements, _, _ = _sanitize_bootstrap(bs_payload, capture_upper=_utc(sources["bootstrap"]["capture_upper"]))
    fx_rows = parse_fixtures_csv_window(fx_dec, capability.gw, horizon=len(targets))

    club_gw_fixtures: dict[tuple[int, int], list[int]] = {}
    for row in fx_rows:
        w = int(row["event"])
        fid = int(row["id"])
        club_gw_fixtures.setdefault((int(row["team_h"]), w), []).append(fid)
        club_gw_fixtures.setdefault((int(row["team_a"]), w), []).append(fid)

    expected: set[tuple[int, int, int]] = set()
    meta_rows: list[dict[str, int]] = []
    for el in elements:
        pid = int(el["id"])
        club = int(el["team"])
        meta_rows.append({"id": pid, "club": club, "position": int(el["element_type"]), "price": int(el["now_cost"])})
        for w in targets:
            fids = club_gw_fixtures.get((club, w), [])
            if not fids:
                expected.add((pid, w, -1))
            else:
                for fid in fids:
                    expected.add((pid, w, fid))
    return expected, pd.DataFrame(meta_rows)


def strict_solver_table(
    predictions: pd.DataFrame,
    capability: AdmittedInput,
    request: dict[str, Any],
    catalog: dict[str, bytes],
) -> pd.DataFrame:
    """Validate every admitted fixture and blank before aggregating for the solver.

    A blank is represented by fixture_id -1 and must carry zero points/minutes.
    This function does not establish forecast provenance or promotion eligibility.
    """
    verify_input(capability, request, catalog)
    origins = [o for o in request["origins"] if o["season"] == capability.season and o["gw"] == capability.gw]
    if len(origins) != 1:
        raise ValueError("Ambiguous issue")
    origin = origins[0]
    targets = list(range(capability.gw, min(capability.gw + 5, 38) + 1))
    if capability.mode == "empirical":
        expected, raw_meta = _expected_empirical_coverage(origin, capability, targets, catalog)
    else:
        if origin["target_gws"] != targets:
            raise ValueError("Incomplete issue horizon")
        expected = {(int(row["player"]), int(row["gw"]), -1 if row["status"] == "blank" else int(row["fixture"])) for row in origin["schedule"]}
        raw_meta = pd.DataFrame(origin["players"])
    columns = ["player_id", "gameweek_id", "fixture_id", "projected_points", "projected_minutes"]
    if not set(columns).issubset(predictions.columns):
        raise ValueError("Forecast columns missing")
    frame: pd.DataFrame = cast(pd.DataFrame, predictions[columns].copy())
    for col in columns:
        frame[col] = pd.to_numeric(frame[col], errors="raise")
        if not bool(frame[col].map(math.isfinite).all()):
            raise ValueError(f"Nonfinite {col}")
    for col in columns[:3]:
        if not (frame[col] == frame[col].astype(int)).all():
            raise ValueError(f"Nonintegral {col}")
        frame[col] = frame[col].astype(int)
    if frame.duplicated(columns[:3]).any() or set(map(tuple, frame[columns[:3]].itertuples(index=False, name=None))) != expected:
        raise ValueError("Forecast population or fixture coverage mismatch")
    if ((frame.projected_minutes < 0) | (frame.projected_minutes > 90)).any():
        raise ValueError("Fixture minutes outside bounds")
    blank = frame.fixture_id == -1
    if ((frame.loc[blank, "projected_points"] != 0) | (frame.loc[blank, "projected_minutes"] != 0)).any():
        raise ValueError("Known blank must be zero")
    grouped: pd.DataFrame = cast(pd.DataFrame, frame.groupby(["player_id", "gameweek_id"], as_index=False)[columns[3:]].sum())
    metadata: pd.DataFrame = cast(pd.DataFrame, raw_meta[["id", "club", "position", "price"]]).rename(columns={"id": "player_id"})
    points = grouped.pivot(index="player_id", columns="gameweek_id", values="projected_points")
    points.columns = [f"{gw}_Pts" for gw in points.columns]
    minutes = grouped.pivot(index="player_id", columns="gameweek_id", values="projected_minutes")
    minutes.columns = [f"{gw}_xMins" for gw in minutes.columns]
    return metadata.merge(points.join(minutes).reset_index(), on="player_id", validate="one_to_one")
