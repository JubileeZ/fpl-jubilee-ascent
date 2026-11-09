---
idea_id: EXT-27
name: Venue-Decoupled Home Advantage
tier: P1
component: xp_goals
status: untested
replaces: "CalibratedMatchupHybridModel._project_event_components (attack multiplier input) and _project_clean_sheets ($\\lambda_{\\text{against}}$)."
grid: "eta=0.50; eta=0.75; eta=1.00; eta=0.75,goals_assists_only; eta=0.75,cs_gc_only; eta=1.00,goals_assists_only"
inputs: features.is_home; features.team_attack_strength; features.team_defence_strength; features.opponent_attack_strength; features.opponent_defence_strength; features.attack_multiplier; features.defence_multiplier; features.club_id; features.opponent_id; history.team_h_score; history.team_a_score; history.fixture_id; history.gameweek_id
nearest_ledger_row: null
spec_path: ideas/EXT-27-venue-decoupled-home-advantage.md
---

# EXT-27: Venue-Decoupled Home Advantage

## 1. Concept & Football Hypothesis

The Champion applies one shrink ($s=0.40$) to the whole strength ratio, including its home/away component. Home advantage is a league-wide effect estimated from hundreds of fixtures, far more reliable than any team-specific opponent gradient, so it should not be attenuated like one. Diagnostic: if the Champion's bias by `is_home` is already near zero, this candidate is inert and fails cheaply.
## 2. Mathematical Formulation

Champion (as documented): $m_c = 1 + s\,(R^{\text{venue}}_c - 1)$. Candidate:
   $$m^*_c = H_{v,c}\,\big(1 + s\,(R^{\text{neutral}}_c - 1)\big),\quad H_{\text{home}} = \tfrac{1+\eta\hat h}{Z},\ H_{\text{away}} = \tfrac{1-\eta\hat h}{Z}$$
   $R^{\text{neutral}}_c$ is built from venue-averaged strengths $\bar a_t = \tfrac12(a_t^{\text{home}} + a_t^{\text{away}})$. This removes the venue term from the shrunk ratio and prevents double counting. $\hat h = \frac{G_H - G_A}{G_H + G_A}$ over seed plus in-season fixtures, and $Z$ is the fixture-weighted mean, so the league mean is exactly 1. For clean sheets and goals conceded, $\lambda_{\text{against}}$ is scaled by $(1 \mp \eta\hat h)$ for the home/away team respectively.
## 3. Decoupled Architecture Placement

$M_{\text{events}}$ (`xp_goals`, `xp_assists`, `xp_clean_sheets`).
## 4. Replaces / Integration Hook

`CalibratedMatchupHybridModel._project_event_components` (attack multiplier input) and `_project_clean_sheets` ($\lambda_{\text{against}}$).
## 5. Parameter Sweep Grid

`eta=0.50; eta=0.75; eta=1.00; eta=0.75,goals_assists_only; eta=0.75,cs_gc_only; eta=1.00,goals_assists_only`
## 6. Small-Sample & Cold-Start Strategy

$\hat h$ comes from seed fixtures ($N_{\text{prior}}=1$, weight 0.5) plus in-season fixtures, so it ramps continuously with no step. Partial application ($\eta<1$) limits noise from a single seed season. No player-level parameters are fitted.
7. **Full Squad & Budget-Constrained Optimizer Interaction**: The factor is mean-preserving, so playable pool bias is unchanged by construction. It adds spread between home-heavy and away-heavy fixture runs, which the 6-GW plan replay can exploit. It adds no per-player parameter, so there is no new optimizer's-curse surface. Venue is known from the schedule, so it adds no GW-to-GW noise and little churn. £4.5m-£5.5m enablers on home-heavy runs are valued more accurately.
## 8. Point-in-Time Feature Requirements

`features.is_home; features.team_attack_strength; features.team_defence_strength; features.opponent_attack_strength; features.opponent_defence_strength; features.attack_multiplier; features.defence_multiplier; features.club_id; features.opponent_id; history.team_h_score; history.team_a_score; history.fixture_id; history.gameweek_id`
## 9. Python Code Skeleton (Optional)

```python
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class VenueDecoupledMatchupChallengerModel(DefXgShrinkChallengerModel):
    def __init__(self, eta: float = 0.75, scope: str = "all", **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.eta, self.scope = float(eta), scope
```

## Ledger Audit & Revisit Justification
- **Flagged Match**: `Defcon venue and opposition pressure scaling (Away/home venue multiplier + opp attack/team defence ratio beta 0.1-0.5)`
- **Audit Status**: Cleared (False Positive)
- **Rationale**: Flagged dead lever `def_07_venue` tested home/away scaling specifically for Defcon defensive points (tackles, interceptions, clearances, blocks). EXT-27 targets attacking and clean sheet projections by decoupling the league-wide home advantage factor from team-strength ratio shrinkage ($s=0.40$), preventing double-attenuation of home advantage. Structurally distinct from Defcon scaling; promoted to `untested`.
