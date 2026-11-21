---
idea_id: EXT-04_1
name: Reduced weight for attacking evidence in dismissal fixtures
tier: P1
component: "xp_goals"
status: "untested"
replaces: Override _project_event_components on the Champion subclass. On rows with a positive per90_xg and an eligible position, give super() a row copy with the adjusted per90_xg. Applying this inside the event method holds the inherited minutes calculation fixed. Stock finishing offsets, penalty isolation, exposure, and bonus allocation consume the adjusted rate. Deduplicate prior player-fixture rows and verify that both historical sides are represented before forming a dismissal tag.
grid: "a=0.50; a=0.80"
inputs: features.player_id; features.club_id; features.position_id; features.per90_xg; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.minutes; history.red_cards; history.expected_goals
nearest_ledger_row: "null"
spec_path: ideas/EXT-04_1-reduced-weight-for-attacking-evidence-in-dismissal-fixtures.md
---

# EXT-04_1: Reduced weight for attacking evidence in dismissal fixtures

## 1. Concept & Football Hypothesis

A match containing a dismissal can produce an unusual attacking environment for either side. Its aggregate xG is weaker evidence of a player's ordinary opportunities. Past red-card counts identify a noisy observation without estimating a future dismissal or its timing.
## 2. Mathematical Formulation

Use a MID/FWD's current-club appearances in completed fixtures. Define R_j=1 if either side recorded a red card, and zero otherwise. Let w_j=0.95^(latest observed GW minus row GW), b=90 Σw_j xG_j/Σw_j m_j, and v_j=w_j(1−aR_j). Set d=90 Σv_j(xG_j−bm_j/90)/(360+Σv_jm_j). The passed xG/90 becomes max(0, xG/90+d). When the tagged fixtures have the same chance rate as the rest, d is zero. The tag applies to the whole fixture as a reliability weight.
## 3. Decoupled Architecture Placement

Event rate for xp_goals and the inherited goal term in xBPS.
## 4. Replaces / Integration Hook

Override _project_event_components on the Champion subclass. On rows with a positive per90_xg and an eligible position, give super() a row copy with the adjusted per90_xg. Applying this inside the event method holds the inherited minutes calculation fixed. Stock finishing offsets, penalty isolation, exposure, and bonus allocation consume the adjusted rate. Deduplicate prior player-fixture rows and verify that both historical sides are represented before forming a dismissal tag.
## 5. Parameter Sweep Grid

`a=0.50; a=0.80`
## 6. Small-Sample & Cold-Start Strategy

The seed is carried by the incoming per90_xg. Only appearances with complete, finite xG, minutes and fixture red-card coverage enter either sum. Use zero difference when either fixture class has no exposure or club identity cannot be recovered. The 360 pseudo-minutes give a continuous local evidence weight. No panel fit.
## 7. Full Squad & Budget-Constrained Optimizer Interaction

An inexpensive forward's high-xG outing against ten men can otherwise justify a transfer and several weeks of projected starts. The same mechanism can restore credit to a player whose own side lost a man. Test whether these changes improve realized points after accounting for hits and churn.
## 8. Point-in-Time Feature Requirements

`features.player_id; features.club_id; features.position_id; features.per90_xg; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.minutes; history.red_cards; history.expected_goals`
## 9. Python Code Skeleton (Auto-Scaffolded)

```python
from __future__ import annotations

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class ReducedWeightForAttackingEvidenceInDismissalFixturesChallengerModel(DefXgShrinkChallengerModel):
    """Auto-scaffolded skeleton for Reduced weight for attacking evidence in dismissal fixtures."""

    def __init__(self, a: float = 0.5, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.a = float(a)

    def _project_event_components(self, *args: object, **kwargs: object) -> object:
        # Hook target: Override _project_event_components on the Champion subclass. On rows with a positive per90_xg and an eligible position, give super() a row copy with the adjusted per90_xg. Applying this inside the event method holds the inherited minutes calculation fixed. Stock finishing offsets, penalty isolation, exposure, and bonus allocation consume the adjusted rate. Deduplicate prior player-fixture rows and verify that both historical sides are represented before forming a dismissal tag.
        parent_method = getattr(super(), '_project_event_components', None)
        if callable(parent_method):
            return parent_method(*args, **kwargs)
        raise NotImplementedError('_project_event_components mechanism not yet implemented')
```

## Pre-slate Review

- Source: ideation specialist, 2026-11-21.
- Disposition: `untested`. Observed fixture dismissals weight historical xG reliability. Existing locks cover red-card probability and opponent-strength schedule adjustment. Queued for serial review after EXT-01_1.
- Evidence: [Replay input audit](../pre-slate-search-2026-11-21.md).
