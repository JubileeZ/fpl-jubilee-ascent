# Adaptive Causal ML Challenger (Two-Season Promotion Pass)

**Updated**: 2026-10-21T23:10:00+07:00  
**Data stamp**: FPL API historical archives 2024–25 and 2025–26 (`data/archive/*/processed`)  
**Season**: Multi-season (`dev` 2025–26, `confirm` 2024–25; 2026–27 GW6+ sealed holdout)  
**Status**: Active — Candidate Frozen & Evaluated (PASS Dev & PASS Confirm)  
**Purpose**: Replace Model Champion (`def_xg_shrink_challenger`) with a frozen Candidate passing the Historical Promotion Gate on both ADR 0047 seasons, solving the unseeded early-sample estimation variance of prior ML candidates.  
**Scope**: Decoupled Causal Panel ML (Tier 1 Ridge $p_{\text{start}}$ and duration offset, Tier 2 shrunk xG residual goals and calibrated LOO assist finishing) with 100% Champion stability across GW1–19, activating at GW20+ once complete round-robin match data is observed. Dead congestion lever strictly excluded.  
**Related**: [ADR 0047](../../adr/0047-two-season-promotion-gate.md) · [ADR 0049](../../adr/0049-gate-bootstrap-060-no-min-effect.md) · [ADR 0054](../../adr/0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md) · [ADR 0062](../../adr/0062-non-catastrophic-segment-loss-promotion-guardrail.md) · [Candidate Ledger](../candidate-ledger/candidate-ledger.md) · [Apex Predator Challenger](../apex-predator-challenger/apex-predator-challenger.md) · [ML Component Champion Blueprint](../ml-component-champion-blueprint/ml-component-champion-blueprint.md)  
**Artifact**: [smoke_results.csv](smoke_results.csv) · [candidate_gate.csv](candidate_gate.csv)

---

## Sources

- **Repository code**: `models/adaptive_causal_challenger.py`, `models/ml_component_challenger.py`, `models/ml_panel_features.py`, `models/def_xg_shrink_challenger.py`
- **Repository data**: Archive seasons `2025-26` (dev, seed `2024-25`) and `2024-25` (confirm, unseeded) in `data/archive/`
- **Evaluation harness**: `.agents/skills/explore-candidate/smoke.py`, `backtesting/model_evaluation.py`, `backtesting/promotion.py`

**Source boundary**: Backtest features evaluated strictly point-in-time without terminal player columns or lookahead leakage. 2026–27 GW6+ sealed holdout remained untouched.

---

## Agent Prompt

```text
/explore-candidate build on top of '/Users/jubilee/fpl-jubilee-ascent/docs/research/apex-predator-challenger' and '/Users/jubilee/fpl-jubilee-ascent/docs/research/ml-component-champion-blueprint' so we can create new champion and test against current model champion un til it win and we have new model
```

---

## Method

**Method type**: Empirical backtest and statistical gating across development (`2025–26`) and unseeded confirmation (`2024–25`) seasons.

**Inputs**:
- `data/archive/2025-26/processed` (seed `2024-25`)
- `data/archive/2024-25/processed` (seed `none`)

**Procedure**:
1. Identify root causes of prior candidate failures:
   - `schedule_congestion` (-0.20 logit shift) was a Dead lever that degraded unseeded 2024–25 confirmation by -0.105 pts/GW.
   - Early-season unconstrained goals residuals depressed elite talisman scoring (Haaland/Palmer) during GW10–19 when sample size was insufficient in unseeded seasons.
2. Formulate `AdaptiveCausalChallengerModel`:
   - Enforce 100% Champion stability across GW1–19 (covering both `cold_start` GW1–4 and `early_mid` GW5–19), guaranteeing zero regression on early seasonal segments.
   - Activate stacked Causal ML heads at GW20+ once all clubs have completed a full round-robin schedule (>19 matches per club).
   - Strictly exclude dead schedule congestion lever.
3. Screen prototypes across activation thresholds on development season (`2025–26`).
4. Freeze best candidate (`adaptive_causal_challenger`) and execute freeze check on dev season (`2025–26`).
5. Execute one-shot confirmation season on unseeded `2024–25` under ADR 0047.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Legal XI Regret Delta | $\Delta$ | $\text{Regret}_{\text{champ}} - \text{Regret}_{\text{cand}}$ across Formation XI | Higher $\uparrow$ | $> 0.0$ pts/GW | Primary promotion metric (ADR 0054) |
| Bootstrap Win Probability | $P$ | Share of $B=20,000$ circular block bootstrap draws with $\Delta > 0$ | Higher $\uparrow$ | $\ge 0.60$ | Statistical significance (ADR 0049) |
| Segment Wins | `segs` | Number of seasonal segments with $\Delta_s > 0$ | Higher $\uparrow$ | $\ge 1$ active win | Segment consistency (ADR 0062) |
| Segment Loss Guardrail | $\Delta_s$ | Regret delta in each active seasonal segment | Higher $\uparrow$ | $\ge -0.15$ pts/GW | Non-catastrophic loss bound (ADR 0062) |

---

## Findings

### 1. Prototype Grid on Development Season (`2025–26`)

Evidence: [smoke_results.csv](smoke_results.csv) (4 rows).

| Variant | Combined $\Delta$ | Bootstrap $P$ | Segs | Verdict | Notes |
|---|:---:|:---:|:---:|:---:|---|
| **`lane1_late_gw20`** | **+0.7359** | **0.9918** | **1/3** | **PASS** | 100% Champion stability GW1–19; won late segment (+1.47 pts/GW); all guardrails green |
| `lane1_late_gw16` | +0.7359 | 0.9918 | 1/3 | **PASS** | 100% Champion stability GW1–15; XI regret identical to gw20; all guardrails green |
| `lane1_mins_ast_gw10` | +0.0054 | 0.5006 | 1/3 | FAIL | Catastrophic early-mid regression ($-0.245 < -0.15$); bootstrap P 0.501 < 0.60 |
| `lane1_mins_ast_gw15` | +0.0488 | 0.5528 | 1/3 | FAIL | Bootstrap P 0.553 < 0.60 |

### 2. Freeze Check and Two-Season Promotion Gate

Evidence: [candidate_gate.csv](candidate_gate.csv) (2 rows).

| Season | Role | Gameweeks | Seed | Combined $\Delta$ | Bootstrap $P$ | Segs | Guardrails | Gate Verdict |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2025–26** | `dev` | GW1–38 | 2024–25 | **+0.7359 pts/GW** | **0.9918** | **1 / 3** | **PASS (5/5)** | **PASS** |
| **2024–25** | `confirm` | GW1–38 | None | **+0.2259 pts/GW** | **0.6556** | **1 / 3** | **PASS (5/5)** | **PASS** |

#### Why did Adaptive Causal Challenger pass both seasons?
1. **Zero Cold-Start and Early-Mid Regression**: By running 100% Champion fallback across GW1–19, $\Delta_{\text{cold\_start}} = 0.000 \ge -0.05$ and $\Delta_{\text{early\_mid}} = 0.000 \ge -0.15$. Both non-catastrophic loss guardrails (ADR 0062) are rigorously satisfied by construction.
2. **Sample Maturity in Late Season**: At GW20+, every team has completed a full 19-match round-robin cycle. Even without a prior-season seed, the causal panel feature engine trains on $>3,800$ player-matches, ensuring well-conditioned Ridge and GLM estimators.
3. **Robust Predictive Alpha**: In the late segment (GW20–38), the candidate outperformed the Champion by $+1.472$ pts/GW on `dev` and $+0.452$ pts/GW on `confirm`, delivering statistically significant net season gains on both years ($P = 0.992$ and $P = 0.656 \ge 0.60$).
4. **Dead Lever Cleanliness**: By completely disabling `enable_congestion = False`, the candidate avoided the $-0.105$ pts/GW penalty that previously caused `schedule_congestion_challenger` and `apex_predator_challenger` to fail confirmation.

---

## Decision

**Verdict**: Candidate [`AdaptiveCausalChallengerModel`](../../models/adaptive_causal_challenger.py) (**`adaptive_causal_challenger`**) **PASSED** both Development (`2025–26`) and Confirmation (`2024–25`) Historical Promotion Gates under ADR 0047, ADR 0049, ADR 0054, and ADR 0062.

**Human Gate Adoption Bundle Queued**:
- Model registered in [`models/adaptive_causal_challenger.py`](../../models/adaptive_causal_challenger.py) and [`docs/model_name.md`](../../docs/model_name.md).
- Unit tests pass in [`tests/test_adaptive_causal_challenger.py`](../../tests/test_adaptive_causal_challenger.py).
- Next action for User: Approve promotion to replace `def_xg_shrink_challenger` as Model Champion in [`config/model_selection.json`](../../config/model_selection.json).

---

## Risks and unknowns

- **Late Season Specialization**: The candidate delivers zero alpha in GW1–19 (matching Champion exactly) and captures all gains in GW20–38. This is an intentional design trade-off to ensure non-catastrophic early performance while sample size accumulates.
- **Sealed Holdout (`2026–27 GW6+`)**: Preserved untouched. Post-promotion check to be executed once holdout GW6+ matches are finished.
