# Active Task: frictionless-candidate-ideation

- **Status:** In Progress
- **Objective:** Streamline candidate ideation dispatch and ingestion via unified UI artifact prompt, 1-line URL dispatch, immediate execution directive, and chat-pasting ingestion.
- **Acceptance:** Tests pass, prompt generated without nested fences, 2-axis review clean pass, delivery gate passes.
- **Issue/Ticket:** frictionless-candidate-ideation

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** `.agents/skills/ideate-candidate/SKILL.md`, `.agents/skills/ideate-candidate/generate_prompt.py`, `docs/research/candidate-ideation/candidate_model_ideation_prompt.md`, `tests/test_ideate_candidate.py`, `docs/agents/current-state.md`
- **Decisions:**
  - Removed outer markdown code fence from Part 1 to unify entire prompt into single 1-click copyable document.
  - Added imperative `### Critical Operational Directive` at prompt head for single-turn output without conversational stalling.
  - Added `--artifact-out` argument to `generate_prompt.py` with deduplicated file write loop.
  - Added 1-line raw GitHub URL dispatch prompt in `SKILL.md` for web-browsing frontier models.
  - Established direct chat pasting as primary ingestion path (zero terminal/file-saving required).
  - Maintained model neutrality in skill comments; refactored test harness to use pytest `monkeypatch`.
- **Blocked:** None
- **Next:** Commit and push checkpoint.

## Todo
- [x] Unify prompt brief and add immediate execution directive
- [x] Add `--artifact-out` dual-write support and test coverage
- [x] Establish model-neutral 1-line URL dispatch and chat-pasting ingestion in SKILL.md
- [ ] Next ideation cycle: dispatch brief to external frontier model and ingest proposals
