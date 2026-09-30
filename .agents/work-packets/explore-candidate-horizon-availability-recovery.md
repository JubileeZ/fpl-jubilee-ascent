# Active Task: explore-candidate horizon-availability-recovery (Scoped mode)

- **Status:** Complete
- **Objective:** Evaluate suggested mechanisms (horizon mean-reversion, intermediate availability scaling, learned-start DNP softening) via Historical Promotion Gate on dev + confirm seasons, or record ledger screens and human judgment path.
- **Acceptance:** Exit (a)/(b)/(c) per .agents/skills/explore-candidate/SKILL.md · Implemented ADR 0053
- **Issue/Ticket:** User request on João Pedro / Brobbey / Isak availability and horizon projection

## Run state

- **Mode:** Scoped · slug horizon-availability-recovery
- **Seasons (2026-10-01):** dev 2025-26 GW1-38 seed 2024-25 · confirm 2024-25 GW1-38 no seed · holdout 2026-27 sealed (GW5 last finished)
- **Champion:** club_def_prior_challenger (ADR 0051)
- **Step:** Complete
- **Scratch:** .tmp/agent/explore-candidate/

## Work Packet (SFDBN)

- **Status:** Complete. ADR 0053 implemented, tested, and verified across all layers (model horizon recovery, Conservative scenario arm, Force Keep dashboard wiring, inline UI status badges and warning banner).
- **Files:** docs/adr/0053-conservative-scenario-and-horizon-recovery.md, CONTEXT.md, models/learned_start_challenger.py, solver/scenarios.py, commands/transfer_plan_scenarios.py, commands/dashboard.py, dashboard/index.html, dashboard/styles.css, dashboard/plan.js, tests/test_learned_start_challenger.py, tests/test_transfer_plan_scenarios.py, tests/test_transfer_plan_dashboard.py, tests/test_transfer_plan_progress.py
- **Decisions:**
  1. ADR 0053 accepted: Must arms expanded from two to three: Optimal, No Hit, and Conservative.
  2. Conservative scenario sets weekly_hit_limit=0, auto-bans unowned players with active FPL flags (status != 'a' or chance < 100), and auto-locks regular starters who missed only 1 match (starts >= 60% in prior games).
  3. Horizon Mean-Reversion implemented in LearnedStartChallengerModel with gamma=0.5: h=0 (single-step backtests) strictly identical to Champion; h >= 1 recovers toward baseline.
  4. Force Keep wired from dashboard frontend via [🔒 Keep] button through POST /api/transfer-plan into execute_transfer_plan_scenarios.
  5. UI displays inline status badges (e.g. ⚠️ Doubt 75%), sell alert warning banners, and 1-click squad locks.
- **Blocked:** None
- **Next:** Ready for user review and commit.
