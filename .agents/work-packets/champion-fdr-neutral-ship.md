# Active Task: Ship Champion rename + FDR neutral fallback

- **Status:** Code ready; Refresh after push
- **Objective:** Land ADR 0037–0039, Process Points eval, research topics, Champion `participation_penalty_hybrid`
- **Acceptance:** Commit on main; dashboard Refresh rewrites product JSON off `dual_vector_state_hybrid`
- **Issue/Ticket:** ADR 0037 · 0038 · 0039

## Work Packet (SFDBN)

- **Status:** In commit
- **Files:** `models/participation_penalty_hybrid.py`, `features/builder.py`, `backtesting/process_points.py`, ADRs, research topics
- **Decisions:** Neutral ×1.0 when Club Strength 0; Dual-Vector / Official xG / team-Poisson overlays stay research-only
- **Blocked:** None
- **Next:** Dashboard Refresh after pull

## Todo
- [x] FDR fallback shrink 0.0 + ADR 0037
- [x] Process Points + ADR 0038
- [x] Official Dual-Vector + team-Poisson research notes
- [x] Champion rename ADR 0039
- [ ] Dashboard Refresh (post-push)
