# Candidate prototype sources

Source snapshots from fixed grids; models unregistered, Champion unchanged. EXT-07/09 failed dev; EXT-08 k2/k4 failed, k8/k16 unfinished. EXT-11 preparation only, not evaluated. No confirmation runs here.

- `ext_07`: deterministic final-state event replay; inherited parameters unchanged.
- `ext_08`: joint own-xG/xA intensity/allocation; k_mix 2, 4, 8, 16.
- `ext_09`: grouped-binomial fixture-exposure likelihood in inherited start anchor.
- `ext_11`: prepared opponent-role allocation source/checks; audit/tests pending.

Session resume: `ext_08/resume_smoke.csv` preserves two completed rows. Use exact command in `.agents/work-packets/explore-candidate-candidate-ideation.md`; harness skips completed k2/k4. Unfinished variants have no verdict. Continue remaining grid before EXT-11/12 evaluation.

Source: `prototypes.py` per lane, identical executable logic to evaluated scratch source. Check-script root paths adjusted for durable location. `FEATURES` records raw/derived lineage; inherited scorer-output schema keys explicitly documented separately.

Audit only:

```powershell
uv run python .agents/skills/explore-candidate/smoke.py docs/research/candidate-ideation/prototypes/ext_07/prototypes.py --audit_only
uv run python .agents/skills/explore-candidate/smoke.py docs/research/candidate-ideation/prototypes/ext_08/prototypes.py --audit_only
uv run python .agents/skills/explore-candidate/smoke.py docs/research/candidate-ideation/prototypes/ext_09/prototypes.py --audit_only
```

Synthetic checks:

```powershell
uv run pytest docs/research/candidate-ideation/prototypes/ext_07/checks_replay.py -q
uv run python docs/research/candidate-ideation/prototypes/ext_08/checks.py
uv run python docs/research/candidate-ideation/prototypes/ext_09/checks.py
```

Empirical reruns: obey Candidate Ledger locks before invoking harness. Failed/dead mechanisms cannot be rebuilt or rerun before revisit date without explicit user override. Existing in-progress runs must finish before any resume command. Durable `smoke_results.csv` owns completed empirical evidence.
