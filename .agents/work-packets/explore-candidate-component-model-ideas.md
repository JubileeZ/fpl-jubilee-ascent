# Active Task: explore-candidate component-model-ideas (Queue mode)

- **Status:** Exit (b) 2026-09-29 — Queue exhausted (batches 1–5, 22 ideas, 106 smoke rows); Champion club_def_prior_challenger stands
- **Objective:** Frozen Candidate passing Historical Promotion Gate dev + confirm via smoke.py, adoption queued — or queue exhausted, every attempt in Candidate Ledger
- **Acceptance:** Exit (a)/(b)/(c) per .agents/skills/explore-candidate/SKILL.md
- **Issue/Ticket:** docs/research/component-model-ideas/idea_queue.csv

## Run state

- **Mode:** Queue · scope docs/research/component-model-ideas/idea_queue.csv · slug component-model-ideas
- **Seasons (2026-09-29):** dev 2025-26 GW1-38 seed 2024-25 · confirm 2024-25 GW1-38 no seed · holdout 2026-27 sealed (GW5 last finished)
- **Champion:** club_def_prior_challenger (ADR 0051). Batches 1–5 complete.
- **Step:** 8 done (Exit (b))
- **Scratch:** .tmp/agent/explore-candidate/ deleted at Exit

## Report

**Verdict:** Queue exhausted (Exit (b)); Champion club_def_prior_challenger stands
**Batches 1–5 Summary:**
- ATK-05 · Promoted Champion (ADR 0051)
- DEF-02 (cs_exposure_challenger) · Dev PASS (+0.096, 2/3, P 0.664), Confirm FAIL (-0.443, 0/3, P 0.000) -> Dead
- ATK-04 · Dev PASS, Confirm FAIL -> Dead
- DEF-01, ATK-02 · Dev PASS vs prior Champion, dropped by stack ablation -> Open in ledger
- 16 ideas failed dev: MIN-01, BON-01, ATK-01, ATK-03, MIN-02, BON-03, BON-02, MIN-03, MIN-04, DEF-05+06, CRD-02, ATK-07, DEF-08, DEF-09, ATK-06, CRD-01, CRD-03 -> Dead
**Audit:** all prototypes AUDIT PASS, no LEAKAGE FAIL
**Ledger:** Dead +12 today (19 total across queue); Shipped +1 (ATK-05); Open +2 (DEF-01, ATK-02)

## Work Packet (SFDBN)

- **Status:** Exit (b); completed queue run
- **Files:** models/cs_exposure_challenger.py, tests/test_cs_exposure_challenger.py, docs/model_name.md, docs/research/candidate-ledger/*, docs/research/component-model-ideas/*, ROADMAP.md, docs/agents/current-state.md
- **Decisions:** Batches 3–5 all failed dev or confirm; Champion club_def_prior_challenger stands; all 12 dead levers locked for 1 year in Candidate Ledger
- **Blocked:** holdout GW6+ not finished (post-promotion check waits); MIN-07 blocked on feature; MIN-05/06/BON-04 needs ruling
- **Next:** User ruling on MIN-05/06/BON-04 or wait for 2026-27 GW6+ post-promotion check / holdout defcon evaluations

## Human Queue

- [ ] Post-promotion holdout check (ADR 0047, once per Champion) when 2026-27 GW6+ finished: uv run python -m commands.evaluate_model_promotion --data_dir data/archive/2026-27/processed --seed_season 2025-26 --gw_range 6-<last finished> (Champion vs slate). FAIL -> revert to learned_start_challenger on user's words. Default: wait.
- [ ] Rule on MIN-05 / MIN-06 / BON-04 (needs ruling)? Options: untested / skip. Default taken: skip. Evidence: idea_queue.csv nearest_ledger_row
- [ ] HOLDOUT rows DEF-03 / DEF-04 / DEF-07 wait for 2026-27 GW6+ protocol (ADR 0046). Default: wait. MIN-07 blocked (needs features.kickoff_time); default: skip.
