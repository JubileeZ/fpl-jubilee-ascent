# Champion multi_feature_assist_challenger; confirmation-season bootstrap bar 0.60

**Amended by ADR 0049**: bootstrap bar 0.60 on both seasons; minimum effect removed.

Amends ADR 0047: 2024-25 confirmation season bootstrap bar lowered 0.95 → 0.60 (`CONFIRMATION_BOOTSTRAP_MIN_P`, `backtesting/promotion.py`; `compare_to_reference(..., bootstrap_min_p=...)`; CLI `commands.evaluate_model_promotion --confirmation`; smoke `--season confirm`). Other confirmation criteria unchanged (delta ≥ 1% Champion regret, ≥2/3 segments, guardrails). 2025-26 development season keeps 0.95. User decision 2026-09-28, set after first 2024-25 verdict seen (post-hoc; recorded as such).

`multi_feature_assist_challenger` replaces `face_value_challenger` as Model Champion. Assists = ridge Poisson GLM on as-of player xA/90, creativity/90, opponent xG conceded, own-team xG, home; rest of ledger = `face_value_challenger`. Evidence `docs/research/multi-feature-event-rate/confirmation_gate_summary.csv`: 2025-26 PASS (delta +0.901, P 0.976, 2/3 segs); 2024-25 delta +0.796 ≥ 0.630, 3/3 segs, P 0.896 → FAIL at 0.95, PASS at 0.60. Status provisional. 2026-27 GW6+ post-promotion check (ADR 0047) applies; FAIL → revert to `face_value_challenger` on user's words.

**Considered Options**: keep 0.95, not promote — rejected by user; one-time override keeping 0.95 — rejected by user (wants standing lower bar); lower both seasons — not chosen (2025-26 = tuning season, overfit risk highest).
