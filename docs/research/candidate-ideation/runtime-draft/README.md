# Exact feature-cache draft

Checkpoint only; not activated in any evaluation. Scratch implementation passed 17 synthetic tests. Saved source/test snapshots; no empirical model verdict depends on cache.

Before use:

- Set `CACHE_ROOT` to `.tmp/agent/explore-candidate/feature_cache/frames` under repository root; current draft default follows module location and would write under this folder after relocation.
- Reject non-null `expected_role_season`; add corresponding bypass case.
- Re-run checks from durable location; independently review key provenance and source/data invalidation.
- Activate only after exact-output review. Never change model/gate mathematics, inputs, columns, or filtering.

`cache.py`: binds original builder arguments; hashes feature sources/runtime/immutable archive metadata; per-key OS lock; atomic own-pickle publication; exact dtype/index/attrs roundtrip; fresh objects per read; bypass unsupported/snapshot/live modes. Patches only walk-forward builder alias when explicitly installed. No install call at import.

`checks_cache.py`: synthetic fixtures only, including spawned-process single population. Explicit test command after pending fixes:

```powershell
uv run pytest docs/research/candidate-ideation/runtime-draft/checks_cache.py -q -p no:cacheprovider
```
