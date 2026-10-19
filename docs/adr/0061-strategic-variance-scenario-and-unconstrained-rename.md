# Strategic Variance Scenario Arm and Unconstrained Rename

Transfer Plan Scenarios replace heuristic Conservative arm with **Strategic** arm and rename **Optimal** to **Unconstrained**. Canonical arm set: `strategic` (default), `unconstrained`, `no_hit`.

1. **Strategic Arm**: Enforces 5 quantitative linear MILP variance constraints from `docs/research/milp-variance-constraints/milp-variance-constraints.md`:
   - Hit Friction Buffer: $\lambda_{\text{hit}} = 1.8\text{ pts}$ objective penalty per paid hit (`weekly_hit_limit=1`, effective hit hurdle $5.8\text{ xP}$).
   - Starter xMins Floor: Outfield starters require $\ge 65.0\text{ xMins}$, guarded against infeasibility via continuous slack $s^{\text{mins}}_{p, w} \ge 0$ with $-10.0\text{ pt}$ penalty.
   - First-Bench Cover: $\ge 12$ active squad players with $\ge 65.0\text{ xMins}$ (slack penalty $-1.5\text{ pts}$).
   - Defensive Stack Limiter: $\le 2$ DEF/GKP starters per Club (slack penalty $-1.2\text{ pts}$).
   - Goalkeeper Transfer Friction: $-1.5\text{ pt}$ penalty on GKP transfer-in, waived on Wildcard and Free Hit.
2. **Unconstrained Arm**: Pure point maximization with standard hits allowed (`weekly_hit_limit=1`, `hit_cost=4.0`, zero variance penalties).
3. **No Hit Arm**: Strict zero-hit baseline (`weekly_hit_limit=0`, Free Transfers only).
4. **Retired Heuristics**: Availability flag bans (`banned_next_gw`) and single-match missed starter locks (`locked_next_gw`) from ADR 0053 retired from scenario arm overrides in favor of native mathematical constraints. ADR 0053 horizon mean-reversion rule for `LearnedStartChallengerModel` stands.
5. **Post-Solve Audit**: Strategic solves record constraint adherence and slack penalties in `meta["strategic_audit"]` for CLI and Transfer Planner UI inspection.

**Status:** Accepted. Amends ADR 0042; supersedes scenario arm definition in ADR 0053.

**Considered:** Retain Conservative heuristic rules alongside variance constraints; keep Optimal label; create 4th arm. Rejected: Heuristic bans distort mathematical frontier; "Optimal" falsely implies unconstrained solves are universally best; 4 arms increase solve latency beyond 3-arm budget.

**Consequences:** `solver/scenarios.py` arms = `strategic` / `unconstrained` / `no_hit`. CLI `commands.solve` defaults to `strategic`. Dashboard Transfer Planner exposes Strategic Solver Options drawer with research baseline preset and renders Strategic Variance Audit in Decision Summary.
