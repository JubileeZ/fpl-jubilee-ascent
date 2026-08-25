"""First-Half Club Occupancy FDR ranking from archive fixtures (diagnostic)."""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_CLUB_OCCUPANCY_DIR = Path(__file__).resolve().parents[1] / "def-fdr-rotation-gw1-19"
if str(_CLUB_OCCUPANCY_DIR) not in sys.path:
    sys.path.insert(0, str(_CLUB_OCCUPANCY_DIR))

from club_occupancy import build_club_occupancy_table  # noqa: E402

FIRST_HALF_GWS = range(1, 20)


def club_gw_fdr(clubs: pd.DataFrame, fixtures: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[int]]:
    club_ids = sorted(int(v) for v in clubs["id"].unique())
    index = {club_id: i for i, club_id in enumerate(club_ids)}
    gw1_19 = fixtures[(fixtures["gameweek_id"] >= 1) & (fixtures["gameweek_id"] <= 19)]
    mod_mat = np.full((len(club_ids), 19), 3.0)
    base_mat = np.full((len(club_ids), 19), 3.0)
    for _, row in gw1_19.iterrows():
        gw = int(row["gameweek_id"])
        if gw not in FIRST_HALF_GWS:
            continue
        col = gw - 1
        home = int(row["home_club_id"])
        away = int(row["away_club_id"])
        if home in index:
            base = float(row["team_h_difficulty"])
            base_mat[index[home], col] = base
            mod_mat[index[home], col] = base - 0.25
        if away in index:
            base = float(row["team_a_difficulty"])
            base_mat[index[away], col] = base
            mod_mat[index[away], col] = base + 0.25
    return mod_mat, base_mat, club_ids


def valid_occupancy_indices(n_clubs: int) -> list[tuple[int, ...]]:
    combos: list[tuple[int, ...]] = []
    for combo in itertools.combinations_with_replacement(range(n_clubs), 5):
        if max(combo.count(i) for i in set(combo)) <= 3:
            combos.append(combo)
    return combos


def first_half_occupancy_table(clubs: pd.DataFrame, fixtures: pd.DataFrame) -> pd.DataFrame:
    mod_mat, base_mat, club_ids = club_gw_fdr(clubs, fixtures)
    combos = valid_occupancy_indices(len(club_ids))
    combo_arr = np.array(combos)
    mod_fdrs = mod_mat[combo_arr]
    base_fdrs = base_mat[combo_arr]
    sort_indices = np.argsort(mod_fdrs, axis=1)
    sorted_mod = np.take_along_axis(mod_fdrs, sort_indices, axis=1)
    sorted_base = np.take_along_axis(base_fdrs, sort_indices, axis=1)
    total_mod = np.sum(sorted_mod[:, :3, :], axis=(1, 2))
    total_base = np.sum(sorted_base[:, :3, :], axis=(1, 2))
    names = dict(zip(clubs["id"].astype(int), clubs["short_name"].astype(str), strict=False))
    club_shorts = [tuple(names[club_ids[i]] for i in combo) for combo in combos]
    return build_club_occupancy_table(club_shorts, total_mod, total_base)


def write_occupancy_csv(path: Path, clubs: pd.DataFrame, fixtures: pd.DataFrame) -> Path:
    table = first_half_occupancy_table(clubs, fixtures)
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path
