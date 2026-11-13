# Backtesting and Promotion Foundation (ADR 0066)

**Status**: Accepted (2026-10-29); Amended (2026-11-12 `#180`; 2026-11-13 **Sections 1–7 retained, Section 8 and static `2026-27 GW6+` / provisional-ban clauses superseded by [ADR 0069](0069-annual-rolling-validation-and-dual-tier-promotion.md)**)

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
- Sealed holdout boundary updated by [ADR 0069](0069-annual-rolling-validation-and-dual-tier-promotion.md) (annual rolling validation firewall replaces static `2026-27 GW6+` lock; runtime guards migrating under `#185`).

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
- Paired calendar dependence evaluated via **non-wrapping Moving Block Bootstrap (MBB, $L=5$)** on stored score traces (`backtesting/evidence_statistics.py`). Re-solving the MILP inside bootstrap draws is strictly prohibited. When active differences exist ($\exists t : |\Delta_t| > 10^{-12}$), exact zero-mean resampled draws ($|\bar{\Delta}^*| \le 10^{-12}$) receive neutral `0.5` tie credit in `p_value_superiority`; pure no-op trajectories return `p_value_superiority = 1.0`.
- Search-wide family-wise error control (Q17) enforces $\text{FWER} \le 0.05$ across registered attempts within a mechanism family using Bonferroni (`default max_family_attempts = 1` for single-finalist confirmation, $\alpha_{\text{adj}} = \alpha_{\text{nominal}} / M$) and one-sided superiority evaluation (`p_value_superiority <= adjusted_alpha` or `ci_lower > 0.0`, yielding a 95% two-season bar for $M=1$ at $\alpha = 0.05$).
- Continuous multi-season normalized weighting across Development (`development_season`) and prospective Confirmation *(amended per `#180` / Section 8: previously inspected `2024-25` prohibited as fresh confirmation)*.
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

### 8. Amendment (`#180`, 2026-11-12) — *Superseded by [ADR 0069](0069-annual-rolling-validation-and-dual-tier-promotion.md) (2026-11-13)*

> **Superseded Notice**: Clean Governance Reset under Wayfinder Map [#184](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/184) (`ADR 0069`) replaced this section's `2027-28`-deferred `-30m` gate and provisional ban with Annual Rolling Validation (`S`=`2026-27` via `Randdalf/fplcache` `<= 24h`, `S-1`=`2025-26`, `S-2`=`2024-25`), Dual-Tier `Provisional Active` operation, and `GW15`/`GW30`/`GW38` checks. Retained technical pieces (`config/season_lifecycle.json`, pre-window `SeasonRules` verification, `+24h` outcome settlement) moved into `ADR 0069` & `#185`–`#187`.

- **Authoritative Confirmation Route**: Previously inspected `2024-25` results are disallowed as fresh confirmation regardless of hashes/aliases, and `Provisional Historical Promotion` without fresh confirmation grants zero authority. Primary confirmation requires future full-season prospective collection starting `2027-28 GW1–38` (neutral GW1 anchor `£100.0m`, `0` carried FT, `opening` anchor, causal `shared_chip_calendar`), keeping `2026-27 GW6+` strictly sealed throughout all `2025-26` development/ideation/smoke searches.
- **Pre-Window Rules & Registration Freeze**: Official native-rule verification (`docs/rules/scoring-rules-<season>.md`, `backtesting/season_rules.py`, `models/scoring_matrix.py`, `GUARD_SEMANTICS` per-guard applicability) must bind verified `rules_id`, `anchor_mode`, `prior_seed_digest`, and causal `shared_chip_calendar` into `protocol_hash` before registration opens; finalists freeze strictly at `registered_at < first_confirmation_gw_deadline`.
- **Two-Step Prospective Capture & Fail-Closed Missingness**: Each confirmation GW requires (1) raw HTTP `retain_receipt` (`2h` target / `6h` cap, `#175`) and (2) `commands.capture_live_evidence` (`before_deadline_minutes=30`, `clock="execution_utc"`) over 100% admitted universe leads `0..5` for Finalist + Champion. Missing or late (`> deadline` or `> 6h`) captures retain raw receipt flagged `late=True` for audit only and mark attempt `Invalid` (no Dead Lever moratorium; no GW skipping, zero-filling, backdating, or carry-forward heuristics).
- **Independent Settlement & Pre-Bundle Verification**: Outcomes admit only at `captured_at >= max(gw_kickoff) + 24h` with Official `finished=True` & `data_checked=True`, zero `admission_fixtures.py` missing rows or 13-component mismatches (preserving `#178` `minutes==0` card rule), blocking `OutcomeNotFinalizedError` on postponed fixtures, and a final pre-bundle Official API re-settlement check.
- **100%-Schedule Non-Peeking & Operational Post-Adoption Review**: Confirmation enforces `IncompleteScheduleError` over full registered GWs. `LiveCaptureManager.evaluate_live_review` (`min_gameweeks=4`, fixed 4-GW-spaced checkpoints) runs strictly **post-adoption** for manual human rollback monitoring (`PendingReview` / `RollbackRecommended`), never substituting for pre-adoption confirmation. Single-season ~38-GW power limitations (`~7–8` $L=5$ MBB blocks) allow `Inconclusive` verdicts (preserving Champion) to continue in successor fresh seasons (`2028-29+`) per `#181` calibration without relaxing `FWER <= 0.05`.
- **Dynamic Season Lifecycle & Prior-Seed Rollover (`#182`)**: Implement a versioned season-lifecycle contract (`config/season_lifecycle.json`) replacing hardcoded `2023-24`/`2024-25`/`2025-26`/`2026-27` checks across backtesting, features, models, CLIs, and `.agents/skills/`. Upon `2026-27` completion + ingest + `SeasonRules` verification, `2026-27` unlocks exclusively to `prior_seed_only` for `2027-28` seeding while remaining barred from Candidate tuning/ideation/smoke searches (`2025-26` remains Dev until `2027-28` closes). Automated collector recovery/idempotency tests execute offline + on `2025-26` mirrors in `#182` without accessing `2026-27 GW6+`.

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
