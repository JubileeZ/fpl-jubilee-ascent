import pandas as pd
from models.base import BaseModel, cap_projected_minutes, iter_feature_rows


def _number(row: pd.Series, column: str, default: float) -> float:
    value = row.get(column, default)
    return default if value is None or pd.isna(value) else float(value)

class LinearBaseline(BaseModel):
    @property
    def name(self) -> str:
        return "linear_baseline"
        
    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        """
        Baseline model: predicts upcoming gameweek points using rolling historical averages
        adjusted by the upcoming fixture difficulty and player availability chance.
        """
        predictions = []
        
        for row, gameweek_id, fixture_id in iter_feature_rows(features_df, horizon):
            if fixture_id is not None and fixture_id < 0:
                xp = 0.0
                xmins = 0.0
            else:
                diff = _number(row, "difficulty", 3.0)
                difficulty_multiplier = max(0.2, (6.0 - diff) / 3.0)
                avail = min(max(_number(row, "chance_of_playing", 100.0) / 100.0, 0.0), 1.0)
                avg_pts = _number(row, "avg_points_3gw", 0.0)
                avg_mins = _number(row, "avg_mins_3gw", 60.0)
                uncapped_xmins = avg_mins * avail
                xmins = cap_projected_minutes(row, uncapped_xmins)
                xp = avg_pts * difficulty_multiplier * avail * (xmins / uncapped_xmins if uncapped_xmins else 0.0)

            prediction = {
                "player_id": int(row["player_id"]),
                "gameweek_id": gameweek_id,
                "projected_points": float(xp),
                "projected_minutes": float(xmins),
            }
            if fixture_id is not None:
                prediction["fixture_id"] = fixture_id
            predictions.append(prediction)
                
        return pd.DataFrame(predictions)
