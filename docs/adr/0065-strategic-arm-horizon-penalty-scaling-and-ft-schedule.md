# Strategic Arm Horizon Penalty Scaling and Emergency Free Transfer Value Schedule

Transfer Plan Scenarios refine the **Strategic** arm (ADR 0061) by scaling one-off friction penalties across variable planning horizons ($1 \le H \le 10$) and introducing a diminishing marginal Free Transfer Value schedule to maintain emergency flexibility against sudden squad injuries.

1. **Horizon Scaling for One-Off Penalties**:
   - In deterministic MILP formulations, player projected point differences accrue across all remaining gameweeks in the planning horizon, whereas one-off penalties (hit friction $\lambda_{\text{hit}} = 1.8\text{ pts}$ and goalkeeper transfer friction $\lambda_{\text{gk}} = 1.5\text{ pts}$) are deducted only once in the transfer gameweek.
   - At long horizons ($H=10$), an unscaled hit penalty requires only $\sim 0.33\text{ xP/GW}$ incremental return over 10 weeks to justify a $-4$ hit, rendering hit friction ineffective against distant noisy projections.
   - We scale one-off strategic penalties by the cumulative discounted horizon ratio relative to the research baseline horizon $H_0 = 5$:
     $$\text{scale}(H) = \frac{\sum_{k=0}^{H-1} \delta^k}{\sum_{k=0}^{4} \delta^k} \quad (\text{with } \delta = \text{decay\_base} = 0.85)$$
     $$\lambda_{\text{hit}}(H) = 1.8 \times \text{scale}(H), \quad \lambda_{\text{gk}}(H) = 1.5 \times \text{scale}(H)$$
   - Yields $\text{scale}(1) \approx 0.27$, $\text{scale}(5) = 1.00$, $\text{scale}(6) \approx 1.12$, and $\text{scale}(10) \approx 1.44$.
   - Weekly per-round variance constraints (Starter xMins floor, First-Bench cover, Defensive stack cap) remain unscaled because their slack penalties scale naturally with weekly objective sums.

2. **Emergency Free Transfer Value Schedule**:
   - The Strategic arm replaces the flat linear credit ($1.5\text{ pts}$ per FT held) with a diminishing schedule reflecting emergency insurance value:
     $$\text{ft\_value\_list} = \{ \text{"2"}: 2.0 \times \text{scale}(H), \; \text{"3"}: 1.2 \times \text{scale}(H), \; \text{"4"}: 0.6 \times \text{scale}(H), \; \text{"5"}: 0.2 \times \text{scale}(H) \}$$
   - Bank state 2 (the first spare Free Transfer) receives the highest marginal valuation ($2.0\text{ pts}$ base), creating a mathematical incentive to bank a transfer as insurance against unexpected multi-player injuries.
   - Bank states 4 and 5 diminish sharply to prevent passive rollover when approaching the 5-FT cap.
   - The per-transfer friction `ft_use_penalty = 0.2` remains unscaled.

3. **Unconstrained and No Hit Arm Isolation**:
   - `unconstrained` and `no_hit` arms remain unaltered, preserving pure-points and strict zero-hit baselines.

4. **Strategic Audit**:
   - `meta["strategic_audit"]` reports `horizon_scale`, effective hit hurdle ($4.0 + \lambda_{\text{hit}}(H)$), and the active `ft_schedule`.

**Status:** Proposed. Amends ADR 0061.

**Considered:**
- *Non-linear injury risk penalty*: Scale FT value dynamically with squad doubtful count. Deferred: requires coupling solver state with dynamic injury news priors; static diminishing schedule provides clean linear MILP formulation.
- *Unscaled FT schedule*: Keep flat $1.5\text{ pts}$. Rejected: linear valuation undervalues the crucial 2nd FT emergency buffer and encourages burning transfers for marginal long-horizon gains.

**Consequences:**
- Strategic arm plans at $H=6$ and $H=10$ preserve a 2 FT buffer when long-horizon marginal gains do not exceed emergency option value.
- High-horizon solves resist low-confidence transfer churn in distant gameweeks.
