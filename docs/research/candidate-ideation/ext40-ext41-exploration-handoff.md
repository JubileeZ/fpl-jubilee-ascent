# EXT-40 and EXT-41 exploration handoff

Scoped EXT-41 forecast screen complete. See [results and replay reproduction](ext41-gw1-4-attack-screen.md). Retained handoff below records fixed test and historical source preparation.

## Disposition

- **EXT-40 dynamic goals and assists — close.** Both forecast from GW1 with zero destination-season fit labels. Every fixed arm improves Champion fixture-component MSE and loses to matched static. No candidate rolling replay or combined arm earned under original gate. Preserve closed queue row and open research ledger without new Dead Lever lock. Use static count heads as EXT-41 Arm A. Post-result static performance supplies control evidence. [EXT-40 screen](ext40-gw1-4-attack-screen.md)
- **EXT-41 Champion features — screen closed.** Source feature preflight verified 33 deadline-bound forecast origins and 9,294 matched training rows per component with zero missing expected rows. Goals and assists run independently at λ=0.03. A uses static process and fixture features, B adds same-component Champion xP, C adds all 13 original Champion components. Champion remains unchanged as paired reference. [EXT-41 dossier](ideas/EXT-41-champion-component-features-for-event-counts.md) · [Source coverage](ext41-source-coverage.csv)

## Recover on another device

Use Python 3.14 and the committed `uv.lock`. From the repository root, run `uv sync --locked` and set the research module search path for the current shell.

| Shell | Search path |
| --- | --- |
| PowerShell | `$env:PYTHONPATH = '.;docs/research/candidate-ideation'` |
| Bash | `export PYTHONPATH=.:docs/research/candidate-ideation` |

```sh
uv run --locked python -m prototypes.ext_40.prepare .tmp/agent/explore-candidate/ext_40
uv run --locked python -m prototypes.ext_40.audit
uv run --locked python -m prototypes.ext_41_preflight .tmp/agent/explore-candidate/ext_40
```

Preparation recovers hash-pinned public 2024–25 and 2025–26 receipts. The checked-in 2023–24 processed archive provides Champion's source-year priors. Preflight builds source issue forecasts using dated bootstrap and fixture inputs, earlier published settlement only and native 2024–25 rules. Source output under `ext41_source/` contains each issue's original Champion parquet and `coverage.csv`. Use lead-0, nonblank rows for source regressors and attach labels only after issuance. Preserve EXT-40's five excluded source weeks (GW1–2 without usable process history, GW23/33/35 without supported fixtures) across all A/B/C arms. A missing expected key, duplicate key, post-deadline receipt or unusable component blocks the comparison. Commit no regenerated scratch or forecasts.

Coverage columns `*_examples` count expected training rows per component and origin. `*_matched` counts one-to-one fixture-key matches with a valid Champion component vector. Ideal coverage equals expected for every origin. Forecast digests identify exact parquet bytes for the observed run. Use row-level parity for reproducibility across platform serialization differences.

To reproduce the closed EXT-40 forecast result, run `uv run --locked python -m prototypes.ext_40.run .tmp/agent/explore-candidate/ext_40`. Use a new run identity if platform serialization, Champion, sources, or code changes. Retain the original reports.

## Decide from the fixed test

1. Generate immutable issue-time Champion vectors on S-1 Dev 2025–26 GW1–4, plus prior-season training vectors. Prove all variants fit zero current-season labels in GW1, respond to admissible roster/fixture context, and remain invariant to mutations of target or later labels. Record fallback and changed nonblank GW1 rows, including new players. Keep original Champion state probabilities and all unrelated scoring components. Apply native event scoring and reconcile fixture xP.
2. Record A, B, C and Champion on identical outfield player-fixture keys. Use lead-0 component MSE as the early accuracy gate, report leads separately, and report a changed legal selection or rolling decision. C must strictly beat Champion, A and B. B supplies evidence about the same-component feature. Preserve identical source cohorts, regularization, participation inputs and label timing.
3. Run one certified 600s zero-gap paired rolling replay at a time for C heads that pass the forecast gate. Require nonnegative GW1–4 net delta against same-policy Champion with shared neutral anchor and native FPL rules. Combine only if goals and assists both pass independently, then rerun the early accuracy, decision, and reconciliation checks on the combination. Both heads read the same original Champion snapshot. Record which gates stop each arm.
4. Record queue and ledger results. For any promotion-track survivor, follow standard S-1 development and frozen S-2 historical-filter gates. S-2 needs a separate pre-2024–25 training panel with independently verified source Champion feature receipts. Keep 2026–27 sealed. GW1–4 comparisons carry development diagnostic authority.

[Historical archive testing](../../testing/archive-testing.md) · [Eval canon](../INDEX.md) · [Candidate Ledger](../candidate-ledger/candidate-ledger.md)
