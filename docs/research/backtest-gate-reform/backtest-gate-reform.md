# Promotion Gate & Evaluation Rigor Overhaul (ADR 0064)

**Updated**: 2026-10-24T02:00:00+07:00  
**Data stamp**: FPL API historical archives 2023–24, 2024–25, and 2025–26 (`data/archive/*/processed`)  
**Season**: Multi-season (`dev` 2025–26, `confirm` 2024–25 warm-seeded with 2023–24, `holdout` 2026–27 GW6+)  
**Status**: Active — Wayfinder Map #166 Charted  
**Purpose**: Overhaul the Historical Promotion Gate (`backtesting/promotion.py`, `backtesting/metrics.py`, `backtesting/walkforward.py`, and `models/ml_panel_features.py`) to eliminate unseeded confirmation regime mismatch, short-panel Nickell bias, unconstrained LegalXI churn blindness, circular bootstrap boundary bugs, and endogenous playable pool masking.  
**Scope**: 7 decision tickets under Wayfinder Map #166 resolving: (1) 2023-24 archive provisioning and warm confirmation seed, (2) short-panel empirical Bayes priors and continuous $N_{\text{eff}}$ sample-size shrinkage, (3) constrained Legal Formation XI and squad churn guardrail, (4) exogenous playable pool masking and active-window guardrails, (5) non-wrapping moving block bootstrap ($L=5$) and pooled 2-season stratified gate, (6) $\sqrt{n_s}$-scaled segment floors, and (7) end-to-end verification, historical candidate re-evaluations, and ADR 0064.  
**Related**: [ADR 0046](../../adr/0046-point-in-time-backtest-and-statistical-gate.md) · [ADR 0047](../../adr/0047-two-season-promotion-gate.md) · [ADR 0049](../../adr/0049-gate-bootstrap-060-no-min-effect.md) · [ADR 0054](../../adr/0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md) · [ADR 0062](../../adr/0062-non-catastrophic-segment-loss-promotion-guardrail.md) · [ADR 0063](../../adr/0063-adaptive-causal-challenger-promotion.md) · [Candidate Ledger](../candidate-ledger/candidate-ledger.md)  
**Artifact**: [wayfinder-tickets.json](wayfinder-tickets.json)

---

## Sources

- **Repository code**: `backtesting/promotion.py`, `backtesting/metrics.py`, `backtesting/walkforward.py`, `models/ml_panel_features.py`
- **Audit reference**: `docs/research/external-collaboration/02_backtest_gate_audit_brief.md`
- **Wayfinder Map**: GitHub Issue [#166](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/166)

---

## Wayfinder Ticket Manifest

| Issue | Key | Priority | Type | Title | Status |
|:---:|---|:---:|:---:|---|:---:|
| [#167](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/167) | `t1_warm_seed_confirmation` | P1 | `task` | How should the 2023-24 Season Archive be provisioned and wired as a warm confirmation seed? | Closed |
| [#168](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/168) | `t2_short_panel_shrinkage` | P1 | `prototype` | How should short-panel priors and Neff sample-size shrinkage be regularized in ml_panel_features.py? | Closed |
| [#169](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/169) | `t3_constrained_legal_xi` | P1 | `prototype` | How should Legal Formation XI enforce club quotas, starting budget caps, and squad churn guardrails? | Closed |
| [#170](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/170) | `t4_exogenous_playable_pool` | P1 | `prototype` | How should exogenous playable pool masking and active-window guardrails be structured? | Closed |
| [#171](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/171) | `t5_non_circular_bootstrap` | P1 | `prototype` | How should non-wrapping moving block bootstrap (L=5) and pooled 2-season gates be formulated? | Open |
| [#172](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/172) | `t6_sqrt_ns_segment_guardrails` | P2 | `grilling` | How should seasonal segment loss guardrails be scaled by sqrt(ns) sample sizes? | Open |
| [#173](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/173) | `t7_verification_adr0064` | P2 | `task` | What verification suite, candidate re-evaluations, and ADR 0064 validate the reformed gate? | Open |
