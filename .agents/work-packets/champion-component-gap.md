# Active Task: Challenger beats Champion (goals then defence link)

- **Status:** Form locked; frontier = build Task #118
- **Objective:** Flip Champion via goals + Poisson defence-link Candidate on 2025-26 Historical Promotion Gate
- **Acceptance:** Map Destination met; soft pre-gate companion improve before `--apply`
- **Issue/Ticket:** Map [#110](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/110) · **Bind next:** [#118 Implement defence-link Candidate](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/118)

## Work Packet (SFDBN)

- **Status:** Decisions #111–#117 + goals build #116 closed. Frontier Task **#118** (unclaimed).
- **Files:** Parent `models/goals_path_challenger.py` (`_GOAL_WEIGHT_SCALE=0.891559`); pattern `docs/research/champion-component-gap/calibrate_goals_k.py`; companions + note § Post-goals residual
- **Decisions:** Defence form #117 — new subclass of `goals_path_challenger`; post-link `k_cs`/`k_gc` only; `k_cs`←`mins_60`/`ALL` CS; `k_gc`←`mins_60` GKP+DEF conceded; τ=0.05 data-driven; no λ/`_DEF_RELAX` change
- **Blocked:** None for #118
- **Next:** Claim #118 → implement → companion refresh → soft pre-gate defence checklist → then admission race (#112 rules)

## Todo
- [x] Component-gap diagnosis + Eval canon
- [x] Decision tickets #111–#115, #117
- [x] #116 `goals_path_challenger` (soft pre-gate goals PASS)
- [ ] **#118** defence-link Candidate (`k_cs`/`k_gc`)
- [ ] Admission race (#112) → soft pre-gate flip → `--apply`

## Recipe for #118 (copy from issue + here)

1. Subclass `GoalsPathChallengerModel`; override event projection to scale `xp_clean_sheet`×`k_cs` and `xp_conceded`×`k_gc` after parent components (or equivalent post-link hook).
2. Calibrate like `calibrate_goals_k.py`: walk-forward → read companion bias → patch module constants.
3. Append model to component-gap runner extras; refresh CSV; fill soft pre-gate defence rows in note.
4. Do **not** edit `config/model_selection.json` / `--apply` in #118.

## Blockers / Notes
- Handoff pointer slug: `challenger-beats-champion` → map #110 / task #118
- Map Notes allow build for #118
- Unpushed local only if this packet/current-state commit pending
