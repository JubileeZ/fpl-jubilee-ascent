# Promotion gate: bootstrap bar 0.60 both seasons, no minimum effect

Amends ADR 0046 (bar 0.95, min effect 1%), ADR 0047 (two-season gate), ADR 0048 (confirmation bar 0.60, dev 0.95). Historical Promotion Gate on 2025-26 development season and 2024-25 confirmation season:

- block-bootstrap P(delta > 0) ≥ **0.60** both seasons (`BOOTSTRAP_MIN_P` = `CONFIRMATION_BOOTSTRAP_MIN_P` = 0.60, `backtesting/promotion.py`);
- minimum effect removed (`MIN_EFFECT_SHARE` = 0.0): combined Blended `top_11_regret` delta must be > 0; bootstrap P alone judges whether improvement is real.

Unchanged: Blended `top_11_regret` primary, ≥2/3 segments, guardrail tolerances; 2024-25 one run per frozen Candidate, no seed, never tuned; 2026-27 GW6+ sealed, one post-promotion check per Champion.

User decisions 2026-09-28, all post-hoc; recorded as such. (1) After dual-lane search (`docs/research/dual-lane-candidate-search/smoke_results.csv`: 88 variants, 0 pass at 0.95; best guardrail-clean `s4_e60_w100_mglob` P 0.928) → bar 0.75 both seasons. (2) After frozen `learned_start_challenger` confirmation FAIL at 0.75 (`candidate_gate.csv`: 2024-25 +0.518 < min effect 0.622, 2/3, P 0.638) → bar 0.60. (3) Same run still FAIL on min effect → min effect removed. Same run re-scored (no new 2024-25 look): PASS.

**Consequences**: gate much weaker than ADR 0046. Candidate ahead in 3 of 5 resampled seasons + any positive delta + 2/3 segments on both seasons = pass. Small, noisy improvements now promote; forking-path risk on dev season high (many variants per search) → 2024-25 one-shot confirmation and 2026-27 GW6+ post-promotion check are main protection. Current Champion at decision time `multi_feature_assist_challenger` passes under this gate (dev P 0.976, confirm P 0.896).

**Considered Options**: keep 0.95 dev / 0.60 confirm + 1% min effect (ADR 0048) — rejected by user; 0.75 both — superseded same day; 0.60 with 1% min effect — superseded same day; one-time override for one Candidate — rejected (user wants standing rule).
