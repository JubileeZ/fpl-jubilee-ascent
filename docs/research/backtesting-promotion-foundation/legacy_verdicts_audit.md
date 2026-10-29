# Legacy Verdicts Audit Report

Audits historical candidate evaluations from `candidate_ledger.csv` against the 4-verdict foundation protocol.
Evaluates recorded artifacts only, without rerunning models, backtests, or solvers.

## Summary Metrics

- **Total Rows Audited**: 104
- **Pass (Shipped / Confirmed)**: 10
- **Demonstrated Fail**: 62
- **Inconclusive**: 29
- **Invalid (Defect / Missing)**: 3
- **Active Dead Lever Locks Preserved**: 92

## Breakdown by Audit Category

- `shipped_accepted`: 10
- `valid_negative`: 62
- `execution_defect`: 1
- `missing_evidence`: 2
- `unsupported_inference`: 29

## Governance and Dead Lever Policy

1. **Lock Integrity**: Inconclusive or Invalid classifications do not automatically reopen dead levers.
2. **Resource Governance**: The 1-year Dead Lever moratorium remains strictly active until the recorded `revisit_after` date.
3. **Reopening Bar**: Any reopening requires explicit user words, a documented rationale, and an approved protocol freeze.
