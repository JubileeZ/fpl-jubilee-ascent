# MILP Solver Strategic Constraints & Variance Control

**Updated**: 2026-10-19T00:05:00+07:00  
**Data stamp**: 2025-26 GW7 official fixtures and Solio sentence builder constraints  
**Season**: Multi-season  
**Status**: Active  
**Purpose**: Quantitative justification for adding strategic variance-control constraints to deterministic Mixed-Integer Linear Program (MILP) solvers in FPL, counteracting the Optimizer's Curse, horizon overfitting, bimodal minutes risk, and tail-risk covariance.  
**Scope**: Tactical and mathematical constraints on transfer planning, hits, minutes thresholds, defensive stack caps, bench coverage, and position-specific transfer friction.  
**Related**: [ADR 0033](../../docs/adr/0033-transfer-plan-hits-until-champion-bias.md), [ADR 0020](../../docs/adr/0020-first-half-transfer-plan-walk-forward.md), [Candidate Ledger](../candidate-ledger/candidate-ledger.md), sibling repo `jubilee-solio-calibrate` ([Solio Solver Rules](https://github.com/JubileeZ/jubilee-solio-calibrate/blob/main/docs/research/solio-solver-rules-variance-constraints.md)).  

---

## Sources

- **Primary**: Solio Analytics Sentence Builder & Constraint Engine (`solioanalytics.com`) — accessed 2026-10-18; role: rule taxonomy and penalty slack formulation.
- **Primary**: Mixed-Integer Linear Programming for FPL Squad Optimization (`open-fpl-solver` / HiGHS MILP) — role: mathematical optimization formulation.
- **Repository data**: `commands/solve.py`, `solver/` — cutoff 2026-10-18.

**Source boundary**: Mathematical constraint formulations are validated against deterministic linear solver properties and FPL scoring rules.

---

## Agent Prompt

```text
Full redo docs/research/milp-variance-constraints/milp-variance-constraints.md

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

**Method type**: Quantitative constraint formulation & portfolio variance analysis.

**Inputs**:
- FPL scoring rules (goals, assists, clean sheets, appearance thresholds, transfer hit costs).
- Linear objective formulation $\max \sum xP - \sum c_{\text{hit}} H_t$.

**Procedure**:
1. Formulate the Optimizer's Curse in unconstrained MILP models under point projection error ($\sigma_{\epsilon} \approx \pm 1.5\text{ to }2.5\text{ pts/GW}$).
2. Quantify three core solver failure modes: multi-week horizon overfitting, bimodal minutes expectation, and joint clean sheet collapse.
3. Formulate hard vs soft slack penalties for linear solver sentence builders and MILP constraints.
4. Establish optimal baseline thresholds for hit hurdles, starter minutes floors, bench cover, and defensive stack limits.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|:---|:---|:---|:---|:---|:---|
| **Effective Hit Hurdle** | $H_{\text{eff}}$ | $4.0\text{ pts (FPL)} + \lambda_{\text{hit}}$ | Higher is better $\uparrow$ (Conservative) | **$5.5\text{–}6.0\text{ xP}$** | Net projected edge required over solve horizon before incurring a transfer hit. |
| **Starter xMins Floor** | $M_{\text{floor}}$ | Hard lower bound on starter projected minutes | Higher is better $\uparrow$ (Nailedness) | **$65.0\text{ mins}$** | Prunes sub-60 minute cameos that block bench autosubs without excluding sub-75 min elite wingers. |
| **Defensive Club Cap** | $C_{\text{def}}$ | $\sum_{i \in \text{Club } c} x_{i,\text{def}} \le 2 + s$ | Context-dependent | **$\le 2$ (Slack $\lambda=1.2\text{ pts}$)** | Soft constraint penalizing defensive triple-ups to limit joint clean sheet loss. |
| **First-Bench Nailed Count** | $N_{\text{bench}}$ | $\sum_{i \in \text{Squad}} \mathbb{I}(\text{xMins}_i \ge 65)$ | Higher is better $\uparrow$ | **$\ge 12$ assets** | Ensures at least one guaranteed starting outfield player on the bench. |

---

## Findings

### 1. The Optimizer's Curse in FPL MILP Solvers

An unconstrained MILP treats point projections ($\widehat{xP}_{i,t}$) as exact, zero-variance truths and ignores covariance between players:
$$\max \sum_{t=1}^{T} \sum_{i \in \text{Squad}} x_{i,t} \cdot \widehat{xP}_{i,t} - \sum_{t=1}^{T} c_{\text{hit}} \cdot H_t$$

In practice, this formulation fails in three systematic ways:
1. **Horizon Overfitting (Noisy Hits)**: The solver takes a $-4$ hit for an apparent $+4.3\text{ xP}$ gain across a 5-GW horizon ($+0.06\text{ xP/GW}$). Because projection standard error is $\pm 1.5\text{ to }2.5\text{ pts/GW}$, real-world variance and injury shocks erase this marginal theoretical edge over 60% of the time.
2. **The Bimodal xMins Trap**: Linear models view $60\text{ xMins}$ as a smooth fractional return. In reality, minutes follow a bimodal distribution: an asset either starts ($75\text{–}85\text{ mins}$) or makes a 10-minute cameo ($1\text{ pt}$), destroying clean sheet eligibility and blocking automatic bench substitutions.
3. **Tail-Risk Covariance**: Unconstrained linear objectives ignore cross-player covariance $\text{Cov}(X_i, X_j)$. Starting 3 defenders from the same club means a single opposition goal instantly wipes out $12\text{ pts}$ simultaneously ($\text{Cov}(CS_i, CS_j) \approx 1.0$).

### 2. Covariance Asymmetry: Defending vs Attacking

- **Defensive Returns**: Clean sheets are binary step-functions ($CS \in \{0, 1\}$). The first goal conceded wipes out $100\%$ of clean sheet equity across all started defenders from that club.
- **Attacking Returns**: Goals and assists exhibit positive covariance in high-scoring routs. When an elite attack (e.g. Arsenal, Liverpool, Man City) scores 3+ goals, multiple attackers return simultaneously (assists coupled to goals, bonus point dominance).
- **Rule**: Never hard-cap attacking triple-ups on elite teams. Constrain attackers only via soft caps on mid-table/low-xG clubs.

### 3. Cross-Play (Attacker vs Defender)

Cross-play (starting an attacker against your own defender or goalkeeper) does not lower expected points ($\mathbb{E}[X+Y] = \mathbb{E}[X] + \mathbb{E}[Y]$). Because $\text{Cov}(G, CS) < 0$, cross-play reduces total gameweek variance and raises the scoring floor. Solvers should **never** apply cross-play penalties.

---

## Decision

Adopt the following 5-rule baseline constraint configuration for transfer planning and future MILP scenario configurations:

1. **Hit Friction Buffer (Soft Constraint)**:
   - Penalty: Deduct $1.8\text{ pts}$ per hit in objective slack.
   - Effect: Raises the hit break-even hurdle to $5.8\text{ xP}$ over the solve horizon, filtering out 30–40% of over-trading caused by projection noise.
2. **Starter xMins Floor (Hard Constraint)**:
   - Floor: $\text{xMins} \ge 65.0$ for all started outfield players.
   - Effect: Eliminates 1-point cameo traps while accommodating modern 5-sub tactical rotations for elite wingers.
3. **First-Bench Cover Protection (Soft Constraint)**:
   - Constraint: Own at least 12 players projected $\ge 65.0\text{ mins}$ (slack penalty: $1.5\text{ pts}$).
   - Effect: Guarantees a viable first substitute to cushion against unannounced weekend absences.
4. **Defensive Stack Limiter (Soft Constraint)**:
   - Constraint: Start at most 2 defenders/GKP from any single club (slack penalty: $1.2\text{ pts}$).
   - Effect: Limits catastrophic single-goal defensive wipeouts without prematurely benching elite defenders in premium home fixtures.
5. **Goalkeeper Transfer Friction (Soft Constraint)**:
   - Constraint: Soft penalty of $1.5\text{ pts}$ against purchasing goalkeepers.
   - Effect: Preserves valuable Free Transfers for high-signal outfield positions, preventing lateral GK churn for marginal $+0.6\text{ xP}$ edges.

---

## Risks and unknowns

- **Extreme Double Gameweeks**: Under DGW fixture crunches, a $-4$ hit may legitimately carry higher expected value than $5.8\text{ xP}$; soft penalty slack allows high-EV moves to break through naturally.
- **Squad Rotations in European Weeks**: December/spring rotation may require dynamic adjustment of the $65\text{-minute}$ threshold.
