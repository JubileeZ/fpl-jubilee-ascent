# Promotion Gate & Evaluation Rigor Overhaul (ADR 0064)

**Updated**: 2026-10-26T16:35:00+07:00  
**Data stamp**: FPL API historical archives 2023–24, 2024–25, and 2025–26 (`data/archive/*/processed`)  
**Season**: Multi-season (`dev` 2025–26, `confirm` 2024–25 warm-seeded with 2023–24, `holdout` 2026–27 GW6+)  
**Status**: Completed — Wayfinder Map #166 Resolved (ADR 0064 Accepted)  
**Purpose**: Overhaul Historical Promotion Gate (`backtesting/promotion.py`, `backtesting/metrics.py`, `backtesting/walkforward.py`, and `models/ml_panel_features.py`) to eliminate unseeded confirmation regime mismatch, short-panel Nickell bias, unconstrained LegalXI churn blindness, circular bootstrap boundary bugs, and endogenous playable pool masking.  
**Scope**: 7 decision tickets under Wayfinder Map #166 resolving: (1) 2023-24 archive provisioning and warm confirmation seed, (2) short-panel empirical Bayes priors and continuous $N_{\text{eff}}$ sample-size shrinkage, (3) constrained Legal Formation XI and squad churn guardrail, (4) exogenous playable pool masking and active-window guardrails, (5) non-wrapping moving block bootstrap ($L=5$) and pooled 2-season stratified gate, (6) $\sqrt{n_s}$-scaled segment floors, and (7) end-to-end verification, historical candidate re-evaluations, and ADR 0064.  
**Related**: [ADR 0046](../../adr/0046-point-in-time-backtest-and-statistical-gate.md) · [ADR 0047](../../adr/0047-two-season-promotion-gate.md) · [ADR 0049](../../adr/0049-gate-bootstrap-060-no-min-effect.md) · [ADR 0054](../../adr/0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md) · [ADR 0062](../../adr/0062-non-catastrophic-segment-loss-promotion-guardrail.md) · [ADR 0063](../../adr/0063-adaptive-causal-challenger-promotion.md) · [Candidate Ledger](../candidate-ledger/candidate-ledger.md)  
**Artifact**: [wayfinder-tickets.json](wayfinder-tickets.json) · [historical_candidate_re_evaluation_summary.csv](historical_candidate_re_evaluation_summary.csv)

---

## Sources

- **Repository code**: `backtesting/promotion.py`, `backtesting/metrics.py`, `backtesting/walkforward.py`, `models/ml_panel_features.py`
- **Audit reference**: `docs/research/external-collaboration/02_backtest_gate_audit_brief.md`
- **Wayfinder Map**: GitHub Issue [#166](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/166)

---

## Agent Prompt

```text
Full redo docs/research/backtest-gate-reform/backtest-gate-reform.md

1. Re-read all primary sources and inspect current repository conventions.
2. Refresh or re-check every input listed under Sources and Method.
3. Preserve source-derived claims separately from Project interpretation.
4. Recompute evidence and decision rules; do not silently change Method.
5. Update Updated, Data stamp, Season, Sources, Findings, Decision, and Risks.
6. Keep filename stable; update cross-links when sibling notes change.
7. Write companions into this topic folder (CSV/HTML beside the note).
8. Store scratch under .tmp/agent/ only; delete scratch before finishing.
```

---

## Method

**Method type**: Empirical combinatorial evaluation, statistical block bootstrap, and econometric panel shrinkage.

**Inputs**:
- `data/archive/2023-24/processed/`
- `data/archive/2024-25/processed/`
- `data/archive/2025-26/processed/`

**Procedure**:
1. Provision 2023-24 archive from Vaastav FPL CSVs and wire as confirmation seed.
2. Regularize short panels with Empirical Bayes priors ($K_{\text{prior}}=12.0$) and continuous $N_{\text{eff}}$ sample-size shrinkage.
3. Upgrade `best_legal_xi` to `select_legal_formation_xi` enforcing $\le 3$ per club, £83.5m budget cap, and deterministic tie-breaking.
4. Anchor Playable Pool mask to model-independent criteria and evaluate guardrails across both full season and active window $\mathcal{G}_{\text{active}}$.
5. Implement non-wrapping Moving Block Bootstrap ($L=5$) and Pooled 2-Season Stratified Gate ($P_{\text{dev}} \ge 0.75, P_{\text{conf}} \ge 0.65, P_{\text{pooled}} \ge 0.85$).
6. Calibrate $\sqrt{n_s}$-scaled segment floors (`cold_start` $\ge -0.25$, `early_mid` $\ge -0.15$, `late` $\ge -0.13$).
7. Re-evaluate historical cases and record in `historical_candidate_re_evaluation_summary.csv`.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Constrained Formation XI Regret** | $\Delta_{\text{regret}}$ | $\text{Regret}_{\text{champ}} - \text{Regret}_{\text{cand}}$ on Blended Target | Higher is better $\uparrow$ | $> 0.0$ pts/GW | Primary promotion metric under £83.5m budget and 3-per-club caps. |
| **Pooled Stratified Win Probability** | $P_{\text{pooled}}$ | Share of 20,000 stratified moving block draws where pooled $\bar{\Delta}^* > 0$ | Higher is better $\uparrow$ | $\ge 0.85$ | Multi-season significance bar across Dev and Confirmation. |
| **Top-15 Squad Churn** | $\text{Churn}_g$ | $15 - \|\mathcal{S}_g \cap \mathcal{S}_{g-1}\|$ on top-15 budget squad | Lower is better $\downarrow$ | $\le \text{Champ} + 0.50$ | Weekly squad turnover stability guardrail. |
| **Exogenous Playable Pool Bias** | $\text{Bias}_{\text{playable}}$ | Mean signed error on players with mins $\ge 30$ or champ xP $\ge 2.0$ | Lower magnitude is better $\downarrow$ | $\le \text{Champ} + 0.01$ | Prevents candidate-induced evaluation sample shifting. |

---

## Findings

Re-evaluations under the reformed gate (artifact: [historical_candidate_re_evaluation_summary.csv](historical_candidate_re_evaluation_summary.csv)):
- `adaptive_causal_challenger` vs `def_xg_shrink_challenger`: Dev FAIL ($\Delta = -0.8947, P = 0.122$, segs 0/3), Conf FAIL (Captain Regret fail), Pooled $P = 0.546$ < 0.85. Rejected under constrained XI.
- `bounded_causal_challenger` vs `adaptive_causal_challenger`: Dev FAIL ($\Delta = -0.4161, P = 0.000$), Conf FAIL ($\Delta = -2.0296, P = 0.000$), Pooled $P = 0.000$. Rejected (early-mid collapse).
- `apex_predator_challenger` vs `adaptive_causal_challenger`: Dev FAIL ($\Delta = -1.1589, P = 0.000$), Conf FAIL ($P = 0.554 < 0.65$), Pooled $P = 0.001$. Rejected (dead congestion lever).

---

## Decision

**Verdict**: Adopt ADR 0064 and lock the reformed Historical Promotion Gate across production and research.

**Recommended action**:
- Keep `def_xg_shrink_challenger` as Model Champion.
- Require all future candidates to pass Dev $P \ge 0.75$, warm Conf $P \ge 0.65$, and Pooled $P \ge 0.85$.

---

## Risks and unknowns

- Realized performance of adaptive estimators under small sample windows without prior-season warm seeding.
- Transfer of £83.5m starting budget cap assumptions to rolling multi-period transfer planning horizons.
