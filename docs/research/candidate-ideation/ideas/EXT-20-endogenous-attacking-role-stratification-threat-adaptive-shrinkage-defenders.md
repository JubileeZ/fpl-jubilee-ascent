---
idea_id: EXT-20
name: "Endogenous Attacking-Role Stratification & Threat-Adaptive Shrinkage for Out-of-Position Defenders"
tier: P1
component: xp_goals
status: untested
replaces: "DefXgShrinkChallengerModel.predict (shrunk_xg_rates generalized to threat-adaptive defender shrinkage while preserving _BASE_K = 360.0 for MID/FWD and _POSITION_K = {2: 2400.0} for traditional defenders)."
grid: "tau_threat=12.0,k_oop=1600,gamma_oop=0.15; tau_threat=12.0,k_oop=1200,gamma_oop=0.15; tau_threat=15.0,k_oop=1200,gamma_oop=0.20; tau_threat=15.0,k_oop=800,gamma_oop=0.20; tau_threat=18.0,k_oop=1200,gamma_oop=0.25; tau_threat=18.0,k_oop=800,gamma_oop=0.25"
inputs: features.player_id; features.club_id; features.position_id; features.per90_xg; features.per90_threat; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.threat
nearest_ledger_row: null
spec_path: ideas/EXT-20-endogenous-attacking-role-stratification-threat-adaptive-shrinkage-defenders.md
---

# EXT-20: Endogenous Attacking-Role Stratification & Threat-Adaptive Shrinkage for Out-of-Position Defenders

## 1. Concept & Football Hypothesis

In `models/def_xg_shrink_challenger.py` (`_POSITION_K = {2: 2400.0}`), the active Champion shrinks all defenders (`position_id == 2`) uniformly with $K_{\text{DEF}} = 2400$ pseudo-minutes toward the league defender mean prior $\bar{\lambda}_{xG, \text{DEF}} \approx 0.06\text{ xG/90}$.
While this heavy shrinkage is mathematically necessary to stop the optimizer from chasing noisy, low-reliability set-piece header goals by central defenders (ADR 0055), it severely depresses genuine Out-of-Position (OOP) attacking defenders (e.g. wing-backs or converted wingers like Maxim De Cuyper, Pedro Porro, Lewis Hall) whose sustained open-play involvement generates legitimate attacking threat.

Specifically, a defender who averages $0.30\text{ xG/90}$ over 500 minutes receives an effective weight of only $500 / (500 + 2400) \approx 17\%$, with $83\%$ of their projection dragged down into the central-defender pool.
By using point-in-time in-game attacking involvement (`per90_threat` computed with standard $K=360$ from observed FPL match history) to endogenously stratify defenders:
1. **Traditional defenders** ($\text{threat} < \tau_{\text{threat}}$) retain $K_{\text{DEF}} = 2400.0$ and standard prior $\bar{\lambda}_{xG, \text{DEF}}$, insulating the team against center-back noise and Optimizer's Curse.
2. **Attacking / OOP defenders** ($\text{threat} \ge \tau_{\text{threat}}$) adaptively relax shrinkage to $K_{\text{OOP}} \in [450, 900]$ and elevate their prior toward the attacking defender stratum, unlocking true open-play attacking potential without manual hard-coding or telemetry leakage.

## 2. Mathematical Formulation

From pre-deadline match history $\mathcal{H}_{<g}$, compute each player's recency-decayed ($\delta = 0.95$) expected goals and threat totals, alongside pooled position rates:
$$\bar{\Theta}_{\text{pos}} = \frac{\sum_{m \in \mathcal{H}_{\text{pos}, <g}} \text{Threat}_m}{\sum_{m \in \mathcal{H}_{\text{pos}, <g}} \text{Minutes}_m} \times 90.0, \quad \bar{\lambda}_{xG, \text{pos}} = \frac{\sum_{m \in \mathcal{H}_{\text{pos}, <g}} xG_m}{\sum_{m \in \mathcal{H}_{\text{pos}, <g}} \text{Minutes}_m} \times 90.0$$
Compute each player's shrunk threat rate with baseline $K = 360.0$:
$$\hat{\Theta}_i(g) = \frac{\sum_{m \in \mathcal{H}_{i, <g}} w_m \cdot \text{Threat}_{i,m} + 360.0 \cdot \frac{\bar{\Theta}_{\text{pos}(i)}}{90.0}}{\sum_{m \in \mathcal{H}_{i, <g}} w_m \cdot \text{Minutes}_{i,m} + 360.0} \times 90.0$$
For outfield defenders ($position\_id == 2$):
$$\text{is\_oop}_i = \mathbb{I}\left(\hat{\Theta}_i(g) \ge \tau_{\text{threat}}\right)$$
Define player-specific prior $\pi_{xG, i}$ and shrinkage constant $K_i$:
$$K_i = \begin{cases} K_{\text{OOP}} & \text{if } position\_id == 2 \text{ and } \text{is\_oop}_i \\ 2400.0 & \text{if } position\_id == 2 \text{ and not } \text{is\_oop}_i \\ 360.0 & \text{if } position\_id \in \{3, 4\} \end{cases}$$
$$\pi_{xG, i} = \begin{cases} \bar{\lambda}_{xG, \text{DEF}} \cdot \left(1.0 + \gamma_{\text{oop}} \cdot \text{clip}\left(\frac{\hat{\Theta}_i(g) - \bar{\Theta}_{\text{DEF}}}{\bar{\Theta}_{\text{DEF}}}, 0.0, 2.0\right)\right) & \text{if } position\_id == 2 \text{ and } \text{is\_oop}_i \\ \bar{\lambda}_{xG, \text{pos}(i)} & \text{otherwise} \end{cases}$$
The updated xG rate is then:
$$\hat{\lambda}_{xG, i}(g) = \frac{\sum_{m \in \mathcal{H}_{i, <g}} w_m \cdot xG_{i,m} + K_i \cdot \frac{\pi_{xG, i}}{90.0}}{\sum_{m \in \mathcal{H}_{i, <g}} w_m \cdot \text{Minutes}_{i,m} + K_i} \times 90.0$$
Applied via ratio replacement `new_rate / old_rate_360` on `features.per90_xg`.

## 3. Decoupled Architecture Placement

Operates in $M_{\text{events}}$ (`xp_goals`, `xbps`, and `xp_bonus`).

## 4. Replaces / Integration Hook

`DefXgShrinkChallengerModel.predict` (`shrunk_xg_rates` generalized to threat-adaptive defender shrinkage while preserving `_BASE_K = 360.0` for MID/FWD and `_POSITION_K = {2: 2400.0}` for traditional defenders).

## 5. Parameter Sweep Grid

`tau_threat=12.0,k_oop=1600,gamma_oop=0.15; tau_threat=12.0,k_oop=1200,gamma_oop=0.15; tau_threat=15.0,k_oop=1200,gamma_oop=0.20; tau_threat=15.0,k_oop=800,gamma_oop=0.20; tau_threat=18.0,k_oop=1200,gamma_oop=0.25; tau_threat=18.0,k_oop=800,gamma_oop=0.25`

## 6. Small-Sample & Cold-Start Strategy

Uses ratio scaling `new_rate / old_rate_360` so warm seed prior and matchup overlays survive at GW1–4. When sample size is small ($\le 3$ appearances), shrunk threat reverts to $\bar{\Theta}_{\text{DEF}} \approx 10.0 < \tau_{\text{threat}}$, safely keeping new/unproven defenders at conservative $K=2400$ until empirical attacking involvement is established.

## 7. Budget-Constrained Optimizer Interaction

Allows the HiGHS MILP optimizer to discover high-ceiling £4.5m–£5.5m attacking fullbacks/wingers classified as defenders, capitalizing on the FPL scoring matrix (+6 pts/goal, +4 CS) without leaking points to low-involvement center-backs.

## 8. Point-in-Time Feature Requirements

`features.player_id`; `features.club_id`; `features.position_id`; `features.per90_xg`; `features.per90_threat`; `history.player_id`; `history.gameweek_id`; `history.minutes`; `history.expected_goals`; `history.threat`

## 9. Python Code Skeleton

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import (
    _BASE_K,
    _DECAY,
    _HIST_COLUMNS,
    _MIDFIELDER,
    _POSITION_K,
    _RATIO_CLIP,
    DefXgShrinkChallengerModel,
    shrunk_xg_rates,
)
```
