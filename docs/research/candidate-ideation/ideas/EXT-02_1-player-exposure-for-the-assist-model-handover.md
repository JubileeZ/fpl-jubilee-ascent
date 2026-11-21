---
idea_id: EXT-02_1
name: Player exposure for the assist model handover
tier: P1
component: "xp_assists"
status: "untested"
replaces: "Override MultiFeatureAssistChallengerModel._fit_assist_rates. Start with the parent's dictionary, then edit only its returned player-fixture keys. Obtain F as CalibratedMatchupHybridModel._project_event_components(self, row, position, 90.0, clean_sheet_minutes=90.0, p_sixty_mins=1.0)[\"xp_assists\"]/3. Reuse the inherited state scorer with R, which updates projected points and xBPS together."
grid: "K=180; K=450"
inputs: features.player_id; features.fixture_id; features.position_id; features.per90_xa; features.per90_creativity; features.per90_assists; features.attack_multiplier; features.difficulty; features.club_id; features.opponent_id; features.is_home; features.gameweek_id; history.player_id; history.fixture_id; history.gameweek_id; history.minutes; history.expected_goals; history.expected_assists; history.creativity; history.opponent_club_id; history.was_home
nearest_ledger_row: "Start vs sub attack intensity (pooled as-of sub/start per90 ratio rho by position; split player rate per state)"
spec_path: ideas/EXT-02_1-player-exposure-for-the-assist-model-handover.md
---

# EXT-02_1: Player exposure for the assist model handover

## 1. Concept & Football Hypothesis

When the league has enough training fixtures, the assist GLM can return a rate for a player who has barely appeared this season. Its player offset comes from current-season xA pooled toward position. The pre-existing seeded projection can still contain individual evidence about that player's creative role.
## 2. Mathematical Formulation

Let G be the inherited fitted fixture xA/90, F the stock face-value fixture assist rate, and m the player's total minutes in completed current-season fixtures before the origin. Use R = (mG + K F)/(m+K) for each outfielder with a fitted rate. F is the rate implied by the original calibrated event branch evaluated at 90 minutes on the same row. In particular its matchup adjustment is already present. Use the original event branch when G is unavailable.
## 3. Decoupled Architecture Placement

Event rate for xp_assists and its existing 12 × expected-assists contribution to xBPS.
## 4. Replaces / Integration Hook

Override MultiFeatureAssistChallengerModel._fit_assist_rates. Start with the parent's dictionary, then edit only its returned player-fixture keys. Obtain F as CalibratedMatchupHybridModel._project_event_components(self, row, position, 90.0, clean_sheet_minutes=90.0, p_sixty_mins=1.0)["xp_assists"]/3. Reuse the inherited state scorer with R, which updates projected points and xBPS together.
## 5. Parameter Sweep Grid

`K=180; K=450`
## 6. Small-Sample & Cold-Start Strategy

At zero current minutes the stock one-season seeded assist path receives all weight. If the builder used a position-price fallback, that is the available F. The GLM's existing training requirements still apply. The handover depends continuously on player exposure once G exists and introduces no second fit or population N_eff ramp.
## 7. Full Squad & Budget-Constrained Optimizer Interaction

An established £5.0m creator returning to the starting XI can retain some of last season's evidence. A low-creation player has the same protection against an upward jump to a pooled rate. A gradual handover can prevent an early transfer reversal. Its value is measured through the six-GW replay and churn guard.
## 8. Point-in-Time Feature Requirements

`features.player_id; features.fixture_id; features.position_id; features.per90_xa; features.per90_creativity; features.per90_assists; features.attack_multiplier; features.difficulty; features.club_id; features.opponent_id; features.is_home; features.gameweek_id; history.player_id; history.fixture_id; history.gameweek_id; history.minutes; history.expected_goals; history.expected_assists; history.creativity; history.opponent_club_id; history.was_home`
## 9. Python Code Skeleton (Auto-Scaffolded)

```python
from __future__ import annotations

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class PlayerExposureForTheAssistModelHandoverChallengerModel(DefXgShrinkChallengerModel):
    """Auto-scaffolded skeleton for Player exposure for the assist model handover."""

    def __init__(self, k: float = 180.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.k = float(k)

    def _fit_assist_rates(self, *args: object, **kwargs: object) -> object:
        # Hook target: Override MultiFeatureAssistChallengerModel._fit_assist_rates. Start with the parent's dictionary, then edit only its returned player-fixture keys. Obtain F as CalibratedMatchupHybridModel._project_event_components(self, row, position, 90.0, clean_sheet_minutes=90.0, p_sixty_mins=1.0)["xp_assists"]/3. Reuse the inherited state scorer with R, which updates projected points and xBPS together.
        parent_method = getattr(super(), '_fit_assist_rates', None)
        if callable(parent_method):
            return parent_method(*args, **kwargs)
        raise NotImplementedError('_fit_assist_rates mechanism not yet implemented')
```

## Pre-slate Review

- Source: ideation specialist, 2026-11-21.
- Disposition: `untested`. Current-season exposure weights two existing assist rates. Existing lock covers attack intensity split by appearance state. Queued for serial review after EXT-01_1.
- Evidence: [Replay input audit](../pre-slate-search-2026-11-21.md).
