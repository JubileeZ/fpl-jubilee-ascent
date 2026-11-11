# EXT-35 execution artifacts

Fixed-K lagged creative-role donor prior. Four preregistered variants; inherited participation isolated from rate changes. Champion unchanged; models unregistered.

- [Specification](../../ideas/EXT-35-leave-player-and-club-out-creative-role-kernel-prior-at-fixed-defender-k.md)
- [Source and evidence review](review.md)
- [Retained diagnostic references](diagnostic_evidence.json)
- `prototypes.py`: frozen grid and manifest; no direct input-file reads.
- `checks.py`: synthetic causal, shrinkage, inheritance, and boundary checks.
- `diagnostic.py`: full-development native/oracle event-on/off capture; handed inputs forwarded unchanged.
- `summarize_diagnostic.py`: retained-artifact post-processing only; no model reruns.
- `paired_gameweeks.csv`, `interactions.csv`: verified diagnostic companions copied from retained summary.
- `dev_smoke.log`: complete fixed-grid development-screen output.
- `execution_results.csv`, `execution_summary.json`: all four terminal outcomes, including inertness admissions absent from smoke CSV. No development winner; scientific verdict inconclusive, ledger open.

Audit: `uv run python .agents/skills/explore-candidate/smoke.py docs/research/candidate-ideation/prototypes/ext_35/prototypes.py --audit_only`.

Synthetic checks: `uv run pytest -q docs/research/candidate-ideation/prototypes/ext_35/checks.py`.

## Metric definitions

- `oracle_regret_delta`: Champion minus candidate blended formation XI regret under reconstructed external-minute states. Higher better; ideal positive. One ordinary nonpassing screen row and three inert admission refusals retained separately.
- `oracle_bootstrap_probability`: existing non-wrapping paired block-bootstrap positive-delta probability. Higher better; oracle screen benchmark at least 0.65. Missing for refused variants; no invented bootstrap value.
- `max_playable_projection_shift`: maximum absolute candidate minus Champion projected points on exogenous playable population. Descriptive activation measure; harness rejects shifts below 0.01 when oracle-regret delta is zero. Larger shift does not imply better quality.

- `*_score_delta`: candidate selected lineup minus Champion selected lineup, same outcome target and participation regime, captain/autosubs included. Higher better; ideal positive. Actual/process/blended targets explicit in column name. Weekly diagnostic scores exclude transfers and hits; not rolling net points.
- `score_delta`: `blended_points_score_delta`; blend = equal actual/process weights. Higher better; ideal positive. Not the smoke runner's captain-excluding formation-regret delta.
- `fixed_selection_projected_delta`: sum candidate minus Champion forecasts on Champion starters, plus Champion captain forecast difference, without predicted autosubs. Descriptive signed forecast change; no preferred direction or ideal value.
- `*_fixed_selection_delta`: common observed outcome score on identical Champion lineup; ideal zero by construction. Any nonzero value signals inconsistent common outcomes or scoring.
- `selection_overlap`: intersection divided by union of selected 15-player squads. Descriptive stability; no preferred direction or ideal value.
- `churn_delta`: candidate minus Champion `top_15_squad_churn`; lower better; ideal no increase, diagnostic guard at most +0.50 players/GW. First GW undefined. Not actual transfers.
- `oracle_minus_native`: oracle paired `score_delta` minus native paired `score_delta`. Smaller absolute magnitude indicates regime stability; ideal zero for transport, not proof of model correctness.
- `*_formation_regret`: canonical best outcome XI score minus predicted XI score with bench auto-subs, captain excluded. Lower better; ideal zero; £100m 15-player squad and club constraints retained.

Capture limitation: original feature frames and rate diagnostics lack capture-time hashes. Later summary hashes establish current artifact identity only. All evidence here remains diagnostic; ADR 0066 admission, registered confirmation, and manual adoption required for production change.
