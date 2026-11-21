---
idea_id: EXT-01_1
name: Shot quality in the conceded-goal rate
tier: P1
component: "xp_clean_sheets"
status: "blocked (replay evidence)"
replaces: "In the Candidate's predict, adjust a copy of per90_goals_conceded before DefXgShrinkChallengerModel.predict. HoldChaseChallengerModel._apply_hard_fixture_defence and CalibratedMatchupHybridModel._project_event_components then apply the normal fixture treatment, exposure and scoring links. Recover the historical player's club from the other side's opponent ID within each complete fixture. Use unique player-fixture records."
grid: "a=0.5; a=1.0"
inputs: features.player_id; features.club_id; features.position_id; features.per90_goals_conceded; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.minutes; history.expected_goals_conceded; history.goals_conceded
nearest_ledger_row: "Multi-feature Poisson GLM goals-conceded rate (player xGC/opp xG/own xG conceded/home)"
spec_path: ideas/EXT-01_1-shot-quality-in-the-conceded-goal-rate.md
---

# EXT-01_1: Shot quality in the conceded-goal rate

## 1. Concept & Football Hypothesis

Two defenders can face similar chances yet concede different goal totals over a run of matches. On-pitch expected goals conceded offers a second measurement of defensive exposure. The Champion's player rate counts actual goals conceded.
## 2. Mathematical Formulation

For completed current-club appearances before the origin deadline, let x, y and m be the player's on-pitch xGC, goals conceded and minutes. Use w = 0.95^(latest observed GW minus row GW). Let d = 90 Σw(x−y)/(360+Σwm). Replace the incoming player GC/90 by max(0.05, GC/90 + a d) for GKP and DEF. This substitutes a fraction of the observed goals with chance quality, shrunk toward zero difference. The fixture addon already in the input stays in the calculation.
## 3. Decoupled Architecture Placement

Event rates for xp_clean_sheet and xp_conceded, including the inherited clean-sheet term in xBPS.
## 4. Replaces / Integration Hook

In the Candidate's predict, adjust a copy of per90_goals_conceded before DefXgShrinkChallengerModel.predict. HoldChaseChallengerModel._apply_hard_fixture_defence and CalibratedMatchupHybridModel._project_event_components then apply the normal fixture treatment, exposure and scoring links. Recover the historical player's club from the other side's opponent ID within each complete fixture. Use unique player-fixture records.
## 5. Parameter Sweep Grid

`a=0.5; a=1.0`
## 6. Small-Sample & Cold-Start Strategy

The builder supplies the usual one-season seeded baseline. The new measurement uses only rows with finite xGC, goals conceded and positive minutes, with 360 pseudo-minutes of zero difference. Empty history or an unidentified historical club gives d=0. There are no learned panel parameters requiring a separate N_eff activation.
## 7. Full Squad & Budget-Constrained Optimizer Interaction

A £4.5m defender whose side repeatedly restricted shot quality can earn a starting slot even after opponents convert several chances. One fortunate clean sheet contributes little evidence for buying a replacement keeper. Both effects can matter across a six-GW hold. Check net replay points and the Champion +0.50 players/GW churn guard separately.
## 8. Point-in-Time Feature Requirements

`features.player_id; features.club_id; features.position_id; features.per90_goals_conceded; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.minutes; history.expected_goals_conceded; history.goals_conceded`
## 9. Python Code Skeleton (Auto-Scaffolded)

```python
from __future__ import annotations

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class ShotQualityInTheConcededGoalRateChallengerModel(DefXgShrinkChallengerModel):
    """Auto-scaffolded skeleton for Shot quality in the conceded-goal rate."""

    def __init__(self, a: float = 0.5, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.a = float(a)

    def _goals_conceded(self, *args: object, **kwargs: object) -> object:
        # Hook target: In the Candidate's predict, adjust a copy of per90_goals_conceded before DefXgShrinkChallengerModel.predict. HoldChaseChallengerModel._apply_hard_fixture_defence and CalibratedMatchupHybridModel._project_event_components then apply the normal fixture treatment, exposure and scoring links. Recover the historical player's club from the other side's opponent ID within each complete fixture. Use unique player-fixture records.
        parent_method = getattr(super(), '_goals_conceded', None)
        if callable(parent_method):
            return parent_method(*args, **kwargs)
        raise NotImplementedError('_goals_conceded mechanism not yet implemented')
```

## Pre-slate Review

- Source: ideation specialist, 2026-11-21.
- Disposition: `blocked (replay evidence)`. Fixed within-player xGC-minus-GC measurement adjustment. Existing lock covers fitted multifeature concession GLM. Replay inputs pending.
- Evidence: [Replay input audit](../pre-slate-search-2026-11-21.md).
