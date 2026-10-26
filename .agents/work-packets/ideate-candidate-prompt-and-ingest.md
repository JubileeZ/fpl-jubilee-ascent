# Active Task: ideate-candidate-prompt-and-ingest

- **Status:** In Progress
- **Objective:** Upgrade ideate-candidate prompt brief with 1-shot exemplar, relax Section 9 code requirement, and add auto-scaffolding of AdaptiveCausalChallengerModel subclass skeletons in ingest_ideas.py.
- **Acceptance:** Tests pass for 1-shot prompt generation, codeless idea parsing, and auto-scaffolding; full test suite passes.
- **Issue/Ticket:** /grill-with-docs ideate candidate upgrade

## Work Packet (SFDBN)

- **Status:** Ready to commit
- **Files:** .agents/skills/ideate-candidate/generate_prompt.py, .agents/skills/ideate-candidate/ingest_ideas.py, .agents/skills/ideate-candidate/SKILL.md, CONTEXT.md, tests/test_ideate_candidate.py
- **Decisions:** Embed 1-shot exemplar in prompt; section 9 optional; auto-scaffold class skeleton in dossier if code missing; dual-mode ingestion documented in SKILL.md.
- **Blocked:** None
- **Next:** Commit changes to main.

## Todo
- [x] Write failing test for 1-shot exemplar in prompt and auto-scaffold in ingest
- [x] Update generate_prompt.py with 1-shot exemplar and Section 9 relaxation
- [x] Update ingest_ideas.py with _scaffold_python_skeleton and codeless support
- [x] Update .agents/skills/ideate-candidate/SKILL.md with Agent-Assisted Fallback Ingestion protocol
- [x] Update CONTEXT.md domain glossary for Ideation Proposal
- [x] Run pytest, ruff, and verify.sh
- [x] Run two-axis code-review
- [ ] Commit changes and clean up work packet

## Blockers / Notes
- None
