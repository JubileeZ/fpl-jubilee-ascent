# Backtesting & Promotion Foundation Operator Workflow

**Status**: Authoritative Operator Guide (ADR 0066)  
**Governing Standard**: [ADR 0066](../adr/0066-backtesting-and-promotion-foundation.md) · [Foundation Rationale](../research/backtesting-promotion-foundation/backtesting-promotion-foundation.md)

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
    model_source_hash="f5e71b7e" + "0" * 56,
    parameters_hash="a1b2c3d4" + "0" * 56,
    dev_selection_record_ref="docs/research/my-topic/dev_evidence.csv",
    protocol_hash="p1p2p3p4" + "0" * 56,
    attempt_id="att_20261029_cand_01",
    registered_gameweeks=list(range(1, 39)),
)
```
- **Integrity**: `registry.verify_integrity()` validates the entire cryptographic SHA-256 chain.
- **Moratorium Check**: Fails closed if the mechanism is an active Dead Lever in `docs/research/candidate-ledger/candidate_ledger.csv`.
- **Holdout Boundary**: Strictly rejects attempts targeting sealed season `2026-27 GW6+`.

### Stage 2 & 3: Input Capture, Causal Forecasts & Admission
- Prospective captures require `capture_time <= deadline_time`. Late captures are rejected with `LateCaptureError`.
- For historical backtesting, inputs are strictly point-in-time from pre-deadline performance rows without terminal leakage (`features.builder`).
- Forecast generation verifies total-to-component ledger reconciliation:
  $$\text{projected\_points} = \sum_{c} \text{xp\_component}_c \quad (\pm 10^{-9})$$
- Common evaluation population masks (`extract_evaluation_population`) ensure identical player universes across comparator models.

### Stage 4: Rolling Multi-Deadline Transfer Plan Replay
Execute continuous sustained-management evaluation:
- Initializes from **neutral GW1 ownership anchor** (`backtesting/ownership_anchor.py`): £100m budget, official constraints, highest summed ownership with deterministic lexicographic tie-breaking.
- GW1 squad locked; transfers begin GW2.
- Solves independent 6-GW Strategic transfer plans per model:
  - Tracks player ownership, purchase prices, selling prices (half-profit rule), bank balance, free transfer bank ($1 \le \text{FT} \le 5$), chip history, and official hit deductions ($-4$).
  - Produces deterministic checkpoints (`record_to_dict`, `record_from_dict`) allowing offline reconstruction without an active solver.

### Stage 5 & 6: Evaluation & Recommendation
Generate complete evidence bundle and 4-way scientific verdict:
```bash
# Multi-season evaluation (read-only; generates evidence bundle JSON)
uv run python -m commands.evaluate_model_promotion \
  --data_dir data/archive/2025-26/processed \
  --seed_season 2024-25 \
  --confirmation_data_dir data/archive/2024-25/processed \
  --confirmation_seed_season 2023-24
```
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
  --expected_champion "def_xg_shrink_challenger"
```
- Re-validates evidence bundle cryptographic integrity.
- Re-validates verdict == `'pass'` and execution_status == `'complete'`.
- Validates non-empty `approval_ref`.
- Validates current Champion matches `expected_champion`.
- Atomically updates `config/model_selection.json` and preserves previous Champion in candidate comparison slate.

### Stage 8: Prospective Review & Rollback
For deployed champions, prospective shadow replay runs each gameweek:
- Tracks provisionally adopted champion and former champion independently.
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

- **Interrupted Replay**: Replay checkpoints are saved per deadline. On restart, verify the last valid state dictionary (`record_from_dict`) and resume from deadline $t+1$.
- **Corrupt Cache**: Content-addressed SHA-256 digests detect altered bytes immediately. Delete the corrupt deadline checkpoint and re-solve.
- **Incomplete Confirmation Schedule**: Stopping rules block admission of partial schedules (`IncompleteScheduleError`). Complete the remaining registered gameweeks before verdict finalization.

---

## 4. Supported Seasons, Components & Chips

- **Supported Historical Seasons**: 2023–24 (seed only), 2024–25 (Confirmation), 2025–26 (Development).
- **Sealed Season**: 2026–27 GW6+ (Holdout; access strictly prohibited).
- **Supported Event Components**:
  - `xp_goals`, `xp_assists`, `xp_clean_sheet`, `xp_saves`, `xp_defcon`, `xp_bonus`, `xp_minutes`.
- **Supported Chips**: Bench Boost, Triple Captain, Free Hit, Wildcard.
