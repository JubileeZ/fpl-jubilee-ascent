# Active Task: Candidate Ideation Skill & Workspace Setup

- **Status:** In Progress
- **Objective:** Relocate and clean up external ideation briefs, create `ideate-candidate` skill with dynamic prompt generation and idea queue ingestion, establish `docs/research/candidate-ideation/` research topic, and set default queue precedence in `explore-candidate`.
- **Acceptance:**
  1. `docs/research/external-collaboration/` cleaned up and removed.
  2. `02_backtest_gate_audit_brief.md` archived to `docs/archive/backtest-gate-audit/backtest_gate_audit_brief.md`.
  3. `01_candidate_ideation_brief.md` relocated to `docs/research/candidate-ideation/candidate_model_ideation_prompt.md`.
  4. `docs/research/candidate-ideation/idea_queue.csv` initialized with standard `explore-candidate` schema.
  5. `docs/research/candidate-ideation/candidate-ideation.md` created following research note conventions.
  6. `.agents/skills/ideate-candidate/SKILL.md`, `generate_prompt.py`, and `ingest_ideas.py` implemented and verified.
  7. `.agents/skills/explore-candidate/SKILL.md` updated with default queue precedence.
  8. Unit test suite `tests/test_ideate_candidate.py` implemented and passing.
  9. `uv run ruff check .`, `uv run pytest`, and `bash tests/verify.sh` all pass.
- **Issue/Ticket:** Candidate Ideation Architecture & Skill Setup

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:**
  - `docs/archive/backtest-gate-audit/backtest_gate_audit_brief.md`
  - `docs/research/candidate-ideation/candidate_model_ideation_prompt.md`
  - `docs/research/candidate-ideation/candidate-ideation.md`
  - `docs/research/candidate-ideation/idea_queue.csv`
  - `docs/research/INDEX.md`
  - `.agents/skills/ideate-candidate/SKILL.md`
  - `.agents/skills/ideate-candidate/generate_prompt.py`
  - `.agents/skills/ideate-candidate/ingest_ideas.py`
  - `.agents/skills/explore-candidate/SKILL.md`
  - `tests/test_ideate_candidate.py`
  - `AGENTS.md`
  - `docs/agents/current-state.md`
- **Decisions:**
  - Archived completed audit brief to `docs/archive/backtest-gate-audit/`
  - Renamed active ideation brief to `candidate_model_ideation_prompt.md` in `docs/research/candidate-ideation/`
  - Built two CLI companion scripts (`generate_prompt.py` and `ingest_ideas.py`) inside `.agents/skills/ideate-candidate/`
  - Wired `docs/research/candidate-ideation/idea_queue.csv` as default work queue for `explore-candidate` before falling back to dual-lane
  - Added unit test coverage for prompt generation, dynamic ADR 0064 constants, and queue ingestion with dead-lever flagging
- **Blocked:** None
- **Next:** Stage files, run delivery gate, commit and push

## Todo
- [x] Move `02_backtest_gate_audit_brief.md` to `docs/archive/backtest-gate-audit/backtest_gate_audit_brief.md`
- [x] Move `01_candidate_ideation_brief.md` to `docs/research/candidate-ideation/candidate_model_ideation_prompt.md`
- [x] Remove `docs/research/external-collaboration/`
- [x] Create `docs/research/candidate-ideation/candidate-ideation.md` and initialize `idea_queue.csv`
- [x] Implement `.agents/skills/ideate-candidate/SKILL.md`
- [x] Implement `.agents/skills/ideate-candidate/generate_prompt.py`
- [x] Implement `.agents/skills/ideate-candidate/ingest_ideas.py`
- [x] Update `.agents/skills/explore-candidate/SKILL.md` with default queue precedence
- [x] Implement unit test suite `tests/test_ideate_candidate.py`
- [x] Test scripts and run verification suite (`ruff`, `pytest`, `verify.sh`)
- [ ] Ingest first batch of external model candidate proposals into idea_queue.csv

## Blockers / Notes
- None
