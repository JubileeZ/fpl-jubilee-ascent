# Active Task: ADR 0069 Governance Reset and Wayfinder Map Alignment

- **Status:** In Progress
- **Objective:** Commit ADR 0069 governance reset, align Map #184 and child tickets strictly with `/wayfinder`, verify gates, and push cleanly.
- **Acceptance:** `uv run ruff check .`, `uv run pytest`, and `bash tests/verify.sh` pass; Map #184 passes Wayfinder structure/label/dependency checks; changes committed and pushed.
- **Issue/Ticket:** [#184](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/184)

## Work Packet (SFDBN)

- **Status:** Saving ADR 0069 Path A governance reset checkpoint before `/wayfinder` map alignment audit.
- **Files:** `docs/adr/0069-annual-rolling-validation-and-dual-tier-promotion.md`, `docs/adr/README.md`, `docs/adr/0046-*`, `0047-*`, `0064-*`, `0066-*`, `CONTEXT.md`, `README.md`, `ROADMAP.md`, `docs/agents/current-state.md`, `docs/research/INDEX.md`, `docs/testing/*`
- **Decisions:** Adopted ADR 0069 Annual Rolling Validation (`S=2026-27` quarantined via `Randdalf/fplcache <= 24h`, `S-1=2025-26`, `S-2=2024-25`), Dual-Tier weekly serving, `M<=2`, `<=5%` FWER bar at `GW15/GW30/GW38`.
- **Blocked:** None
- **Next:** Commit & push Path A docs checkpoint, then audit/align Map #184 and child tickets with `/wayfinder`, sync `ROADMAP.md`/`current-state.md`, re-verify, delete finished packet, commit & push.

## Todo
- [x] Author ADR 0069 and align repo governance/testing/tracking docs (Python/test code untouched pending #185)
- [ ] Audit and align Map #184 and child tickets with `/wayfinder`, sync progress docs, verify all gates, and complete final push

## Blockers / Notes
- `commit-gate.sh` classifies non-tracking doc changes as code commits requiring a Work Packet under `.agents/work-packets/`.
