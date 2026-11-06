# Legacy Verdicts Audit Report

**Updated**: 2026-11-05T06:35:00Z  
**Data stamp**: docs/research/candidate-ledger/candidate_ledger.csv (108 rows)  
**Season**: Multi-season  
**Status**: Active  
**Purpose**: Audit historical candidate evaluations from candidate_ledger.csv against the 4-verdict foundation protocol without rerunning models, backtests, or solvers.  
**Scope**: Evaluates recorded artifacts only. Strictly preserves 1-year Dead Lever locks.  
**Artifact**: [legacy_verdicts_audit.csv](legacy_verdicts_audit.csv)  

## Sources

- **Repository data**: `docs/research/candidate-ledger/candidate_ledger.csv` — historical candidate log (108 records)

## Method

Classify recorded attempts against 4-verdict taxonomy (`pass`, `fail`, `inconclusive`, `invalid`) and 5 audit categories (`shipped_accepted`, `valid_negative`, `execution_defect`, `missing_evidence`, `unsupported_inference`). Maintain strict fail-closed Dead Lever lock policy.

## Findings

### Summary Metrics

- **Total Rows Audited**: 108
- **Pass (Shipped / Confirmed)**: 10
- **Demonstrated Fail**: 66
- **Inconclusive**: 31
- **Invalid (Defect / Missing)**: 1
- **Active Dead Lever Locks Preserved**: 96

### Breakdown by Audit Category

- `shipped_accepted`: 10
- `valid_negative`: 66
- `execution_defect`: 1
- `missing_evidence`: 0
- `unsupported_inference`: 31

## Decision

1. **Lock Integrity**: Inconclusive or Invalid classifications do not automatically reopen dead levers.
2. **Resource Governance**: The 1-year Dead Lever moratorium remains strictly active until the recorded `revisit_after` date.
3. **Reopening Bar**: Any reopening requires explicit user words, a documented rationale, and an approved protocol freeze.

## Risks and unknowns

- Legacy runs with incomplete artifacts remain permanently classified inconclusive/invalid without retrospective re-evaluation.
