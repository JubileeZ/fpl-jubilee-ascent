# Apex Predator Challenger (Composite ML + Scheduling Candidate)

**Updated**: 2026-10-21T04:12:00+07:00  
**Data stamp**: FPL API historical archives 2024–25 and 2025–26 (`data/archive/*/processed`)  
**Season**: Multi-season (`dev` 2025–26, `confirm` 2024–25; 2026–27 GW6+ sealed holdout)  
**Status**: Completed — Candidate Evaluated (Confirm Fail)  
**Purpose**: Evaluate composite candidate stacking zero-leakage ML components (Ridge $p_{\text{start}}$, start duration offset, shrunk xG residual goals, LOO assist finishing) with Champion stability in GW1–9 and schedule congestion turnaround penalties under ADR 0062 segment guardrails.  
**Scope**: Ridge GLM participation and event multipliers, Bayesian warm-up activation threshold, rest-day schedule congestion, two-season promotion gate.  
**Related**: [ADR 0047](../../adr/0047-two-season-promotion-gate.md) · [ADR 0049](../../adr/0049-gate-bootstrap-060-no-min-effect.md) · [ADR 0054](../../adr/0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md) · [ADR 0062](../../adr/0062-non-catastrophic-segment-loss-promotion-guardrail.md) · [Candidate Ledger](../candidate-ledger/candidate-ledger.md)  
**Artifact**: [smoke.csv](smoke.csv) · [candidate_gate.csv](candidate_gate.csv)

---

## Sources

- **Repository code**: `models/apex_predator_challenger.py`, `models/ml_component_challenger.py`, `models/ml_panel_features.py`, `models/def_xg_shrink_challenger.py`, `models/schedule_congestion_challenger.py`
- **Repository data**: Archive seasons `2025-26` (dev) and `2024-25` (confirm) in `data/archive/`
- **Evaluation harness**: `.agents/skills/explore-candidate/smoke.py`, `backtesting/model_evaluation.py`, `backtesting/promotion.py`

**Source boundary**: Backtest features evaluated point-in-time without terminal player columns or lookahead leakage. 2026–27 GW6+ sealed holdout remained untouched.

---

## Agent Prompt

```text
/explore-candidate with ML candidate and past winning components as Apex Predator Challenger
```

---

## Method

**Method type**: Empirical backtest and statistical gating across development (`2025–26`) and unseeded confirmation (`2024–25`) seasons.

**Inputs**:
- `data/archive/2025-26/processed` (seed `2024-25`)
- `data/archive/2024-25/processed` (seed `none`)

**Procedure**:
1. Formulate composite candidate architecture (`ApexPredatorChallengerModel`) stacking passing Tier 1/2 ML heads with schedule congestion rest penalty (-0.20 logit for fixtures $< 3.5$ days rest) and Champion prior preservation during early-season sample building (GW1–9).
2. Screen prototype grid across warm-up activation thresholds (`apex_predator_gw10`, `apex_predator_gw12`, `apex_predator_gw15`).
3. Freeze best candidate (`apex_predator_gw10` / `apex_predator_challenger`) and execute freeze check on dev season (`2025–26`).
4. Execute one-shot unseeded confirmation season on `2024–25` under ADR 0047.

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

Evidence: [smoke.csv](smoke.csv) (6 rows).

| Variant | Combined $\Delta$ | Bootstrap $P$ | Segs | Verdict | Notes |
|---|:---:|:---:|:---:|:---:|---|
| `apex_ml_ramp14` | +0.4071 | 0.7781 | 1/3 | FAIL | Early-mid regression ($-0.833 < -0.15$) |
| `apex_ml_ramp12` | +0.3974 | 0.7743 | 1/3 | FAIL | Early-mid regression ($-0.858 < -0.15$) |
| `apex_predator_full` | +0.4071 | 0.7781 | 1/3 | FAIL | Early-mid regression ($-0.833 < -0.15$) |
| `apex_predator_gw15` | +0.6771 | 0.9791 | 1/3 | **PASS** | 100% Champion stability GW1–14; active win in late season |
| `apex_predator_gw12` | +0.8026 | 0.9907 | 2/3 | **PASS** | Champion stability GW1–11; won early-mid and late |
| **`apex_predator_gw10`** | **+0.8400** | **0.9922** | **2/3** | **PASS** | **Best single variant**: $+31.9$ season points, 99.2% bootstrap confidence |

### 2. Freeze Check and Two-Season Promotion Gate

Evidence: [candidate_gate.csv](candidate_gate.csv) (2 rows).

| Season | Role | Gameweeks | Seed | Combined $\Delta$ | Bootstrap $P$ | Segs | Guardrails | Gate Verdict |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2025–26** | `dev` | GW1–38 | 2024–25 | **+0.8400 pts/GW** | **0.9922** | **2 / 3** | **PASS (5/5)** | **PASS** |
| **2024–25** | `confirm` | GW1–38 | None | **-0.1528 pts/GW** | **0.3764** | **1 / 3** | **PASS (5/5)** | **FAIL** |

#### Why did it fail Confirmation Season (2024–25)?
In `2024–25`, the confirmation season runs **without prior-season seed data** (ADR 0047). Without prior-season history, in-season ML feature tables lack the historical baseline depth available in `dev`. Furthermore, the 2024–25 season featured extreme high-volume scoring runs by elite talisman assets (e.g. Cole Palmer and Erling Haaland). Champion [`def_xg_shrink_challenger`](../def_xg_shrink_challenger/def_xg_shrink_challenger.md) with static empirical Bayes shrinkage ($K=2400$) captures their raw output without dampening, whereas within-season ML models over-regularized goal residuals, producing a $-0.959$ pts/GW deficit in the `early_mid` segment.

Because the candidate produced a negative net delta ($-0.153$) and bootstrap $P = 0.376 < 0.60$ on `confirm`, it fails the two-season gate under ADR 0047.

---

## Decision

**Verdict**: Candidate evaluated and rejected under ADR 0047 confirmation protocol. Model Champion [`def_xg_shrink_challenger`](../../models/def_xg_shrink_challenger.py) in [`config/model_selection.json`](../../config/model_selection.json) stands unchanged.

**Details**:
- Built candidate [`ApexPredatorChallengerModel`](../../models/apex_predator_challenger.py) and registered in [`docs/model_name.md`](../../docs/model_name.md).
- Passed all unit and leakage tests in [`tests/test_apex_predator_challenger.py`](../../tests/test_apex_predator_challenger.py) and [`tests/test_ml_panel_leakage.py`](../../tests/test_ml_panel_leakage.py).
- Staged results in [`smoke.csv`](smoke.csv) and [`candidate_gate.csv`](candidate_gate.csv).
- Logged lever as `dead` in [`candidate_ledger.csv`](../candidate-ledger/candidate_ledger.csv) and [`candidate-ledger.md`](../candidate-ledger/candidate-ledger.md) (`revisit_after = 2027-10-21`).

---

## Risks and unknowns

- **Unseeded ML Generalization Barrier**: Within-season ML models without multi-season pre-training face an inherent variance disadvantage in unseeded confirmation runs compared to static Empirical Bayes shrinkage models ($K=2400$). Multi-season transfer learning or cross-season pooled feature engines may be required before pure ML components can generalize across unseeded seasons.
- **Sealed Holdout (`2026–27 GW6+`)**: Preserved untouched.
