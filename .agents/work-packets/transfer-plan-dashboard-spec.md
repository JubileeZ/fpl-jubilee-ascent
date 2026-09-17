# Active Task: Transfer Plan dashboard spec

- **Status:** In Progress
- **Objective:** Hand-off spec (glossary/ADR + AGENTS.md/README/ROADMAP) for Refresh → Model Champion projections → Transfer Plan → dashboard. Plan; do not implement.
- **Acceptance:** Map [Transfer Plan dashboard spec](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/88) has empty frontier; destination spec ready to implement.
- **Issue/Ticket:** [Transfer Plan dashboard spec](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/88)

## Work Packet (SFDBN)

- **Status:** Charted. Cut closed. Four research tickets closed. Notes on disk under `docs/research/wayfinder-transfer-plan-spec/`.
- **Files:** `docs/research/wayfinder-transfer-plan-spec/*.md`, `docs/research/INDEX.md`, `docs/agents/current-state.md`, `.agents/handoff-pointer`
- **Decisions:** Must/Should/Later cut on issue 89. Transfer Plan = new dashboard surface (not What-If, not Dream Team). Ranked roll/1-FT/Hit. Expected GW Score new term. Single User Squad. Solve already writes `data/solution.json`; Explorer hides news/chance/fixtures. Official `selected_by_percent` is not EO. `price_report` is observed only.
- **Blocked:** Surface sketch blocked on Expected GW Score + scenario arms.
- **Next:** Bind this packet. Claim [Expected GW Score definition](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/94). Skills: grilling, domain-modeling. Do not implement dashboard.

## Todo

- [x] Chart map 88 + child tickets
- [x] Must Should Later cut (89)
- [x] Research 90–93
- [ ] Expected GW Score (94)
- [ ] Remaining grilling/prototype tickets on the map
- [ ] Glossary + first-run docs chapters after sketch

## Blockers / Notes

- Live season parquet/JSON dirty in working tree: do not commit with this packet.
- Research worktrees still on disk; notes copied to main. Cleanup `/delete-worktree` optional after push.
- Other device: `git pull`, Bind packet `transfer-plan-dashboard-spec`, open map 88.
