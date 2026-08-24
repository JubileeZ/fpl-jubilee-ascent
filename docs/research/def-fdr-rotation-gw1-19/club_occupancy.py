"""Club Occupancy table for a five-defender Defensive Rotation Set."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

import pandas as pd

OCCUPANCY_COLUMNS: tuple[str, ...] = (
    "occupancy_key",
    "club_1",
    "club_2",
    "club_3",
    "club_4",
    "club_5",
    "distinct_clubs",
    "occupancy_shape",
    "rank_mod_fdr",
    "total_mod_fdr",
    "total_base_fdr",
    "avg_def_mod_fdr",
    "avg_def_base_fdr",
)

STARTED_DEF_SLOTS: int = 19 * 3


def occupancy_shape(club_shorts: Sequence[str]) -> str:
    counts = sorted(Counter(club_shorts).values(), reverse=True)
    return "-".join(str(n) for n in counts)


def build_club_occupancy_table(
    club_shorts_per_set: Sequence[Sequence[str]],
    total_mod_fdr: Sequence[float],
    total_base_fdr: Sequence[float],
) -> pd.DataFrame:
    """One row per Club Occupancy. Rows sorted by occupancy_key.

    rank_mod_fdr is ordinal after (total_mod_fdr ascending, occupancy_key ascending).
    """
    rows: list[dict[str, object]] = []
    for shorts, mod_fdr, base_fdr in zip(
        club_shorts_per_set, total_mod_fdr, total_base_fdr, strict=True
    ):
        ordered = tuple(sorted(shorts))
        if len(ordered) != 5:
            raise ValueError("Club Occupancy must have exactly 5 slots")
        rows.append(
            {
                "occupancy_key": "-".join(ordered),
                "club_1": ordered[0],
                "club_2": ordered[1],
                "club_3": ordered[2],
                "club_4": ordered[3],
                "club_5": ordered[4],
                "distinct_clubs": len(set(ordered)),
                "occupancy_shape": occupancy_shape(ordered),
                "total_mod_fdr": round(float(mod_fdr), 2),
                "total_base_fdr": round(float(base_fdr), 2),
                "avg_def_mod_fdr": round(float(mod_fdr) / STARTED_DEF_SLOTS, 3),
                "avg_def_base_fdr": round(float(base_fdr) / STARTED_DEF_SLOTS, 3),
            }
        )
    table = pd.DataFrame(rows)
    table = table.sort_values(
        ["total_mod_fdr", "occupancy_key"], kind="mergesort"
    ).reset_index(drop=True)
    table["rank_mod_fdr"] = range(1, len(table) + 1)
    table = table.sort_values("occupancy_key", kind="mergesort").reset_index(drop=True)
    return table.loc[:, list(OCCUPANCY_COLUMNS)]
