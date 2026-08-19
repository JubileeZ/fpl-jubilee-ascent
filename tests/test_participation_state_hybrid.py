import pandas as pd
import pytest

from models.participation_state_hybrid import ParticipationStateHybridModel


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "player_id": 1,
        "position_id": 2,
        "gameweek_id": 10,
        "fixture_id": 100,
        "difficulty": 3.0,
        "chance_of_playing": 100.0,
        "has_availability_snapshot": False,
        "is_immediate_next_gw": False,
        "p_dnp": 0.5,
        "p_start": 0.4,
        "p_sub_in": 0.1,
        "xmins_if_start": 80.0,
        "xmins_if_sub_in": 20.0,
        "p_60_if_start": 1.0,
        "p_60_if_sub_in": 0.0,
        "per90_xg": 0.0,
        "per90_xa": 0.0,
        "per90_threat": 0.0,
        "per90_creativity": 0.0,
        "per90_goals": 0.0,
        "per90_assists": 0.0,
        "per90_goals_conceded": 1.0,
        "per90_saves": 0.0,
        "per90_yellow_cards": 0.0,
        "per90_red_cards": 0.0,
        "per90_penalties_saved": 0.0,
        "per90_penalties_missed": 0.0,
        "per90_own_goals": 0.0,
        "per90_defensive_contribution": 0.0,
    }
    row.update(overrides)
    return row


def test_state_probabilities_drive_expected_minutes_and_minute_points():
    result = ParticipationStateHybridModel().predict(
        pd.DataFrame([_row()]),
        horizon=1,
    ).iloc[0]

    assert result["p_dnp"] + result["p_start"] + result["p_sub_in"] == pytest.approx(1.0)
    assert result["projected_minutes"] == pytest.approx(34.0)
    assert result["xp_minutes"] == pytest.approx(0.9)
    assert result["xmins_if_start"] == pytest.approx(80.0)
    assert result["xmins_if_sub_in"] == pytest.approx(20.0)


def test_dnp_state_has_zero_points_and_minutes():
    result = ParticipationStateHybridModel().predict(
        pd.DataFrame([_row(p_dnp=1.0, p_start=0.0, p_sub_in=0.0)]),
        horizon=1,
    ).iloc[0]

    assert result["projected_minutes"] == 0.0
    assert result["projected_points"] == 0.0


def test_immediate_snapshot_zero_chance_forces_dnp():
    result = ParticipationStateHybridModel().predict(
        pd.DataFrame([
            _row(
                chance_of_playing=0.0,
                has_availability_snapshot=True,
                is_immediate_next_gw=True,
            )
        ]),
        horizon=1,
    ).iloc[0]

    assert result["p_dnp"] == 1.0
    assert result["projected_minutes"] == 0.0


def test_later_fixture_does_not_reuse_immediate_zero_chance():
    result = ParticipationStateHybridModel().predict(
        pd.DataFrame([
            _row(
                chance_of_playing=0.0,
                has_availability_snapshot=True,
                is_immediate_next_gw=False,
            )
        ]),
        horizon=1,
    ).iloc[0]

    assert result["projected_minutes"] > 0.0


def _full_start(**overrides: object) -> dict[str, object]:
    return _row(
        p_dnp=0.0,
        p_start=1.0,
        p_sub_in=0.0,
        xmins_if_start=90.0,
        p_60_if_start=1.0,
        **overrides,
    )


def test_harder_defence_multiplier_increases_keeper_save_xp():
    model = ParticipationStateHybridModel()
    easy = model.predict(
        pd.DataFrame([
            _full_start(
                position_id=1,
                per90_saves=4.0,
                attack_multiplier=1.0,
                defence_multiplier=0.4,
            )
        ]),
        horizon=1,
    ).iloc[0]
    hard = model.predict(
        pd.DataFrame([
            _full_start(
                position_id=1,
                per90_saves=4.0,
                attack_multiplier=1.0,
                defence_multiplier=1.8,
            )
        ]),
        horizon=1,
    ).iloc[0]

    assert easy["xp_saves"] > 0.0
    assert hard["xp_saves"] > easy["xp_saves"]


def test_harder_defence_multiplier_increases_defender_defcon_xp():
    model = ParticipationStateHybridModel()
    easy = model.predict(
        pd.DataFrame([
            _full_start(
                position_id=2,
                per90_defensive_contribution=8.0,
                attack_multiplier=1.0,
                defence_multiplier=0.4,
            )
        ]),
        horizon=1,
    ).iloc[0]
    hard = model.predict(
        pd.DataFrame([
            _full_start(
                position_id=2,
                per90_defensive_contribution=8.0,
                attack_multiplier=1.0,
                defence_multiplier=1.8,
            )
        ]),
        horizon=1,
    ).iloc[0]

    assert easy["xp_defcon"] > 0.0
    assert hard["xp_defcon"] > easy["xp_defcon"]


def test_save_and_defcon_xp_ignore_attack_multiplier():
    model = ParticipationStateHybridModel()
    weak_attack = model.predict(
        pd.DataFrame([
            _full_start(
                position_id=1,
                per90_saves=4.0,
                per90_defensive_contribution=8.0,
                attack_multiplier=0.4,
                defence_multiplier=1.0,
            )
        ]),
        horizon=1,
    ).iloc[0]
    strong_attack = model.predict(
        pd.DataFrame([
            _full_start(
                position_id=1,
                per90_saves=4.0,
                per90_defensive_contribution=8.0,
                attack_multiplier=1.8,
                defence_multiplier=1.0,
            )
        ]),
        horizon=1,
    ).iloc[0]
    easy_def = model.predict(
        pd.DataFrame([
            _full_start(
                position_id=2,
                per90_defensive_contribution=8.0,
                attack_multiplier=0.4,
                defence_multiplier=1.0,
            )
        ]),
        horizon=1,
    ).iloc[0]
    hard_def = model.predict(
        pd.DataFrame([
            _full_start(
                position_id=2,
                per90_defensive_contribution=8.0,
                attack_multiplier=1.8,
                defence_multiplier=1.0,
            )
        ]),
        horizon=1,
    ).iloc[0]

    assert weak_attack["xp_saves"] == pytest.approx(strong_attack["xp_saves"])
    assert easy_def["xp_defcon"] == pytest.approx(hard_def["xp_defcon"])


def test_supplied_defence_multiplier_overrides_fdr_for_saves():
    model = ParticipationStateHybridModel()
    fdr_hard = model.predict(
        pd.DataFrame([_full_start(position_id=1, per90_saves=4.0, difficulty=5.0)]),
        horizon=1,
    ).iloc[0]
    seeded_easy = model.predict(
        pd.DataFrame([
            _full_start(
                position_id=1,
                per90_saves=4.0,
                difficulty=5.0,
                attack_multiplier=1.0,
                defence_multiplier=0.4,
            )
        ]),
        horizon=1,
    ).iloc[0]

    assert seeded_easy["xp_saves"] < fdr_hard["xp_saves"]


def test_missing_strength_uses_official_fdr_for_saves_and_defcon():
    model = ParticipationStateHybridModel()
    easy_saves = model.predict(
        pd.DataFrame([_full_start(position_id=1, per90_saves=4.0, difficulty=2.0)]),
        horizon=1,
    ).iloc[0]
    hard_saves = model.predict(
        pd.DataFrame([_full_start(position_id=1, per90_saves=4.0, difficulty=5.0)]),
        horizon=1,
    ).iloc[0]
    easy_defcon = model.predict(
        pd.DataFrame([
            _full_start(position_id=2, per90_defensive_contribution=8.0, difficulty=2.0)
        ]),
        horizon=1,
    ).iloc[0]
    hard_defcon = model.predict(
        pd.DataFrame([
            _full_start(position_id=2, per90_defensive_contribution=8.0, difficulty=5.0)
        ]),
        horizon=1,
    ).iloc[0]

    assert hard_saves["xp_saves"] > easy_saves["xp_saves"]
    assert hard_defcon["xp_defcon"] > easy_defcon["xp_defcon"]
