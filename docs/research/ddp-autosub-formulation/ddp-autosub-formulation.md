# Research Report: Dynamic Disruption Probability (DDP), Bench Weights, and Autosub Probability Formulations

**Issue Reference:** GitHub Issue #136 (Parent #135: Unified Solio-Style Decision Tree Planner Rebuild)  
**Sources:** `open-fpl-solver` (vendored under `solver/`), `sertalpbilal/fpl_optimized`, Sertalp B. Çay's research, and Solio Analytics.

---

## 1. Mathematical Formulation of Dynamic Disruption Probability (DDP)

In standard deterministic Mixed-Integer Linear Programming (MILP) models, the solver optimizes squad selection assuming static unconditional probabilities that bench players will be called upon:
$$\text{bench\_weights}_{\text{static}} = \{0: 0.03,\; 1: 0.21,\; 2: 0.06,\; 3: 0.002\}$$
*(where slot $0 = \text{GK sub}$, $1 = \text{1st outfield sub}$, $2 = \text{2nd outfield sub}$, $3 = \text{3rd outfield sub}$)*.

### What DDP Solves
Static weights ignore two critical dimensions:
1. **Starting XI Rotation/Fragility:** A manager starting high-risk rotation players faces a much higher probability of disruption than a manager starting nailed 90-minute talismans.
2. **Horizon Compounding Uncertainty:** As lookahead moves further into the future ($h = w - w_0$ for $h \in [0, H-1]$), tactical rotation increases. The probability of starting XI disruption grows with horizon distance $h$.

### Mathematical Formulation
Let $D \in [0.0, 1.0]$ denote the **Dynamic Disruption Probability (DDP)** parameter.

#### Direct Bench Weight Multiplier Across Horizon
Under the linear scaling model across planning horizon $h = w - w_{\text{start}}$:
$$w_{o}(w, D) = w_o^{\text{base}} \cdot \mathcal{M}(D) \cdot (1 + \alpha_h \cdot h)$$
where:
- $w_o^{\text{base}}$ is the empirical baseline weight vector $\{0: 0.03, 1: 0.21, 2: 0.06, 3: 0.002\}$.
- $\mathcal{M}(D) = \frac{D}{0.50} = 2 \cdot D$ is the DDP preset scaling multiplier (normalized so Default 50% DDP has $\mathcal{M}=1.0$).
- $\alpha_h \ge 0$ is the horizon uncertainty expansion factor (typically $\alpha_h \in [0.05, 0.10]$ per week lookahead).

---

## 2. Autosub Probability Formulation

### Step 1: Converting Expected Minutes to Appearance Probability
Given projected minutes $\text{xMin}_{p, w}$:
$$\text{start\_prob}(p, w) = \text{clip}\left(\frac{\text{xMin}_{p, w} - 25 \cdot s_{\text{on}}}{90 \cdot (1 - s_{\text{off}}) + 65 \cdot s_{\text{off}} - 25 \cdot s_{\text{on}}},\; 0.001,\; 0.999\right)$$
where:
- Outfield players: $s_{\text{on}} = 0.50$, $s_{\text{off}} = 0.30$.
- Goalkeepers: $s_{\text{on}} = 0.0$, $s_{\text{off}} = 0.0 \implies \text{start\_prob} = \frac{\text{xMin}}{90}$.

Total appearance probability $p_{p, w} = P(\text{plays } \ge 1 \text{ min})$:
$$p_{p, w} = \text{start\_prob}(p, w) + (1 - \text{start\_prob}(p, w)) \cdot s_{\text{on}}$$

### Step 2: Goalkeeper Autosub Probability
Because goalkeepers can only be substituted by the backup goalkeeper (slot $o=0$):
$$P(\text{sub}_0 \text{ activated}) = q_{\text{GK\_start}} = 1 - p_{\text{GK\_start}}$$

### Step 3: Outfield Autosub Probabilities (Poisson-Binomial Distribution)
Let $\{p_1, p_2, \dots, p_{10}\}$ be the appearance probabilities of the 10 starting outfielders, and $q_j = 1 - p_j$.
The number of non-appearing outfield starters $K = \sum_{j=1}^{10} \mathbb{I}(\text{starter } j \text{ DNP})$ follows a **Poisson-Binomial distribution**:
1. **Sub 1 Activation Probability (at least 1 outfield starter misses out):**
   $$P(\text{sub}_1) = P(K \ge 1) = 1 - P(K = 0) = 1 - \prod_{j=1}^{10} p_j$$
2. **Sub 2 Activation Probability (at least 2 outfield starters miss out):**
   $$P(\text{sub}_2) = P(K \ge 2) = 1 - P(K = 0) - P(K = 1) = 1 - \prod_{j=1}^{10} p_j - \sum_{j=1}^{10} q_j \prod_{k \ne j} p_k$$
3. **Sub 3 Activation Probability (at least 3 outfield starters miss out):**
   $$P(\text{sub}_3) = P(K \ge 3) = 1 - P(K = 0) - P(K = 1) - P(K = 2)$$

---

## 3. Parameter Settings for DDP Presets

| Preset Name | DDP Value ($D$) | Scaling Multiplier ($\mathcal{M}$) | Bench Weights $\{0: \text{GK}, 1: \text{Sub1}, 2: \text{Sub2}, 3: \text{Sub3}\}$ | Tactical Behavior & Optimization Impact |
|:---|:---:|:---:|:---|:---|
| **Optimistic** | **0% DDP** ($0.00$) | $0.00\times$ (or $0.10\times$) | $\{0: 0.000, 1: 0.000, 2: 0.000, 3: 0.000\}$ | **Pure Lineup Maximization:** Assumes zero unexpected rotation. Sells all bench capital into starting XI; selects cheapest £4.0m non-playing fodder. High risk of zero-point blanks if any starter misses out. |
| **High Risk** | **25% DDP** ($0.25$) | $0.50\times$ | $\{0: 0.015, 1: 0.105, 2: 0.030, 3: 0.001\}$ | **Aggressive Differential:** Modest safety net. Allows 1 cheap enabler on the bench, but prioritizes maximum funds in the starting XI. Suitable for rank chasing. |
| **Default** | **50% DDP** ($0.50$) | $1.00\times$ | $\{0: 0.030, 1: 0.210, 2: 0.060, 3: 0.002\}$ | **Empirical Baseline:** Standard Solio / Sertalp baseline derived from historical Premier League substitution frequencies (~21% Sub 1, 6% Sub 2, 3% GK). Balances budget between XI and bench. |
| **Safe** | **75% DDP** ($0.75$) | $1.50\times$ | $\{0: 0.045, 1: 0.315, 2: 0.090, 3: 0.003\}$ | **Robust Defense:** Expects heavy rotation / disruption (e.g. European game congestion, winter schedule). Strongly incentivizes reliable £4.5m-£5.0m starters on bench slots 1 & 2. |

---

## 4. Python / HiGHS MILP Formulation

```python
from __future__ import annotations
import highspy
from typing import Mapping, Sequence

DDP_PRESETS = {
    "optimistic": 0.00,
    "high_risk": 0.25,
    "default": 0.50,
    "safe": 0.75,
}

BASE_BENCH_WEIGHTS = {0: 0.03, 1: 0.21, 2: 0.06, 3: 0.002}

def compute_ddp_bench_weights(
    ddp: float = 0.50,
    horizon_weeks: Sequence[int] = (),
    base_gw: int = 1,
    horizon_alpha: float = 0.05,
) -> dict[tuple[int, int], float]:
    ddp_mult = ddp / 0.50
    weights: dict[tuple[int, int], float] = {}
    
    for gw in horizon_weeks:
        h = max(0, gw - base_gw)
        horizon_mult = 1.0 + (horizon_alpha * h)
        for order, base_w in BASE_BENCH_WEIGHTS.items():
            weights[order, gw] = round(base_w * ddp_mult * horizon_mult, 5)
            
    return weights
```
