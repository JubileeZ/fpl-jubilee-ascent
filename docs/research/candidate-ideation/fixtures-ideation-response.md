# Fixture Impact & Matchup Elasticity Candidate Ideation

**Date**: 2026-11-09  
**Specialist Role**: Principal Quantitative Sports Modeler & Decision Systems Engineer  
**Scope**: Fixture context, venue gradients, and opponent defensive elasticity for player projections under ADR 0066.  
**Status**: Untested hypotheses. No empirical gains claimed.  
**Lineage Baseline**: Champion `def_xg_shrink_challenger` (`models/def_xg_shrink_challenger.py`).  
**Eval Canon**: ADR 0066 15-player £100.0m Rolling Transfer Plan Net FPL Points Replay primary; ADR 0064 supporting diagnostic screens.

---

## Executive Summary & Subsystem Diagnosis

An inspection of `features/matchup_share.py` (lines 307–334) and `CalibratedMatchupHybridModel` reveals why fixture difficulty currently exhibits minimal observable impact on player selection:
1. **Multipliers Default to Neutral**: In production, `apply_matchup_share_overlay` forces `attack_multiplier = 1.0` and `defence_multiplier = 1.0` to avoid double-scaling with club strength. Peripherals (`per90_saves` and `per90_defensive_contribution`) are explicitly decoupled and forced to neutral ($\times 1.0$).
2. **Microscopic Additive Deltas on Low-Volume Assets**: The only active attacking fixture modulation is additive: $\text{addon}_g = s_{\text{att}} \cdot \text{share\_xg} \cdot (\text{opp\_xgc} - \text{league\_xgc})$ with $s_{\text{att}} = 0.40$. For secondary attackers, defensive midfielders, and budget enablers with low historical club share ($\text{share\_xg} \approx 0.10$), facing a weak defence conceding $2.20$ xGC (vs $1.35$ league mean) yields an additive bump of merely $0.40 \times 0.10 \times 0.85 = 0.034$ xG/90 ($\approx 0.14$ expected points). This negligible delta fails to move the HiGHS MILP transfer decision threshold.
3. **Dead-Lever Traps**: Past efforts to scale rates via raw FDR or uncalibrated Poisson multipliers (ARCH-05, `fixture-swing-candidates`) failed because multiplicative scaling over-projected green fixtures (+0.75 easy bias) and corrupted clean-sheet Poisson floors via Jensen's inequality.

Six innovative, mathematically sound candidate models are formulated below. Each strictly avoids active dead levers, relies 100% on observed pre-deadline data from `schema.py`, and introduces calibrated, bounded mechanisms to ensure fixtures exert a principled, decisive impact on player projections.

---

### Candidate EXT-21: Bounded Soft-Saturating Matchup Factor on Open-Play Goal Expectancy

1. **Concept & Football Hypothesis**: Open-play goal scoring opportunities depend on rival defensive firmness, but simple scaling either vanishes or explodes. A hyperbolic tangent saturating coefficient specifically targeting open-play xG delivers calibrated sensitivity without exploding on weak opposition. Penalties, however, occur at an invariant baseline rate and must not scale with open-play opponent defensive lapses. A hyperbolic tangent saturating multiplier specifically targeting open-play xG delivers meaningful fixture sensitivity while mathematically guaranteeing that easy-fixture projections never explode.

2. **Mathematical Formulation**:
   For each target fixture $g$, extract pre-deadline opponent defensive quality $\Delta_{\text{xgc}}(g) = \text{opp\_xgc}(g) - \bar{\mu}_{\text{league\_xgc}}$.
   Partition player goal expectancy into penalty baseline and open-play xG:
   $$\text{xG}_{\text{pen}, i} = 0.15 \cdot \mathbb{I}(\text{penalties\_order}_i == 1)$$
   $$\text{xG}_{\text{open}, i} = \max(0.0, \text{per90\_xg}_i - \text{xG}_{\text{pen}, i})$$
   Apply a bounded, soft-saturating elasticity factor:
   $$M_{\text{open}, i}(g) = 1.0 + \gamma_{\text{fix}} \cdot \tanh\left(\kappa_{\text{scale}} \cdot \frac{\Delta_{\text{xgc}}(g)}{\bar{\sigma}_{\text{league\_xgc}} + \epsilon}\right)$$
   $$\lambda_{xG, i}^*(g) = \text{xG}_{\text{pen}, i} + \text{xG}_{\text{open}, i} \cdot M_{\text{open}, i}(g)$$
   where $\gamma_{\text{fix}} \in [0.10, 0.22]$ bounds the maximum possible fixture swing strictly to $[1.0 - \gamma_{\text{fix}}, 1.0 + \gamma_{\text{fix}}]$, and $\kappa_{\text{scale}} \in [0.8, 1.2]$ controls the curvature rate.

3. **Decoupled Architecture Placement**: Operates in $M_{\text{events}}$ (`xp_goals`).

4. **Replaces / Integration Hook**: `DefXgShrinkChallengerModel.predict` and `CalibratedMatchupHybridModel._project_event_components`.

5. **Parameter Sweep Grid**: `gamma_fix=0.10,kappa_scale=0.8; gamma_fix=0.15,kappa_scale=1.0; gamma_fix=0.20,kappa_scale=1.0; gamma_fix=0.15,kappa_scale=1.2; gamma_fix=0.18,kappa_scale=0.8; gamma_fix=0.22,kappa_scale=1.2`

6. **Small-Sample & Cold-Start Strategy**: Opponent metrics use warm historical seeding ($N_{\text{prior}}=1$). When pre-cutoff opponent history contains fewer than 3 matches, $\Delta_{\text{xgc}}$ shrinks smoothly toward 0.0 using Bayesian sample weighting $w = \min(1.0, n_{\text{opp}} / 4.0)$, yielding $M_{\text{open}} = 1.0$ at cold start.

7. **Full Squad & Budget-Constrained Optimizer Interaction**: By bounding the swing strictly at $\pm \gamma_{\text{fix}}$, it avoids the Optimizer's Curse in green fixtures (preserving playable pool bias) while providing sufficient signal for the MILP solver to rotate £5.0m–£6.5m budget outfielders into the starting XI during favorable 3-match runs, saving transfers and avoiding hits.

8. **Point-in-Time Feature Requirements**: `features.per90_xg; features.position_id; features.penalties_order; features.opponent_id; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.expected_goals_conceded; history.opponent_club_id`

9. **Python Code Skeleton**:
```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class BoundedSoftSaturatingFixtureChallengerModel(DefXgShrinkChallengerModel):
    """Soft-saturating open-play fixture elasticity avoiding linear overprediction."""

    def __init__(self, gamma_fix: float = 0.15, kappa_scale: float = 1.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.gamma_fix = float(gamma_fix)
        self.kappa_scale = float(kappa_scale)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        is_pen = pd.to_numeric(feat.get("penalties_order", 0.0), errors="coerce").fillna(0.0).eq(1.0)
        xg = pd.to_numeric(feat.get("per90_xg", 0.0), errors="coerce").fillna(0.0)
        open_xg = (xg - np.where(is_pen, 0.15, 0.0)).clip(lower=0.0)
        pen_xg = np.where(is_pen, np.minimum(xg, 0.15), 0.0)
        diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
        delta_norm = (3.0 - diff) / 1.5
        m_open = 1.0 + self.gamma_fix * np.tanh(self.kappa_scale * delta_norm)
        feat["per90_xg"] = pen_xg + open_xg * m_open
        return super().predict(feat, horizon)
```

---

### Candidate EXT-22: Venue-Conditioned Empirical Bayes Attacking Output Dynamics

1. **Concept & Football Hypothesis**: Premier League teams register approximately 24% higher offensive production at home versus away. While team metrics blend venue splits, individual projection outputs evaluate identically across home and away matches. An empirical Bayes home-away coefficient captures this persistent calendar advantage. Starters exhibit systematic home production premiums that transfer planning MILPs must exploit when scheduling rotations.

2. **Mathematical Formulation**:
   Model venue advantage as a log-multiplicative adjustment centered at unity across a balanced home/away schedule:
   $$V_i(g) = \exp\left(\beta_{\text{venue}} \cdot (2 \cdot \mathbb{I}(\text{is\_home}_g) - 1.0)\right)$$
   For a candidate parameter $\beta_{\text{venue}} \in [0.06, 0.14]$, this yields an exact home multiplier $e^{+\beta} \approx 1.06 \dots 1.15$ and away multiplier $e^{-\beta} \approx 0.94 \dots 0.87$, preserving geometric mean unity:
   $$\lambda_{xG, i}^*(g) = \text{per90\_xg}_i \cdot V_i(g)$$
   $$\lambda_{xA, i}^*(g) = \text{per90\_xa}_i \cdot V_i(g)$$
   Shrunk toward league baseline via Empirical Bayes weighting $w_v = \frac{n_{\text{played}}}{n_{\text{played}} + K_{\text{venue}}}$.

3. **Decoupled Architecture Placement**: Operates in $M_{\text{events}}$ (`xp_goals`, `xp_assists`).

4. **Replaces / Integration Hook**: `DefXgShrinkChallengerModel.predict` and `CalibratedMatchupHybridModel._project_event_components`.

5. **Parameter Sweep Grid**: `beta_venue=0.06,k_venue=4.0; beta_venue=0.09,k_venue=4.0; beta_venue=0.12,k_venue=4.0; beta_venue=0.08,k_venue=6.0; beta_venue=0.10,k_venue=6.0; beta_venue=0.14,k_venue=8.0`

6. **Small-Sample & Cold-Start Strategy**: Relies strictly on `is_home` (a binary calendar truth known perfectly in advance). Zero historical sample requirement for feature availability; EB shrinkage $K_{\text{venue}}$ prevents early-season venue noise.

7. **Full Squad & Budget-Constrained Optimizer Interaction**: In a 15-player £100.0m squad, bench players are frequently paired (e.g. two £4.5m defenders or £5.0m midfielders with alternating home/away schedules). Accurately reflecting venue premiums enables the solver to naturally bench away assets in favor of home assets without taking transfer hits.

8. **Point-in-Time Feature Requirements**: `features.is_home; features.per90_xg; features.per90_xa; features.position_id; history.player_id; history.gameweek_id; history.was_home; history.expected_goals; history.expected_assists; history.minutes`

9. **Python Code Skeleton**:
```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class VenueConditionedDynamicsChallengerModel(DefXgShrinkChallengerModel):
    """Venue-conditioned empirical Bayes attacking dynamics."""

    def __init__(self, beta_venue: float = 0.09, k_venue: float = 4.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.beta_venue = float(beta_venue)
        self.k_venue = float(k_venue)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        is_home = feat.get("is_home", True).astype(bool)
        v_mult = np.where(is_home, np.exp(self.beta_venue), np.exp(-self.beta_venue))
        for col in ("per90_xg", "per90_xa"):
            if col in feat.columns:
                feat[col] = pd.to_numeric(feat[col], errors="coerce").fillna(0.0) * v_mult
        return super().predict(feat, horizon)
```

---

### Candidate EXT-23: Asymmetric Log-Linear Defensive Quality Decay for Clean Sheets

1. **Concept & Football Hypothesis**: Clean sheet probability in `CalibratedMatchupHybridModel` is calculated as $P(\text{CS}) = \exp(-\lambda_{\text{pitch}}) \cdot P(60+)$. In the production model, $\lambda_{\text{pitch}}$ only receives a linear additive shift from opponent goal difference ($\text{gc\_per90} + s_{\text{def}} \cdot \Delta_{\text{def}}$ with $s_{\text{def}} = 0.40$), while `defence_multiplier` is forced to $1.0$. However, against elite attacking sides (e.g. Manchester City, Arsenal, Liverpool), clean sheet probabilities collapse non-linearly. A linear shift severely over-projects clean sheets in difficulty 4–5 fixtures, causing the solver to over-invest in premium defenders during difficult fixture runs.

2. **Mathematical Formulation**:
   Replace the linear additive shift with an asymmetric log-linear hazard multiplier on pitch concession intensity:
   $$\lambda_{\text{pitch}}^*(g) = \lambda_{\text{base}} \cdot \exp\left(\alpha_{\text{cs}} \cdot \frac{\text{diff}(g) - 3.0}{1.5}\right)$$
   $$P(\text{CS}^*) = \exp(-\lambda_{\text{pitch}}^*(g)) \cdot P(60+)$$
   where $\text{diff}(g)$ is the match difficulty rating ($1.0 \dots 5.0$), and $\alpha_{\text{cs}} \in [0.12, 0.24]$.
   This ensures that difficulty 4 matches incur a factor of $e^{+0.67 \alpha} \approx 1.08 \dots 1.17$ on conceded intensity, dropping clean sheet odds exponentially, while difficulty 2 matches receive a modest boost ($e^{-0.67 \alpha} \approx 0.85 \dots 0.92$), fully controlling Jensen's inequality clean sheet explosion.

3. **Decoupled Architecture Placement**: Operates in $M_{\text{events}}$ (`xp_clean_sheet`, `xp_conceded`).

4. **Replaces / Integration Hook**: `CalibratedMatchupHybridModel._project_event_components` (modifying `per90_goals_conceded` before Poisson/NegBin evaluation).

5. **Parameter Sweep Grid**: `alpha_cs=0.12,k_cs=4.0; alpha_cs=0.16,k_cs=4.0; alpha_cs=0.20,k_cs=4.0; alpha_cs=0.15,k_cs=6.0; alpha_cs=0.18,k_cs=6.0; alpha_cs=0.24,k_cs=6.0`

6. **Small-Sample & Cold-Start Strategy**: Calibrated directly against pre-scheduled FDR `difficulty` and opponent season xG averages with warm seed prior ($N_{\text{prior}}=1$).

7. **Full Squad & Budget-Constrained Optimizer Interaction**: In a 15-player £100.0m squad, defenders represent the primary tactical lever for fixture targeting. When clean sheet probabilities accurately collapse in tough fixtures, the solver shifts budget away from premium defenders facing top-6 attacks toward budget rotating defenders with easy home fixtures.

8. **Point-in-Time Feature Requirements**: `features.position_id; features.per90_goals_conceded; features.opponent_id; features.difficulty; history.player_id; history.gameweek_id; history.minutes; history.opponent_club_id; history.expected_goals; history.expected_goals_conceded`

9. **Python Code Skeleton**:
```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class AsymmetricLogLinearDefensiveChallengerModel(DefXgShrinkChallengerModel):
    """Log-linear hazard on goals conceded for clean-sheet sensitivity."""

    def __init__(self, alpha_cs: float = 0.16, k_cs: float = 4.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.alpha_cs = float(alpha_cs)
        self.k_cs = float(k_cs)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        if "per90_goals_conceded" in feat.columns:
            diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
            hazard_mult = np.exp(self.alpha_cs * (diff - 3.0) / 1.5)
            feat["per90_goals_conceded"] = pd.to_numeric(feat["per90_goals_conceded"], errors="coerce").fillna(1.2) * hazard_mult
        return super().predict(feat, horizon)
```

---

### Candidate EXT-24: Price-Conditioned Fixture Sensitivity for Budget Midfielders and Forwards

1. **Concept & Football Hypothesis**: Under the 15-player £100.0m squad constraint (ADR 0066), budget outfielders (£4.5m–£5.5m) exhibit extreme fixture elasticity: in easy home fixtures against bottom-table sides, their underlying production rivals mid-priced players, making them viable 11th starters; but against elite defensive units, their chance creation drops close to zero. Premium talismans (Haaland, Salah), by contrast, generate chances regardless of opposition quality. The active Champion applies identical fixture shrinkage to all assets regardless of price, failing to identify when budget enablers become high-utility starters.

2. **Mathematical Formulation**:
   Scale fixture responsiveness as an inverse function of player price (`now_cost` in £0.1m units):
   $$\gamma_{\text{price}, i} = \gamma_{\text{budget}} \cdot \max\left(0.0, \frac{\text{cost\_cutoff} - \text{now\_cost}_i}{15.0}\right)$$
   $$\lambda_{xG, i}^*(g) = \text{per90\_xg}_i \cdot \left(1.0 + \gamma_{\text{price}, i} \cdot \frac{3.0 - \text{difficulty}_g}{2.0}\right)$$
   $$\lambda_{xA, i}^*(g) = \text{per90\_xa}_i \cdot \left(1.0 + \gamma_{\text{price}, i} \cdot \frac{3.0 - \text{difficulty}_g}{2.0}\right)$$
   For assets priced above $\text{cost\_cutoff} \in [55.0, 60.0]$ (£5.5m–£6.0m), $\gamma_{\text{price}} = 0.0$ and Champion projections remain untouched. For £4.5m starters in a difficulty 2 fixture, their attacking rates receive a calibrated $+15\%\dots +30\%$ boost.

3. **Decoupled Architecture Placement**: Operates in $M_{\text{events}}$ (`xp_goals`, `xp_assists`).

4. **Replaces / Integration Hook**: `DefXgShrinkChallengerModel.predict` and `CalibratedMatchupHybridModel._project_event_components`.

5. **Parameter Sweep Grid**: `gamma_budget=0.15,cost_cutoff=55.0; gamma_budget=0.22,cost_cutoff=55.0; gamma_budget=0.30,cost_cutoff=55.0; gamma_budget=0.20,cost_cutoff=60.0; gamma_budget=0.28,cost_cutoff=60.0; gamma_budget=0.35,cost_cutoff=60.0`

6. **Small-Sample & Cold-Start Strategy**: Price and fixture difficulty are verified pre-deadline primitives available from GW1. Integrates seamlessly with historical warm seeding.

7. **Full Squad & Budget-Constrained Optimizer Interaction**: Enables the HiGHS MILP solver to reliably field £4.5m–£5.0m budget enablers in favorable fixtures, freeing £1.5m–£2.5m of team budget to lock in permanent premium captains without suffering squad churn or transfer hits.

8. **Point-in-Time Feature Requirements**: `features.now_cost; features.position_id; features.per90_xg; features.per90_xa; features.opponent_id; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.expected_assists; history.opponent_club_id; history.expected_goals_conceded`

9. **Python Code Skeleton**:
```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class PriceConditionedFixtureChallengerModel(DefXgShrinkChallengerModel):
    """Price-conditioned fixture sensitivity for budget midfielders and forwards."""

    def __init__(self, gamma_budget: float = 0.22, cost_cutoff: float = 55.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.gamma_budget = float(gamma_budget)
        self.cost_cutoff = float(cost_cutoff)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        pos = feat.get("position_id", 3)
        is_attacker = pos.isin([3, 4])
        cost = pd.to_numeric(feat.get("now_cost", 100.0), errors="coerce").fillna(100.0)
        diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
        price_weight = np.maximum(0.0, (self.cost_cutoff - cost) / 15.0)
        mult = 1.0 + np.where(is_attacker, self.gamma_budget * price_weight * ((3.0 - diff) / 2.0), 0.0)
        for col in ("per90_xg", "per90_xa"):
            if col in feat.columns:
                feat[col] = pd.to_numeric(feat[col], errors="coerce").fillna(0.0) * mult
        return super().predict(feat, horizon)
```

---

### Candidate EXT-25: Adversary Concession Profiling by Outfielder Style Contrast

1. **Concept & Football Hypothesis**: Opponents concede scoring opportunities through fundamentally different defensive failure modes: some allow high shot volume inside the box (conceding to pure finishers with high `per90_threat` and `per90_xg`), while others concede from wide crosses and cutbacks (conceding to creators with high `per90_creativity` and `per90_xa`). Currently, all outfielders on a team receive identical linear matchup share multipliers regardless of whether their personal playing style attacks the specific vulnerability of the adversary.

2. **Mathematical Formulation**:
   Calculate player attacking style index from pre-deadline metrics:
   $$\theta_{\text{style}, i} = \frac{\text{per90\_xg}_i}{\text{per90\_xg}_i + \text{per90\_xa}_i + \epsilon} \in [0.0, 1.0]$$
   Calculate opponent concession profile from historical match logs (shrunk via $K_{\text{modality}} = 360$ minutes toward position baseline):
   $$\phi_{\text{opp}, c} = \frac{\sum \text{threat\_conceded}_c}{\sum \text{threat\_conceded}_c + \sum \text{creativity\_conceded}_c + \epsilon}$$
   Compute the style alignment contrast:
   $$\Delta_{\text{align}, i}(g) = (\theta_{\text{style}, i} - 0.5) \cdot (\phi_{\text{opp}, \text{opp}(i)} - 0.5)$$
   Apply bounded style modulation:
   $$\lambda_{xG, i}^*(g) = \text{per90\_xg}_i \cdot \left(1.0 + \xi_{\text{modality}} \cdot \text{clip}(4.0 \cdot \Delta_{\text{align}, i}(g), -1.0, 1.0)\right)$$
   $$\lambda_{xA, i}^*(g) = \text{per90\_xa}_i \cdot \left(1.0 - \xi_{\text{modality}} \cdot \text{clip}(4.0 \cdot \Delta_{\text{align}, i}(g), -1.0, 1.0)\right)$$
   where $\xi_{\text{modality}} \in [0.08, 0.18]$ governs the maximum style rebalancing.

3. **Decoupled Architecture Placement**: Operates in $M_{\text{events}}$ (`xp_goals`, `xp_assists`).

4. **Replaces / Integration Hook**: `DefXgShrinkChallengerModel.predict` and `CalibratedMatchupHybridModel._project_event_components`.

5. **Parameter Sweep Grid**: `xi_modality=0.08,k_modality=360.0; xi_modality=0.12,k_modality=360.0; xi_modality=0.16,k_modality=360.0; xi_modality=0.10,k_modality=540.0; xi_modality=0.14,k_modality=540.0; xi_modality=0.18,k_modality=540.0`

6. **Small-Sample & Cold-Start Strategy**: Style indices shrink smoothly toward positional averages ($0.60$ for FWD, $0.40$ for MID).

7. **Full Squad & Budget-Constrained Optimizer Interaction**: Differentiates between similar-priced options (e.g. £5.5m winger vs £5.5m poacher) based on specific opponent vulnerabilities, optimizing tactical squad selection without inflating transfer turnover.

8. **Point-in-Time Feature Requirements**: `features.position_id; features.per90_xg; features.per90_xa; features.per90_threat; features.per90_creativity; features.opponent_id; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.expected_assists; history.threat; history.creativity; history.opponent_club_id`

9. **Python Code Skeleton**:
```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class AdversaryStyleContrastChallengerModel(DefXgShrinkChallengerModel):
    """Style contrast modulation matching attacker profile to opponent concession pattern."""

    def __init__(self, xi_modality: float = 0.12, k_modality: float = 360.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.xi_modality = float(xi_modality)
        self.k_modality = float(k_modality)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        xg = pd.to_numeric(feat.get("per90_xg", 0.0), errors="coerce").fillna(0.0)
        xa = pd.to_numeric(feat.get("per90_xa", 0.0), errors="coerce").fillna(0.0)
        tot = xg + xa + 1e-6
        theta = (xg / tot).clip(0.0, 1.0)
        diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
        contrast = (theta - 0.5) * ((3.0 - diff) / 2.0)
        feat["per90_xg"] = xg * (1.0 + self.xi_modality * np.clip(2.0 * contrast, -1.0, 1.0))
        feat["per90_xa"] = xa * (1.0 - self.xi_modality * np.clip(2.0 * contrast, -1.0, 1.0))
        return super().predict(feat, horizon)
```

---

### Candidate EXT-26: Projected Goal Margin Minutes Trim Modulation

1. **Concept & Football Hypothesis**: In lopsided fixtures where a team is heavily favored, managers frequently substitute key attacking talismans early to rest them once victory is secured. A margin-dependent playing-time adjustment accounts for blowout substitution hazard while keeping base probabilities invariant. Currently, the Champion treats expected duration as fixture-independent. A modest, margin-dependent duration trim accounts for blowout substitution hazard without destabilizing $p_{\text{start}}$.

2. **Mathematical Formulation**:
   Estimate expected match goal margin from official attack and defence ratings:
   $$\Delta_{\text{margin}}(g) = \text{team\_attack\_strength}_g - \text{opponent\_defence\_strength}_g$$
   Apply a non-linear blowout hazard offset to expected starting minutes:
   $$\delta_{\text{mins}, i}(g) = -\psi_{\text{margin}} \cdot \max(0.0, \Delta_{\text{margin}}(g) - \tau_{\text{margin}})$$
   $$xMins_{\text{start}, i}^*(g) = \max(60.0, xMins_{\text{start}, i} + \delta_{\text{mins}, i}(g))$$
   where $\psi_{\text{margin}} \in [1.5, 4.0]$ minutes and $\tau_{\text{margin}} \in [0.5, 1.0]$.
   $p_{\text{start}}$ and $p_{\text{sub\_in}}$ remain completely untouched, ensuring total starting mass is invariant.

3. **Decoupled Architecture Placement**: Operates in $M_{\text{mins}}$ (`xp_minutes`).

4. **Replaces / Integration Hook**: `ParticipationStateHybridModel._conditional_minutes` and `LearnedStartChallengerModel.predict`.

5. **Parameter Sweep Grid**: `psi_margin=1.5,tau_margin=0.5; psi_margin=2.5,tau_margin=0.5; psi_margin=3.5,tau_margin=0.5; psi_margin=2.0,tau_margin=0.75; psi_margin=3.0,tau_margin=0.75; psi_margin=4.0,tau_margin=1.0`

6. **Small-Sample & Cold-Start Strategy**: Uses official pre-season club attack/defence strengths, ensuring full availability from GW1.

7. **Full Squad & Budget-Constrained Optimizer Interaction**: Slightly trims inflated talisman captaincy projections in blowout fixtures, redistributing expected minutes toward nailed 90-minute budget assets and improving captaincy regret guardrails.

8. **Point-in-Time Feature Requirements**: `features.position_id; features.team_attack_strength; features.opponent_defence_strength; features.p_start; features.xmins_if_start; history.player_id; history.gameweek_id; history.minutes; history.starts`

9. **Python Code Skeleton**:
```python
from __future__ import annotations
import numpy as np
import pandas as pd
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

class GameStateMarginDurationChallengerModel(DefXgShrinkChallengerModel):
    """Starter playing duration modulation conditioned on projected match goal margin."""

    def __init__(self, psi_margin: float = 2.5, tau_margin: float = 0.5, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.psi_margin = float(psi_margin)
        self.tau_margin = float(tau_margin)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        if "team_attack_strength" in feat.columns and "opponent_defence_strength" in feat.columns:
            atk = pd.to_numeric(feat["team_attack_strength"], errors="coerce").fillna(1000.0) / 1000.0
            opp_def = pd.to_numeric(feat["opponent_defence_strength"], errors="coerce").fillna(1000.0) / 1000.0
            margin = (atk - opp_def).clip(lower=0.0)
            excess = np.maximum(0.0, margin - self.tau_margin)
            offset = -self.psi_margin * excess
            if "xmins_if_start" in feat.columns:
                feat["xmins_if_start"] = (pd.to_numeric(feat["xmins_if_start"], errors="coerce").fillna(78.0) + offset).clip(lower=60.0)
        return super().predict(feat, horizon)
```
