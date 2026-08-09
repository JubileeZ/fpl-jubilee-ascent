# Active Task: Expand GW1–6 Strategy with No-Haaland GW1–2 + FH3 + WC4 Scenarios

- **Status:** Complete
- **Objective:** Add and optimize the No-Haaland (GW1–2) + Free Hit 3 (GW3) + Wildcard 4 (GW4) strategy across `docs/research/gw1-6-preseason-pipeline/`
- **Acceptance:** `run_wc4_simulation.py` expanded to solve No-Haaland drafts, FH3 single-GW maximization, and WC4 structural variants; S7–S11 records added to `gw1-6_wc4_simulation.csv`; documentation updated; delivery gates green
- **Issue/Ticket:** Pre-season strategy optimization

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** docs/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/*, docs/research/gw1-6-preseason-pipeline/README.md, docs/agents/current-state.md, task.md
- **Decisions:** Integrated No-Haaland GW1–2 (BB1 119.13 xP / BB2 118.38 xP / Std 102.95 xP), GW3 Free Hit (54.98 xP with Haaland/MCI/BRE/LIV/BHA targeting), and GW4 Wildcard Options 1-3. S7 (BB1+FH3+Opt1) reaches 325.96 xP (+6.15 xP vs S1); S9 (BB1+FH3+Opt3) reaches 320.67 xP (+6.15 xP vs S3) with £3.0m ITB and 2 banked FTs in GW6.
- **Blocked:** None
- **Next:** Proceed with GW1 squad finalization and operational runs

## Todo
- [x] Formulate and solve No-Haaland GW1–2 draft MILPs (BB1, BB2, Std)
- [x] Formulate and solve GW3 Free Hit (FH3) single-GW MILP
- [x] Expand `run_wc4_simulation.py` to evaluate S7–S11 scenarios
- [x] Regenerate `gw1-6_wc4_simulation.csv` and verify master pipeline
- [x] Update `gw1-6-chip-wc4-squads.md` and `README.md`
- [x] Update `docs/agents/current-state.md`
- [x] Verify delivery gates (ruff, pytest, verify.sh)
- [x] Clean up `.tmp/agent/` scratch files

## Blockers / Notes
- None
