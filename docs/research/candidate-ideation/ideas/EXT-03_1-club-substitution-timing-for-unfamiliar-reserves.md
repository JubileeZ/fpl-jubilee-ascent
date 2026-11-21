---
idea_id: EXT-03_1
name: Club substitution timing for unfamiliar reserves
tier: P1
component: "xp_minutes"
status: "blocked (replay evidence)"
replaces: "Adjust xmins_if_sub_in on a feature copy at Candidate.predict before delegating to DefXgShrinkChallengerModel.predict. Count a cameo as starts=0 and 0<minutes\u226490 in unique completed player-fixture rows. Use both observed sides to recover the club at the time. Use current position for current-season player IDs with known position. Hard DNPs, blank fixtures, and explicit external-minute handling follow ParticipationStateHybridModel.predict."
grid: "a=0.5; a=1.0"
inputs: features.player_id; features.club_id; features.position_id; features.xmins_if_sub_in; features.p_60_if_sub_in; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.starts; history.minutes
nearest_ledger_row: "Learned participation variants other than shipped learned_start_challenger: ridge-logistic p_start (per-position; +learned p_sub_in / xmins-if-start / club rotation; no / per-club / club\u00d7position mass), alone or with soft P(60) bonus eligibility"
spec_path: ideas/EXT-03_1-club-substitution-timing-for-unfamiliar-reserves.md
---

# EXT-03_1: Club substitution timing for unfamiliar reserves

## 1. Concept & Football Hypothesis

Some coaches introduce attacking substitutes early enough to contribute while others use short late appearances. Other players at the same club and position provide evidence about cameo duration before a reserve has established a personal record.
## 2. Mathematical Formulation

For position p, let L be mean minutes of other players' prior current-season cameos at other clubs. For the player's own club and position, let T be the sum of other players' cameo minutes and n their cameo count. Define d = (T−nL)/(n+12). Let h be the player's number of prior current-club cameos and u the inherited conditional cameo minutes. Set u' = clip(u + a d × 4/(4+h), 1+59q, 59+31q), where q is the inherited conditional chance of a 60+ cameo. Those bounds give the possible mean for a mixture of 1–59 and 60–90 minute appearances. Apply only when d is available, d is nonzero, u is within those bounds and the player is an outfielder.
## 3. Decoupled Architecture Placement

Conditional substitute minutes in the participation model. Changes expected playing time and conditional event exposure. The input to the appearance-points calculation is the inherited participation and 60+ probability.
## 4. Replaces / Integration Hook

Adjust xmins_if_sub_in on a feature copy at Candidate.predict before delegating to DefXgShrinkChallengerModel.predict. Count a cameo as starts=0 and 0<minutes≤90 in unique completed player-fixture rows. Use both observed sides to recover the club at the time. Use current position for current-season player IDs with known position. Hard DNPs, blank fixtures, and explicit external-minute handling follow ParticipationStateHybridModel.predict.
## 5. Parameter Sweep Grid

`a=0.5; a=1.0`
## 6. Small-Sample & Cold-Start Strategy

The one-season seeded u is the starting point. Twelve pseudo-cameos shrink the club contrast toward zero, and the player's own cameo record continuously reduces its influence. Use u for missing position, missing reference group, zero club observations, or invalid inputs. No fitted coefficients or population activation gate.
## 7. Full Squad & Budget-Constrained Optimizer Interaction

Two same-price reserves can have similar appearance probabilities but different expected playing time when called on. This can change the value of cover behind an expensive starter. Stable club-level evidence should be tested against both replay gain and weekly turnover.
## 8. Point-in-Time Feature Requirements

`features.player_id; features.club_id; features.position_id; features.xmins_if_sub_in; features.p_60_if_sub_in; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.starts; history.minutes`
## 9. Python Code Skeleton (Auto-Scaffolded)

```python
from __future__ import annotations

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class ClubSubstitutionTimingForUnfamiliarReservesChallengerModel(DefXgShrinkChallengerModel):
    """Auto-scaffolded skeleton for Club substitution timing for unfamiliar reserves."""

    def __init__(self, a: float = 0.5, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.a = float(a)

    def _if_sub_in(self, *args: object, **kwargs: object) -> object:
        # Hook target: Adjust xmins_if_sub_in on a feature copy at Candidate.predict before delegating to DefXgShrinkChallengerModel.predict. Count a cameo as starts=0 and 0<minutes≤90 in unique completed player-fixture rows. Use both observed sides to recover the club at the time. Use current position for current-season player IDs with known position. Hard DNPs, blank fixtures, and explicit external-minute handling follow ParticipationStateHybridModel.predict.
        parent_method = getattr(super(), '_if_sub_in', None)
        if callable(parent_method):
            return parent_method(*args, **kwargs)
        raise NotImplementedError('_if_sub_in mechanism not yet implemented')
```

## Pre-slate Review

- Source: ideation specialist, 2026-11-21.
- Disposition: `blocked (replay evidence)`. Peer contrast shifts conditional cameo duration. Existing lock covers learned starter and appearance probabilities or starter duration. Replay inputs pending.
- Evidence: [Replay input audit](../pre-slate-search-2026-11-21.md).
