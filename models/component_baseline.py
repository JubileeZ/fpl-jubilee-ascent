"""Component model: reconstructs xP from per-90 Event Rates via the scoring matrix.

Mid-season slice (ADR-0003, issue #84). Per-90 Event Rates are seeded from
prior history (computed in build_features as per90_* columns) and reconstructed
through models.scoring_matrix.event_points. Players without a prior seed project 0.
"""

import pandas as pd

from models.base import BaseModel
from models.scoring_matrix import event_points

_POS_CODE = {1: "GK", 2: "D", 3: "M", 4: "F"}

# Per-90 event-rate columns in the FeatureContract. `minutes` is handled
# separately (it is a per-match threshold on expected minutes, not a per-90 rate).
_COMPONENT_RATES = [
    ("goals", "per90_goals"),
    ("assists", "per90_assists"),
    ("clean_sheets", "per90_clean_sheets"),
    ("goals_conceded", "per90_goals_conceded"),
    ("saves", "per90_saves"),
    ("bonus", "per90_bonus"),
    ("yellow_cards", "per90_yellow_cards"),
    ("red_cards", "per90_red_cards"),
    ("penalties_saved", "per90_penalties_saved"),
    ("penalties_missed", "per90_penalties_missed"),
    ("own_goals", "per90_own_goals"),
]


class ComponentBaseline(BaseModel):
    @property
    def name(self) -> str:
        return "component_baseline"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        predictions = []
        for offset in range(horizon):
            for _, row in features_df.iterrows():
                if not row.get("has_prior_seed", False):
                    predictions.append({
                        "player_id": int(row["player_id"]),
                        "gameweek_id": int(row["gameweek_id"]) + offset,
                        "projected_points": 0.0,
                        "projected_minutes": 0.0,
                    })
                    continue

                avail = row.get("chance_of_playing", 100.0) / 100.0
                expected_minutes = float(row.get("avg_mins_3gw", 0.0)) * avail
                diff = row.get("difficulty", 3.0)
                difficulty_multiplier = max(0.2, (6.0 - diff) / 3.0)

                pos = _POS_CODE.get(int(row["position_id"]), "M")
                # Minutes points are a per-match threshold on expected minutes
                # (not a per-90 rate, not scaled by fixture difficulty).
                xp = event_points("minutes", pos, expected_minutes)
                for component, rate_col in _COMPONENT_RATES:
                    per90 = float(row.get(rate_col, 0.0) or 0.0)
                    expected_events = per90 * (expected_minutes / 90.0) * difficulty_multiplier
                    xp += event_points(component, pos, expected_events)

                predictions.append({
                    "player_id": int(row["player_id"]),
                    "gameweek_id": int(row["gameweek_id"]) + offset,
                    "projected_points": float(xp),
                    "projected_minutes": float(expected_minutes),
                })
        return pd.DataFrame(predictions)
