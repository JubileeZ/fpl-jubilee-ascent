# Active Task: Blended eval target (ADR 0044)

- **Status:** Done
- **Objective:** Backtest + promotion score Gameweek Projection vs 50/50 Realized/Process blend; blend primary, both reported guardrails
- **Acceptance:** `--eval_target blend` works in CLI + walkforward; promotion primary on blend with Realized/Process mae hold; new tests green; ruff + full pytest + verify.sh green
- **Issue/Ticket:** ADR 0044

## Work Packet (SFDBN)

- **Status:** In Progress — committing this checkpoint; delete file right after commit
- **Files:** backtesting/process_points.py, backtesting/walkforward.py, backtesting/promotion.py, backtesting/model_evaluation.py, commands/backtest.py, commands/compare_models.py, commands/evaluate_model_promotion.py, models/champion_trust.py, tests, docs/adr/0044, CONTEXT.md, docs/testing/archive-testing.md, docs/research/xp-cross-gw-dispersion
- **Decisions:** Fixed 50/50 all positions; guardrail swing; extend dispersion note; gate replace-with-guardrails; Champion keeps status; trust EmptyDataError hardening (twin sweep)
- **Blocked:** None
- **Next:** Blend-row note extension on background walk-forward completion

## Todo
- [x] Red: blend helper + gate tests
- [x] Green: source edits + compare_models blend + trust hardening
- [x] Verify: ruff, 412 pytest, verify.sh 59/0, 1-GW blend smoke
- [x] Commit code
- [ ] Blend-row note extension on background walk-forward completion

## Blockers / Notes
- None
