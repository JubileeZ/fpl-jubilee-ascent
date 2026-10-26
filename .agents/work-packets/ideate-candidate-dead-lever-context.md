# Active Task: ideate-candidate-dead-lever-context

- **Status:** In Progress
- **Objective:** Dynamically ingest active dead levers from candidate_ledger.csv into candidate ideation prompts partitioned by subsystem, replace poisoned 1-shot exemplar with continuous game-pace elasticity, formalize domain definitions in CONTEXT.md, and ensure ingest flags dead-matches.
- **Acceptance:** All 13 tests in test_ideate_candidate.py pass, test_candidate_ledger.py passes, ruff is clean, verify.sh passes.
- **Issue/Ticket:** Candidate Ideation Dynamic Dead Lever Context

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:**
  - `CONTEXT.md`
  - `.agents/skills/ideate-candidate/generate_prompt.py`
  - `.agents/skills/ideate-candidate/ingest_ideas.py`
  - `.agents/skills/ideate-candidate/SKILL.md`
  - `tests/test_ideate_candidate.py`
  - `docs/research/candidate-ideation/candidate_model_ideation_prompt.md`
- **Decisions:**
  - In-memory deterministic subsystem classifier in generate_prompt.py with zero schema changes to candidate_ledger.csv
  - Continuous Game-Pace & Match-State Elasticity replaces dead Beta-Binomial survival exemplar
  - Dynamic dead lever list filtered by subsystem focus (--focus) with 1-year lock dates
  - CONTEXT.md updated with Candidate Ledger, Dead Lever, Revisit Period, and Ledger Screen domain definitions
  - ingest_ideas.py records dead-match and notes ledger_result
- **Blocked:** None
- **Next:** Run code-review and commit
