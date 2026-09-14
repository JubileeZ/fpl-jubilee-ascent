# Live Transfer Plan keeps Hits; do not retune xP until Champion bias is measured

Live `commands.solve` keeps `hit_cost=4` and `weekly_hit_limit=1`. Wildcard and Free Hit already waive Hits. A Hit the Solver Objective still wants after mean xP is calibrated is taken. Do not forbid live Hits by default. Do not add a calibration layer, raise `hit_cost`, or treat Hit-taking as overprediction until Champion `dual_vector_state_hybrid` signed bias (`projected_points − actual_points` vs Realized Points) is measured. Gate window: 2025-26 Season Archive GW1–38; 2026-27 is a sanity check only. Not FPL `ep_*`. Not third-party xP (ADR 0023). A later Hit-allowed vs Hit-forbidden walk-forward may justify a robustness margin; not a silent default change.

Gate measurement: `docs/research/champion-signed-bias-2025-26/champion_bias_summary.csv` `signed_bias`. Refresh via `uv run python -m commands.measure_champion_bias`. Do not add a calibration layer from that cell.

**Status:** Accepted.

**Considered:** `weekly_hit_limit=0` to match walk-forward; raise `hit_cost`; calibrate to FPL `ep_next` or third-party xP; tune on 2026-27 live pin. Rejected: Hit ban contradicts the kept live rule; third-party xP is Research-Only Evidence; live-season tune leaks the season being played.

**Consequences:** Walk-forward may still forbid Hits as a research policy. Squad What-If remains warn-only. Dream Team remains a Wildcard 15, not a Hit sequence.
