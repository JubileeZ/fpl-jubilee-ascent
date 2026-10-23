# Early Gameweek ML Activation & Sample Maturity Exploration

**Updated**: 2026-10-23T19:20:00+07:00  
**Data stamp**: FPL API historical archives 2024–25 and 2025–26 (`data/archive/*/processed`)  
**Season**: Multi-season (`dev` 2025–26, `confirm` 2024–25; 2026–27 GW6+ sealed holdout)  
**Status**: Completed — Candidate Evaluated (Confirm Fail)  
**Purpose**: Investigate architectures, transition ramps, and safety bounds to activate Causal Panel ML earlier in the season (e.g. GW8–10 rather than GW20) without triggering catastrophic early-mid segment regression (ADR 0062) or failing unseeded confirmation (ADR 0047).  
**Scope**: 4 exploration lanes: (1) continuous ESS minutes ramp, (2) decoupled component-staggered activation ladder, (3) empirical Bayes prior anchoring & talisman protection, (4) hybrid component ladders with continuous event ramps; stack protocol; frozen candidate evaluation on two-season promotion gate.  
**Related**: [ADR 0047](../../adr/0047-two-season-promotion-gate.md) · [ADR 0049](../../adr/0049-gate-bootstrap-060-no-min-effect.md) · [ADR 0054](../../adr/0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md) · [ADR 0062](../../adr/0062-non-catastrophic-segment-loss-promotion-guardrail.md) · [ADR 0063](../../adr/0063-adaptive-causal-challenger-promotion.md) · [Candidate Ledger](../candidate-ledger/candidate-ledger.md) · [Adaptive Causal Challenger](../ml-adaptive-champion/ml-adaptive-champion.md)  
**Artifact**: [smoke_results.csv](smoke_results.csv) · [candidate_gate.csv](candidate_gate.csv)

---

## Sources

- **Repository code**: `models/bounded_causal_challenger.py`, `models/adaptive_causal_challenger.py`, `models/ml_component_challenger.py`, `models/def_xg_shrink_challenger.py`
- **Repository data**: Archive seasons `2025-26` (dev, seed `2024-25`) and `2024-25` (confirm, unseeded) in `data/archive/`
- **Evaluation harness**: `.agents/skills/explore-candidate/smoke.py`, `backtesting/model_evaluation.py`, `backtesting/promotion.py`

**Source boundary**: Backtest features evaluated point-in-time without terminal player columns or lookahead leakage. 2026–27 GW6+ sealed holdout remained untouched.

---

## Agent Prompt

```text
/goal test all approach see which work or not if multiple apporach work then backtest it and develop candidates and promote gate it. goal is too test all of this areas
```

---

## Method

**Method type**: Empirical backtest, multi-lane exploration, and statistical gating across development (`2025–26`) and unseeded confirmation (`2024–25`) seasons.

**Inputs**:
- `data/archive/2025-26/processed` (seed `2024-25`)
- `data/archive/2024-25/processed` (seed `none`)

**Procedure**:
1. Formulate 4 exploration lanes addressing the early-GW ML sample starvation problem:
   - **Lane 1 (`lane1_ess_ramp`)**: Continuous convex blending $(1-w)\text{Champion} + w\text{ML}$ starting between GW8 and GW16, reaching full ML at GW20.
   - **Lane 2 (`lane2_staggered_ladder`)**: Component milestones activating $H_1$ at GW6/8, duration at GW12, assists at GW14, and goals at GW20.
   - **Lane 3 (`lane3_prior_anchoring`)**: Bounding goal multipliers to $[0.90, 1.10]$ or enforcing talisman floors ($xG \ge 0.35$ lower bound 1.0) during GW8–19.
   - **Lane 4 (`lane4_hybrid_ladder`)**: Early $H_1$ activation combined with continuous goal ramping.
2. Evaluate all 20 pre-declared prototype variants against Champion `adaptive_causal_challenger` on `dev` season (`2025–26`).
3. Evaluate Stack Protocol (`stack_ramp10_clamp10`, `stack_ramp8_clamp10`) on dev winners.
4. Freeze best single variant (`bounded_causal_challenger`), register in catalog, and verify contract and dev reproduction.
5. Execute one-shot unseeded confirmation season on `2024–25` under ADR 0047.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Legal XI Regret Delta | $\Delta$ | $\text{Regret}_{\text{champ}} - \text{Regret}_{\text{cand}}$ across Formation XI | Higher $\uparrow$ | $> 0.0$ pts/GW | Primary promotion metric (ADR 0054) |
| Bootstrap Win Probability | $P$ | Share of $B=20,000$ circular block bootstrap draws with $\Delta > 0$ | Higher $\uparrow$ | $\ge 0.60$ | Statistical significance (ADR 0049) |
| Segment Wins | `segs` | Number of seasonal segments with $\Delta_s > 0$ | Higher $\uparrow$ | $\ge 1$ active win | Segment consistency (ADR 0062) |
| Segment Loss Guardrail | $\Delta_s$ | Regret delta in each active seasonal segment | Higher $\uparrow$ | $\ge -0.15$ pts/GW | Non-catastrophic loss bound (ADR 0062) |

---

## Findings

### 1. Multi-Lane Prototype Exploration on Development Season (`2025–26`)

Evidence: [smoke_results.csv](smoke_results.csv) (22 rows).

#### Lane 1: Continuous Convex Transition Ramp
- `lane1_ramp_gw12_s8`: **PASS** ($\Delta = +0.1576$, boot $P = 0.6553$, segs 1/3, all guardrails green)
- `lane1_ramp_gw10_s10`: **PASS** ($\Delta = +0.0913$, boot $P = 0.6268$, segs 1/3, all guardrails green)
- `lane1_ramp_gw8_s12`: **PASS** ($\Delta = +0.0803$, boot $P = 0.6267$, segs 1/3, all guardrails green)
- `lane1_ramp_gw14_s6`: FAIL ($\Delta = -0.0533$, boot $P = 0.0000$)
- `lane1_ramp_gw16_s4`: FAIL ($\Delta = +0.0000$, boot $P = 0.0000$)

#### Lane 2: Component-Staggered Activation Ladder
- All 5 variants failed dev season due to catastrophic `early_mid` regressions ($-0.245$ to $-1.299$ pts/GW).
- *Mechanism failure*: Step-function activation of individual ML heads without convex damping injects small-sample estimation variance directly into the lineup optimizer.

#### Lane 3: Informative Prior Anchoring & Talisman Protection
- `lane3_anchor_clamp10_gw10`: **PASS** ($\Delta = +0.1555$, boot $P = 0.8030$, segs 1/3, all guardrails green).
- Activating ML at GW10 with goals ratio clamped to $[0.90, 1.10]$ prevents early haul dampening while harvesting minutes alpha.
- Step-activation at GW8 remained too noisy ($-0.237$ to $-0.476$ pts/GW).

#### Lane 4: Hybrid Component Ladder
- All 5 variants failed dev season ($-0.097$ to $-0.499$ pts/GW) due to early un-damped $H_1$ volatility.

#### Stack Protocol
- `stack_ramp10_clamp10` and `stack_ramp8_clamp10` both failed dev ($-0.1196$ pts/GW, early_mid $-0.303 < -0.15$). Compounding multiple dampening layers degraded the predictive alpha of the late season.
- Surviving frozen pick: Best single variant `lane3_anchor_clamp10_gw10` (`bounded_causal_challenger`) with $P = 0.8030 \gg 0.60$.

---

### 2. Freeze Check and Two-Season Promotion Gate

Evidence: [candidate_gate.csv](candidate_gate.csv) (2 rows).

| Season | Role | Gameweeks | Seed | Combined $\Delta$ | Bootstrap $P$ | Segs | Guardrails | Gate Verdict |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2025–26** | `dev` | GW1–38 | 2024–25 | **+0.1555 pts/GW** | **0.8033** | **1 / 3** | **PASS (5/5)** | **PASS** |
| **2024–25** | `confirm` | GW1–38 | None | **-2.2797 pts/GW** | **0.0117** | **0 / 3** | **FAIL (3 regressed)** | **FAIL** |

#### Why did Bounded Causal Challenger fail Confirmation Season (`2024–25`)?
1. **The Unseeded Asymmetry Reality**:
   In `dev` (`2025–26`), the feature pipeline benefits from prior-season seed history (`2024–25`). When GW10 arrives in `dev`, the Causal Feature Scaler and Ridge models train on rich, pre-conditioned player representations.
2. **Extreme Small-Sample Noise in Unseeded Seasons**:
   In `confirm` (`2024–25`), there is **zero seed history** (ADR 0047). At GW10, only 9 gameweeks of matches exist league-wide. The in-season feature tables lack player stability.
3. **Severe Early-Mid Regression and Guardrail Collapse**:
   Even with a $[0.90, 1.10]$ clamp on goal multipliers, turning on ML minutes ($H_1, H_3$) and assist finishing at GW10 in an unseeded season produced a catastrophic drop of **$-5.775$ pts/GW** in `early_mid`.
   Captaincy regret severely deteriorated ($4.993$ vs $4.256$, breaking the $+0.15$ guardrail tolerance by $+0.587$ pts/GW), and Playable Pool Bias exploded to $0.4355$ vs $0.3984$.
   The candidate scored bootstrap $P = 0.012$, decisively failing the ADR 0047 confirmation gate.

---

## Decision

**Verdict**: Candidate evaluated and rejected under ADR 0047 confirmation protocol. Model Champion [`adaptive_causal_challenger`](../../models/adaptive_causal_challenger.py) in [`config/model_selection.json`](../../config/model_selection.json) stands unchanged.

**Key Architectural Conclusion**:
- Activating ML before GW20 in unseeded seasons is fundamentally hazardous under the Two-Season Promotion Gate because within-season ML models cannot condition on sufficient player-level evidence in the first 9–15 gameweeks without a prior-season seed.
- Champion [`AdaptiveCausalChallengerModel`](../../models/adaptive_causal_challenger.py) with 100% Champion fallback across GW1–19 (`min_ml_gw = 20`) remains the mathematically optimal, gate-passing policy for unseeded season operations.

**Ledger Updates**:
- Logged `bounded_causal_challenger` as `dead` in [`candidate_ledger.csv`](../candidate-ledger/candidate_ledger.csv) (`revisit_after = 2027-10-23`).
- Registered in catalog [`docs/model_name.md`](../../docs/model_name.md) as Model Candidate.

---

## Risks and unknowns

- Future seasons with guaranteed prior-season archives (like live season `2026–27` once live holdout checks are performed) might safely support GW10 activation, but any model aiming to pass the ADR 0047 Historical Promotion Gate must survive unseeded confirmation seasons where GW1–19 ML activation fails.
