# Causal forecast boundary

Phase 3 engineering accepted 2026-10-29. Verified causal issue-by-target forecasts, strict solver CSV export, and atomic reproducible store. Synthetic foundation verification only; empirical forecasts and promotion evidence remain unadmitted.

`issue_gameweek` DataFrame attribute makes the issue cutoff explicit for models using `resolve_asof_target_gw`. Targets must lie within the clipped six-GW horizon; history must strictly precede issue (`fixture.event < capability.gw`). Rows carry full grain metadata (`horizon_lead`, `issue_gameweek`, `model`, `rules_version`, `cutoff`, `training_cutoff`). Legacy callers without this attribute retain prior behavior. Attribute alone does not establish input admission or timestamp provenance.

`strict_solver_table` revalidates synthetic issue capability, checks forecast rows against complete fixture and blank schedule, validates finite values and per-fixture minutes, then aggregates double Gameweeks. Known blanks require zero points and minutes. Missing rows fail; horizon padding in backtesting solver export is strictly prohibited via runtime call-stack inspection. Output contains admitted price, club and position.

`verify_training_bundle` checks synthetic v2 authority and canonical source bytes against admitted input authority, source capture/publication cutoffs, seed identity mapping, club coverage, current history cutoff and fixture finalization. Prior-season GW38 seed rows allowed for current-season GW1; current-season history must precede issue. Proved seed absence allowed for newcomers; no fabricated historical observations.

`predict_synthetic_issue` stages snapshot-backed feature inputs with native rules and explicit issue context. Pluggable concrete model adapter (defaults to `DefXgShrinkChallengerModel`) fits verified current history once and predicts six targets once. Prohibits oracle minutes (`features["external_xmins"]` or `features.oracle_minutes`). `BaseModel` exposes only `predict`; concrete adapter support does not establish generic fit or fitted-state serialization.

`forecast_store.py`, `forecast_solver_export.py` and `replay_cache.py` provide content-addressed material identity (`_sha256_hex`), atomic publication (`started.json`, `complete.json`, `failed.json`), ForecastID-linked solver CSV and parent-state checkpoints. Manifest, coverage report (`coverage_report.json`), and generator log (`generator_log.json`) are validated for existence and SHA256 integrity on load. Dependency closure hashes modeling and scoring modules (`config`, `backtesting`, `features`, `models`, `projections`, `solver`), excluding UI/CLI scripts.

Verified offline synthetic integration covers end-to-end admission, fit, prediction, manifest generation, solver CSV export, and multi-GW checkpoint transitions with parent verification. All paths remain synthetic diagnostic only. Empirical coverage and admission follow-through remain Phase 4/5/8 responsibilities.
