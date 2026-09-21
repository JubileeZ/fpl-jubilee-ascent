# Active Task: Ship matchup share as production fixture scale

- **Status:** Ready to commit
- **Objective:** Matchup share main; no this-season games → Club Strength; strength 0 → neutral
- **Acceptance:** Tests green; ADR 0037/0019 + CONTEXT; suite green; committed
- **Issue/Ticket:** User override ADR 0037 research gate

## Work Packet (SFDBN)

- **Status:** Pre-commit
- **Files:** `features/matchup_share.py`, `features/builder.py`, `tests/test_matchup_share.py`, ADR 0037/0019, CONTEXT, docs
- **Decisions:** Production priority matchup → strength → neutral; multipliers ×1.0 when matchup applied
- **Blocked:** None
- **Next:** Commit (exclude data/archive ingest)

## Todo
- [x] Overlay unit tests + module
- [x] Wire build_features
- [x] ADR/CONTEXT/research note
- [x] Full suite + code-review
- [ ] Commit

## Blockers / Notes
- Research all-pool failed vs neutral; shipped per product choice.
