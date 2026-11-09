# External Frontier Model Fixture Ideation Response

**Date**: 2026-11-09  
**Source**: Principal Quantitative Sports Modeler (ideation slate, fixture-context focus), 2026-11-09  
**Scope**: External frontier model response to candidate model ideation prompt brief (fixture-context focus).  
**Status**: Ingested via `ingest_ideas.py`.

---

### Candidate EXT-27: Venue-Decoupled Home Advantage
1. **Concept & Football Hypothesis**: The Champion applies one shrink ($s=0.40$) to the whole strength ratio, including its home/away component. Home advantage is a league-wide effect estimated from hundreds of fixtures, far more reliable than any team-specific opponent gradient, so it should not be attenuated like one. Diagnostic: if the Champion's bias by `is_home` is already near zero, this candidate is inert and fails cheaply.
2. **Mathematical Formulation**: Champion (as documented): $m_c = 1 + s\,(R^{\text{venue}}_c - 1)$. Candidate:
   $$m^*_c = H_{v,c}\,\big(1 + s\,(R^{\text{neutral}}_c - 1)\big),\quad H_{\text{home}} = \tfrac{1+\eta\hat h}{Z},\ H_{\text{away}} = \tfrac{1-\eta\hat h}{Z}$$
   $R^{\text{neutral}}_c$ is built from venue-averaged strengths $\bar a_t = \tfrac12(a_t^{\text{home}} + a_t^{\text{away}})$. This removes the venue term from the shrunk ratio and prevents double counting. $\hat h = \frac{G_H - G_A}{G_H + G_A}$ over seed plus in-season fixtures, and $Z$ is the fixture-weighted mean, so the league mean is exactly 1. For clean sheets and goals conceded, $\lambda_{\text{against}}$ is scaled by $(1 \mp \eta\hat h)$ for the home/away team respectively.
3. **Decoupled Architecture Placement**: $M_{\text{events}}$ (`xp_goals`, `xp_assists`, `xp_clean_sheets`).
4. **Replaces / Integration Hook**: `CalibratedMatchupHybridModel._project_event_components` (attack multiplier input) and `_project_clean_sheets` ($\lambda_{\text{against}}$).
5. **Parameter Sweep Grid**: `eta=0.50; eta=0.75; eta=1.00; eta=0.75,goals_assists_only; eta=0.75,cs_gc_only; eta=1.00,goals_assists_only`
6. **Small-Sample & Cold-Start Strategy**: $\hat h$ comes from seed fixtures ($N_{\text{prior}}=1$, weight 0.5) plus in-season fixtures, so it ramps continuously with no step. Partial application ($\eta<1$) limits noise from a single seed season. No player-level parameters are fitted.
7. **Full Squad & Budget-Constrained Optimizer Interaction**: The factor is mean-preserving, so playable pool bias is unchanged by construction. It adds spread between home-heavy and away-heavy fixture runs, which the 6-GW plan replay can exploit. It adds no per-player parameter, so there is no new optimizer's-curse surface. Venue is known from the schedule, so it adds no GW-to-GW noise and little churn. £4.5m-£5.5m enablers on home-heavy runs are valued more accurately.
8. **Point-in-Time Feature Requirements**: `features.is_home; features.team_attack_strength; features.team_defence_strength; features.opponent_attack_strength; features.opponent_defence_strength; features.attack_multiplier; features.defence_multiplier; features.club_id; features.opponent_id; history.team_h_score; history.team_a_score; history.fixture_id; history.gameweek_id`
9. **Python Code Skeleton (Optional)**:
```python
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class VenueDecoupledMatchupChallengerModel(DefXgShrinkChallengerModel):
    def __init__(self, eta: float = 0.75, scope: str = "all", **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.eta, self.scope = float(eta), scope
```

### Candidate EXT-28: Schedule-Neutralized Attack Baselines
1. **Concept & Football Hypothesis**: Player per-90 baselines pool minutes at face value. A player whose recent fixtures were easy carries an inflated `per90_xg`/`per90_xa`, which is then multiplied again by a green-fixture multiplier (a double count). This is a plausible driver of easy-fixture bias. The brief documents no schedule adjustment of baselines. The locked "fixture unscaling for derived penalty takers" lever was a taker signal; this applies to all MID/FWD baselines using the already shipped multiplier.
2. **Mathematical Formulation**: For each past fixture $h$, using the shipped pre-match multiplier $m^{\text{att}}_{i,h}$:
   $$\tilde x_{i,h} = \frac{x_{i,h}}{1 + \phi\,(m^{\text{att}}_{i,h} - 1)},\qquad \hat\lambda_i = \frac{\sum_h \tilde x_{i,h}\cdot 90 + K\,\bar\lambda_{\text{pos}}}{\sum_h \text{min}_{i,h} + K}$$
   Forward projection is unchanged: $\lambda^*_i(g) = \hat\lambda_i\, m^{\text{att}}_{i,g}$. $K=360$ is unchanged. MID/FWD only, so $K_{\text{DEF}}=2400$ logic is untouched.
3. **Decoupled Architecture Placement**: $M_{\text{events}}$ (`xp_goals`, `xp_assists`).
4. **Replaces / Integration Hook**: The history aggregation feeding `per90_xg`/`per90_xa` inside `CalibratedMatchupHybridModel._project_event_components`. No new multiplier parameters are introduced.
5. **Parameter Sweep Grid**: `phi=0.50; phi=0.75; phi=1.00; phi=0.75,xg_only; phi=0.75,xa_only; phi=0.75,in_season_only`
6. **Small-Sample & Cold-Start Strategy**: Seed rows are de-matchuped with their archived multipliers ($N_{\text{prior}}=1$), which are near 1 over a full season, so GW1-4 is almost identical to the Champion. The effect grows as schedule imbalance accumulates in-season, entering continuously through $N_{\text{eff}}$ with no activation date.
7. **Full Squad & Budget-Constrained Optimizer Interaction**: It stops the solver from buying players at the peak of an easy run and from selling them after a hard run. That reduces buy-high-sell-low transfers and churn. Cheap enablers on weak sides with a hard early schedule get fair credit, which helps fund premiums. Only bias-reducing corrections are made, with no fitted per-player terms.
8. **Point-in-Time Feature Requirements**: `features.per90_xg; features.per90_xa; features.position_id; features.attack_multiplier; history.expected_goals; history.expected_assists; history.minutes; history.gameweek_id; history.fixture_id; history.was_home; history.opponent_club_id`
9. **Python Code Skeleton (Optional)**:
```python
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class ScheduleNeutralBaselineChallengerModel(DefXgShrinkChallengerModel):
    def __init__(self, phi: float = 0.75, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.phi = float(phi)
```

### Candidate EXT-29: Opponent Positional Concession Share (Mean-Preserving)
1. **Concept & Football Hypothesis**: Opponents differ in where they concede (wide areas versus central, striker versus attacking-midfield chances). ADR 0040 scales the total opponent effect, but every attacker on a club gets the same factor. A compositional reallocation across positions can sharpen fixture discrimination without raising the pool mean, so it avoids the ARCH-05 failure mode. Unlike the locked rate multipliers, it is zero-sum across positions by construction.
2. **Mathematical Formulation**: For opponent $o$, position $\pi \in \{\text{MID},\text{FWD}\}$, component $c \in \{xG, xA\}$:
   $$\hat R_{o,\pi,c} = \frac{\sum_{h:\,\text{opp}=o,\,\text{pos}=\pi} x^c_h + K_x}{\sum_{h:\,\text{opp}=o,\,\text{pos}=\pi} E^c_h + K_x},\quad E^c_h = \hat\lambda^c_{i,h}\,\tfrac{\text{min}_{i,h}}{90}$$
   $$\rho_{o,\pi,c} = \frac{\hat R_{o,\pi,c}}{\sum_{\pi'} w_{\pi',c}\,\hat R_{o,\pi',c}},\qquad \lambda^*_i = \lambda_i\,\rho_{o,\text{pos}(i),c}$$
   $w$ is the league xG share per position, so $\sum_\pi w_\pi\rho_\pi = 1$. This is a gamma-Poisson posterior mean with prior 1. The player's then-current shrunk baseline is the exposure, which removes the confound of who faced $o$. The factor is applied after the matchup share, and DEF is untouched.
3. **Decoupled Architecture Placement**: $M_{\text{events}}$ (`xp_goals`, `xp_assists`).
4. **Replaces / Integration Hook**: A new post-matchup stage in `CalibratedMatchupHybridModel._project_event_components`. ADR 0040 totals are unchanged.
5. **Parameter Sweep Grid**: `K_x=15; K_x=30; K_x=60; K_x=120; K_x=60,xg_only; K_x=60,xa_only`
6. **Small-Sample & Cold-Start Strategy**: With no exposure, $\hat R=1$ and $\rho=1$, which reproduces the Champion. Seed-season opponent records enter at weight 0.5 ($N_{\text{prior}}=1$), and the effect ramps with accumulated exposure ($N_{\text{eff}}$), so GW1-4 stays near neutral.
7. **Full Squad & Budget-Constrained Optimizer Interaction**: Mean preservation keeps the pool bias guardrail intact. The candidate improves relative valuation of MID versus FWD options in specific fixtures, which helps captaincy and transfer timing without lifting every attacker. The strong shrink ($K_x$) limits tail inflation, which is the optimizer's-curse channel. It is opponent-specific rather than player-specific, so it adds little churn. It helps pick the cheaper attacker type against a given opponent.
8. **Point-in-Time Feature Requirements**: `history.expected_goals; history.expected_assists; history.minutes; history.opponent_club_id; history.gameweek_id; history.fixture_id; features.player_id; features.position_id; features.per90_xg; features.per90_xa; features.opponent_id; features.attack_multiplier`
9. **Python Code Skeleton (Optional)**:
```python
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class PositionalConcessionShareChallengerModel(DefXgShrinkChallengerModel):
    def __init__(self, k_x: float = 60.0, components: str = "both", **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.k_x, self.components = float(k_x), components
```

### Candidate EXT-30: Component-Specific Matchup Elasticity from Team-Level Calibration Slopes
1. **Concept & Football Hypothesis**: The Champion uses one global $s=0.40$. The reliability of the attacking gradient and the defensive (clean-sheet) gradient need not match. The calibration slope can be estimated at team-fixture level (hundreds of observations per season), which is much less noisy than player-level slopes. This makes the elasticity calibrated per component instead of globally tuned.
2. **Mathematical Formulation**: Team-fixture log-link regression for $c \in \{\text{att}, \text{def}\}$: $\mathbb{E}[y_f] = \mu_c\,R_f^{\beta_c}$, with $y_f$ the team xG (att) or goals conceded (def), and $R_f$ the raw strength ratio from official strengths. First-order equivalence $s_c \approx \beta_c$. Shrunk and capped:
   $$s_c = \min\!\left(0.60,\ \frac{n_f\,\hat\beta_c + K_s\cdot 0.40}{n_f + K_s}\right),\quad n_f = 0.5\,n_{\text{seed}} + n_{\text{in-season}}$$
   $s_{\text{att}}$ drives the xG/xA multiplier and $s_{\text{def}}$ drives $\lambda_{\text{against}}$.
3. **Decoupled Architecture Placement**: $M_{\text{events}}$ (`xp_goals`, `xp_assists`, `xp_clean_sheets`).
4. **Replaces / Integration Hook**: The single $s=0.40$ constant in ADR 0040 (`attack_multiplier`, `defence_multiplier`), replaced by $s_{\text{att}}$ and $s_{\text{def}}$.
5. **Parameter Sweep Grid**: `K_s=150,att_def; K_s=300,att_def; K_s=600,att_def; K_s=300,att_only; K_s=300,def_only; K_s=300,att_def,beta_cap=0.60`
6. **Small-Sample & Cold-Start Strategy**: At GW1, $n_f$ is the seed weight only, and $K_s$ pulls both slopes toward 0.40, so the Champion is the default. In-season team-fixtures enter continuously through $N_{\text{eff}}$. This is not an ML activation and has no step.
7. **Full Squad & Budget-Constrained Optimizer Interaction**: It is calibrated at team level, so it is unbiased in-sample by construction. The 0.60 cap bounds the easy-fixture bias that sank the raw multipliers (+0.681 versus neutral +0.221). It changes fixture elasticity only, with no per-player terms, so there is little added churn. A better-calibrated $s_{\text{def}}$ affects clean-sheet value for cheap DEF/GKP enablers.
8. **Point-in-Time Feature Requirements**: `features.team_attack_strength; features.team_defence_strength; features.opponent_attack_strength; features.opponent_defence_strength; features.attack_multiplier; features.defence_multiplier; features.is_home; history.expected_goals; history.team_h_score; history.team_a_score; history.fixture_id; history.was_home`
9. **Python Code Skeleton (Optional)**:
```python
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class ComponentElasticityChallengerModel(DefXgShrinkChallengerModel):
    def __init__(self, k_s: float = 300.0, beta_cap: float = 0.60, arms: str = "att_def", **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.k_s, self.beta_cap, self.arms = float(k_s), float(beta_cap), arms
```

### Candidate EXT-31: Opponent-Sample-Reliability Matchup Share (Promoted-Club Cold Start)
1. **Concept & Football Hypothesis**: Official strength ratings for newly promoted clubs, or clubs with little Premier League data, are far less reliable than for established clubs, yet the Champion applies the same $s$ to every opponent. Fixtures involving low-sample clubs should be attenuated early in the season and ramp to the full $s$ as data accumulates. This is attenuation only, never amplification.
2. **Mathematical Formulation**: For club $t$: $n_t = 0.5\,n_{\text{seed},t} + n_{\text{in-season},t}$, $w_t = \frac{n_t}{n_t + K_t}$. Normalized to a reference established club at GW1 ($n_{\text{ref}} = 19$): $\hat w_t = \min\!\left(1,\ w_t / w_{\text{ref}}\right)$. Pair weight: $\hat w_{\text{pair}} = \sqrt{\hat w_{\text{own}}\,\hat w_{\text{opp}}}$ (or the min). Effective share:
   $$s_{\text{eff}} = s\cdot \hat w_{\text{pair}},\qquad m = 1 + s_{\text{eff}}\,(R - 1)$$
   Promoted clubs with $n_t=0$ get $s_{\text{eff}}=0$ (neutral) at GW1.
3. **Decoupled Architecture Placement**: $M_{\text{events}}$ (`xp_goals`, `xp_assists`, `xp_clean_sheets`).
4. **Replaces / Integration Hook**: The $s$ constant applied in `CalibratedMatchupHybridModel` (`attack_multiplier`, `defence_multiplier`), now per fixture.
5. **Parameter Sweep Grid**: `K_t=10; K_t=19; K_t=38; K_t=19,rule=min; K_t=38,rule=min; K_t=19,w_floor=0.25`
6. **Small-Sample & Cold-Start Strategy**: This is a cold-start mechanism. It uses the same $N_{\text{eff}}$ form with seed weight 0.5 ($N_{\text{prior}}=1$). Established clubs have $\hat w=1$ and match the Champion at GW1. Promoted clubs ramp continuously, fully by roughly GW19 at $K_t=19$. There is no activation step and no ML.
7. **Full Squad & Budget-Constrained Optimizer Interaction**: Attenuation can only move projections toward neutral, so it cannot widen easy-fixture bias, and the guardrail margin is protected. It reduces early-season transfers made on unreliable promoted-club fixture swings, cutting hits and churn in GW2-10. It limits over-reliance on fixture runs against promoted sides when funding premiums from cheap enablers.
8. **Point-in-Time Feature Requirements**: `features.club_id; features.opponent_id; features.gameweek_id; features.team_strength; features.attack_multiplier; features.defence_multiplier; history.fixture_id; history.gameweek_id; history.team_h_score; history.team_a_score; history.was_home`
9. **Python Code Skeleton (Optional)**:
```python
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class OpponentReliabilityMatchupChallengerModel(DefXgShrinkChallengerModel):
    def __init__(self, k_t: float = 19.0, rule: str = "geo", w_floor: float = 0.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.k_t, self.rule, self.w_floor = float(k_t), rule, float(w_floor)
```
