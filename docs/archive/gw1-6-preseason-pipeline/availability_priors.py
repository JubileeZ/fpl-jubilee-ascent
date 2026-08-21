"""Draft Availability → Participation State prior overlays.

Canonical implementation lives in features.expected_role_prior (ADR 0016).
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from features.expected_role_prior import (
    EXCLUDE_GW1_5_MAX_GW,
    WATCH_HORIZON_MAX_GW,
    WATCH_P_START_FACTOR,
    apply_availability_priors,
)

__all__ = [
    "EXCLUDE_GW1_5_MAX_GW",
    "WATCH_HORIZON_MAX_GW",
    "WATCH_P_START_FACTOR",
    "apply_availability_priors",
]
