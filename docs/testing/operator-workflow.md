# Backtesting & Promotion Foundation Operator Workflow

**Status**: Authoritative Operator Guide (ADR 0066)  
**Governing Standard**: [ADR 0066](../adr/0066-backtesting-and-promotion-foundation.md) · [Foundation Rationale](../research/backtesting-promotion-foundation/backtesting-promotion-foundation.md)

**Operational boundary (2026-10-30):** Legacy archive walkforward and smoke results = diagnostics only. Final recommendation re-verifies retained replay evidence through `backtesting.promotion_evidence`; synthetic admission cannot authorize production adoption. Empirical admission and approved numerical calibration remain prerequisites, not outcomes of infrastructure tests. Bonferroni supported with frozen family budget; chronological/sequential Holm configuration rejected.

---

## 1. Lifecycle Overview

The evaluation lifecycle separates research exploration from scientific confirmation, read-only recommendation, and manual adoption:

```
[1. Register] ──> [2. Capture / Forecast] ──> [3. Verify / Admit] ──> [4. Replay]
                                                                            │
[8. Review / Rollback] <── [7. Human Adopt] <── [6. Recommend] <── [5. Evaluate]
```

| Stage | Operation | Primary Command / Module | Mutation Authority |
|---|---|---|---|
| **1. Register** | Register frozen finalist in append-only confirmation registry | `backtesting.confirmation_registry` | Append-only registry record |
| **2. Capture** | Pre-deadline prospective capture or point-in-time forecast | `backtesting.live_capture` / `backtesting.forecast_adapter` | Read-only input snapshot |
| **3. Verify** | Causal input admission & component reconciliation | `backtesting.data_admission` / `backtesting.projection_guards` | Read-only validation |
| **4. Replay** | Rolling multi-deadline Strategic transfer plan simulation | `backtesting.rolling_replay` | In-memory / trace cache |
| **5. Evaluate** | Block bootstrap, loss floors, and guard checks | `backtesting.evidence_statistics` | Evaluation metrics |
| **6. Recommend** | Generate verified evidence bundle and scientific verdict | `commands.evaluate_model_promotion` | Evidence bundle JSON (read-only) |
| **7. Adopt** | Explicit user-authorized Champion update | `commands.evaluate_model_promotion --adopt` | `config/model_selection.json` |
| **8. Review** | Dual shadow replay and material-harm monitoring | `backtesting.live_capture` | Rollback recommendation |

---

## 2. Stage-by-Stage Operator Instructions

### Stage 1: Register Finalist Attempt
Before executing a formal confirmation evaluation, register the frozen finalist in the append-only registry:
```python
from backtesting.confirmation_registry import ConfirmationRegistry

registry = ConfirmationRegistry("data/confirmation_registry.jsonl")
entry = registry.register_finalist(
    candidate_name="my_model_challenger",
    champion_name="def_xg_shrink_challenger",
    mechanism_family="def_xg_shrink_family",
    model_source_hash=frozen_model_source_hash,
    parameters_hash=frozen_parameters_hash,
    dev_selection_record_ref="docs/research/my-topic/dev_evidence.csv",
    protocol_hash=frozen_protocol_hash,
    attempt_id="att_20261029_cand_01",
    registered_gameweeks=list(range(1, 39)),
    requested_seasons=["2024-25"],
    max_family_attempts=frozen_attempt_budget,
)
```
- **Integrity**: `registry.verify_integrity()` validates the entire cryptographic SHA-256 chain.
- **Moratorium Check**: Fails closed if the mechanism is an active Dead Lever in `docs/research/candidate-ledger/candidate_ledger.csv`.
- **Holdout Boundary**: Strictly rejects attempts targeting sealed season `2026-27 GW6+`.
- **Frozen identities**: Variables above = hashes of retained source, parameters and complete approved protocol; example is a registration shape, not standalone runnable evidence. Register before confirmation; preserve inspected-data history.
- **Completion**: Attach exact completed confirmation score digest and schedule before assessment. Finalize scientific verdict after reconstruction. Duplicate IDs, terminal verdict replacement and reopening terminal attempts rejected.

### Stage 2 & 3: Input Capture, Causal Forecasts & Admission
- Prospective captures require `capture_time <= deadline_time`. Late captures are rejected with `LateCaptureError`.
- Local capture command: `uv run python -m commands.capture_live_evidence --request data/reports/my-evaluation/capture-request.json --storage data/reports/live-captures`. Request identifies retained admission, verified forecast store/ID, model/source hash and protocol hash. Command uses execution-time UTC; caller-supplied capture time rejected. Configure an actual pre-deadline local job separately; this guide creates no scheduled task. A configured job is readiness evidence, not completed prospective validation.
- For historical backtesting, inputs are strictly point-in-time from pre-deadline performance rows without terminal leakage (`features.builder`).
- Forecast generation verifies total-to-component ledger reconciliation:
  $$\text{projected\_points} = \sum_{c} \text{xp\_component}_c \quad (\pm 10^{-9})$$
- Common evaluation population masks (`extract_evaluation_population`) ensure identical player universes across comparator models.

### Stage 4: Rolling Multi-Deadline Transfer Plan Replay
Execute continuous sustained-management evaluation:
- Initializes from **neutral GW1 ownership anchor** (`backtesting/ownership_anchor.py`): £100m budget, official constraints, highest summed ownership with deterministic lexicographic tie-breaking.
- GW1 squad locked; transfers begin GW2.
- Solves independent 6-GW Strategic transfer plans per model:
  - Tracks player ownership, purchase prices, selling prices (half-profit rule), bank balance, native free-transfer cap (2 in 2023-24; 5 in 2024-25/2025-26; GW1 locked with 0), chip history, and official hit deductions ($-4$).
  - Produces deterministic checkpoints (`record_to_dict`, `record_from_dict`) allowing offline reconstruction without an active solver.
- Native adapter = `backtesting.native_transfer_solver.native_strategic_solve`; complete issue-time price/club/position/eligibility and all target points/minutes required. Planning holds issue prices constant; subsequent deadlines refresh metadata from that deadline's admitted forecast. Native season rules and shared fixed chip calendar enforced.
- Explicit `heuristic_zero_transfer_solve` = diagnostic fixture only; cannot supply final evidence. Solver quality uses measured objective/bound/gap and termination status.

### Stage 5 & 6: Evaluation & Recommendation
Generate complete evidence bundle and 4-way scientific verdict:
```bash
# Reconstruct registered multi-season replay evidence; no new model or solver runs
uv run python -m commands.evaluate_model_promotion \
  --evidence_request data/reports/my-evaluation/request.json \
  --output_bundle data/reports/my-evaluation/recommendation_bundle.json
```
Request contract: `backtesting.promotion_evidence.EVIDENCE_VERSION`; exact candidate/former Champion, frozen source and parameters, hashed protocol/live-readiness references, registry path/attempt ID, both comparator replay entries for each declared season, and separately admitted target-GW `guard_outcome_sources` covering every forecast lead. Each replay retains anchor, full trace and per-issue admission/forecast-store references. All referenced evidence remains inside request directory; every checksum, source admission, native transition, forecast population and guard input re-verified. Copying a `pass` field into JSON cannot produce a recommendation.

`development_selection` descriptor retains exact development trace references and identities; its hash must match registry development-selection reference. Development generation precedes finalist registration; confirmation generation follows registration. Previously generated confirmation forecasts cannot be relabeled as a fresh registered attempt. Supported model parameters currently empty (`{}`); nonempty parameter payloads rejected until generator support is explicit and tested.

Protocol binds complete windows, six-GW horizon, shared chip calendar, solver/quality policy, required guard definitions and statistical settings. Missing guards or incomplete execution never become Pass. Existing `--data_dir`/`--two_season` routes remain diagnostic; `--apply` may write diagnostic reports but cannot authorize promotion. No command above acquires or admits historical data.

Guard outcomes distinguish demonstrated non-inferiority, demonstrated harm and overlapping uncertainty. A wide interval crossing the harm margin is Inconclusive; a single observation cannot supply an estimated uncertainty interval. Invalid numeric evidence stays Invalid. Unapproved numerical limits cannot establish scientific Pass or Fail. Season/segment floors use canonical gameweek segments; chip-state flags come from executed decisions.

Projection guards aggregate fixture forecasts to common player/issue/target-GW cells, then compare with complete independently admitted actual target-GW totals. Later fixture introductions count in observed totals; original blanks are not automatically observed zeros. Postponed fixtures follow finalized target-GW chronology. Zero permitted only from complete admitted outcome coverage; missing player/source/component evidence blocks assessment. Future outcome packages never enter issue-time feature or solver inputs.
Output yields:
- **`pass`**: Delta $> 0$, bootstrap bar met with family-wise error control ($\text{FWER} \le 0.05$), non-catastrophic segment floors held, substantive guards passed.
- **`fail`**: Statistically demonstrated regression or material harm.
- **`inconclusive`**: Uncertainty spans zero or confirmation evidence pending. Routes to registered confirmation; does NOT trigger 1-year Dead Lever lock.
- **`invalid`**: Contract breach, execution crash, or inert prototype. Does NOT trigger 1-year Dead Lever lock.

### Stage 7: Manual Champion Adoption
Once an evidence bundle has achieved scientific verdict `pass` and execution status `complete`, the operator executes explicit manual adoption:
```bash
uv run python -m commands.evaluate_model_promotion \
  --adopt path/to/evidence_bundle.json \
  --approval_ref "RFC-2026-10-29-PROD-01" \
  --expected_champion "def_xg_shrink_challenger" \
  --bundle_hash "<exact-approved-bundle-hash>"
```
- Re-validates evidence bundle cryptographic integrity.
- Re-validates verdict == `'pass'` and execution_status == `'complete'`.
- Validates non-empty `approval_ref`.
- Validates current Champion matches `expected_champion`.
- Binds approval to exact bundle hash and candidate; re-verifies retained source/parameters/protocol, complete confirmation registry and live-readiness declaration. Synthetic evidence rejected; candidate override cannot select another comparison row.
- Atomically updates `config/model_selection.json` and preserves previous Champion in candidate comparison slate.

### Stage 8: Prospective Review & Rollback
For deployed champions, prospective shadow replay runs each gameweek:
- Tracks provisionally adopted champion and former champion independently.
- `step_shadow_state` requires retained native `ReplayState`, native `Decision` and complete finalized `OutcomeBatch`; sparse player IDs/point totals cannot reconstruct purchase prices, bank, chip history, appearances or autosubs and are rejected.
- Outcomes are evaluated after official settlement delay.
- If material harm is detected over fixed evaluation horizons ($H \ge 4$), the engine emits a rollback recommendation citing the bundle hash and requiring human approval:
```python
from backtesting.live_capture import evaluate_live_review

review = evaluate_live_review(
    season="2025-26",
    gameweeks=list(range(1, 5)),
    adopted_history=adopted_history,
    champion_history=champion_history,
    material_loss_limit=8.0,
    min_gameweeks=4,
)
if review.should_rollback:
    print(f"ROLLBACK RECOMMENDED: {review.rollback_reasons}")
    print("Action requires human approval reference: approval_ref")
```

---

## 3. Failure Recovery & Interruption Resumption

- **Interrupted Replay**: Provide explicit frozen model/protocol hashes and the same evaluation identity. Resume re-verifies full checkpoint contents, parent lineage, forecasts, outcomes, native transition and score; deserialization alone does not establish validity. Changed horizon/calendar/policy/model/forecast requires distinct problem identity.
- **Corrupt Cache**: Content-addressed SHA-256 digests detect altered bytes immediately. Delete the corrupt deadline checkpoint and re-solve.
- **Incomplete Confirmation Schedule**: Stopping rules block admission of partial schedules (`IncompleteScheduleError`). Complete the remaining registered gameweeks before verdict finalization.
- **Profiling**: `uv run python -m commands.profile_transfer_replay --problem-manifest data/reports/native-problems.json --output data/reports/native-profile.json` executes actual HiGHS calls on retained synthetic native problems. Manifest: `version=1`, `mode=synthetic_diagnostic`, `problems` containing unique `problem_id`, predefined `archetype`, complete native `state`, `horizon`, `forecasts.rows` and shared `chip_calendar`. Input assumptions and content hashes retained; measured solve time remains distinct from empirical full-season runtime evidence. Hard cap: 20 calls, 30 seconds/call, one thread, serial, 20 minutes total. `--dry-run` reports explicit simulation; no policy recommendation from simulated timings. Empirical profiling inputs require separate causal admission authority; unavailable cache/resume measurements remain missing.

---

## 4. Supported Seasons, Components & Chips

- **Supported Historical Seasons**: 2023–24 (seed only), 2024–25 (Confirmation), 2025–26 (Development).
- **Sealed Season**: 2026–27 GW6+ (Holdout; access strictly prohibited).
- **Supported Event Components**:
  - `xp_goals`, `xp_assists`, `xp_clean_sheet`, `xp_saves`, `xp_defcon`, `xp_bonus`, `xp_minutes`.
- **Supported Chips**: Bench Boost, Triple Captain, Free Hit, Wildcard.
