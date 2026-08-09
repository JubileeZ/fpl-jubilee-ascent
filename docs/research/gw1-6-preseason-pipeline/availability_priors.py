"""Draft Availability → Participation State prior overlays for research projections.

Grill lock (2026-08-10):
- Watch (GW1–5): p_start *= 0.70; cut mass shifts to p_dnp; p_sub unchanged.
- Exclude GW1–5: zero participation for GW1–5 only (GW6 uses fit-role priors).
- Exclude GW1: zero participation for GW1 only.
"""

from __future__ import annotations

WATCH_P_START_FACTOR = 0.70
WATCH_HORIZON_MAX_GW = 5
EXCLUDE_GW1_5_MAX_GW = 5


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
