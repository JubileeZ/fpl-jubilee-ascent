"""Metrics Component Hybrid Model: Regression Attack + Poisson Defence + Softmax Bonus.

Reconstructs xP from underlying metrics (xG, Threat, xA, Creativity, Defcon) and discrete
Poisson probability distributions for Clean Sheets and Goals Conceded deductions, mapped
through a Softmax BPS Bonus model. See ADR-0005.
"""

import math
import pandas as pd
from models.base import BaseModel
from models.scoring_matrix import event_points

_POS_CODE = {1: "GK", 2: "D", 3: "M", 4: "F"}
_CLEAN_SHEET_POINTS = {"GK": 4.0, "D": 4.0, "M": 1.0, "F": 0.0}

def _poisson_pmf(k: int, lmbda: float) -> float:
    if lmbda <= 0:
        return 1.0 if k == 0 else 0.0
    return (lmbda ** k) * math.exp(-lmbda) / math.factorial(k)


def _poisson_cdf_complement(threshold: int, lmbda: float) -> float:
    """Returns P(X >= threshold) for X ~ Poisson(lmbda)."""
    if lmbda <= 0:
        return 0.0
    cdf = sum(_poisson_pmf(k, lmbda) for k in range(threshold))
    return max(0.0, 1.0 - cdf)


class MetricsComponentHybridModel(BaseModel):
    @property
    def name(self) -> str:
        return "metrics_component_hybrid"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        predictions = []
        for offset in range(horizon):
            for _, row in features_df.iterrows():
                # Allow fallback for non-seeded players if chance_of_playing/avg_mins are available
                has_seed = row.get("has_prior_seed", True)
                avail = float(row.get("chance_of_playing", 100.0) or 100.0) / 100.0
                avg_mins = float(row.get("avg_mins_3gw", 0.0) or 0.0)
                
                if not has_seed and avg_mins == 0.0:
                    predictions.append({
                        "player_id": int(row["player_id"]),
                        "gameweek_id": int(row["gameweek_id"]) + offset,
                        "projected_points": 0.0,
                        "projected_minutes": 0.0,
                    })
                    continue

                expected_minutes = avg_mins * avail
                diff = float(row.get("difficulty", 3.0) or 3.0)
                
                # Split fixture multipliers
                attack_multiplier = max(0.2, (6.0 - diff) / 3.0)
                defence_multiplier = max(0.2, (6.0 - diff) / 3.0)

                pos = _POS_CODE.get(int(row.get("position_id", 3)), "M")

                # 1. Attack Regression Model (Goals & Assists via xG/Threat and xA/Creativity)
                raw_goals_per90 = float(row.get("per90_goals", 0.0) or 0.0)
                xg_per90 = float(row.get("per90_xg", 0.0) or 0.0)
                threat_per90 = float(row.get("per90_threat", 0.0) or 0.0)
                
                if xg_per90 > 0 or threat_per90 > 0:
                    expected_goals_per90 = 0.75 * xg_per90 + 0.25 * (threat_per90 / 100.0)
                else:
                    expected_goals_per90 = raw_goals_per90

                # Cameo damping for players with <30 mins
                minute_damping = min(1.0, expected_minutes / 30.0) if expected_minutes < 30.0 else 1.0

                expected_goals = expected_goals_per90 * (expected_minutes / 90.0) * attack_multiplier * minute_damping

                raw_assists_per90 = float(row.get("per90_assists", 0.0) or 0.0)
                xa_per90 = float(row.get("per90_xa", 0.0) or 0.0)
                creativity_per90 = float(row.get("per90_creativity", 0.0) or 0.0)

                if xa_per90 > 0 or creativity_per90 > 0:
                    expected_assists_per90 = 0.75 * xa_per90 + 0.25 * (creativity_per90 / 100.0)
                else:
                    expected_assists_per90 = raw_assists_per90

                expected_assists = expected_assists_per90 * (expected_minutes / 90.0) * attack_multiplier * minute_damping

                # 2. Poisson Defence & Clean Sheet Model (lambda floor = 0.65 caps CS prob at ~52%)
                gc_per90 = float(row.get("per90_goals_conceded", 0.0) or 1.2)
                lmbda_conceded = max(0.65, gc_per90 * (expected_minutes / 90.0) * defence_multiplier)

                if expected_minutes >= 60.0:
                    prob_clean_sheet = math.exp(-lmbda_conceded)
                else:
                    prob_clean_sheet = 0.0

                xp_clean_sheet = prob_clean_sheet * _CLEAN_SHEET_POINTS[pos]

                # Goals conceded deduction (GK & D lose -1 per 2 goals)
                xp_conceded = 0.0
                if pos in ("GK", "D"):
                    for k in range(2, 10):
                        deduction = math.floor(k / 2)
                        pmf = _poisson_pmf(k, lmbda_conceded)
                        xp_conceded -= deduction * pmf

                # 3. Position-Aware Defcon Model (Threshold: 10 for DEF, 12 for MID/FWD)
                defcon_per90 = float(row.get("per90_defensive_contribution", 0.0) or 0.0)
                lmbda_defcon = defcon_per90 * (expected_minutes / 90.0)
                defcon_threshold = 10 if pos == "D" else 12
                prob_defcon = _poisson_cdf_complement(defcon_threshold, lmbda_defcon) if pos != "GK" else 0.0

                # 4. Saves & Cards
                saves_per90 = float(row.get("per90_saves", 0.0) or 0.0)
                expected_saves = saves_per90 * (expected_minutes / 90.0) if pos == "GK" else 0.0
                xp_saves = event_points("saves", pos, expected_saves)

                yellow_per90 = float(row.get("per90_yellow_cards", 0.0) or 0.0)
                red_per90 = float(row.get("per90_red_cards", 0.0) or 0.0)
                xp_cards = (yellow_per90 * -1.0 + red_per90 * -3.0) * (expected_minutes / 90.0)

                # 5. Softmax BPS & Bonus Model (Starters only: mins >= 45)
                if expected_minutes >= 45.0:
                    xbps = (
                        expected_minutes * 0.1
                        + expected_goals * 24.0
                        + expected_assists * 12.0
                        + prob_clean_sheet * 12.0
                        + prob_defcon * 6.0
                        + expected_saves * 2.0
                    )
                    xp_bonus = 1.8 / (1.0 + math.exp(-(xbps - 30.0) / 5.0))
                else:
                    xp_bonus = 0.0

                # Minutes points
                xp_minutes = event_points("minutes", pos, expected_minutes)

                # Total reconstructed xP
                xp_attack = event_points("goals", pos, expected_goals) + event_points("assists", pos, expected_assists)
                xp_total = xp_minutes + xp_attack + xp_clean_sheet + xp_conceded + xp_saves + xp_cards + xp_bonus

                predictions.append({
                    "player_id": int(row["player_id"]),
                    "gameweek_id": int(row["gameweek_id"]) + offset,
                    "projected_points": float(max(0.0, xp_total)),
                    "projected_minutes": float(expected_minutes),
                })

        return pd.DataFrame(predictions)
