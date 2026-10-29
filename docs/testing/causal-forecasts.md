# Causal forecast boundary

Phase 3 unfinished draft, paused for handoff 2026-10-29. No empirical forecasts or promotion evidence authorized. No completed-phase review or acceptance.

`issue_gameweek` DataFrame attribute makes the issue cutoff explicit for models using `resolve_asof_target_gw`. Targets must lie within the clipped six-GW horizon; history must precede issue. Legacy callers without this attribute retain prior behavior. Attribute alone does not establish input admission or timestamp provenance.

`strict_solver_table` revalidates a synthetic issue capability, checks forecast rows against its complete fixture and blank schedule, validates finite values and per-fixture minutes, then aggregates double Gameweeks. Known blanks require zero points and minutes. Missing rows fail; no horizon padding. Output contains admitted price, club and position, but is not a complete solver CSV or promotion artifact.

`verify_training_bundle` checks a synthetic v2 authority and its canonical source bytes against the admitted input authority, source capture/publication cutoffs, seed identity mapping, club coverage, current history cutoff and fixture finalization. Prior-season GW38 seed rows allowed for current-season GW1; current-season history must precede issue. Full source/staging schema hardening remains required.

`predict_synthetic_issue` stages snapshot-backed feature inputs with native rules and explicit issue context. Fresh concrete `DefXgShrinkChallengerModel` fits verified current history once and predicts six targets once. `BaseModel` exposes only `predict`; concrete adapter support does not establish generic fit or fitted-state serialization.

Draft `forecast_store.py`, `forecast_solver_export.py` and `replay_cache.py` introduce material identity, atomic publication, ForecastID-linked solver CSV and parent-state checkpoints. Presence does not establish correctness: component validation not yet wired into verified cache loads; multi-deadline/resume, corruption, interruption/concurrency and identity mutation tests incomplete. Original admission/catalog required on verified forecast loads. Current checkpoint test mocks forecast admission; no end-to-end replay proof.

Before acceptance: complete source/staging hardening; apply declared native component coverage/reconciliation consistently; verify complete solver parser contract; test identity and outcome isolation; validate atomic cache/recovery and full parent chain; review implementation against standards/specification; run required checks. Model inputs must never rely on terminal metadata or archive fallback. All paths remain synthetic diagnostic only.
