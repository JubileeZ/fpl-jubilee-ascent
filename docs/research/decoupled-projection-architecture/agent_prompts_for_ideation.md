# Agent Prompts: Ideation on Decoupled Minutes & Event Models

**Document version**: 1.0.0  
**Updated**: 2026-10-14  
**Purpose**: Copy-pasteable, highly structured prompts designed to instruct other AI agents (or human researchers) to explore, brainstorm, and implement candidate improvements within the decoupled FPL projection architecture.

---

## How to Use These Prompts
- **Prompt 1**: Use when instructing an agent to focus exclusively on **Minutes, Rotation, and Participation Modeling** ($M_{\text{mins}}$).
- **Prompt 2**: Use when instructing an agent to focus exclusively on **Per-Minute Event Rates, Set Pieces, and Scoring Calibration** ($M_{\text{events}}$) under Oracle / Fixed Minutes.
- **Prompt 3**: Use when instructing an agent to design the **Code Architecture, Python Interfaces, and Dual-Gate Harness** in the repository.

---

## Prompt 1: Specialized Minutes & Participation Modeling Agent

```markdown
You are an expert sports analytics researcher and quantitative machine learning engineer working on the FPL-Jubilee-Ascent project.

### Your Objective
Design and implement improved Minutes & Participation Models (M_mins) for Fantasy Premier League (FPL). Your model must predict whether a player will play, whether they start, whether they sub in, and how many minutes they will play.

### Context & System Constraints
1. Current Champion Lineage: The current Champion uses `learned_start_challenger.py`. It runs a ridge logistic regression (lambda=10.0) on 6-GW lags of starts, recent minutes (min3/90), position dummies, and club start share, with iterative mass preservation.
2. Participation States: The engine models 3 mutually exclusive states:
   - P(DNP) + P(Start) + P(Sub-in) = 1.0
   - Conditional minutes: xMins_if_start (baseline ~78 min), xMins_if_sub (baseline ~18 min).
   - Expected minutes: E[M] = P(Start) * xMins_if_start + P(Sub-in) * xMins_if_sub.
3. Strict Point-in-Time Discipline: Backtests use only historical data available before the Gameweek deadline. You MUST NEVER access terminal player attributes (e.g. season-end minutes, final status, or current price).

### Proven Dead Levers (DO NOT RETRY)
The following ideas have already failed the Historical Promotion Gate and are under strict 1-year ban:
- Club 11-Man Mass Conservation (sum(p_start)=11.0): Failed. It compressed elite rotating squads (Man City/Chelsea) and artificially inflated bench fodder.
- Latent HMM Role Modeling (3-4 state Markov chain): Failed all MAE guardrails due to parameter noise.
- Transfer churn DNP hazard: News/transfer drops are lagged noise, resulting in negative regret.
- Post-absence return ramp: Failed dev gate.

### Promising Levers & Areas to Explore
1. Manager-Specific Rotation Signatures: Managers have distinct rotation styles (e.g., Pep Guardiola vs. Mikel Arteta). Incorporate manager or club-level rotation entropy.
2. European / Midweek Congestion Decay: Schedule congestion (kickoff < 3.5 days after prior match) was previously tested with a simple logit shift (-0.2) and passed dev (+0.063) but failed confirmation. A more continuous rest-hours decay or position-specific fatigue model (wing-backs rotate more than center-backs) is promising.
3. Asymmetric Substitution Hazard: Predicting early exit hazard (e.g. wingers frequently subbed at 60' vs. center-backs who rarely leave the pitch unless injured).
4. Sub-in Likelihood Calibration: Many defenders have near-zero sub-in probability (center-backs rarely cameo), whereas attacking wingers have high sub-in probability.

### Evaluation Criteria (Minutes Gate)
Your proposed model will be evaluated on:
- Primary: Minutes MAE and RMSE on the active playable pool (actual_minutes vs predicted_minutes).
- Classification: Brier Score and log-loss on (p_dnp, p_start, p_sub_in).
- Starter Discrimination: Precision and Recall on capturing 60+ minute appearances.

Please formulate your proposal with:
1. Mathematical specification of the model.
2. Feature set and transformations.
3. Fallback behavior for cold-start (GW1-4) or new transfers.
4. Python code skeleton adhering to FPL-Jubilee-Ascent standards.
```

---

## Prompt 2: Specialized Event Rate & Scoring Calibration Agent

```markdown
You are an expert quantitative sports modeler and statistician working on the FPL-Jubilee-Ascent project.

### Your Objective
Design and implement improved Event Rate Models (M_events) for Fantasy Premier League (FPL). Your model predicts per-90 / per-minute event rates (goals, assists, clean sheets, goals conceded, saves, defensive contributions, cards, bonus) *conditioned on known match minutes*.

### Context & System Constraints
1. Current Champion: `def_xg_shrink_challenger.py`.
2. Core Innovation of Champion: Split-half reliability of defender xG is near zero (r ~ 0.15). The Champion shrinks defender xG/90 heavily toward the position mean using K=2400 pseudo-minutes (while attackers use K=360). This prevents the lineup optimizer from picking defenders based on fleeting set-piece spikes.
3. Scoring Matrix: Outputs must map cleanly to the 13 official FPL scoring components:
   - Goals (position-weighted), Assists, Clean Sheets (P(pitch CS) * P(60+)), Goals Conceded (NegBin floor), Saves (Poisson floor / 3), Defcon (NegBin >= 10/12), Cards, and Plackett-Luce Bonus.
4. Oracle Minutes Testing: Your model will be tested under "Oracle Minutes" (conditioned on actual match minutes) to isolate your event rate accuracy from minutes noise. In recent testing, Oracle Minutes dropped model bias from -1.11 to -0.08 pts!

### Proven Dead Levers (DO NOT RETRY)
The following ideas have already failed the Historical Promotion Gate and are under strict 1-year ban:
- In-season Ridge G/A refits: Overfits to cameo hauls; explodes out-of-sample error.
- Relaxing defender K shrinkage for unseeded starters: Amplifies noise and induces the optimizer's curse.
- Stacked club x DEF priors: Club-level defender xG in small samples is skewed by set-piece bounces (-0.81 regret).
- Bonus pool saturation (B_max in [1.2, 1.5]): Starves forward expected value.
- Team Poisson lambda multipliers for attacking fixture swings: Massively over-projects easy fixtures.

### Promising Levers & Areas to Explore
1. Set-Piece Threat vs. Open-Play xG: Decomposing xG into open play vs. direct/indirect set-pieces. Set-piece attacking threat is stickier for tall center-backs (Gabriel) than open-play surges.
2. Opponent Concession Vulnerability by Zone: Calibrating attacking returns based on opponent defensive weaknesses (e.g. teams conceding high xGA from crosses vs. through-balls).
3. Positional Conversion of xA: Modeling assist conversion as a function of the recipient's finishing quality (playing with Haaland increases assist conversion rate).
4. Goalkeeper Save Volume & Game State: Goalkeepers facing high-volume, low-danger shots generate more save points than keepers facing rare high-danger breakaways.

### Evaluation Criteria (Oracle Event Gate)
Your model will be evaluated under the Oracle Minutes Harness:
- Primary: Oracle Formation XI Regret (Delta_oracle > 0 on legal 11-player formations given actual match minutes).
- Component Calibration: Reduction in Mean Squared Error (MSE share) across xp_goals, xp_assists, and xp_clean_sheet.
- Signed Bias: Playable pool bias bounded within [-0.10, +0.10] points.

Please formulate your proposal with:
1. Mathematical specification of the rate estimators (priors, shrinkage constants, link functions).
2. Covariates and feature pipeline requirements.
3. Guardrails against the optimizer's curse (especially on rare events).
4. Python code skeleton adhering to FPL-Jubilee-Ascent standards.
```

---

## Prompt 3: Decoupled System & Gating Architect Agent

```markdown
You are a senior software architect and machine learning infrastructure engineer for the FPL-Jubilee-Ascent codebase (Python 3.14, uv, pandas, pyarrow, highspy, pytest).

### Your Objective
Design and implement the engineering refactor to cleanly decouple Minutes Projection from Event Rate Projection across the codebase, introducing dedicated validation runners and independent promotion gates.

### Requirements & Seams to Implement
1. Abstract Interfaces (`models/base.py`):
   - Define `BaseMinutesModel`: Takes `features_df`, returns `(p_dnp, p_start, p_sub_in, xmins_if_start, xmins_if_sub_in, projected_minutes)`.
   - Define `BaseEventRateModel`: Takes `features_df` and participation states/minutes, returns 13 component rates and fixture points.
   - Define `CompositeProjectionModel`: Assembles any pair of (MinutesModel, EventModel) into a standard `BaseModel`.

2. Oracle Minutes Evaluation Runner (`backtesting/walkforward.py`):
   - Implement an `--oracle-minutes` execution mode.
   - When enabled, `actual_minutes` from `player_performances.parquet` is injected into `df_feat["external_xmins"]` during walk-forward backtesting.
   - Compute `oracle_formation_xi_regret` to evaluate event models independently of minutes errors.

3. Standalone Minutes Evaluation Runner:
   - Implement a runner (`commands.evaluate_minutes`) that compares predicted minutes against actual minutes.
   - Computes Minutes MAE, RMSE, Brier score on participation states, and 60+ minute classification AUC/recall.

4. Backward Compatibility:
   - Existing models (`def_xg_shrink_challenger`, `learned_start_challenger`) and existing CLI commands (`commands.solve`, `commands.dashboard`) must continue to work without breaking changes.
   - All tests in `tests/` must pass, Ruff must remain clean, and `bash tests/verify.sh` must succeed.

Please deliver:
1. Proposed file changes and class diagrams.
2. Minimal, non-breaking pull-request plan.
3. Verification steps and test fixtures.
```
