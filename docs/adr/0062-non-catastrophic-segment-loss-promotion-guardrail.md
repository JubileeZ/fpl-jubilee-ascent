# Promotion Gate: Non-Catastrophic Segment Loss Guardrail

**Status**: Accepted; amended by [ADR 0064](0064-promotion-gate-and-evaluation-rigor-overhaul.md) and [ADR 0066](0066-backtesting-and-promotion-foundation.md) (Continuous segment loss floors integrated into multi-season statistical protocol and substantive projection guards).

Amends ADR 0010 (seasonal segments majority), ADR 0046 (point-in-time features & statistical gate), ADR 0047 (two-season promotion gate), and ADR 0049 (bootstrap bar 0.60, no minimum effect).

## Context

The historical Promotion Gate (`backtesting/promotion.py`) required a candidate model to win at least 2 out of 3 seasonal segments (`cold_start` GW1–4, `early_mid` GW5–19, `late` GW20–38). This rule was originally instituted in July 2026 (ADR 0010 / Wayfinder #121) as a heuristic to reject "single-haul fluke" candidates (such as `defence_link_challenger`).

However, the binary formulation (`cand_metric < champ_metric`) introduced severe statistical distortions:
1. **Cold-Start Parity Trap (Tie = Loss)**: Principled machine learning models (e.g. `ml_component_challenger`, `learned_start_challenger`) use conservative cold-start fallback or ramps ($w_{\text{ML}} = 0$ in GW1–3/4), producing $\Delta = 0.00$ in the cold-start segment. Strict inequality `<` evaluates $0.00 < 0.00$ as `False` (a defeat), forcing ML models to win 100% of the remaining active season.
2. **Simpson's Paradox & Margin Insensitivity**: A candidate winning two segments by $+0.001$ pts/GW and catastrophically losing the third by $-2.000$ pts/GW (net $-38$ pts) passed; while a model with cold-start parity, $-0.010$ noise in mid-season, and a $+0.800$ late season crush (net $+15$ pts, bootstrap $P > 0.75$) failed.
3. **Window Size Imbalance**: A 4-week window had the exact same voting weight as a 19-week window.
4. **Redundancy with Circular Block Bootstrapping**: ADR 0046 introduced circular block bootstrapping ($B=20,000, L=3$ GWs). Empirical evaluation confirms that `defence_link_challenger` has a bootstrap win probability of only $P = 0.528 < 0.60$, failing on the bootstrap alone.
5. **False Negative Toll**: The binary rule falsely killed high-performing candidates in the ledger, including `ml_component_challenger` ($+0.342$ pts/GW, $+13.0$ season pts, boot $P = 0.740$, 5/5 green guardrails), `min_01_v4_preserve_mass` ($+0.593$, boot $P = 0.784$), and `schedule_congestion_challenger` ($+0.114$, boot $P = 0.623$).

## Decision

Replace the binary `segment_wins >= 2` rule with continuous **Non-Catastrophic Segment Loss Guardrails** in `backtesting/promotion.py`:

```python
SEGMENT_REGRESSION_TOL: float = 0.15  # Max allowable regret loss in any active segment
COLD_START_PARITY_TOL: float = 0.05   # Cold start tolerance allowing fallback parity
```

A candidate passes the segment consistency requirement if and only if:
1. **Cold-Start Parity**: $\Delta_{\text{cold\_start}} \ge -0.05$ pts/GW.
2. **No Catastrophic Regression**: $\Delta_{\text{early\_mid}} \ge -0.15$ and $\Delta_{\text{late}} \ge -0.15$ pts/GW (aligned with `CAPTAIN_REGRET_ABS_TOL = 0.15`).
3. **Active Season Win**: $\max(\Delta_{\text{early\_mid}}, \Delta_{\text{late}}) > 0.0$ pts/GW (candidate must outperform Champion in at least one active in-season segment).

The `segment_wins` count is preserved on `PromotionVerdict` for backwards compatibility in logging and reports.

## Consequences

- Eliminates structural discrimination against models with cold-start fallback or gradual Bayesian ramp-up.
- Protects against catastrophic single-segment regressions while preserving margin sensitivity.
- In combination with circular block bootstrapping ($P \ge 0.60$), ensures robust, multi-layered defense against fluke promotions.
- Allows `ml_component_challenger` to advance to the confirmation season (`2024–25`).
