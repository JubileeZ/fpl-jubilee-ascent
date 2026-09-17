# Active Task: Transfer Plan dashboard spec

- **Status:** In Progress — implement phase unlocked
- **Objective:** Implement Must+Should Transfer Plan Surface per map + ADR 0034. Later (differentials) third.
- **Acceptance:** Live path Refresh → Transfer Plan Surface scenarios; Should chip calendar, Champion Trust, legends, Auto C next-best.
- **Issue/Ticket:** [Transfer Plan dashboard spec](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/88)

## Work Packet (SFDBN)

- **Status:** Must+Should grilling done (15/16). Only Later open: Differentials ranking widget.
- **Files:** `CONTEXT.md`, ADR 0034, `docs/agents/current-state.md`, this packet
- **Decisions:** Full Must+Should spec on map 88 Decisions so far. Champion Trust includes Regret + walk-forward summary.
- **Blocked:** none for implement.
- **Next:** Start Must+Should implementation (new packet OK). Other device: `git pull`, Bind this packet or new implement packet, open map 88.

## Todo

- [x] Must grilling
- [x] Should grilling (96, 97, 102, 103)
- [ ] Implement Must+Should
- [ ] Later: Differentials (104) + fog

## Blockers / Notes

- Map Notes: implement Must+Should next; Later third.
- Prototype reference: `origin/prototype/transfer-plan-surface-sketch`.
- Spec-only map tickets done except Later; building is now in scope per user split.
