# Active Task: Champion search 2026-09-28

- **Status:** Done — awaiting user commit
- **Objective:** New projection model beats Champion `hold_chase_challenger` on Historical Promotion Gate (2025-26 GW1–38, seed 2024-25, Blended) and adopts.
- **Acceptance:** Candidate in `models/` + catalog row; `commands.evaluate_model_promotion` PASS vs Champion; 2026-27 GW1–5 holdout reported; ruff/pytest/verify green.
- **Issue/Ticket:** none (user goal, chat 2026-09-28)

## Work Packet (SFDBN)

- **Status:** `face_value_challenger` PASS gate (3/3, Δ +1.670, all guardrails improve), `--apply` → Champion. Holdout 2026-27 Δ +5.472 (contaminated). ruff clean, pytest 436 pass, verify 67/0.
- **Files:** `models/face_value_challenger.py`, `tests/test_face_value_challenger.py`, `config/model_selection.json`, `docs/model_name.md`, `docs/adr/0045-champion-face-value-challenger.md`, `docs/research/face-value-challenger/`, `docs/research/INDEX.md`, `docs/agents/current-state.md`, `ROADMAP.md`.
- **Decisions:** ADR 0045. Learned hurdle correction deferred (live path lacks per-GW feature memory). `bonus_arm_challenger` → Catalog.
- **Blocked:** none
- **Next:** User commits; delete this packet in same Checkpoint.

## Todo
- [x] Lane results
- [x] Candidate model + catalog
- [x] Adopt gate + apply
- [x] Docs (ADR, INDEX, current-state)
- [ ] Commit + push; delete packet next Checkpoint

## Blockers / Notes
- `chance_of_playing` terminal in archive features; Champion legacy dependency (zero backtest effect).
- INDEX Eval canon says Blended MAE primary; `promotion.py` uses Blended `top_11_regret` when informative. Pre-existing doc/code mismatch.
