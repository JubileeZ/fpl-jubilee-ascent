# Backtesting & Promotion Gate Context

**Document version**: 1.0.0  
**Updated**: 2026-10-14  
**Authoritative code**: `backtesting/promotion.py`, `backtesting/walkforward.py`, `backtesting/metrics.py`, `docs/research/INDEX.md`  
**Key ADRs**: ADR 0054 (Formation XI Regret), ADR 0049 (Bootstrap 0.60 Bar), ADR 0046 (Point-in-Time & Statistical Gate), ADR 0044 (Blended Eval Target)  
**Purpose**: Specification of the walk-forward evaluation engine, statistical promotion gate, and decision criteria used to promote Candidate models to Champion.

---

## 1. Core Evaluation Philosophy: Decision Regret Over Point MAE

In fantasy sports, **ranking assets correctly for lineup decisions matters far more than minimizing raw point prediction errors**. 

A model that predicts 2.5 pts for player A and 2.4 pts for player B makes the correct start/bench decision if player A scores 6 and player B scores 2 (Decision Regret = 0), even though its point MAE is high. Conversely, a model with low MAE that flips the relative order causes a painful benching mistake.

Therefore, the primary promotion metric is **Formation XI Regret**, with point accuracy metrics acting as safety guardrails.

---

## 2. Primary Promotion Metric: Formation XI Regret (ADR 0054)

### Definition
For each gameweek $g$, let $\mathcal{P}_g$ be the set of available players with their projected points $\hat{y}_{i,g}$ and actual realized points $y_{i,g}$.

1. **Optimal Legal Formation XI**:
   FPL rules require an 11-man starting lineup satisfying:
   - Exactly 1 Goalkeeper (GKP).
   - 3 to 5 Defenders (DEF).
   - 2 to 5 Midfielders (MID).
   - 1 to 3 Forwards (FWD).
   This corresponds to exactly 8 legal formations: `3-5-2`, `3-4-3`, `4-4-2`, `4-3-3`, `4-5-1`, `5-3-2`, `5-4-1`, `5-2-3`.

2. **Model Starting Selection**:
   For candidate model $M$, select the 11-player lineup $\mathbf{x}^{(M)}_g$ that maximizes projected points $\sum_{i \in \mathbf{x}} \hat{y}^{(M)}_{i,g}$ subject to the legal formation constraints.

3. **Per-Gameweek Regret**:
   $$\text{Regret}(M, g) = \max_{\mathbf{x} \in \text{LegalXI}} \sum_{i \in \mathbf{x}} y_{i,g} - \sum_{i \in \mathbf{x}^{(M)}_g} y_{i,g}$$
   (The actual points difference between the theoretical best possible legal XI and the model's chosen legal XI).

4. **Candidate Improvement Delta ($\Delta$)**:
   $$\Delta_g = \text{Regret}(\text{Champion}, g) - \text{Regret}(\text{Candidate}, g)$$
   - **$\Delta_g > 0$**: The Candidate made better lineup decisions than the Champion in gameweek $g$.
   - **Combined Primary Delta**: $\bar{\Delta} = \frac{1}{N} \sum_{g=1}^N \Delta_g$.

---

## 3. Statistical Promotion Gate Requirements

To defeat the reigning Champion and achieve promotion, a Candidate model must satisfy **all 4 conditions** simultaneously:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      HISTORICAL PROMOTION GATE                         │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Combined Primary Delta:  Δ_combined > 0.0 pts/GW                    │
│ 2. Circular Block Bootstrap: P(Δ_combined > 0) ≥ 0.60 (B=20,000 draws) │
│ 3. Seasonal Segment Wins:    Win ≥ 2 of 3 segments (Cold, Mid, Late)   │
│ 4. Guardrail Compliance:     Pass ALL 5 Hard Safety Guardrails         │
└────────────────────────────────────────────────────────────────────────┘
```

### 1. Positive Combined Delta
- Combined $\bar{\Delta} > 0.0$ across the full season.

### 2. Circular Block Bootstrap ($P \ge 0.60$, ADR 0049)
- Football results exhibit temporal autocorrelation across consecutive weeks (fixture runs, fatigue, manager changes).
- A circular block bootstrap resamples blocks of **3 consecutive gameweeks** across $B = 20,000$ iterations.
- At least **$60.0\%$** of bootstrap resamples must yield a positive mean delta:
  $$P\left(\bar{\Delta}_{\text{bootstrap}} > 0\right) \ge 0.60$$

### 3. Seasonal Segment Consistency ($\ge 2/3$ Wins)
The 38-game season is partitioned into three distinct operational phases:
- **Cold-Start (`cold_start`)**: GW1–4 (low historical sample size, high reliance on priors).
- **Early-Mid (`early_mid`)**: GW5–19 (established player form, first half-season).
- **Late Season (`late`)**: GW20–38 (fixture congestion, rotation, second half).

The Candidate must achieve $\bar{\Delta}_{\text{segment}} > 0$ in at least **2 out of the 3 segments**. A model that wins only late in the season while destroying cold-start viability is rejected.

### 4. Hard Safety Guardrails (Must Pass ALL)

| Guardrail Metric | Threshold | Target Pool | Purpose |
|---|---|---|---|
| **Playable Pool MAE** | $\le \text{Champ} \times 1.01$ | $\max(\hat{y}_{\text{cand}}, \hat{y}_{\text{champ}}) \ge 2.0$ or mins $\ge 30$ | Prevents zero-minute players from distorting error metrics. |
| **Playable Pool Signed Bias** | $|\text{bias}_{\text{cand}}| \le |\text{bias}_{\text{champ}}| + 0.01$ | Same Playable Pool | Prevents systematic over- or under-projection drift. |
| **Captaincy Regret** | $\le \text{Champ} + 0.15$ pts/GW | Highest projected player in XI | Protects captain pick quality ($\max_i y_i - y_{\text{captain}}$). |
| **Minutes MAE** | $\le \text{Champ} \times 1.01$ | All active players | Ensures minutes accuracy does not degrade. |
| **Spearman Rank Correlation** | $\ge \text{Champ} - 0.005$ | All active players | Ensures overall squad rank-ordering remains solid. |

---

## 4. Multi-Season Verification Protocol (ADR 0047, 0049)

To prevent data mining and overfitting to a single season's quirks, candidates are held to a multi-season testing standard:

1. **Development Season (2025-26 GW1–38)**:
   - Run with prior-season seed (2024-25 processed archive).
   - Candidate is tuned and iteratively tested here.
   - Must achieve full gate PASS ($\Delta > 0, P \ge 0.60, \ge 2/3$ segments, all guardrails).

2. **Confirmation Season (2024-25 GW1–38)**:
   - **Zero tuning allowed**. Strictly one single run per frozen candidate.
   - Run without prior seed (unseeded cold-start).
   - Must independently achieve $P(\Delta > 0) \ge 0.60$ and positive delta.

3. **Sealed Holdout (2026-27 GW6+)**:
   - Strictly sealed: zero tuning, zero smoke runs, zero ablation tests.
   - Evaluated only post-promotion as a live operational health-check. If a promoted Champion regresses severely on holdout, it is reverted.

---

## 5. Strict Point-in-Time Discipline & Data Leakage Rules

All backtesting code in `backtesting/walkforward.py` operates under strict point-in-time constraints (ADR 0046):
- **Pre-Cutoff History Only**: When predicting Gameweek $g$, the model has access only to fixture rows where `gameweek_id < g` and `kickoff_time < deadline_time(g)`.
- **Forbidden Terminal Attributes**: Never read `players.parquet` terminal columns (e.g., season-end `total_points`, season-end `minutes`, final `goals_scored`, current `now_cost`, current `status`, current `selected_by_percent`). Backtest features reconstruct player price and club from as-of historical match rows.
- **Strict Leak Audit**: The harness executes automated leak audits (`smoke.py --audit_only`) before accepting any prototype run. Any feature accessing future rows is flagged with immediate disqualification.
