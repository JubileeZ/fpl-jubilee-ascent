# EXT-07 implementation lineage

- No new statistical estimator, data source, or tuned constant.
- `ExposureReplay.predict`: unchanged Adaptive prediction produces final H1/H3 states. Before GW20 or insufficient history: returns inherited output exactly.
- Instance scorer hook captures effective row after DEF xG shrink, inherited HoldChase xG/GC adjustments, and conditional-minute preparation. Replaying scorer directly avoids applying any `predict` wrapper twice.
- Inherited `_assist_rates` cache remains unchanged between original prediction and replay. Each conditional state calls inherited scorer once; cached GLM assist rate replaces baseline assists once.
- `_event_multipliers`: same causal panel, scaler, Group A Poisson fit/normalization/clamps, Group B LOO factor as existing ML implementation. Recomputed to recover multipliers exactly even when original anchor goal exposure equals zero. This duplicates computation, not evidence or model fitting specification. No extra head or hyperparameter.
- Final p_start preserved. Existing `blend_states` reconciles remaining bench/DNP mass. Conditional durations scaled only when current non-oracle cap binds. Existing p60 threshold semantics retained.
- Event points reconstructed per state, mixed by final state probabilities. Existing Group A/B factors applied once. BPS count increments: goal point delta divided by position goal points, multiplied by 24; assist point delta divided by 3, multiplied by 12.
- Inherited bonus allocation first runs while generating the required Champion anchor. That discarded anchor bonus never enters replay result. Final bonus initializes to zero and existing P60-weighted allocator runs once on replayed BPS. No bonus law change.
- All component outputs reconciled through `LEDGER_COMPONENTS`. Runtime simplex/minute-expectation checks.

## Manifest namespace limitation

Harness accepts only `features`, `history`, `local`; no output/derived namespace. Manifest uses existing FeatureContract state keys for inherited projection-state labels and `history` for causal-panel intermediates/targets. The two `local` entries, `xbps` and `eligible_bonus`, are static output-schema key labels, not data inputs. They read no file or external object. Manifest-only normalization performed during ongoing smoke; model logic unchanged.

- Actual FeatureContract reads: IDs, position, optional external minutes, cap; effective event-rate fields handed in by inherited row.
- Deterministic inherited projection outputs: probabilities, conditional duration, conditional P60, scoring components.
- Inherited scorer output-schema labels: xbps, eligible_bonus.
- Causal-panel intermediates from supplied fit history / predict features: obs_count, shrunk_xg90, shot_quality_ratio, club_xg_share, finishing_offset_90, team_att_ratio, opp_def_ratio, is_home, pos_*.
- Strict pre-target training outcomes: target_minutes, target_expected_goals, target_goals_blend.
- LOO teammate finishing: inherited causal panel factor using pre-target history only.

## Verification

- `--audit_only`: AUDIT PASS.
- `uv run pytest .tmp/agent/explore-candidate/ext_07/test_replay.py -q -p no:cacheprovider`: 8 passed, including inherited DEF adjustment identity.
- Initial full smoke: OS named-pipe permission crash before any evaluation, not model verdict.
- Same exact smoke command with named-pipe permissions: running; result pending.
- Parent durable-copy verification: `uv run pytest docs/research/candidate-ideation/prototypes/ext_07/checks_replay.py -q`, 8 passed; pytest cache warning only.
