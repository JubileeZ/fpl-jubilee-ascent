# EXT-09 Binomial Fixture Exposure

Fixed variant: `ext_09_binomial_fixture_exposure`; no parameter sweep.

Only inherited start-anchor observation likelihood changes: grouped player-GW successes = distinct recorded fixture starts; trials = distinct known fixture opportunities. Existing `_panel`/`_covariates` preserve binary any-start lags, minutes covariates, predictor standardization, ridge 10, support thresholds, mass preservation, horizon decay, downstream main H1/H3, and event/bonus laws. New weighted Newton step uses gradient `X.T @ (K-F*p)` and Hessian `X.T @ diag(F*p*(1-p)) @ X + penalty`.

Candidate computes corrected map locally before inherited prediction and overrides only instance `_state_probabilities`; no module-global mutation. `finally` resets map after prediction. Missing exposure or no DGW support falls back to shipped anchor. Unknown fixture/start records or contradictory duplicate starts exclude their entire player-GW from new likelihood. Identical duplicate fixture observations count once.

Reliability: `clip((N_current_unique_player_fixture - 3500) / 4000, 0, 1)`; genuine new-head seed count zero. Prior-season rows absent from supplied fit history; no invented seed metadata. Original builder warm priors retained. Raw corrected probabilities blended toward original learned probabilities before unchanged global mass normalization. Activation at target cutoff GW20; exact inherited fallback GW1-19.

Manifest `history.*` entries beyond raw player/fixture/GW/starts/minutes/home/opponent fields denote strictly causal derived panel/exposure columns, not exported history-contract promises. `local.coerce` identifies pandas numeric coercion configuration; included because source audit traverses nested column expressions. `features.position_id` and `features.club_id` supply existing current point-in-time mapping only.

Checks: `checks.py` and `checks.log`. Binary F=1 equality at 1e-12; grouped DGW optimum; duplicate/unknown handling; GW1-19 synthetic exact parity; entirely absent fixture column fallback; corrected anchor differs from any-start likelihood on synthetic DGWs. Full-season dev gate output pending in `smoke.csv`; no empirical pass claimed by synthetic checks.
