# Active Task: #189 unified mode="empirical" replay, Strategic 6-GW parity, Stage A->B

- **Status:** In Progress (code + tests done; final gate + close pending)
- **Objective:** Resolve only GH #189 under Map #184. No #187/#188/#186 edits. No 2026-27 peeks. Champion + candidate_ledger locks preserved. No git push unless user asks.
- **Acceptance:** ruff + full pytest + `bash tests/verify.sh` green; Standards+Spec code-review 0 confirmed findings; ROADMAP/current-state synced; resolution comment on #189; #189 closed; 1-line gist appended to Map #184 "Decisions so far".
- **Issue/Ticket:** #189 (specs #176 #178 #179, ADR 0065/0066/0069)

## Work Packet (SFDBN)

- **Status:** Impl done. Post-review fixes applied. 82 targeted tests + ruff pass (observed). Stage A->B rerun exit 0 on fixed code. Full pytest + verify.sh NOT yet rerun after fixes. Re-review (Standards+Spec) NOT completed: subagents hit 429 quota (resets ~17m after 23:18 +07).
- **Files:** `backtesting/{empirical_admission,empirical_mirrors}.py` (new); `commands/{acquire_empirical_mirrors,run_stage_a_and_b}.py` (new); `config/{dev_mirror_2025_26_manifest,dev_mirror_2024_25_manifest,seed_manifest_2024_25}.json` (new); `tests/test_{empirical_admission,empirical_mirrors,empirical_replay,stage_controls,strategic_parity_and_profiler}.py` (new); modified `backtesting/{data_admission,forecast_adapter,forecast_export,forecast_inputs,forecast_store,fplcache_ingest,input_pilot,native_transfer_solver,promotion_evidence,replay_cache,replay_state,rolling_replay}.py`, `commands/profile_transfer_replay.py`, `tests/test_profile_transfer_replay.py`.
- **Decisions:**
  - Upstream vaastav gaps keep full 1..38 fail-closed: 2025-26 contiguous prefix GW1..7 (first blocked GW8), 2024-25 prefix GW1..1 (first blocked GW2). partial_prefix, non-promotable. #175 Q7 bounds not relaxed. Label this blockage on #189.
  - Exact solver speedup: 0%-loss dominance prune, compact MILP, hybrid warm start; `target_gap=0.0`, 60s cap.
  - Manifest SHA256 (pre-regeneration of acquisition not changed since): recompute via `sha256sum config/dev_mirror_*_manifest.json config/seed_manifest_2024_25.json` before posting.
  - Stage A (observed last run): 8/8 calls, 0 censored, 251.30s wall, 855.94 MB peak RSS, anchor 685 players, est season 1031.77s, extrapolation_reliable True, resume verified. Stage B: B1 synthetic, B2 2025-26 GW1-2, B3 GW1-7, B4 2024-25 GW1 + cross-season; 15 MANDATORY_GUARDS, null control p=1.0 delta=0.
- **Blocked:** Gitignored quarantine `data/reports/empirical_mirrors/` (bootstraps, fixtures, merged_gw csv, stage reports) NOT in git. Other device must regenerate: `uv run python -m commands.acquire_empirical_mirrors --seasons 2025-26 2024-25` (needs `gh` auth + network) before `commands.run_stage_a_and_b`. Subagent quota 429 until ~23:35 +07.
- **Next:**
  1. Pull; regenerate quarantine (above); `uv run python -m commands.run_stage_a_and_b` (~5-10 min) -> expect exit 0, Stage A 0 censored.
  2. Re-run parallel Standards + Spec `code-review` (code-review skill) on diff vs HEAD; fix confirmed findings until 0.
  3. `uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`.
  4. Sync `ROADMAP.md` + `docs/agents/current-state.md` (telegraphic).
  5. Post resolution comment on #189 (manifest SHAs, Stage A wall/RSS, Stage B pass counts, ruff/pytest/verify results, labeled vaastav 1..38 blockage); close #189; append gist to Map #184; delete this packet + `.agents/handoff-pointer` on commit; do not push unless asked.

## Todo
- [x] Acquire/pin mirrors + zero-diff (#176)
- [x] Unified empirical admission + 8 negative classes (#178)
- [x] ADR 0065 parity, QualityPolicy, profiler telemetry, Stage A->B (#179)
- [x] First review round fixes (Standards 13, Spec 16 findings)
- [ ] Re-review 0 findings
- [ ] Full pytest + verify.sh
- [ ] Docs sync, #189 comment/close, #184 gist

## Blockers / Notes
- Not pushed. Not committed as of packet write unless git log shows otherwise.
