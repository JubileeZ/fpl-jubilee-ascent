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

2. **Emergency Free Transfer Value Schedule & Post-Transfer Bank Valuation (Amended `#231`, 2026-11-24)**:
   - Strategic arm replaces flat linear credit ($1.5\text{ pts}$ per FT held) with unscaled diminishing schedule calibrated across `2025-26` (`S-1`) and `2024-25` (`S-2`) (`#229`–`#231`):
     $$\text{ft\_value\_list} = \{ \text{"2"}: 2.4, \; \text{"3"}: 1.44, \; \text{"4"}: 0.72, \; \text{"5"}: 0.24 \} \quad (\text{constant across all } 1 \le H \le 10)$$
   - Keeping $\text{ft\_value\_list}$ and `spare_ft_hold_weight = 0.15` unscaled ($\text{ratio } 1.0 : 0.6 : 0.3 : 0.1$, `DEFAULT_STRATEGIC_FT_USE_PENALTY = 0.6`) fixes pre-amendment $H=10$ hit-cost inversion ($6.72 > 6.60 \implies 4.84 < 6.60$, permanent $2 \to 1\text{ FT}$ hurdle $4.34$ at $H=6$ / $4.84$ at $H=10$, $\text{delay}_1 = 0.81\text{ xP}$), preserves one-off $\text{scale}(H)$ scaling strictly on `hit_friction` and `gk_transfer_friction`, and gains `+8` pts two-season (`2,138` `S-1` / `2,336` `S-2`, `4,474` vs `4,466` baseline; rejecting two-phase `GW1–8` under `#230` Q9).
   - Evaluated on post-transfer carried bank (`fts[w + 1]` clamped to $[1, 5]$ across `ft_gws = [*gws, last_gw + 1]`) vs pre-transfer bank (`fts[w]`), eliminating final-week ($w = H$) hoard-and-dump double-counting and $H=1$ roll blind spots.
   - Intermediate weeks ($w < \text{last\_gw}$) credit unscaled weekly spare-FT holding buffer (`spare_ft_hold_weight = 0.15` $\times$ spare FT value above 1 FT, $+0.36\text{ pts/GW}$ at 2 FT) alongside `ft_use_penalty = 0.6`, preventing $85\%$ telescoping cancellation from burning FTs on marginal weekly noise.
   - Both live MILP (`solver/solver.py`) and 6-GW native replay (`backtesting/native_transfer_solver.py`) share 100% objective parity: both waive `gw_ft_hold` (`0.0`) on Wildcard/Free Hit weeks (`not free`) AND on `5`-FT cap-overflow transitions (`ft_above_ub[w]` / `max(previous - n, 0) + 1 > 5`), and live `solver/solver.py` restores pre-transfer `ft_base` on `next_gw` for both `WC` and `FH`.
   - Bank states 4 and 5 diminish sharply to prevent passive rollover near 5-FT cap.
   - `unconstrained` and `no_hit` arms retain `ft_use_penalty = 0.2`, cleared `ft_value_list`, and cleared `spare_ft_hold_weight`.

3. **Unconstrained and No Hit Arm Isolation**:
   - `unconstrained` and `no_hit` arms remain unaltered, preserving pure-points and strict zero-hit baselines.

4. **Strategic Audit**:
   - `meta["strategic_audit"]` reports `horizon_scale`, effective hit hurdle ($4.0 + \lambda_{\text{hit}}(H)$), and the active `ft_schedule`.

**Status:** Accepted; Amended `2026-11-24` (`#231` under [ADR 0066 §7](0066-backtesting-and-promotion-foundation.md) & [ADR 0069](0069-annual-rolling-validation-and-dual-tier-promotion.md)). Amends ADR 0061.

**Considered:**
- *Non-linear injury risk penalty*: Scale FT value dynamically with squad doubtful count. Deferred: requires coupling solver state with dynamic injury news priors; static diminishing schedule provides clean linear MILP formulation.
- *Unscaled FT schedule*: Keep flat $1.5\text{ pts}$. Rejected: linear valuation undervalues the crucial 2nd FT emergency buffer and encourages burning transfers for marginal long-horizon gains.

**Consequences:**
- Strategic arm plans at $H=6$ and $H=10$ preserve a 2 FT buffer when long-horizon marginal gains do not exceed emergency option value.
- High-horizon solves resist low-confidence transfer churn in distant gameweeks.
