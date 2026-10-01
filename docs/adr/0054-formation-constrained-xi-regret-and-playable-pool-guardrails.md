# Promotion Gate: Formation-Constrained Legal XI Regret and Playable-Pool Guardrails

Amends ADR 0044 (Blended Eval Target primary), ADR 0046 (point-in-time gate), ADR 0049 (bootstrap bar 0.60, delta > 0).

## Context
Historical Promotion Gate previously evaluated unconstrained `top_11_regret` across ~650 players in `players.parquet`. Attacking midfielders and forwards dominated unconstrained selections; defensive and goalkeeping calibration contributed negligibly to promotions. Full-population MAE/bias guardrails diluted by 400+ zero-minute fringe squad members, allowing models to game global error metrics by deflating benchwarmers (demonstrated by `face_value_challenger`, ADR 0046).

## Decision
1. **Primary Metric Upgrade:**
   - Upgrade primary metric from unconstrained `top_11_regret` to **Formation-Constrained Legal XI Regret** (`formation_xi_regret`) on Blended Eval Target ($0.5 \times \text{Process} + 0.5 \times \text{Realized}$).
   - Evaluate best legal FPL formation (1 GKP, 3–5 DEF, 2–5 MID, 1–3 FWD; 10 outfielders) via combinatorial scan over 8 legal topologies (`3-5-2`, `3-4-3`, `4-4-2`, `4-3-3`, `4-5-1`, `5-3-2`, `5-4-1`, `5-2-3`).
   - Regret = Oracle Legal XI Blended points minus Model Legal XI Blended points. Fall back to unconstrained `top_11_regret` if `position_id` missing.

2. **Captaincy Regret Guardrail:**
   - Evaluate captaincy regret within model Legal XI: $\text{Regret}_{\text{cap}} = \max_{i \in \text{XI}} (\text{target}_i) - \text{target}_{\text{predicted\_captain}}$.
   - Candidate mean captaincy regret must not regress beyond Champion by > **$0.15\text{ pts/GW}$** (`CAPTAIN_REGRET_ABS_TOL = 0.15`).

3. **Playable-Pool Accuracy Guardrails:**
   - Accuracy (MAE $\le \times 1.01$) and Signed Bias ($|\text{bias}| \le |\text{champ}| + 0.01$) guardrails evaluated on **Playable Pool**: $\max(\hat{y}_{\text{cand}}, \hat{y}_{\text{champ}}) \ge 2.0\text{ xP}$ OR $\text{actual minutes} \ge 30$.
   - Eliminates zero-minute benchwarmer distortion; verifies point calibration across viable fantasy assets.

4. **Transfer Plan Walk-Forward:**
   - Stays advisory rolling multi-GW research companion (`backtesting/transfer_plan_walkforward.py`); not blocking gate requirement.

## Consequences
- Lineup evaluation matches legal FPL starting constraints; DEF/GKP projection quality actively drives promotions.
- Guardrails protect captain selection and playable starter calibration without zero-minute deflation artifacts.
