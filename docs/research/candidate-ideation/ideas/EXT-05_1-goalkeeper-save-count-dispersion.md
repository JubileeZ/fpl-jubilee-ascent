---
idea_id: EXT-05_1
name: Goalkeeper save-count dispersion
tier: P1
component: "xp_saves"
status: "untested"
replaces: "In the Candidate's _project_event_components, call super(), reconstruct \u03bc for GK from CalibratedMatchupHybridModel's per90_saves \u00d7 state minutes/90 \u00d7 defence_multiplier, and substitute the new xp_saves. Use the exact inherited difficulty fallback when defence_multiplier is missing. Add the xp_saves difference to projected_points before weighting each state. Leave underlying save expectation with the normal bonus allocator."
grid: "r=3; r=8"
inputs: features.position_id; features.per90_saves; features.defence_multiplier; features.difficulty; features.xmins_if_start; features.xmins_if_sub_in
nearest_ledger_row: "DEF-08: Club SoT volume x pooled save rate (negative-binomial arm)"
spec_path: ideas/EXT-05_1-goalkeeper-save-count-dispersion.md
---

# EXT-05_1: Goalkeeper save-count dispersion

## 1. Concept & Football Hypothesis

Shots can arrive in bursts, so two goalkeepers with the same expected save count can have a different chance of earning a point for three saves than the Poisson law implies. FPL pays at three, six and subsequent thresholds.
## 2. Mathematical Formulation

For each keeper participation state retain its inherited expected saves μ. Let S follow a negative binomial with shape r, success probability r/(r+μ) and variance μ+μ²/r. Compute E[floor(S/3)] = (μ−P(S mod 3=1)−2P(S mod 3=2))/3 exactly. With ω=exp(2πi/3), P(S mod 3=k)=[1+2 Re(ω^(−k)(1+μ(1−ω)/r)^(−r))]/3. Use zero for μ=0 and clamp tiny negative roundoff to zero.
## 3. Decoupled Architecture Placement

Event distribution for xp_saves. The inherited xBPS save term uses μ.
## 4. Replaces / Integration Hook

In the Candidate's _project_event_components, call super(), reconstruct μ for GK from CalibratedMatchupHybridModel's per90_saves × state minutes/90 × defence_multiplier, and substitute the new xp_saves. Use the exact inherited difficulty fallback when defence_multiplier is missing. Add the xp_saves difference to projected_points before weighting each state. Leave underlying save expectation with the normal bonus allocator.
## 5. Parameter Sweep Grid

`r=3; r=8`
## 6. Small-Sample & Cold-Start Strategy

Inherit the normal one-season seeded keeper save rate and apply a fixed law from GW1. Missing save history follows the Champion's input defaults. This mechanism estimates no keeper-specific or population coefficients, so no minimum history or N_eff ramp is required.
## 7. Full Squad & Budget-Constrained Optimizer Interaction

The size of a threshold payout matters when comparing an inexpensive busy keeper with a more expensive clean-sheet keeper. A fixed distribution avoids week-to-week parameter refits. Keeper transfer friction and net points in the legal replay determine whether a difference affects the squad.
## 8. Point-in-Time Feature Requirements

`features.position_id; features.per90_saves; features.defence_multiplier; features.difficulty; features.xmins_if_start; features.xmins_if_sub_in`
## 9. Python Code Skeleton (Auto-Scaffolded)

```python
from __future__ import annotations

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class GoalkeeperSaveCountDispersionChallengerModel(DefXgShrinkChallengerModel):
    """Auto-scaffolded skeleton for Goalkeeper save-count dispersion."""

    def __init__(self, r: float = 3.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.r = float(r)

    def _project_event_components(self, *args: object, **kwargs: object) -> object:
        # Hook target: In the Candidate's _project_event_components, call super(), reconstruct μ for GK from CalibratedMatchupHybridModel's per90_saves × state minutes/90 × defence_multiplier, and substitute the new xp_saves. Use the exact inherited difficulty fallback when defence_multiplier is missing. Add the xp_saves difference to projected_points before weighting each state. Leave underlying save expectation with the normal bonus allocator.
        parent_method = getattr(super(), '_project_event_components', None)
        if callable(parent_method):
            return parent_method(*args, **kwargs)
        raise NotImplementedError('_project_event_components mechanism not yet implemented')
```

## Pre-slate Review

- Source: ideation specialist, 2026-11-21.
- Disposition: `untested` (back of `#206` queue). Operator ruled distinct from locked `DEF-08` (2026-11-22): standalone Negative Binomial on unchanged Champion `μ` vs bundled Club SoT rate pooling (`xp_saves` MSE share `0.0055`); low leverage, run only if `EXT-02_1`..`EXT-04_1` yield `0` qualifiers.
- Evidence: [Replay input audit](../pre-slate-search-2026-11-21.md).
