# Champion Model Context: `def_xg_shrink_challenger`

**Document version**: 1.0.0  
**Updated**: 2026-10-14  
**Authoritative source**: `config/model_selection.json` (`champion`), `models/def_xg_shrink_challenger.py`  
**Purpose**: Comprehensive technical context on the active FPL-Jubilee-Ascent Model Champion for external AI agents and researchers proposing candidate models and algorithmic improvements.

---

## 1. Executive Summary & Project Identity

- **Repository**: FPL score projection and optimization engine. Ingests official FPL API data, evaluates models using backtesting, and generates transfer plans via Mixed-Integer Linear Programming (MILP).
- **Active Champion**: `def_xg_shrink_challenger` (promoted 2026-10-01 under ADR 0055).
- **Core Identity of Champion**: An empirical Bayes event-component model that models participation through mutually exclusive states (DNP, Start, Sub-in), predicts per-90 event rates through shrunk metrics and GLMs, calculates fixture outcomes through the FPL scoring matrix, and applies heavy shrinkage ($K=2400$ pseudo-minutes) to defender xG to eliminate optimizer's curse on noisy attacking returns.

---

## 2. Complete Inheritance Lineage & Architecture

The Champion model is structured as an object-oriented inheritance chain. Each class adds or refines a specific statistical mechanism:

```
BaseModel (models/base.py)
  └── ComponentBaselineModel (models/component_baseline.py)
        └── MetricsComponentHybridModel (models/metrics_component_hybrid.py)
              └── ParticipationStateHybridModel (models/participation_state_hybrid.py)
                    └── CalibratedMatchupHybridModel (models/calibrated_matchup_hybrid.py)
                          └── HoldChaseChallengerModel (models/hold_chase_challenger.py)
                                └── FaceValueChallengerModel (models/face_value_challenger.py)
                                      └── MultiFeatureAssistChallengerModel (models/multi_feature_assist_challenger.py)
                                            └── LearnedStartChallengerModel (models/learned_start_challenger.py)
                                                  └── DefXgShrinkChallengerModel [CHAMPION] (models/def_xg_shrink_challenger.py)
```

### Layer-by-Layer Breakdown

### 1. `MetricsComponentHybridModel` (`models/metrics_component_hybrid.py`)
- **Event-Level Empirical Bayes**: Instead of predicting total fantasy points directly, the model projects individual underlying match events (goals, assists, clean sheets, goals conceded, saves, defensive contributions, cards, bonus) and passes them through the exact FPL rules scoring matrix (`models/scoring_matrix.py`).
- **Scoring Matrix Reconstruct**:
  - Goals: Positional points (GK/DEF: 6 pts, MID: 5 pts, FWD: 4 pts).
  - Clean Sheets: Poisson probability of pitch clean sheet ($e^{-\lambda_{\text{pitch}}}$) multiplied by $P(60+\text{ mins})$ (GK/DEF: 4 pts, MID: 1 pt).
  - Goals Conceded: Negative Binomial expectation $\mathbb{E}[\lfloor X / 2 \rfloor]$ with dispersion $r=3.0$ ($-1$ pt per 2 goals conceded for GK/DEF).
  - Defensive Contribution (Defcon): Negative Binomial probability of achieving $\ge 10$ (DEF) or $\ge 12$ (MID/FWD) tackles/interceptions/blocks (+2 pts).
  - Saves: Expected Poisson floor $\mathbb{E}[\lfloor \text{saves} / 3 \rfloor]$ (+1 pt per 3 saves for GK).
  - Bonus Points System (xBPS): Synthetic BPS score generated from event rates and minutes ($0.1 \times \text{mins} + 24 \times \text{goals} + 12 \times \text{assists} + 12 \times \text{CS} + 6 \times \text{defcon} + 2 \times \text{saves}$).

### 2. `ParticipationStateHybridModel` (`models/participation_state_hybrid.py`)
- **Mutually Exclusive Participation States**: Every fixture outcome is evaluated under three distinct states:
  $$P(\text{DNP}) + P(\text{Start}) + P(\text{Sub-in}) = 1.0$$
- **Conditional Minutes**:
  - $xMins_{\text{start}}$: Player's expected minutes if starting (default $\approx 78.0$ min).
  - $xMins_{\text{sub}}$: Player's expected minutes if substituted in (default $\approx 18.0$ min).
  - $P(60+\mid \text{state}) = \text{clip}\left(\frac{\text{minutes} - 45.0}{30.0}, 0.0, 1.0\right)$.
  - Expected Minutes: $\mathbb{E}[\text{Mins}] = P(\text{Start}) \cdot xMins_{\text{start}} + P(\text{Sub-in}) \cdot xMins_{\text{sub}}$.
- **Operational Hard DNP (ADR 0056)**:
  - If immediate next GW has official FPL status $\in \{\text{'i'}, \text{'s'}, \text{'u'}, \text{'n'}\}$ or `chance_of_playing` $\le 0\%$, $P(\text{DNP}) = 1.0, P(\text{Start}) = 0.0, P(\text{Sub-in}) = 0.0$.
- **External Minutes Override Hook**:
  - If `external_xmins` is provided, `target_to_states()` converts external scalar minutes directly into $(p_{\text{start}}, p_{\text{sub}}, p_{\text{dnp}}, m_{\text{start}}, m_{\text{sub}})$.

### 3. `CalibratedMatchupHybridModel` (`models/calibrated_matchup_hybrid.py`)
- **Calibrated Matchup Share (ADR 0040)**: Replaces raw FDR with an empirical shrinkage of club attacking and defensive strength:
  - Attacking multiplier: Opponent defensive vulnerability scaled to league average.
  - Defensive multiplier: Opponent attacking threat scaled to league average.
  - Shrunk delta $s = 0.40$ toward neutral ($1.0$).
- **Model-Only Penalty Isolation**: Penalties are isolated so spot-kick duties don't distort open-play xG projections.

### 4. `HoldChaseChallengerModel` (`models/hold_chase_challenger.py`)
- **Nailed vs. Fringe Starter Adjustment**:
  - If appearance $\ge 90\%$ and average minutes $\ge 75$, boost $P(\text{Start})$ by $+30\%$ of remaining probability mass.
  - If appearance $< 50\%$, push $P(\text{DNP})$ up by $+50\% \times (1 - \text{app})$.
- **Top-End Ordering & Ceiling Tilt**:
  - Exponential sharp slope applied to players with $xG \ge 0.45/90$.
  - Minutes tilt ($1.04\times$) for players with combined $xG + xA \ge 0.70/90$.
- **Relaxed Hard Fixture Defense**: Softens defensive expectation on difficult fixtures (FDR $\ge 4.0$).

### 5. `FaceValueChallengerModel` (`models/face_value_challenger.py`)
- **Face-Value Attack (ADR 0045)**: Fixed weights $1.0$ on xG, $1.0$ on xA (zero weight on raw threat/creativity). Eliminates unstable in-season ridge regression refits that previously overfitted to cameo hauls.
- **Minute-Pooled Goal Finishing Offset**:
  $$\text{Offset}_i = \frac{\sum (\text{Goals}_i - xG_i) \cdot 90}{\sum \text{Minutes}_i + 1800.0}$$
  Shrinks player finishing skill toward zero over 1800 pseudo-minutes, preventing single-match finishing spikes from blowing up long-term projections.
- **Mid-Range Start Probability Shrink**: Shrinks uncertain mid-range starters toward DNP:
  $$p_{\text{start}} \leftarrow p_{\text{start}} \cdot (1 - 0.15 \cdot (1 - p_{\text{start}}))$$

### 6. `MultiFeatureAssistChallengerModel` (`models/multi_feature_assist_challenger.py`)
- **Ridge Poisson GLM for Assist Rates (ADR 0048)**:
  - Replaces single-variable xA with a log-link Poisson GLM ($\lambda_{\text{ridge}} = 10.0$):
    $$\log(\text{Assists}/90) = \beta_0 + \beta_1 z(\log xA) + \beta_2 z(\log(\text{creativity} + 1)) + \beta_3 z(\log \text{Opp xGC}) + \beta_4 z(\log \text{Team xG}) + \beta_5 \text{Home}$$
  - Standardized covariates $z$, trained on current-season history pre-target GW.
  - Requires $\ge 3$ gameweeks of history; otherwise falls back to face-value xA.

### 7. `LearnedStartChallengerModel` (`models/learned_start_challenger.py`)
- **Ridge Logistic Regression for Start Probability (ADR 0050)**:
  - Predicts $p_{\text{start}}$ using player-level covariates:
    - 6-Gameweek lags of starts (`started.shift(1..6)`).
    - `min3`: Minutes played over last 3 GWs $/ 90$.
    - `starts6`: Total starts in last 6 GWs.
    - `since_start`: Gameweeks since last start (capped at 6).
    - Position one-hot dummies (GK, DEF, MID).
    - `club_frac`: Fraction of club fixtures started by this player.
  - Trained on current-season rows from GW4+ ($\ge 500$ rows).
- **Iterative Mass Preservation (`preserve_mass`)**:
  - The sum of learned start probabilities across the squad is rescaled to match the baseline start mass, preventing artificial inflation of total starts. Excess probability $> 0.99$ is redistributed to other starters.
- **Weighted Plackett-Luce Bonus Model**:
  - Generates fixture-level 3/2/1 bonus points via sequential Plackett-Luce sampling on:
    $$\text{Mass}_i = \text{softmax}\left(\frac{xBPS_i}{6.0}\right) \times P(60+\text{ mins}_i)$$

### 8. `DefXgShrinkChallengerModel` [CHAMPION] (`models/def_xg_shrink_challenger.py`)
- **Position-Specific xG Rate Shrinkage (ADR 0055, Idea ATK-04)**:
  - Empirical finding: Split-half reliability of defender xG is near zero ($r \approx 0.15$). Defenders who record high xG over short windows (e.g. 2 set-piece headers) trigger the "optimizer's curse", causing the MILP solver to pick them over elite clean-sheet defenders (Saliba, Gabriel, Virgil).
  - Defender xG/90 is shrunk towards the league defender mean with $K=2400.0$ pseudo-minutes (whereas attackers use standard $K=360.0$):
    $$\text{shrunk\_rate}_{\text{DEF}} = \frac{\sum w \cdot xG + 2400 \cdot \mu_{\text{DEF}} / 90}{\sum w \cdot \text{mins} + 2400} \cdot 90$$
  - Applied as a multiplier ratio on `per90_xg` with recency decay $\gamma = 0.95$.

---

## 3. Data Contracts: Inputs & Outputs

### Input Contract: `features/contracts.py` (`FeatureContract`)
The model consumes a pandas DataFrame where each row is a `(player_id, fixture_id, gameweek_id)` tuple:
- **Identifiers**: `player_id`, `gameweek_id`, `fixture_id`, `club_id`, `opponent_club_id`, `position_id` (1=GK, 2=DEF, 3=MID, 4=FWD).
- **Match Context**: `was_home` (bool), `difficulty` (Modified FDR 1.0–5.0).
- **Rolling Performance**: `per90_xg`, `per90_xa`, `per90_goals_conceded`, `per90_saves`, `per90_defcon`, `per90_yellow_cards`, `per90_red_cards`.
- **Availability & History**: `avg_mins_3gw`, `appearance_probability`, `starts`, `minutes`, `chance_of_playing`, `status`.
- **Optional Overrides**: `external_xmins` (external minutes input).

### Output Contract: `features/contracts.py` (`ProjectionContract`)
The model outputs a DataFrame containing:
- **Core Projections**: `player_id`, `gameweek_id`, `fixture_id`, `projected_points` ($xP$), `projected_minutes` ($xMins$).
- **13 Additive Component Columns** ($\sum \text{xp\_components} = \text{projected\_points}$):
  1. `xp_minutes`: Appearance points (1 pt for $1-59$ mins, 2 pts for $60+$ mins).
  2. `xp_goals`: Projected goal points by position.
  3. `xp_assists`: Projected assist points (3 pts each).
  4. `xp_clean_sheet`: Clean sheet probability $\times$ position points.
  5. `xp_conceded`: Penalty points for conceded goals.
  6. `xp_saves`: Goalkeeper save points.
  7. `xp_defcon`: Defensive contribution bonus (+2 pts).
  8. `xp_yellow_cards`: Yellow card deduction ($-1$ pt).
  9. `xp_red_cards`: Red card deduction ($-3$ pts).
  10. `xp_penalties_saved`: Penalty save points (+5 pts).
  11. `xp_penalties_missed`: Penalty miss penalty ($-2$ pts).
  12. `xp_own_goals`: Own goal deduction ($-2$ pts).
  13. `xp_bonus`: Expected 3/2/1 bonus points.
- **Participation State Probabilities**: `p_dnp`, `p_start`, `p_sub_in`, `xmins_if_start`, `xmins_if_sub_in`, `xbps`.

---

## 4. Known Weaknesses & Improvement Opportunities

1. **Coupling of Minutes Uncertainty & Event Rates**:
   - Because $xP$ multiplies event rate by projected minutes, an error in minutes directly corrupts event metrics.
   - Diagnosed in October 2026: Feeding actual match minutes ("Oracle Minutes") instantly collapsed model bias from $-1.11$ to $-0.08$ pts and boosted correlation by $+52\%$.
2. **Real-Life Performer Adaptation Lag**:
   - Emerging regular starters (e.g., Maxim De Cuyper) with low historical sample sizes get penalized by the $K=2400$ defender shrinkage and lag 6-GW start histories, projecting at $\sim 2.5$ pts when true expectation is $\sim 4.2$ pts.
3. **Rigid Discrete Participation States**:
   - Fixed conditional minutes ($78$ min start, $18$ min sub) fail to capture tactical early substitutions (e.g. 60th-minute winger changes) or 90-minute center-back endurance.
4. **Fixture Attacking Dispersion Understatement**:
   - Cross-GW dispersion research shows the model produces relatively flat attacking fixture swings compared to realized variance.

---

## 5. Candidate Ledger: Proven Dead Levers (Strictly Forbidden to Retry)

Under project rules, **any lever proven Dead cannot be re-tested within 1 year** of its evidence date. Do not propose or implement these mechanisms:

| Lever Class | What was tried | Why it failed | Revisit After |
|---|---|---|---|
| **Club 11-Man Mass Conservation** | Enforcing $\sum_{\text{club}} p_{\text{start}} = 11.0$ and reallocating DNP mass | Bias exploded (0.70 vs 0.42); crushed elite rotating squads (City/Chelsea) while over-projecting unplayable bench fodder | 2027-10-01 |
| **Unseeded Starter K Relaxation** | Relaxing $K=2400 \to 600$ for unseeded starting defenders | Amplified small-sample set-piece noise; optimizer picked volatile defenders over reliable clean sheets | 2027-10-13 |
| **Stacked Club × DEF Prior** | Combining club defensive prior with player $K=2400$ shrinkage | Regret delta $-0.81$ pts/GW; club-level small samples are dominated by random set-piece bounces | 2027-10-13 |
| **In-Season Ridge G/A Refit** | Dynamic refitting of goal/assist weights on in-season points | Overfitted to cameo hauls; severely degraded out-of-sample MAE | 2027-09-28 |
| **Bonus Pool Saturation ($B_{\max} \in [1.2, 1.5]$)** | Capping maximum bonus allocation per match | Starved premium forward expected value; degraded top-11 formation regret | 2027-10-01 |
| **Latent-Role HMM Participation** | 3-4 state Hidden Markov Models for player role transitions | High parameter variance; failed all MAE guardrails | 2027-09-29 |
| **Opponent Poisson $\lambda$ Multipliers** | Direct multiplicative scaling of goal expectancy by opponent conceded rate | Massively over-projected easy fixtures; breached bias tolerances | 2027-09-22 |
