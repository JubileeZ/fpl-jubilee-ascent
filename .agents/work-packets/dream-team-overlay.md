# Active Task: Dream Team Explorer overlay

- **Status:** In Progress
- **Objective:** In-page Solve paints Dream Team on Ownership Explorer chart and table
- **Acceptance:** pytest dream-team + explorer markers; overlay not in dashboard JSON; Squad Board unchanged
- **Issue/Ticket:** ADR 0028

## Work Packet (SFDBN)

- **Status:** Code on main; restart dashboard process to pick up Solve
- **Files:** commands/dream_team.py, commands/dashboard.py, dashboard/*, tests/test_dream_team.py
- **Decisions:** ADR 0028. Frozen unconstrained 15. Budget ITB+Selling or £100.0m. Session-only. Badge Dream.
- **Blocked:** None
- **Next:** Restart `commands.dashboard` (port 8000 still serves old process)

## Todo
- [x] Dream Team budget and solver options
- [x] execute_dream_team + /api/dream-team
- [x] Explorer overlay (badge + ring); clear on horizon/model/Refresh
- [x] verify.sh + live Solve check
- [ ] Restart dashboard process so Solve Dream Team is on the open server
