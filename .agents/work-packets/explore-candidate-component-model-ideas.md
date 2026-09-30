# Active Task: explore-candidate component-model-ideas (Queue mode)

- **Status:** Exit (b) 2026-09-30 — Queue exhausted (all 29 ideas + all open & blocked levers resolved); Champion club_def_prior_challenger stands
- **Objective:** Frozen Candidate passing Historical Promotion Gate dev + confirm via smoke.py, adoption queued — or queue exhausted, every attempt in Candidate Ledger
- **Acceptance:** Exit (a)/(b)/(c) per .agents/skills/explore-candidate/SKILL.md
- **Issue/Ticket:** docs/research/component-model-ideas/idea_queue.csv

## Run state

- **Mode:** Queue · scope docs/research/component-model-ideas/idea_queue.csv · slug component-model-ideas
- **Seasons (2026-09-30):** dev 2025-26 GW1-38 seed 2024-25 · confirm 2024-25 GW1-38 no seed · holdout 2026-27 sealed (GW5 last finished)
- **Champion:** club_def_prior_challenger (ADR 0051). All queue rows 100% complete.
- **Step:** 8 done (Exit (b))
- **Scratch:** .tmp/agent/explore-candidate/ deleted at Exit

## Report

**Verdict:** Queue exhausted (Exit (b)); Champion club_def_prior_challenger stands
**Summary:**
- ATK-05 · Promoted Champion (ADR 0051)
- DEF-02 (cs_exposure_challenger) · Dev PASS, Confirm FAIL -> Dead (Catalog)
- ATK-04 · Dev PASS, Confirm FAIL -> Dead
- MIN-07 (schedule_congestion_challenger) · Unblocked (kickoff_time added to Feature Contract), Dev PASS (+0.063, 2/3, P 0.967), Confirm FAIL (-0.105, 0/3, P 0.000) -> Dead (Catalog)
- Open Levers re-tested vs Champion: DEF-01 Poisson GC and ATK-02 club assist mass both failed dev -> Dead
- Dual-Vector ratios shrunk -> Dead (superseded by ADR 0040)
- 25 ideas failed dev or confirm -> Dead: MIN-01..07, BON-01..04, ATK-01..04, ATK-06..07, DEF-01..02, DEF-05..06, DEF-08..09, CRD-01..03
**Audit:** all prototypes AUDIT PASS, no LEAKAGE FAIL
**Ledger:** All queue ideas resolved; 0 Open rows remain in candidate_ledger.csv

## Work Packet (SFDBN)

- **Status:** Exit (b); completed queue run, all open & blocked levers resolved
- **Files:** models/schedule_congestion_challenger.py, tests/test_schedule_congestion_challenger.py, features/builder.py, docs/model_name.md, docs/research/candidate-ledger/*, docs/research/component-model-ideas/*, ROADMAP.md, docs/agents/current-state.md
- **Decisions:** MIN-07 dev PASS, confirm FAIL -> Dead; open levers DEF-01, ATK-02 fail dev -> Dead; Champion club_def_prior_challenger stands; all dead levers locked for 1 year in Candidate Ledger
- **Blocked:** holdout GW6+ not finished (post-promotion check waits)
- **Next:** Wait for 2026-27 GW6+ post-promotion check

## Human Queue

- [ ] Post-promotion holdout check (ADR 0047, once per Champion) when 2026-27 GW6+ finished: uv run python -m commands.evaluate_model_promotion --data_dir data/archive/2026-27/processed --seed_season 2025-26 --gw_range 6-<last finished> (Champion vs slate). FAIL -> revert to learned_start_challenger on user's words. Default: wait.
- [ ] HOLDOUT rows DEF-03 / DEF-04 / DEF-07 wait for 2026-27 GW6+ protocol (ADR 0046). Default: wait.
