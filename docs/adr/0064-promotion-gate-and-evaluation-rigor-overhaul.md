# Promotion Gate & Evaluation Rigor Overhaul (ADR 0064)

**Status**: Accepted (2026-10-26, Wayfinder Map #166 completion)

Amends ADR 0046 (point-in-time features & statistical gate), ADR 0047 (two-season promotion gate), ADR 0049 (bootstrap bar 0.60, no minimum effect), ADR 0054 (formation-constrained XI regret and playable pool guardrails), and ADR 0062 (non-catastrophic segment loss guardrail).

---

## Context

An adversarial quantitative audit (`docs/research/external-collaboration/02_backtest_gate_audit_brief.md`) exposed four structural distortions in the historical evaluation and gating machinery:

1. **Unseeded Confirmation Regime Mismatch**: While live production operates with historical prior-season data ($N_{\text{prior}}=1$) and the Development Season (2025–26) was seeded with 2024–25 archive data, the Confirmation Season (2024–25) was run completely unseeded ($N_{\text{prior}}=0$). This imposed an artificial cold-start penalty that never occurs in deployment, discriminating against adaptive ML models in favor of static heuristics.
2. **Short-Panel Nickell Bias & Activation Cliffs**: Unseeded within-player estimators on small early-season samples ($T < 10$) inverted signs, causing early-mid regressions (-5.775 pts/GW in `bounded_causal_challenger`). Prior models bypassed this by hardcoding discrete 19-gameweek Champion fallback wrappers.
3. **Unconstrained Lineup Thrashing & Churn Blindness**: Single-gameweek `best_legal_xi` selected all premium assets simultaneously without budget or club constraints, and weekly lineup turnover had zero penalty in single-gameweek regret despite severely degrading rolling multi-week MILP transfer plans.
4. **Circular Block Bootstrap Boundary & Dilution Bugs**: Circular block bootstrapping wrapped GW38 into GW1 cold start (`% n`) and truncated the terminal block (`[:, :n]`). Resampling across dormant 19-GW fallback wrappers artificially diluted error variance by 50%. Furthermore, a single-season $P \ge 0.60$ gate exhibited an unacceptably high Type I error rate ($\alpha \approx 0.40$).
5. **Endogenous Masking & Segment Stringency Asymmetry**: The playable pool mask included candidate predictions ($\hat{y}_{\text{cand}} \ge 2.0$), allowing candidates to alter their own evaluation set. In seasonal segments, requiring $\Delta_{\text{cold\_start}} \ge -0.05$ over $n=4$ games ($\text{SE} \approx 1.10$) imposed an extreme $-0.045 \times \text{SE}$ tolerance ($0.2$ total points), artificially requiring 100% Champion cloning in GW1–4.

---

## Decisions

Wayfinder Map #166 resolved these distortions across seven decision tickets:

### 1. Warm-Seeded Confirmation Season (Issue #167)
- Provisioned the 2023–24 Season Archive (`data/archive/2023-24/processed`) from Vaastav FPL data with 100% schema parity across all five parquet tables.
- Updated `commands/snapshot_season.py` and `backtesting/walkforward.py` so confirmation evaluations default to `seed_season="2023-24"`, matching live production and dev season regimes ($N_{\text{prior}}=1$).

### 2. Short-Panel Priors & Continuous $N_{\text{eff}}$ Sample Shrinkage (Issue #168)
- Regularized within-player ML estimators on small samples ($T < 15$) with Empirical Bayes positional price-tier priors ($K_{\text{prior}} = 12.0$) in `models/ml_panel_features.py` and `CausalFeatureScaler`.
- Replaced discrete gameweek activation cliffs with continuous effective sample-size blending:
  $$\alpha_g = \text{clip}\left(\frac{N_{\text{eff}, g} - N_{\min}}{N_{\text{full}} - N_{\min}}, 0.0, 1.0\right)$$
  where $N_{\text{eff}, g} = 0.5 N_{\text{seed}} + N_{\text{in\_season}, <g}$, $N_{\min} = 3500$, $N_{\text{full}} = 7500$.

### 3. Constrained Legal Formation XI & Squad Churn Guardrail (Issue #169)
- Upgraded `best_legal_xi` to `select_legal_formation_xi` using HiGHS/scipy MILP enforcing:
  - $\le 3$ players per club
  - Starting XI budget cap: $B_{\text{XI}} = 835.0$ (£83.5m in FPL 0.1m units)
  - Deterministic tie-breaking: `[pred DESC, cost ASC, id ASC]`.
- Implemented rolling top-15 budget-feasible squad churn $\text{Churn}_g = 15 - |\mathcal{S}_g \cap \mathcal{S}_{g-1}|$ with guardrail $\overline{\text{Churn}}_{\text{cand}} \le \overline{\text{Churn}}_{\text{champ}} + 0.50$ players/GW.

### 4. Exogenous Playable Pool Mask & Active-Window Guardrails (Issue #170)
- Anchored the playable pool strictly to model-independent exogenous criteria:
  $$\mathcal{M}_{i,g} = (\text{Mins}_{i,g} \ge 30) \lor (\hat{y}^{\text{champ}}_{i,g} \ge 2.0)$$
- Evaluated all safety guardrails across both full season (38 GWs) and active gameweeks:
  $$\mathcal{G}_{\text{active}} = \{g : \max_i |\hat{y}^{\text{cand}}_{i,g} - \hat{y}^{\text{champ}}_{i,g}| > 10^{-6}\}$$
  preventing dormant fallback wrappers from diluting active estimation errors. Both windows must pass.

### 5. Non-Wrapping Moving Block Bootstrap (L=5) & Pooled Stratified Gate (Issue #171)
- Implemented non-wrapping Moving Block Bootstrap restricting start indices to $0 \le s \le n - L$, evaluating complete blocks of length $L$ without boundary wrapping or terminal truncation.
- Increased default block length from $L=3$ to $L=5$ (`BOOTSTRAP_BLOCK_GWS = 5`) to span 4–6 week Premier League fixture swings.
- Formulated Pooled 2-Season Stratified Bootstrap Gate (`evaluate_two_season_gate`):
  - Dev Season: $P_{\text{dev}}(\bar{\Delta}^* > 0) \ge 0.75$ (`BOOTSTRAP_MIN_P = 0.75`, raised from 0.60)
  - Confirmation Season (warm-seeded): $P_{\text{conf}}(\bar{\Delta}^* > 0) \ge 0.65$ (`CONFIRMATION_BOOTSTRAP_MIN_P = 0.65`)
  - Pooled 2-Season Stratified: $P_{\text{pooled}}(\bar{\Delta}^* > 0) \ge 0.85$ (`POOLED_BOOTSTRAP_MIN_P = 0.85`).

### 6. $\sqrt{n_s}$-Scaled Seasonal Segment Loss Floors (Issue #172)
- Standardized statistical confidence intervals across asymmetric seasonal windows to uniform stringency ($z \approx -0.23$ to $-0.26 \times \text{SE}_s$ under $\sigma_\Delta \approx 2.20$ pts/GW):
  - `cold_start` ($n=4$): $\Delta_{\text{cold\_start}} \ge -0.25$ pts/GW (max $-1.00$ cumulative pt)
  - `early_mid` ($n=15$): $\Delta_{\text{early\_mid}} \ge -0.15$ pts/GW (max $-2.25$ cumulative pts)
  - `late` ($n=19$): $\Delta_{\text{late}} \ge -0.13$ pts/GW (max $-2.47$ cumulative pts)
- Retained active-season win requirement: $\max(\Delta_{\text{early\_mid}}, \Delta_{\text{late}}) > 0.0$ pts/GW.

---

## Historical Re-Evaluation Results (Issue #173)

All three canonical historical cases were re-evaluated under the reformed gate using live 38-gameweek walk-forward backtests on empirical data (artifact: `docs/research/backtest-gate-reform/historical_candidate_re_evaluation_summary.csv`):

| Case | Candidate | Champion | Dev 2025–26 ($P \ge 0.75$) | Conf 2024–25 ($P \ge 0.65$) | Pooled Stratified ($P \ge 0.85$) | Reformed Gate Verdict |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Case 1** | `adaptive_causal_challenger` | `def_xg_shrink_challenger` | **FAIL** ($\Delta = -0.8947, P = 0.122$, segs 0/3) | **FAIL** ($\Delta = +0.5075, P = 0.832$, Captain Regret fail) | **FAIL** ($P = 0.546$) | **REJECTED** under Constrained XI (£83.5m budget cap) |
| **Case 2** | `bounded_causal_challenger` | `adaptive_causal_challenger` | **FAIL** ($\Delta = -0.4161, P = 0.000$, segs 0/3) | **FAIL** ($\Delta = -2.0296, P = 0.000$, Guardrail fails) | **FAIL** ($P = 0.000$) | **REJECTED** (Early-mid collapse & Captain Regret fail) |
| **Case 3** | `apex_predator_challenger` | `adaptive_causal_challenger` | **FAIL** ($\Delta = -1.1589, P = 0.000$, segs 0/3) | **FAIL** ($\Delta = +0.0957, P = 0.554 < 0.65$) | **FAIL** ($P = 0.001$) | **REJECTED** (Dead congestion lever regression) |

---

## Consequences

- Validates the core audit thesis (Brief 02, Dilemma 2): unconstrained Legal XI evaluation previously favored high-turnover premium-heavy models (`adaptive_causal_challenger`) that won by picking illegal £100m+ starting lineups, but fail when constrained to a realistic £83.5m starting budget cap and 3-per-club quota.
- When evaluated under realistic £83.5m budget constraints, `def_xg_shrink_challenger` outperforms `adaptive_causal_challenger` on Dev 2025–26 ($\Delta = +0.8947$ pts/GW advantage to `def_xg_shrink_challenger`), proving the necessity of the Constrained Legal Formation XI reform.
- Reaffirms the Candidate Ledger Dead status for `bounded_causal_challenger` and `apex_predator_challenger` with decisive empirical statistical rejections ($P_{\text{pooled}} \le 0.001$).
- Completely closes the four audit dilemmas, providing a principled, robust, and reproducible evaluation gate for future model development.
