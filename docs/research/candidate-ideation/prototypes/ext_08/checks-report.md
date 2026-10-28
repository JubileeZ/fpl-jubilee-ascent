# EXT-08 implementation checks

- Synthetic fixture generator: existing `tests.test_ml_panel_leakage` helpers, 19 prior GWs / 300 players.
- PASS: each k_mix grid value has nonzero finite-difference own-xA to goal-factor sensitivity.
- PASS: k_mix = 12 * prior_total reproduces independent-shrink identity.
- PASS: zero reliability reproduces identity.
- PASS: current-only row reliability produces active factors; direct correction absent for GKP/DEF.
- PASS: changing prices after first observed row leaves factors unchanged.
- PASS: exact full-frame Champion parity at synthetic GW1, GW10, GW19.
- PASS: all four variants produce finite synthetic late projections; projected points reconcile to xp component sum within 1e-9.
- PASS: Ruff prototype check.
- PASS: independent source harness audit before smoke.
- Manifest: `history.weighted_xg`, `history.weighted_xa`, `history.exposure90` are derived exclusively from supplied pre-cutoff fit history.
- Manifest exception: `local.xbps` declares inherited computed scorer output because audit accepts only features/history/local namespaces. No configuration, observed feature, or external data source asserted.
- Initial smoke crashed during Windows multiprocessing IPC creation before variant evidence. Original traceback: `smoke.log`. Exact escalated retry: `smoke-retry.log`.
