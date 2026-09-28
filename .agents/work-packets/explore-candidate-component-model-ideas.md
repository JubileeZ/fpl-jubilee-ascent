# Active Task: explore-candidate component-model-ideas (Queue mode)

- **Status:** Exit (a) 2026-09-29 — Candidate `club_def_prior_challenger` PASS dev + confirm, promoted (user-authorized); Human Queue open
- **Objective:** Frozen Candidate passing Historical Promotion Gate dev + confirm via `smoke.py`, adoption queued — or queue exhausted, every attempt in Candidate Ledger
- **Acceptance:** Exit (a)/(b)/(c) per `.agents/skills/explore-candidate/SKILL.md`
- **Issue/Ticket:** `docs/research/component-model-ideas/idea_queue.csv`

## Run state

- **Mode:** Queue · scope `docs/research/component-model-ideas/idea_queue.csv` · slug `component-model-ideas`
- **Seasons (2026-09-29):** dev 2025-26 GW1-38 seed 2024-25 · confirm 2024-25 GW1-38 no seed · holdout 2026-27 sealed (GW5 last finished)
- **Champion:** was `learned_start_challenger` (ADR 0050) → now `club_def_prior_challenger` (ADR 0051). Next invocation: Champion changed → prior smoke rows = hints only; re-smoke on new Champion. Shipped id = ATK-05; no queue row lists ATK-05 in `conflicts_with`.
- **Step:** 8 done (Exit (a))
- **Scratch:** `.tmp/agent/explore-candidate/` deleted at Exit

## Report

**Verdict:** Candidate `club_def_prior_challenger` PASS dev + confirm → promoted to Champion (user authorized 2026-09-29 00:19; ADR 0051 Accepted)
**Lanes (dev 2025-26 vs `learned_start_challenger`):**
- ATK-05 · club × DEF xG prior · `atk_05_def_k5` · +0.504 · 2/3 · P 0.955 → confirm 2024-25 +0.080 2/3 P 0.619 PASS
- ATK-04 · position rate shrink K · `atk_04_def2400` · +0.707 · 3/3 · P 0.959 → confirm −0.076 1/3 P 0.385 FAIL
- DEF-01 · goals-against shape · `def_01_nu1p0` · +0.371 · 2/3 · P 0.989 → dropped by stack ablation (Open)
- ATK-02 · club assist mass · `atk_02_w05_real` · +0.173 · 2/3 · P 0.655 → dropped by stack ablation (Open)
- MIN-01 +0.593 1/3 · ATK-03 +0.176 1/3 · ATK-01 +0.073 1/3 · MIN-02 −0.074 · BON-03 −0.216 · BON-01 −0.687 → Dead
- Stack b2: all −0.252; ATK-05+DEF-01 +0.417; ATK-05+ATK-02 −0.200; DEF-01+ATK-02 +0.054
**Audit:** all prototypes AUDIT PASS (re-run by orchestrator), no LEAKAGE FAIL; every winner re-run identical; freeze checks identical
**Ledger:** Dead +7 (MIN-01, BON-01, ATK-01, ATK-03, ATK-04, MIN-02, BON-03); Shipped +1 (ATK-05); Open +2 (DEF-01, ATK-02)
**Promotion:** `config/model_selection.json` champion `club_def_prior_challenger`, candidates `learned_start_challenger`, `multi_feature_assist_challenger`; `evaluate_model_promotion --data_dir data/archive/2024-25/processed --confirmation --apply` replay identical (+0.0799 2/3 P 0.619); evidence `data/reports/promotion_evidence/20260928T193910Z-club_def_prior_challenger.{json,md}`

## Work Packet (SFDBN)

- **Status:** Exit (a); committed + pushed per user 00:16/00:19
- **Files:** `config/model_selection.json`, `models/club_def_prior_challenger.py`, `models/def_xg_shrink_challenger.py`, `tests/test_club_def_prior_challenger.py`, `tests/test_def_xg_shrink_challenger.py`, `docs/adr/0051-champion-club-def-prior-challenger.md`, `docs/model_name.md`, `docs/research/component-model-ideas/{component-model-ideas.md,idea_queue.csv,smoke_results.csv,candidate_gate.csv}`, `docs/research/candidate-ledger/*`, `docs/research/INDEX.md`, `ROADMAP.md`, `docs/agents/current-state.md`
- **Decisions:** frozen pick = best single after stack ablation; `atk_05_def_k5` over `def_k15` (higher verified delta). `face_value_challenger` off slate (max 2 Candidates). Dead-row override not treated as blanket.
- **Blocked:** holdout GW6+ not finished (post-promotion check waits)
- **Next:** resolve Human Queue; next `/explore-candidate docs/research/component-model-ideas/idea_queue.csv` = batch 3 vs new Champion (DEF-02, BON-02, MIN-03, MIN-04, DEF-05+06 by order; re-smoke DEF-01 / ATK-02 Open rows)

## Human Queue

- [ ] Post-promotion holdout check (ADR 0047, once per Champion) when 2026-27 GW6+ finished: `uv run python -m commands.evaluate_model_promotion --data_dir data/archive/2026-27/processed --seed_season 2025-26 --gw_range 6-<last finished>` (Champion vs slate). FAIL → revert to `learned_start_challenger` on user's words. Default: wait.
- [ ] Rule on MIN-05 / MIN-06 / BON-04 (`needs ruling`)? Options: untested / skip. Default taken: skip. Evidence: `idea_queue.csv` `nearest_ledger_row`
- [ ] HOLDOUT rows DEF-03 / DEF-04 / DEF-07 wait for 2026-27 GW6+ protocol (ADR 0046). Default: wait. MIN-07 blocked (needs `features.kickoff_time`); default: skip.
