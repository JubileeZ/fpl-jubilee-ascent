# Backtesting and Promotion Foundation (ADR 0066)

**Status**: Accepted (2026-10-29)

**Amends / Supersedes**:
- Supersedes [ADR 0044](0044-blended-eval-target-promotion-primary.md) (Blended Eval Target as promotion primary; now a supporting diagnostic).
- Amends [ADR 0046](0046-point-in-time-backtest-and-statistical-gate.md) (Point-in-time features retained; single-GW regret replaced by rolling replay net score primary; 4-verdict taxonomy; attempt registry).
- Amends [ADR 0047](0047-two-season-promotion-gate.md) (Two-season evaluation retained; automatic promotion eliminated; fresh registered confirmation and manual adoption required).
- Supersedes [ADR 0049](0049-gate-bootstrap-060-no-min-effect.md) (Single-season $P \ge 0.60$ threshold replaced by search-wide family-wise error control $\text{FWER} \le 0.05$ via Bonferroni/Holm).
- Amends [ADR 0054](0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md) (Formation XI regret and squad churn preserved as fast development screens; rolling transfer plan net score is primary authority).
- Amends [ADR 0062](0062-non-catastrophic-segment-loss-promotion-guardrail.md) (Segment loss floors integrated into continuous multi-season protocol and substantive guards).
- Amends [ADR 0064](0064-promotion-gate-and-evaluation-rigor-overhaul.md) (Warm-seeded confirmation and non-wrapping MBB retained; binary pass/fail replaced by 4-verdict taxonomy; rolling net-score primary; manual adoption enforced).
- Reconciles [ADR 0020](0020-transfer-plan-walk-forward-first-half.md) (GW1–19 first-half walkforward retained as optional historical diagnostic; replaced by continuous 6-GW rolling replay primary).
- Freezes [ADR 0065](0065-strategic-arm-horizon-penalty-scaling-and-ft-schedule.md) (Strategic arm horizon scaling and diminishing FT schedule frozen as active research baseline).
- Retains sealed holdout boundary (2026-27 GW6+ strictly protected).

---

## Context

Previous promotion decisions relied on single-gameweek proxy regret formulations (ADR 0038 Process Points, ADR 0044 Blended Eval Target, ADR 0054 Formation XI regret). While these proxies isolated individual gameweek projection quality, they exhibited structural disconnects from the actual game:
1. **Disconnected Lineup Optimization**: Single-gameweek regret evaluates assets in isolation without modeling multi-period transfer budgets, selling price dynamics (half-profit rule), free transfer accumulation, or paid transfer hits.
2. **Binary Gate Vulnerability**: A binary pass/fail gate failed to distinguish genuine model defects from wide statistical uncertainty or operational execution failures, leading to false dead-lever lockouts or premature promotions.
3. **Automatic Promotion Hazard**: Unattended promotion routines (e.g. `--apply` flags or CI workflows) possessed unilateral write authority over `config/model_selection.json`, creating risks of accidental promotion on noisy or incomplete evidence.
4. **Adaptive Family Risk**: Multiple iterative re-evaluations under the same mechanism family inflated false-positive risk without formal family-wise error rate control.

Foundation discussions (Q1–Q28, `docs/research/backtesting-promotion-foundation/backtesting-promotion-foundation.md`) established an authoritative scientific standard aligning model evaluation with actual sustained-management net FPL points.

---

## Decisions

### 1. Primary Estimand: Rolling Transfer Plan Net FPL Points
- The primary promotion estimand is the **actual cumulative net FPL points** (gross points minus official hit deductions) achieved under an independent rolling 6-Gameweek Strategic transfer plan replay (`backtesting/rolling_replay.py`).
- Evaluation starts from a **neutral GW1 ownership anchor** (`backtesting/ownership_anchor.py`): the single highest summed reported ownership feasible £100m squad under official position/club constraints with exact lexicographic tie-breaking.
- Squad is locked at GW1 deadline; lineup and captain scored for GW1. Transfers begin at GW2 deadline.
- Candidate and Champion models evolve **independent continuous paths**: each maintains its own squad, player purchase prices, selling prices (half-profit rounding), bank balance, free transfer bank ($1 \le \text{FT} \le 5$), chip calendar, and official hit deductions ($-4$ per excess transfer).
- Single-gameweek proxies (Process Points, Blended Eval Target, Formation XI regret) are retained exclusively as supporting diagnostic screens.

### 2. Substantive Player-Level Projection Safeguards
- Candidates must pass substantive non-inferiority guards on player-level projections (`backtesting/projection_guards.py`):
  - Invariant common evaluation population masks (`extract_evaluation_population`) preventing candidate-manipulated evaluation sets.
  - Total-to-component ledger reconciliation (`reconcile_total_to_ledger`) enforcing strict point-event consistency.
  - Substantive non-inferiority bounds across total points, minutes, and measurable components (goals, assists, clean sheets, saves, bonus).
  - Explicit oracle-minutes diagnostics permitted for mechanism attribution but prohibited from promotion justification.

### 3. Numerical & Statistical Evaluation Protocol
- Paired calendar dependence evaluated via **non-wrapping Moving Block Bootstrap (MBB, $L=5$)** on stored score traces (`backtesting/evidence_statistics.py`). Re-solving the MILP inside bootstrap draws is strictly prohibited.
- Search-wide family-wise error control (Q17) enforces $\text{FWER} \le 0.05$ across registered attempts within a mechanism family using Bonferroni or Holm-Bonferroni step-down adjustments.
- Continuous multi-season normalized weighting across Development (2025-26, seed 2024-25) and un-tuned Confirmation (2024-25, seed 2023-24).
- Formal four-way scientific verdicts:
  - **`pass`**: Statistically significant positive net score delta meeting bootstrap bar, material-loss floors, and substantive guards.
  - **`fail`**: Statistically demonstrated regression or material harm.
  - **`inconclusive`**: Uncertainty spans zero, or fresh confirmation evidence is pending. Routes to registered confirmation; does NOT trigger a 1-year Dead Lever moratorium.
  - **`invalid`**: Contract breach, execution crash, or inert prototype. Does NOT trigger a 1-year Dead Lever moratorium.
- Execution status (`not_run`, `partial`, `censored`, `complete`) is tracked independently from the scientific verdict.

### 4. Immutable Confirmation Attempt Registry
- Confirmation evaluations require prior registration in an append-only JSONL registry (`backtesting/confirmation_registry.py`).
- Cryptographic SHA-256 tamper-evident integrity chaining (`verify_integrity()`).
- Tracks frozen source hash, parameter digest, protocol hash, and family history across aliases and model renames.
- Blocks duplicate or adaptive runs on active or completed attempts.
- Enforces strict stopping rules: full registered gameweek schedule must be completed before admission.
- Enforces Candidate Ledger safety: blocks active 1-year dead levers.
- Sealed Holdout Protection: strictly prohibits registration or evaluation on sealed season `2026-27 GW6+`.

### 5. Prospective Capture & Shadow Replay
- Operational live review uses scheduled pre-deadline capture (`backtesting/live_capture.py`) enforcing strict timestamp cutoffs (`capture_time <= deadline_time`). Late captures are permanently inadmissible.
- Dual shadow replay tracks independent states for provisionally adopted candidates and former champions.
- Outcome finalization delay prevents peeking before official gameweek point settlement.
- Minimum evaluation horizon prevents knee-jerk rollbacks on weekly variance.
- Material-harm rollback recommendations require explicit human approval and cite exact bundle hashes.

### 6. Read-Only Pipelines & Explicit Manual Adoption
- All evaluation CLI commands (`commands/evaluate_model_promotion.py`) and CI workflows are strictly read-only with respect to Model Champion configuration (`config/model_selection.json`).
- Champion adoption is strictly isolated in an explicit function (`adopt_champion`):
  - Requires verified evidence bundle hash.
  - Requires scientific verdict `pass` and execution status `complete`.
  - Requires non-empty human approval reference (`approval_ref`).
  - Requires expected current champion match.
  - Fails closed on any discrepancy, partial data, or inconclusive verdict.

### 7. Strategic Optimization Constants Freeze
- Effective Strategic arm optimization settings (ADR 0061, ADR 0065) are frozen as the authoritative research baseline:
  - Horizon scaling for one-off friction penalties: $\text{scale}(H) = \sum_{k=0}^{H-1} \delta^k / \sum_{k=0}^4 \delta^k$ ($\delta = 0.85$).
  - Effective hit hurdle: $4.0 + 1.8 \times \text{scale}(H)$.
  - Goalkeeper transfer friction: $1.5 \times \text{scale}(H)$.
  - Diminishing emergency FT value schedule: `{"2": 2.0, "3": 1.2, "4": 0.6, "5": 0.2} * scale(H)`.
  - Weekly variance constraints (Starter xMins floor, First-Bench cover, DEF stack cap) remain active.

---

## Considered Options

Key alternatives evaluated and rejected during Q1–Q28 foundation research:
1. **MILP Solver Inside Bootstrap Draws**:
   - *Proposal*: Re-solve the full rolling MILP transfer plan on every bootstrap draw ($B=1000$).
   - *Rejected*: Infeasible computational cost (~200 CPU hours per evaluation) with zero statistical benefit over resampling stored paired score differences ($\Delta_t = \text{cand}_t - \text{champ}_t$) that directly preserve the paired calendar autocorrelation structure.
2. **Mandatory Multi-Archetype Panel Evaluation**:
   - *Proposal*: Require simultaneous wins across diverse initial squads (e.g. premium-heavy, budget-spread, chip-early).
   - *Rejected (Q28)*: High portfolio collinearity and arbitrary archetype weights. Replaced by a single objective neutral GW1 ownership anchor (highest-owned feasible £100m fifteen) with optional archetype diagnostics.
3. **Automatic Promotion from CI Workflows or CLI Flags**:
   - *Proposal*: Allow `--apply` or scheduled GitHub Actions workflows to write `config/model_selection.json` when tests pass.
   - *Rejected*: Poses critical operational hazard of silent production mutation from stale, unconfirmed, or noisy runs. Replaced by strict read-only pipelines and explicit manual adoption (`adopt_champion`) requiring human approval references.
4. **Binary Pass / Fail Gate**:
   - *Proposal*: Retain binary gate forcing all non-passing runs into 1-year Dead Lever locks.
   - *Rejected*: Collapses execution defects (invalid) and wide uncertainty (inconclusive) into model failure. Replaced by 4-way scientific taxonomy where inconclusive runs route cleanly to fresh confirmation.

---

## Consequences

- Model promotions are governed exclusively by actual sustained-management net FPL points, eliminating proxy-gaming.
- Automated CI workflows cannot silently alter model selection.
- Research attempts maintain cryptographic provenance and statistical error control.
- Inconclusive results direct candidates to confirmation rather than prematurely locking them in the Dead Lever moratorium.
- Sealed holdout season (2026-27 GW6+) remains untainted.
